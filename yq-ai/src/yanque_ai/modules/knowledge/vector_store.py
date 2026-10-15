"""Milvus 知识库 Collection 管理。"""

from __future__ import annotations

import os
import re
import json
from dataclasses import dataclass

from llama_index.core import Document, Settings
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core.schema import MetadataMode
from pymilvus import DataType, MilvusClient

from .hybrid_store import HybridSearchStore


@dataclass(frozen=True)
class MilvusKnowledgeConfig:
    """Milvus 知识库 Collection 配置。"""

    uri: str
    token: str | None
    db_name: str
    dense_dim: int
    dense_metric_type: str
    sparse_metric_type: str
    embedding_api_key: str
    embedding_base_url: str
    embedding_model: str
    embedding_batch_size: int


def load_milvus_config() -> MilvusKnowledgeConfig:
    """从环境变量读取 Milvus 配置。"""
    return MilvusKnowledgeConfig(
        uri=os.getenv("MILVUS_URI", "http://124.223.194.220:19530"),
        token=os.getenv("MILVUS_TOKEN") or None,
        db_name=os.getenv("MILVUS_DB_NAME", "default"),
        dense_dim=int(os.getenv("MILVUS_DENSE_VECTOR_DIM", "1024")),
        dense_metric_type=os.getenv("MILVUS_DENSE_METRIC_TYPE", "COSINE"),
        sparse_metric_type=os.getenv("MILVUS_SPARSE_METRIC_TYPE", "BM25"),
        embedding_api_key=os.getenv("DASHSCOPE_API_KEY", "").strip(),
        embedding_base_url=_build_embedding_base_url(),
        embedding_model=os.getenv("BAILIAN_EMBEDDING_MODEL", "text-embedding-v4").strip()
        or "text-embedding-v4",
        embedding_batch_size=int(os.getenv("BAILIAN_EMBEDDING_BATCH_SIZE", "10")),
    )


def _build_embedding_base_url() -> str:
    base_url = os.getenv("BAILIAN_BASE_URL")
    if base_url:
        return base_url.rstrip("/")
    workspace_id = os.getenv("BAILIAN_WORKSPACE_ID")
    if workspace_id:
        return f"https://{workspace_id}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    return "https://dashscope.aliyuncs.com/compatible-mode/v1"


def build_collection_name(code: str) -> str:
    """直接使用知识库编码作为 Milvus Collection 名称。"""
    safe_code = re.sub(r"[^a-z0-9_]", "_", code.lower()).strip("_")
    if not safe_code:
        raise ValueError("知识库编码不能为空")
    return safe_code


