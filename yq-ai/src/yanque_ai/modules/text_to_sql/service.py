"""Text-to-SQL 编排服务。"""

from __future__ import annotations

from ...common.config import Settings
from ...integrations.bailian.client import BailianClient
from ...integrations.java.text_to_sql_client import JavaTextToSqlClient
from ...integrations.langchain_model import build_chat_model
from .graph import TextToSqlGraph
from .intent import LangChainIntentClassifier
from .eval_judge import TextToSqlSemanticJudge
from .nodes import SqlExecutor, TextToSqlNodes
from .retrieval import (
    TextToSqlBusinessRetriever,
    TextToSqlMetricRetriever,
    TextToSqlTableCatalogRetriever,
    TextToSqlTableDdlRetriever,
)
from .result_summary import ResultSummarizer
from .schemas import (
    MetricHit,
    TextToSqlMetricSearchRequest,
    TextToSqlMetricSearchResponse,
    TextToSqlRequest,
    TextToSqlResponse,
    TextToSqlSemanticJudgeRequest,
    TextToSqlSemanticJudgeResponse,
)
from .sql_generation import LangChainSqlGenerator
from .table_selection import LangChainTableSelector


class TextToSqlService:
    """Text-to-SQL 服务入口。"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        model = build_chat_model(settings, temperature=0.0)
        rerank_client = BailianClient(settings) if settings.text_to_sql_rerank_enabled else None
        self._metric_retriever = TextToSqlMetricRetriever(settings, rerank_client=rerank_client)
        self._graph = TextToSqlGraph(
            TextToSqlNodes(
                LangChainIntentClassifier(model, settings),
                self._metric_retriever,
                TextToSqlBusinessRetriever(settings),
                TextToSqlTableCatalogRetriever(settings),
                TextToSqlTableDdlRetriever(settings),
                LangChainTableSelector(model, settings),
                LangChainSqlGenerator(model, settings),
                SqlExecutor(JavaTextToSqlClient(settings)),
                ResultSummarizer(model, settings),
            )
        )
        self._semantic_judge = TextToSqlSemanticJudge(model)

    def query(self, request: TextToSqlRequest) -> TextToSqlResponse:
        """执行 Text-to-SQL 总流程。"""
        return self._graph.run(request)

    def search_metrics(self, request: TextToSqlMetricSearchRequest) -> TextToSqlMetricSearchResponse:
        """从 Milvus 指标知识库检索相关指标口径。"""
        records = self._metric_retriever.retrieve(request.query, top_k=request.top_k)
        return TextToSqlMetricSearchResponse(
            query=request.query,
            collection_name=self._settings.text_to_sql_metric_collection,
            top_k=request.top_k,
            records=records,
            metric_context=_build_metric_context(records),
        )

    def judge_semantic(self, request: TextToSqlSemanticJudgeRequest) -> TextToSqlSemanticJudgeResponse:
        """执行评测样本里的自然语言语义断言。"""
        return self._semantic_judge.judge(request)


def _build_metric_context(metric_hits: list[MetricHit]) -> str:
    """把指标召回结果拼成模型可读上下文。"""

    if not metric_hits:
        return "未检索到相关指标口径。"
    return "\n\n".join(
        f"[{hit.rank}] 文档：{hit.document_code}，chunk：{hit.chunk_index}\n{hit.content}"
        for hit in metric_hits
    )
