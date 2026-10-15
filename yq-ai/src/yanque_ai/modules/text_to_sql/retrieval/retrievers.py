"""Text-to-SQL 用到的知识库检索器。"""

from __future__ import annotations

import logging
import json
import re

from ....common.config import Settings
from ....integrations.bailian.client import BailianClient, RerankResult
from ....integrations.mcp import McpResourceClient
from ...knowledge.vector_store import KnowledgeVectorStore, load_milvus_config
from ..schemas import MetricHit


logger = logging.getLogger(__name__)


class BusinessContextError(RuntimeError):
    """业务说明读取失败，后续不应该继续生成 SQL。"""


class TableCatalogError(RuntimeError):
    """全量表目录读取失败，后续不应该继续选表或生成 SQL。"""


class TableDdlError(RuntimeError):
    """表 DDL 读取失败，后续不应该继续生成 SQL。"""


class TextToSqlMetricRetriever:
    """从 Milvus 指标知识库做 HYBRID 混合检索。"""

    def __init__(
        self,
        settings: Settings,
        vector_store: KnowledgeVectorStore | None = None,
        rerank_client: BailianClient | None = None,
    ) -> None:
        self._settings = settings
        self._vector_store = vector_store or KnowledgeVectorStore(load_milvus_config())
        self._rerank_client = rerank_client

    def retrieve(self, question: str, top_k: int | None = None) -> list[MetricHit]:
        """按用户问题检索相关指标口径。"""

        final_top_k = _limit_top_k(top_k or self._settings.text_to_sql_metric_top_k)
        records = self._vector_store.recall(
            self._settings.text_to_sql_metric_collection,
            question,
            mode="HYBRID",
            top_k=max(_limit_top_k(self._settings.text_to_sql_metric_recall_top_k), final_top_k),
        )
        records = _rerank_records(
            question,
            records,
            final_top_k,
            self._settings,
            self._rerank_client,
        )
        return [
            MetricHit(
                rank=int(record.get("rank") or index + 1),
                score=float(record.get("score") or 0),
                document_code=str(record.get("document_code") or ""),
                document_version=int(record.get("document_version") or 0),
                chunk_index=int(record.get("chunk_index") or 0),
                content=str(record.get("content") or ""),
            )
            for index, record in enumerate(records)
        ]


class TextToSqlBusinessRetriever:
    """根据业务域读取 Bear MCP Resource 里的业务说明。"""

    def __init__(
        self,
        settings: Settings,
        resource_client: McpResourceClient | None = None,
    ) -> None:
        self._settings = settings
        self._resource_client = resource_client or McpResourceClient(settings)

    def retrieve(self, business_domain: str | None) -> str:
        """读取当前业务域对应的业务说明、查询注意事项和口径解释。"""

        domain = (business_domain or "").strip()
        if not domain:
            raise BusinessContextError("未识别到业务域，无法读取业务说明。")

        uri = f"bear://yanque/text-to-sql/business/{domain}"
        try:
            content = self._resource_client.read_text(uri).strip()
        except Exception as exc:
            raise BusinessContextError(f"业务说明 Resource 不存在、未发布或无权限读取：{uri}") from exc
        if not content:
            raise BusinessContextError(f"未读取到业务说明 Resource：{uri}")
        return content


class TextToSqlTableCatalogRetriever:
    """读取 Bear MCP Resource 里的全量轻量表目录。"""

    RESOURCE_URI = "bear://yanque/text-to-sql/table-catalog"

    def __init__(
        self,
        settings: Settings,
        resource_client: McpResourceClient | None = None,
    ) -> None:
        self._settings = settings
        self._resource_client = resource_client or McpResourceClient(settings)

    def retrieve(self) -> str:
        """读取全量表目录。

        这个目录只用于选表，不包含完整 DDL。
        选表完成后，再按表名读取 bear://yanque/text-to-sql/ddl/{table_name}。
        """

        try:
            content = self._resource_client.read_text(self.RESOURCE_URI).strip()
        except Exception as exc:
            raise TableCatalogError(f"表目录 Resource 不存在、未发布或无权限读取：{self.RESOURCE_URI}") from exc
        if not content:
            raise TableCatalogError(f"未读取到表目录 Resource：{self.RESOURCE_URI}")
        return content