class KnowledgeVectorStore:
    """负责创建和删除知识库对应的 Milvus Collection。"""

    def __init__(self, config: MilvusKnowledgeConfig) -> None:
        self.config = config
        self.hybrid_store = HybridSearchStore(config)

    def create_collection(self, collection_name: str) -> None:
        """创建包含稠密向量和 BM25 稀疏向量的 Collection；已存在则直接复用。"""
        client = self._client()
        if client.has_collection(collection_name=collection_name):
            self._validate_collection_schema(client, collection_name)
            return

        schema = MilvusClient.create_schema(
            auto_id=False,
            enable_dynamic_field=False,
        )
        schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=128)
        schema.add_field("document_code", DataType.VARCHAR, max_length=64)
        schema.add_field("document_version", DataType.INT64)
        schema.add_field("chunk_index", DataType.INT64)
        self.hybrid_store.add_vector_fields(schema)
        index_params = self.hybrid_store.prepare_index_params()
        client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params,
        )

    def index_document(self, collection_name: str, payload, document_text: str) -> int:
        """按文档配置切分后写入 Milvus。

        普通知识文档适合按 Markdown 标题切分；指标、表结构这类结构化知识
        更适合整体入库，避免召回时只拿到半截口径。
        """
        file_type = (payload.file_type or "").lower()
        strategy = (payload.chunk_strategy or "").upper()
        if strategy == "MARKDOWN":
            if file_type != "md":
                raise ValueError("MARKDOWN 切分策略只支持 md 文件")
            texts = self._split_markdown(document_text, payload.document_code)
        elif strategy == "NONE":
            texts = [self._normalize_single_document_text(document_text, file_type)]
        elif strategy == "BY_ITEM":
            if file_type != "json":
                raise ValueError("BY_ITEM 切分策略只支持 json 文件")
            texts = self._split_json_by_item(document_text)
        else:
            raise ValueError("切分策略不合法")

        texts = [text for text in texts if text]
        if not texts:
            return 0

        return self._index_texts(collection_name, payload, texts)

    def index_markdown_document(self, collection_name: str, payload, markdown_text: str) -> int:
        """兼容旧调用：按 Markdown 结构切分并入库。"""
        payload.file_type = "md"
        payload.chunk_strategy = "MARKDOWN"
        return self.index_document(collection_name, payload, markdown_text)

    def _index_texts(self, collection_name: str, payload, texts: list[str]) -> int:
        """把已经切好的文本块写入 Milvus。"""
        self.create_collection(collection_name)
        self.delete_document_vectors(collection_name, payload.document_code)

        embeddings = self.hybrid_store.embed_documents(texts)
        rows = [
            {
                "id": f"{payload.document_code}_v{payload.document_version}_{index}",
                "document_code": payload.document_code,
                "document_version": payload.document_version,
                "chunk_index": index,
                "text": text,
                "dense_vector": embeddings[index],
            }
            for index, text in enumerate(texts)
        ]
        self._client().insert(collection_name=collection_name, data=rows)
        return len(texts)

    def _split_markdown(self, markdown_text: str, document_code: str) -> list[str]:
        """使用 LlamaIndex 按 Markdown 标题结构切分普通文档。"""
        Settings.llm = None
        document = Document(text=markdown_text, id_=document_code)
        nodes = MarkdownNodeParser().get_nodes_from_documents([document])
        return [
            text
            for text in (node.get_content(metadata_mode=MetadataMode.NONE).strip() for node in nodes)
            if text
        ]

    def _normalize_single_document_text(self, document_text: str, file_type: str) -> str:
        """整体入库时，JSON 会格式化一下，MD 保持原文。"""
        text = document_text.strip()
        if file_type != "json":
            return text
        return json.dumps(json.loads(text), ensure_ascii=False, indent=2)

    def _split_json_by_item(self, document_text: str) -> list[str]:
        """把 JSON 数组切成多条知识；每个对象仍然保持完整结构。"""
        data = json.loads(document_text)
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and isinstance(data.get("items"), list):
            items = data["items"]
        else:
            raise ValueError("BY_ITEM 策略要求 JSON 顶层是数组，或包含 items 数组")
        return [
            json.dumps(item, ensure_ascii=False, indent=2)
            for item in items
        ]

    def query_document_chunks(
        self,
        collection_name: str,
        document_code: str,
        document_version: int,
        page_num: int,
        page_size: int,
    ) -> list[dict]:
        """从 Milvus 查询指定文档当前版本的 chunk 列表。"""
        start = (page_num - 1) * page_size
        end = start + page_size
        rows = self._query_document_chunk_rows(
            collection_name,
            document_code,
            document_version,
            output_fields=["text", "chunk_index"],
            chunk_index_start=start,
            chunk_index_end=end,
        )
        return [self._to_chunk_item(row) for row in rows]

    def get_document_chunk_detail(
        self,
        collection_name: str,
        document_code: str,
        document_version: int,
        chunk_index: int,
    ) -> dict | None:
        """从 Milvus 查询指定 chunk 的完整文本。"""
        rows = self._query_document_chunk_rows(
            collection_name,
            document_code,
            document_version,
            chunk_index=chunk_index,
            output_fields=["text", "chunk_index"],
        )
        if not rows:
            return None
        row = rows[0]
        text = row.get("text") or ""
        return {
            "chunk_index": int(row.get("chunk_index") or chunk_index),
            "content": text,
            "word_count": self._count_words(text),
            "char_count": len(text),
        }

    def _query_document_chunk_rows(
        self,
        collection_name: str,
        document_code: str,
        document_version: int,
        output_fields: list[str],
        chunk_index: int | None = None,
        chunk_index_start: int | None = None,
        chunk_index_end: int | None = None,
    ) -> list[dict]:
        """按文档编码、版本和 chunk 范围查询 Milvus 行，并按 chunk_index 升序返回。"""
        client = self._client()
        if not client.has_collection(collection_name=collection_name):
            raise RuntimeError(f"Milvus Collection {collection_name} 不存在")

        filters = [
            f'document_code == "{document_code}"',
            f"document_version == {document_version}",
        ]
        if chunk_index is not None:
            filters.append(f"chunk_index == {chunk_index}")
            limit = 1
        else:
            if chunk_index_start is not None:
                filters.append(f"chunk_index >= {chunk_index_start}")
            if chunk_index_end is not None:
                filters.append(f"chunk_index < {chunk_index_end}")
            if chunk_index_start is not None and chunk_index_end is not None:
                limit = max(1, chunk_index_end - chunk_index_start)
            else:
                limit = 16384

        rows = client.query(
            collection_name=collection_name,
            filter=" and ".join(filters),
            output_fields=output_fields,
            limit=limit,
        )
        return sorted(rows, key=lambda row: int(row.get("chunk_index") or 0))

    def _to_chunk_item(self, row: dict) -> dict:
        """把 Milvus 原始行转换成前端展示需要的 chunk 摘要。"""
        text = row.get("text") or ""
        return {
            "chunk_index": int(row.get("chunk_index") or 0),
            "content_preview": self._preview_text(text),
            "word_count": self._count_words(text),
            "char_count": len(text),
        }

    def _preview_text(self, text: str) -> str:
        """生成压缩换行后的 chunk 预览文本。"""
        preview = re.sub(r"\s+", " ", text).strip()
        if len(preview) <= 160:
            return preview
        return preview[:160] + "..."

    def _count_words(self, text: str) -> int:
        """按去除空白后的字符数统计中文友好的字数。"""
        return len(re.sub(r"\s+", "", text))

    def delete_document_vectors(self, collection_name: str, document_code: str) -> bool:
        """删除指定文档编码在 Collection 中的全部向量；不存在时视为成功。"""
        client = self._client()
        if not client.has_collection(collection_name=collection_name):
            return False
        client.delete(
            collection_name=collection_name,
            filter=f'document_code == "{document_code}"',
        )
        return True

    def recall(self, collection_name: str, query: str, mode: str, top_k: int) -> list[dict]:
        """按召回模式从 Milvus 检索知识库 chunk。"""
        client = self._client()
        if not client.has_collection(collection_name=collection_name):
            raise RuntimeError(f"Milvus Collection {collection_name} 不存在")

        hits = self.hybrid_store.search(
            collection_name,
            query,
            mode,
            top_k,
            ["document_code", "document_version", "chunk_index", "text"],
        )

        return [self._to_recall_item(index + 1, hit) for index, hit in enumerate(hits)]

    def _to_recall_item(self, rank: int, hit: dict) -> dict:
        """把 Milvus hit 转成召回测试展示对象。"""
        entity = hit.get("entity") or {}
        text = entity.get("text") or hit.get("text") or ""
        return {
            "rank": rank,
            "score": float(hit.get("distance") or hit.get("score") or 0),
            "document_code": entity.get("document_code") or hit.get("document_code") or "",
            "document_version": int(entity.get("document_version") or hit.get("document_version") or 0),
            "chunk_index": int(entity.get("chunk_index") or hit.get("chunk_index") or 0),
            "content": text,
            "content_preview": self._preview_text(text),
            "word_count": self._count_words(text),
        }

    def drop_collection(self, collection_name: str) -> bool:
        """删除知识库 Collection；不存在时直接视为成功。"""
        client = self._client()
        if not client.has_collection(collection_name=collection_name):
            return False
        client.drop_collection(collection_name=collection_name)
        return True

    def _client(self) -> MilvusClient:
        """兼容知识库现有调用，客户端创建由公共层负责。"""
        return self.hybrid_store.client()

    def _validate_collection_schema(self, client: MilvusClient, collection_name: str) -> None:
        """确认已有 Collection 字段满足干净业务字段入库要求。"""
        description = client.describe_collection(collection_name=collection_name)
        field_names = {field["name"] for field in description.get("fields", [])}
        required_fields = {
            "id",
            "document_code",
            "document_version",
            "chunk_index",
            "text",
            "dense_vector",
            "sparse_vector",
        }
        missing_fields = sorted(required_fields - field_names)
        if missing_fields:
            raise RuntimeError(
                f"Milvus Collection {collection_name} 缺少字段 {missing_fields}，请删除后重新创建知识库向量表"
            )