class TextToSqlTableDdlRetriever:
    """按选中的表名读取 Bear MCP Resource 里的 DDL JSON。"""

    RESOURCE_URI_PREFIX = "bear://yanque/text-to-sql/ddl"

    def __init__(
        self,
        settings: Settings,
        resource_client: McpResourceClient | None = None,
    ) -> None:
        self._settings = settings
        self._resource_client = resource_client or McpResourceClient(settings)

    def retrieve(self, table_names: list[str]) -> str:
        """读取选中表的 DDL Resource，并组装成后续模型可读的 JSON。"""

        normalized_table_names = _normalize_table_names(table_names)
        if not normalized_table_names:
            raise TableDdlError("没有选中任何表，无法读取 DDL Resource。")

        ddl_items: list[dict] = []
        for table_name in normalized_table_names:
            uri = f"{self.RESOURCE_URI_PREFIX}/{table_name}"
            try:
                content = self._resource_client.read_text(uri).strip()
            except Exception as exc:
                raise TableDdlError(f"表 DDL Resource 不存在、未发布或无权限读取：{uri}") from exc
            if not content:
                raise TableDdlError(f"未读取到表 DDL Resource：{uri}")

            try:
                ddl_items.append(json.loads(content))
            except json.JSONDecodeError as exc:
                raise TableDdlError(f"表 DDL Resource 不是合法 JSON：{uri}") from exc

        return json.dumps({"ddls": ddl_items}, ensure_ascii=False, indent=2)


def _rerank_records(
    question: str,
    records: list[dict],
    top_k: int,
    settings: Settings,
    rerank_client: BailianClient | None,
) -> list[dict]:
    """对召回结果重排，并过滤低相关结果。

    Milvus HYBRID 负责先找候选；rerank 再判断这些候选和用户问题到底有多相关。
    """

    final_top_k = _limit_top_k(top_k)
    if not records:
        return []
    if not settings.text_to_sql_rerank_enabled or rerank_client is None:
        return records[:final_top_k]

    try:
        indexed_documents = [
            (index, content)
            for index, record in enumerate(records)
            if (content := str(record.get("content") or "").strip())
        ]
        if not indexed_documents:
            return []
        rerank_results = rerank_client.rerank(
            question,
            [content for _, content in indexed_documents],
            top_n=len(indexed_documents),
        )
    except Exception:
        logger.warning("Text-to-SQL 检索重排失败，使用原始召回顺序", exc_info=True)
        return records[:final_top_k]

    selected: list[dict] = []
    for rerank_result in rerank_results:
        if not _passes_min_score(rerank_result, settings):
            continue
        if rerank_result.index < 0 or rerank_result.index >= len(indexed_documents):
            continue

        original_index = indexed_documents[rerank_result.index][0]
        record = dict(records[original_index])
        record["score"] = rerank_result.score
        record["rank"] = len(selected) + 1
        selected.append(record)

        if len(selected) >= final_top_k:
            break
    return selected


def _passes_min_score(result: RerankResult, settings: Settings) -> bool:
    """判断重排分数是否达到入模阈值。"""

    return result.score >= settings.text_to_sql_rerank_min_score


def _limit_top_k(top_k: int) -> int:
    """限制 top_k 的范围，避免一次召回太多内容。"""

    return min(max(top_k, 1), 20)


def _normalize_table_names(table_names: list[str]) -> list[str]:
    """清理选表结果，只允许普通数据库表名，避免拼出异常 Resource URI。"""

    normalized_table_names: list[str] = []
    seen: set[str] = set()
    for table_name in table_names:
        normalized = table_name.strip()
        if not re.fullmatch(r"[A-Za-z0-9_]+", normalized):
            raise TableDdlError(f"表名不合法，无法读取 DDL Resource：{table_name}")
        if normalized in seen:
            continue
        seen.add(normalized)
        normalized_table_names.append(normalized)
    return normalized_table_names
