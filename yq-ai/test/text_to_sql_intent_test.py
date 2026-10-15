"""Text-to-SQL 总图中的意图识别节点测试。"""

from __future__ import annotations

import logging
import json
import unittest
from types import SimpleNamespace

from yanque_ai.integrations.bailian.client import RerankResult
from yanque_ai.integrations.java.text_to_sql_client import SqlExecutionResult
from yanque_ai.modules.text_to_sql.graph import TextToSqlGraph
from yanque_ai.modules.text_to_sql.intent.classifier import DEFAULT_BUSINESS_DOMAINS
from yanque_ai.modules.text_to_sql.nodes import TextToSqlNodes
from yanque_ai.modules.text_to_sql.retrieval import (
    BusinessContextError,
    TableCatalogError,
    TableDdlError,
    TextToSqlBusinessRetriever,
    TextToSqlMetricRetriever,
    TextToSqlTableCatalogRetriever,
    TextToSqlTableDdlRetriever,
)
from yanque_ai.modules.text_to_sql.result_summary import ResultChartData, ResultSummary
from yanque_ai.modules.text_to_sql.schemas import (
    IntentRecognitionResult,
    IntentType,
    MetricHit,
    TextToSqlRequest,
)
from yanque_ai.modules.text_to_sql.sql_generation import SqlGenerationAction, SqlGenerationResult
from yanque_ai.modules.text_to_sql.table_selection import TableSelectionResult


class FakeIntentClassifier:
    """避免测试真实调用大模型。"""

    def __init__(self, result: IntentRecognitionResult | None = None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.called = False

    def classify(
        self,
        question: str,
        *,
        business_domains: list[str] | None = None,
    ) -> IntentRecognitionResult:
        self.called = True
        if self.error:
            raise self.error
        if self.result:
            return self.result
        return IntentRecognitionResult(
            intent=IntentType.GENERAL_CHAT,
            reason="假模型返回普通问答。",
            normalized_question=question,
        )


class FakeMetricRetriever:
    """避免测试真实访问 Milvus。"""

    def __init__(self, error: Exception | None = None) -> None:
        self.called = False
        self.error = error

    def retrieve(self, question: str) -> list[MetricHit]:
        self.called = True
        if self.error:
            raise self.error
        return [
            MetricHit(
                rank=1,
                score=0.88,
                document_code="order_metric",
                document_version=1,
                chunk_index=0,
                content="订单量：统计支付成功订单数。",
            )
        ]


class FakeBusinessRetriever:
    """避免测试真实访问 Bear MCP。"""

    def __init__(self, error: BusinessContextError | None = None) -> None:
        self.called = False
        self.business_domain: str | None = None
        self.error = error

    def retrieve(self, business_domain: str | None) -> str:
        self.called = True
        self.business_domain = business_domain
        if self.error:
            raise self.error
        return "订单业务：支付成功后订单进入有效统计范围。"


class FakeTableCatalogRetriever:
    """避免测试真实访问 Bear MCP 表目录 Resource。"""

    def __init__(self, error: TableCatalogError | None = None) -> None:
        self.called = False
        self.error = error

    def retrieve(self) -> str:
        self.called = True
        if self.error:
            raise self.error
        return '{"tables":[{"table_name":"order_payment","description":"支付订单表"}]}'


class FakeTableSelector:
    """避免测试真实调用选表模型。"""

    def __init__(self, error: Exception | None = None) -> None:
        self.called = False
        self.error = error

    def select_tables(
        self,
        *,
        question: str,
        metric_context: str,
        business_context: str,
        table_catalog_context: str,
    ) -> TableSelectionResult:
        self.called = True
        if self.error:
            raise self.error
        return TableSelectionResult(
            selected_tables=["order_payment"],
            reason="订单量指标需要使用支付订单表。",
        )


class FakeTableDdlRetriever:
    """避免测试真实访问 Bear MCP DDL Resource。"""

    def __init__(self, error: TableDdlError | None = None) -> None:
        self.called = False
        self.table_names: list[str] = []
        self.calls: list[list[str]] = []
        self.error = error

    def retrieve(self, table_names: list[str]) -> str:
        self.called = True
        self.table_names = table_names
        self.calls.append(table_names)
        if self.error:
            raise self.error
        return (
            '{"ddls":[{"table_name":"order_payment","ddl":"CREATE TABLE `order_payment` (...)",'
            '"columns":['
            '{"name":"order_no","query_policy":"ALLOW"},'
            '{"name":"status","query_policy":"ALLOW"},'
            '{"name":"order_amount","query_policy":"ALLOW"},'
            '{"name":"student_phone","query_policy":"MASK"},'
            '{"name":"unique_order_no","query_policy":"DENY"}'
            ']}]}'
        )


class FakeSqlGenerator:
    """避免测试真实调用 SQL 生成模型。"""

    def __init__(
        self,
        result: SqlGenerationResult | None = None,
        results: list[SqlGenerationResult] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.called = False
        self.result = result
        self.results = results or []
        self.call_count = 0
        self.error = error
        self.table_ddl_context = ""
        self.clarification_context = ""

    def generate_sql(
        self,
        *,
        question: str,
        metric_context: str,
        business_context: str,
        table_ddl_context: str,
        clarification_context: str = "",
    ) -> SqlGenerationResult:
        self.called = True
        self.call_count += 1
        self.table_ddl_context = table_ddl_context
        self.clarification_context = clarification_context
        if self.error:
            raise self.error
        if self.results:
            index = min(self.call_count - 1, len(self.results) - 1)
            return self.results[index]
        if self.result:
            return self.result
        return SqlGenerationResult(
            action=SqlGenerationAction.SQL_READY,
            sql="SELECT COUNT(DISTINCT order_no) AS order_count FROM order_payment WHERE status = 'SUCCESS'",
            reason="订单量按支付成功订单数统计。",
        )


class FakeSqlExecutor:
    """避免 Graph 测试真实调用 Java 查询中心。"""

    def __init__(
        self,
        result: SqlExecutionResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.called = False
        self.sql = ""
        self.table_ddl_context = ""
        self.user_id: str | None = None
        self.roles: list[str] | None = None
        self.business_domain: str | None = None
        self.result = result
        self.error = error

    def execute_sql(
        self,
        *,
        sql: str,
        table_ddl_context: str,
        user_id: str | None = None,
        roles: list[str] | None = None,
        business_domain: str | None = None,
        max_rows: int = 100,
    ) -> SqlExecutionResult:
        self.called = True
        self.sql = sql
        self.table_ddl_context = table_ddl_context
        self.user_id = user_id
        self.roles = roles
        self.business_domain = business_domain
        if self.error:
            raise self.error
        if self.result:
            return self.result
        return SqlExecutionResult(
            success=True,
            message="SQL执行成功。",
            sql=sql,
            rows=[{"order_count": 12}],
            row_count=1,
            validation={"valid": True, "reason": "SQL校验通过。"},
            permission={"allowed": True, "reason": "数据权限校验通过。"},
        )


class FakeResultSummarizer:
    """避免 Graph 测试真实调用结果总结模型。"""

    def __init__(self) -> None:
        self.called = False
        self.question = ""
        self.sql: str | None = None
        self.rows: list[dict[str, object]] = []

    def summarize(
        self,
        *,
        question: str,
        sql: str | None,
        rows: list[dict[str, object]],
        sql_execution_result: SqlExecutionResult | None = None,
        metric_context: str = "",
        business_context: str = "",
    ) -> ResultSummary:
        self.called = True
        self.question = question
        self.sql = sql
        self.rows = rows
        return ResultSummary(
            conclusion="本次查询返回 1 行结果，order_count 为 12。",
            data_description="按订单口径统计的一行指标结果。",
            key_findings=["order_count 为 12。"],
            cautions=[],
            chart_type="stat",
            chart_title="订单量",
            chart_reason="结果是单行指标，适合用指标卡展示。",
            chart_data=ResultChartData(chart_type="stat", y_fields=["order_count"], rows=rows),
            echarts_option={},
            basis=[f"SQL 返回 {len(rows)} 行结果。", f"执行 SQL：{sql}"],
            sql=sql,
            row_count=len(rows),
        )


class FakeVectorStore:
    """避免检索测试真实访问 Milvus。"""

    def __init__(self, records: list[dict]) -> None:
        self.records = records
        self.top_k = 0

    def recall(self, collection_name: str, query: str, mode: str, top_k: int) -> list[dict]:
        self.top_k = top_k
        return self.records[:top_k]


class FakeRerankClient:
    """避免检索测试真实调用 rerank 模型。"""

    def rerank(self, query: str, documents: list[str], top_n: int) -> list[RerankResult]:
        return [
            RerankResult(index=1, score=0.95),
            RerankResult(index=2, score=0.72),
            RerankResult(index=0, score=0.40),
        ]


class FakeResourceClient:
    """避免业务资源测试真实访问 Bear MCP。"""

    def __init__(
        self,
        content: str = "订单业务说明：支付成功订单才进入统计。",
        contents_by_uri: dict[str, str] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.uri = ""
        self.content = content
        self.contents_by_uri = contents_by_uri or {}
        self.error = error

    def read_text(self, uri: str) -> str:
        self.uri = uri
        if self.error:
            raise self.error
        if uri in self.contents_by_uri:
            return self.contents_by_uri[uri]
        return self.content


def build_test_graph(
    classifier: FakeIntentClassifier,
    metric_retriever: FakeMetricRetriever | None = None,
    business_retriever: FakeBusinessRetriever | None = None,
    table_catalog_retriever: FakeTableCatalogRetriever | None = None,
    table_ddl_retriever: FakeTableDdlRetriever | None = None,
    table_selector: FakeTableSelector | None = None,
    sql_generator: FakeSqlGenerator | None = None,
    sql_executor: FakeSqlExecutor | None = None,
    result_summarizer: FakeResultSummarizer | None = None,
) -> TextToSqlGraph:
    """组装测试图，避免每个用例重复传依赖。"""

    return TextToSqlGraph(
        TextToSqlNodes(
            classifier,
            metric_retriever or FakeMetricRetriever(),
            business_retriever or FakeBusinessRetriever(),
            table_catalog_retriever or FakeTableCatalogRetriever(),
            table_ddl_retriever or FakeTableDdlRetriever(),
            table_selector or FakeTableSelector(),
            sql_generator or FakeSqlGenerator(),
            sql_executor or FakeSqlExecutor(),
            result_summarizer or FakeResultSummarizer(),
        )
    )


class TextToSqlIntentTest(unittest.TestCase):
    def test_default_business_domains_match_existing_resources(self) -> None:
        self.assertIn("order", DEFAULT_BUSINESS_DOMAINS)
        self.assertNotIn("payment", DEFAULT_BUSINESS_DOMAINS)
        self.assertNotIn("refund", DEFAULT_BUSINESS_DOMAINS)

    def test_model_classifies_data_operation_then_rejects(self) -> None:
        classifier = FakeIntentClassifier(
            IntentRecognitionResult(
                intent=IntentType.DATA_OPERATION,
                reason="用户要求修改订单状态。",
                normalized_question="把昨天失败的订单改成成功",
            )
        )
        metric_retriever = FakeMetricRetriever()
        business_retriever = FakeBusinessRetriever()
        table_catalog_retriever = FakeTableCatalogRetriever()
        table_ddl_retriever = FakeTableDdlRetriever()
        table_selector = FakeTableSelector()
        sql_generator = FakeSqlGenerator()
        sql_executor = FakeSqlExecutor()
        graph = build_test_graph(
            classifier,
            metric_retriever,
            business_retriever,
            table_catalog_retriever,
            table_ddl_retriever,
            table_selector,
            sql_generator,
            sql_executor,
        )

        response = graph.run(TextToSqlRequest(question="把昨天失败的订单改成成功", user_id="u1"))

        self.assertEqual(response.intent, IntentType.DATA_OPERATION)
        self.assertEqual(response.action, "REJECT_OPERATION")
        self.assertTrue(classifier.called)
        self.assertFalse(metric_retriever.called)
        self.assertFalse(business_retriever.called)
        self.assertFalse(table_catalog_retriever.called)
        self.assertFalse(table_ddl_retriever.called)
        self.assertFalse(table_selector.called)
        self.assertFalse(sql_generator.called)
        self.assertFalse(sql_executor.called)

    def test_model_classifies_data_query(self) -> None:
        classifier = FakeIntentClassifier(
            IntentRecognitionResult(
                intent=IntentType.DATA_QUERY,
                reason="用户询问经营数据。",
                business_domain="order",
                normalized_question="昨天经营情况怎么样",
            )
        )
        metric_retriever = FakeMetricRetriever()
        business_retriever = FakeBusinessRetriever()
        table_catalog_retriever = FakeTableCatalogRetriever()
        table_ddl_retriever = FakeTableDdlRetriever()
        table_selector = FakeTableSelector()
        sql_generator = FakeSqlGenerator()
        sql_executor = FakeSqlExecutor()
        result_summarizer = FakeResultSummarizer()
        graph = build_test_graph(
            classifier,
            metric_retriever,
            business_retriever,
            table_catalog_retriever,
            table_ddl_retriever,
            table_selector,
            sql_generator,
            sql_executor,
            result_summarizer,
        )

        response = graph.run(TextToSqlRequest(question="昨天经营情况怎么样", user_id="9", roles=["ORDER_VIEWER"]))

        self.assertEqual(response.intent, IntentType.DATA_QUERY)
        self.assertEqual(response.action, "ENTER_TEXT_TO_SQL")
        self.assertTrue(classifier.called)
        self.assertTrue(metric_retriever.called)
        self.assertTrue(business_retriever.called)
        self.assertTrue(table_catalog_retriever.called)
        self.assertTrue(table_selector.called)
        self.assertTrue(table_ddl_retriever.called)
        self.assertTrue(sql_generator.called)
        self.assertTrue(sql_executor.called)
        self.assertTrue(result_summarizer.called)
        self.assertEqual(result_summarizer.rows, [{"order_count": 12}])
        self.assertEqual(response.business_domain, "order")
        self.assertEqual(business_retriever.business_domain, "order")
        self.assertEqual(response.metric_hits[0].document_code, "order_metric")
        self.assertIn("订单量", response.metric_context)
        self.assertIn("订单业务", response.business_context)
        self.assertIn("order_payment", response.table_catalog_context)
        self.assertEqual(response.selected_tables, ["order_payment"])
        self.assertEqual(table_ddl_retriever.table_names, ["order_payment"])
        self.assertIn("order_payment", response.table_ddl_context)
        self.assertIn("order_payment", sql_generator.table_ddl_context)
        self.assertEqual(sql_executor.sql, response.sql)
        self.assertIn("order_payment", sql_executor.table_ddl_context)
        self.assertEqual(sql_executor.user_id, "9")
        self.assertEqual(sql_executor.roles, ["ORDER_VIEWER"])
        self.assertEqual(sql_executor.business_domain, "order")
        self.assertEqual(response.executed_sql, response.sql)
        self.assertEqual(response.rows, [{"order_count": 12}])
        self.assertEqual(response.answer, "本次查询返回 1 行结果，order_count 为 12。")
        self.assertEqual(response.chart_type, "stat")
        self.assertEqual(response.chart_data.y_fields, ["order_count"])
        self.assertEqual(response.result_summary_detail.sql, response.executed_sql)
        self.assertIn("执行 SQL", response.result_summary_detail.basis[1])
        self.assertEqual(response.result_summary_detail.key_findings, ["order_count 为 12。"])
        self.assertEqual(response.query_trace.original_question, "昨天经营情况怎么样")
        self.assertEqual(response.query_trace.generated_sql, response.sql)
        self.assertEqual(response.query_trace.executed_sql, response.executed_sql)
        self.assertEqual(response.query_trace.row_count, 1)
        self.assertEqual(response.query_trace.validation["valid"], True)
        self.assertTrue(response.sql_execution_detail.success)
        self.assertIn("COUNT", response.sql)
        self.assertEqual(response.sql_generation_detail.action, SqlGenerationAction.SQL_READY)
        self.assertEqual(response.sql_generation_detail.reason, "订单量按支付成功订单数统计。")
        self.assertEqual(response.table_selection_detail.reason, "订单量指标需要使用支付订单表。")

    def test_graph_continues_when_metric_retrieval_fails(self) -> None:
        classifier = FakeIntentClassifier(
            IntentRecognitionResult(
                intent=IntentType.DATA_QUERY,
                reason="用户询问经营数据。",
                business_domain="order",
                normalized_question="昨天订单量是多少",
            )
        )
        metric_retriever = FakeMetricRetriever(error=RuntimeError("metric collection missing"))
        sql_executor = FakeSqlExecutor()
        graph = build_test_graph(classifier, metric_retriever=metric_retriever, sql_executor=sql_executor)

        response = graph.run(TextToSqlRequest(question="昨天订单量是多少"))

        self.assertIsNone(response.error_message)
        self.assertTrue(metric_retriever.called)
        self.assertTrue(sql_executor.called)
        self.assertEqual(response.metric_hits, [])
        self.assertEqual(response.metric_context, "未检索到相关指标口径。")

    def test_metric_retriever_reranks_and_filters_low_score_hits(self) -> None:
        settings = SimpleNamespace(
            text_to_sql_metric_collection="text_to_sql_metrics",
            text_to_sql_metric_top_k=2,
            text_to_sql_metric_recall_top_k=3,
            text_to_sql_rerank_enabled=True,
            text_to_sql_rerank_min_score=0.6,
        )
        vector_store = FakeVectorStore(
            [
                {
                    "rank": 1,
                    "score": 0.80,
                    "document_code": "metric_a",
                    "document_version": 1,
                    "chunk_index": 0,
                    "content": "不太相关的指标。",
                },
                {
                    "rank": 2,
                    "score": 0.78,
                    "document_code": "metric_b",
                    "document_version": 1,
                    "chunk_index": 1,
                    "content": "订单量指标。",
                },
                {
                    "rank": 3,
                    "score": 0.75,
                    "document_code": "metric_c",
                    "document_version": 1,
                    "chunk_index": 2,
                    "content": "支付金额指标。",
                },
            ]
        )
        retriever = TextToSqlMetricRetriever(
            settings,
            vector_store=vector_store,
            rerank_client=FakeRerankClient(),
        )

        hits = retriever.retrieve("昨天订单量和支付金额是多少")

        self.assertEqual(vector_store.top_k, 3)
        self.assertEqual([hit.document_code for hit in hits], ["metric_b", "metric_c"])
        self.assertEqual([hit.rank for hit in hits], [1, 2])
        self.assertEqual([hit.score for hit in hits], [0.95, 0.72])

    def test_business_retriever_reads_bear_mcp_resource_by_domain(self) -> None:
        settings = SimpleNamespace()
        resource_client = FakeResourceClient()
        retriever = TextToSqlBusinessRetriever(settings, resource_client=resource_client)

        context = retriever.retrieve("order")

        self.assertEqual(resource_client.uri, "bear://yanque/text-to-sql/business/order")
        self.assertIn("订单业务说明", context)

    def test_business_retriever_raises_when_domain_missing(self) -> None:
        settings = SimpleNamespace()
        retriever = TextToSqlBusinessRetriever(settings, resource_client=FakeResourceClient())

        with self.assertRaises(BusinessContextError):
            retriever.retrieve(None)

    def test_business_retriever_raises_when_resource_empty(self) -> None:
        settings = SimpleNamespace()
        resource_client = FakeResourceClient(content="")
        retriever = TextToSqlBusinessRetriever(settings, resource_client=resource_client)

        with self.assertRaises(BusinessContextError):
            retriever.retrieve("order")

    def test_business_retriever_wraps_resource_read_error(self) -> None:
        settings = SimpleNamespace()
        resource_client = FakeResourceClient(error=RuntimeError("resource not found"))
        retriever = TextToSqlBusinessRetriever(settings, resource_client=resource_client)

        with self.assertRaisesRegex(BusinessContextError, "业务说明 Resource 不存在"):
            retriever.retrieve("payment")

    def test_table_catalog_retriever_reads_bear_mcp_resource(self) -> None:
        settings = SimpleNamespace()
        resource_client = FakeResourceClient(content='{"tables":[]}')
        retriever = TextToSqlTableCatalogRetriever(settings, resource_client=resource_client)

        context = retriever.retrieve()

        self.assertEqual(resource_client.uri, "bear://yanque/text-to-sql/table-catalog")
        self.assertEqual(context, '{"tables":[]}')

    def test_table_catalog_retriever_raises_when_resource_empty(self) -> None:
        settings = SimpleNamespace()
        retriever = TextToSqlTableCatalogRetriever(settings, resource_client=FakeResourceClient(content=""))

        with self.assertRaises(TableCatalogError):
            retriever.retrieve()

    def test_table_ddl_retriever_reads_selected_table_resources(self) -> None:
        settings = SimpleNamespace()
        resource_client = FakeResourceClient(
            contents_by_uri={
                "bear://yanque/text-to-sql/ddl/order_payment": (
                    '{"table_name":"order_payment","ddl":"CREATE TABLE `order_payment` (...)"}'
                )
            }
        )
        retriever = TextToSqlTableDdlRetriever(settings, resource_client=resource_client)

        context = retriever.retrieve(["order_payment"])

        self.assertEqual(resource_client.uri, "bear://yanque/text-to-sql/ddl/order_payment")
        self.assertEqual(json.loads(context)["ddls"][0]["table_name"], "order_payment")

    def test_table_ddl_retriever_raises_when_resource_empty(self) -> None:
        settings = SimpleNamespace()
        retriever = TextToSqlTableDdlRetriever(settings, resource_client=FakeResourceClient(content=""))

        with self.assertRaises(TableDdlError):
            retriever.retrieve(["order_payment"])

    def test_graph_stops_when_business_context_missing(self) -> None:
        classifier = FakeIntentClassifier(
            IntentRecognitionResult(
                intent=IntentType.DATA_QUERY,
                reason="用户询问经营数据。",
                business_domain="order",
                normalized_question="昨天订单量是多少",
            )
        )
        metric_retriever = FakeMetricRetriever()
        business_retriever = FakeBusinessRetriever(
            error=BusinessContextError("未读取到业务说明 Resource：bear://yanque/text-to-sql/business/order")
        )
        table_catalog_retriever = FakeTableCatalogRetriever()
        graph = build_test_graph(classifier, metric_retriever, business_retriever, table_catalog_retriever)

        response = graph.run(TextToSqlRequest(question="昨天订单量是多少"))

        self.assertEqual(response.action, "ENTER_TEXT_TO_SQL")
        self.assertEqual(
            response.error_message,
            "未读取到业务说明 Resource：bear://yanque/text-to-sql/business/order",
        )
        self.assertEqual(response.message, response.error_message)
        self.assertEqual(response.business_context, "")
        self.assertTrue(metric_retriever.called)
        self.assertTrue(business_retriever.called)
        self.assertTrue(table_catalog_retriever.called)

    def test_graph_stops_when_table_catalog_missing(self) -> None:
        classifier = FakeIntentClassifier(
            IntentRecognitionResult(
                intent=IntentType.DATA_QUERY,
                reason="用户询问经营数据。",
                business_domain="order",
                normalized_question="昨天订单量是多少",
            )
        )
        metric_retriever = FakeMetricRetriever()
        business_retriever = FakeBusinessRetriever()
        table_catalog_retriever = FakeTableCatalogRetriever(
            error=TableCatalogError("未读取到表目录 Resource：bear://yanque/text-to-sql/table-catalog")
        )
        graph = build_test_graph(classifier, metric_retriever, business_retriever, table_catalog_retriever)

        response = graph.run(TextToSqlRequest(question="昨天订单量是多少"))

        self.assertEqual(response.action, "ENTER_TEXT_TO_SQL")
        self.assertEqual(
            response.error_message,
            "未读取到表目录 Resource：bear://yanque/text-to-sql/table-catalog",
        )
        self.assertEqual(response.message, response.error_message)
        self.assertEqual(response.table_catalog_context, "")
        self.assertTrue(metric_retriever.called)
        self.assertTrue(business_retriever.called)
        self.assertTrue(table_catalog_retriever.called)

    def test_graph_stops_when_table_ddl_missing(self) -> None:
        classifier = FakeIntentClassifier(
            IntentRecognitionResult(
                intent=IntentType.DATA_QUERY,
                reason="用户询问经营数据。",
                business_domain="order",
                normalized_question="昨天订单量是多少",
            )
        )
        table_ddl_retriever = FakeTableDdlRetriever(
            error=TableDdlError("未读取到表 DDL Resource：bear://yanque/text-to-sql/ddl/order_payment")
        )
        sql_generator = FakeSqlGenerator()
        graph = build_test_graph(
            classifier,
            table_ddl_retriever=table_ddl_retriever,
            sql_generator=sql_generator,
        )

        response = graph.run(TextToSqlRequest(question="昨天订单量是多少"))

        self.assertEqual(response.action, "ENTER_TEXT_TO_SQL")
        self.assertEqual(
            response.error_message,
            "未读取到表 DDL Resource：bear://yanque/text-to-sql/ddl/order_payment",
        )
        self.assertEqual(response.message, response.error_message)
        self.assertEqual(response.selected_tables, ["order_payment"])
        self.assertEqual(response.table_ddl_context, "")
        self.assertTrue(table_ddl_retriever.called)
        self.assertFalse(sql_generator.called)

    def test_graph_stops_after_table_selection_error_before_reading_ddl(self) -> None:
        classifier = FakeIntentClassifier(
            IntentRecognitionResult(
                intent=IntentType.DATA_QUERY,
                reason="用户询问经营数据。",
                business_domain="order",
                normalized_question="昨天订单量是多少",
            )
        )
        table_selector = FakeTableSelector(error=RuntimeError("model timeout"))
        table_ddl_retriever = FakeTableDdlRetriever()
        graph = build_test_graph(
            classifier,
            table_ddl_retriever=table_ddl_retriever,
            table_selector=table_selector,
        )

        logging.getLogger("yanque_ai.modules.text_to_sql.nodes").disabled = True
        try:
            response = graph.run(TextToSqlRequest(question="昨天订单量是多少"))
        finally:
            logging.getLogger("yanque_ai.modules.text_to_sql.nodes").disabled = False

        self.assertEqual(response.error_message, "选表失败，请稍后重试。")
        self.assertEqual(response.selected_tables, [])
        self.assertEqual(response.table_ddl_context, "")
        self.assertTrue(table_selector.called)
        self.assertFalse(table_ddl_retriever.called)

    def test_graph_stops_when_sql_generation_fails(self) -> None:
        classifier = FakeIntentClassifier(
            IntentRecognitionResult(
                intent=IntentType.DATA_QUERY,
                reason="用户询问经营数据。",
                business_domain="order",
                normalized_question="昨天订单量是多少",
            )
        )
        sql_generator = FakeSqlGenerator(error=RuntimeError("model timeout"))
        sql_executor = FakeSqlExecutor()
        graph = build_test_graph(
            classifier,
            sql_generator=sql_generator,
            sql_executor=sql_executor,
        )

        logging.getLogger("yanque_ai.modules.text_to_sql.nodes").disabled = True
        try:
            response = graph.run(TextToSqlRequest(question="昨天订单量是多少"))
        finally:
            logging.getLogger("yanque_ai.modules.text_to_sql.nodes").disabled = False

        self.assertEqual(response.error_message, "生成 SQL 失败，请稍后重试。")
        self.assertEqual(response.sql, "")
        self.assertIsNone(response.executed_sql)
        self.assertIsNone(response.sql_generation_detail)
        self.assertTrue(sql_generator.called)
        self.assertFalse(sql_executor.called)

    def test_graph_retrieves_more_ddl_when_sql_generator_requests_it(self) -> None:
        classifier = FakeIntentClassifier(
            IntentRecognitionResult(
                intent=IntentType.DATA_QUERY,
                reason="用户询问经营数据。",
                business_domain="order",
                normalized_question="按课程产品统计昨天订单量",
            )
        )
        table_ddl_retriever = FakeTableDdlRetriever()
        sql_generator = FakeSqlGenerator(
            results=[
                SqlGenerationResult(
                    action=SqlGenerationAction.NEED_TABLE_DDL,
                    sql=None,
                    reason="需要产品表 DDL 才能按课程产品分组。",
                    needed_table_names=["order_product"],
                ),
                SqlGenerationResult(
                    action=SqlGenerationAction.SQL_READY,
                    sql=(
                        "SELECT op.product_id, COUNT(DISTINCT op.order_no) AS order_count "
                        "FROM order_payment op GROUP BY op.product_id"
                    ),
                    reason="补充产品表 DDL 后可以生成 SQL。",
                ),
            ]
        )
        sql_executor = FakeSqlExecutor()
        graph = build_test_graph(
            classifier,
            table_ddl_retriever=table_ddl_retriever,
            sql_generator=sql_generator,
            sql_executor=sql_executor,
        )

        response = graph.run(TextToSqlRequest(question="按课程产品统计昨天订单量"))

        self.assertIsNone(response.error_message)
        self.assertEqual(response.sql_generation_detail.action, SqlGenerationAction.SQL_READY)
        self.assertEqual(response.selected_tables, ["order_payment", "order_product"])
        self.assertEqual(table_ddl_retriever.calls[0], ["order_payment"])
        self.assertEqual(table_ddl_retriever.calls[1], ["order_payment", "order_product"])
        self.assertEqual(sql_generator.call_count, 2)
        self.assertTrue(sql_executor.called)
        self.assertEqual(response.executed_sql, response.sql)

    def test_graph_stops_when_sql_generator_keeps_requesting_more_ddl(self) -> None:
        classifier = FakeIntentClassifier(
            IntentRecognitionResult(
                intent=IntentType.DATA_QUERY,
                reason="用户询问经营数据。",
                business_domain="order",
                normalized_question="按课程产品统计昨天订单量",
            )
        )
        table_ddl_retriever = FakeTableDdlRetriever()
        sql_generator = FakeSqlGenerator(
            results=[
                SqlGenerationResult(
                    action=SqlGenerationAction.NEED_TABLE_DDL,
                    sql=None,
                    reason="缺少产品表 DDL。",
                    needed_table_names=["order_product"],
                ),
                SqlGenerationResult(
                    action=SqlGenerationAction.NEED_TABLE_DDL,
                    sql=None,
                    reason="缺少学生产品表 DDL。",
                    needed_table_names=["student_product"],
                ),
                SqlGenerationResult(
                    action=SqlGenerationAction.NEED_TABLE_DDL,
                    sql=None,
                    reason="仍然缺少预支付订单表 DDL。",
                    needed_table_names=["prepay_order"],
                ),
            ]
        )
        sql_executor = FakeSqlExecutor()
        graph = build_test_graph(
            classifier,
            table_ddl_retriever=table_ddl_retriever,
            sql_generator=sql_generator,
            sql_executor=sql_executor,
        )

        response = graph.run(TextToSqlRequest(question="按课程产品统计昨天订单量"))

        self.assertEqual(response.error_message, "SQL 生成多次要求补充表 DDL，已停止继续重试。")
        self.assertEqual(sql_generator.call_count, 3)
        self.assertEqual(len(table_ddl_retriever.calls), 3)
        self.assertEqual(response.selected_tables, ["order_payment", "order_product", "student_product"])
        self.assertFalse(sql_executor.called)

    def test_graph_interrupts_and_resumes_when_sql_generator_asks_clarification(self) -> None:
        classifier = FakeIntentClassifier(
            IntentRecognitionResult(
                intent=IntentType.DATA_QUERY,
                reason="用户询问经营数据。",
                business_domain="order",
                normalized_question="统计订单量",
            )
        )
        sql_generator = FakeSqlGenerator(
            results=[
                SqlGenerationResult(
                    action=SqlGenerationAction.ASK_CLARIFICATION,
                    sql=None,
                    reason="订单量口径不明确。",
                    clarification_question="订单量按支付成功订单数，还是全部创建订单数？",
                ),
                SqlGenerationResult(
                    action=SqlGenerationAction.SQL_READY,
                    sql=(
                        "SELECT COUNT(DISTINCT op.order_no) AS order_count "
                        "FROM order_payment op WHERE op.status = 'SUCCESS'"
                    ),
                    reason="用户澄清按支付成功订单数统计。",
                ),
            ]
        )
        sql_executor = FakeSqlExecutor()
        graph = build_test_graph(
            classifier,
            sql_generator=sql_generator,
            sql_executor=sql_executor,
        )

        paused_response = graph.run(TextToSqlRequest(question="统计订单量"))

        self.assertTrue(paused_response.need_clarification)
        self.assertIsNotNone(paused_response.conversation_id)
        self.assertEqual(paused_response.message, "生成 SQL 前需要补充信息。")
        self.assertEqual(paused_response.clarification_question, "订单量按支付成功订单数，还是全部创建订单数？")
        self.assertEqual(paused_response.clarification_reason, "订单量口径不明确。")
        self.assertFalse(sql_executor.called)

        final_response = graph.run(
            TextToSqlRequest(
                question="按支付成功订单数",
                conversation_id=paused_response.conversation_id,
                clarification_answer="按支付成功订单数",
            )
        )

        self.assertFalse(final_response.need_clarification)
        self.assertIsNone(final_response.error_message)
        self.assertEqual(final_response.question, "统计订单量")
        self.assertEqual(final_response.conversation_id, paused_response.conversation_id)
        self.assertEqual(final_response.clarification_answer, "按支付成功订单数")
        self.assertEqual(final_response.query_trace.clarification_answer, "按支付成功订单数")
        self.assertIn("按支付成功订单数", sql_generator.clarification_context)
        self.assertEqual(sql_generator.call_count, 2)
        self.assertTrue(sql_executor.called)
        self.assertEqual(final_response.sql_generation_detail.action, SqlGenerationAction.SQL_READY)

    def test_graph_stops_when_java_query_center_rejects_sql(self) -> None:
        classifier = FakeIntentClassifier(
            IntentRecognitionResult(
                intent=IntentType.DATA_QUERY,
                reason="用户询问经营数据。",
                business_domain="order",
                normalized_question="昨天订单量是多少",
            )
        )
        sql_executor = FakeSqlExecutor(
            result=SqlExecutionResult(
                success=False,
                message="SQL不能使用SELECT *或表.*。",
                rows=[],
                row_count=0,
                validation={"valid": False, "reason": "SQL不能使用SELECT *或表.*。"},
            )
        )
        graph = build_test_graph(classifier, sql_executor=sql_executor)

        response = graph.run(TextToSqlRequest(question="昨天订单量是多少"))

        self.assertEqual(response.error_message, "SQL不能使用SELECT *或表.*。")
        self.assertEqual(response.message, response.error_message)
        self.assertTrue(sql_executor.called)
        self.assertEqual(response.rows, [])
        self.assertIsNone(response.answer)
        self.assertIsNone(response.result_summary_detail)
        self.assertFalse(response.sql_execution_detail.success)

    def test_model_failure_falls_back_to_clarification(self) -> None:
        classifier = FakeIntentClassifier(error=RuntimeError("model timeout"))
        metric_retriever = FakeMetricRetriever()
        business_retriever = FakeBusinessRetriever()
        table_catalog_retriever = FakeTableCatalogRetriever()
        graph = build_test_graph(classifier, metric_retriever, business_retriever, table_catalog_retriever)

        logging.getLogger("yanque_ai.modules.text_to_sql.nodes").disabled = True
        try:
            response = graph.run(TextToSqlRequest(question="最近怎么样"))
        finally:
            logging.getLogger("yanque_ai.modules.text_to_sql.nodes").disabled = False

        self.assertEqual(response.intent, IntentType.AMBIGUOUS)
        self.assertEqual(response.action, "ASK_CLARIFICATION")
        self.assertTrue(response.intent_detail.clarification_question)
        self.assertFalse(metric_retriever.called)
        self.assertFalse(business_retriever.called)
        self.assertFalse(table_catalog_retriever.called)

    def test_ambiguous_intent_must_have_clarification_question(self) -> None:
        classifier = FakeIntentClassifier(error=ValueError("AMBIGUOUS 意图必须包含 clarification_question"))
        metric_retriever = FakeMetricRetriever()
        business_retriever = FakeBusinessRetriever()
        table_catalog_retriever = FakeTableCatalogRetriever()
        graph = build_test_graph(classifier, metric_retriever, business_retriever, table_catalog_retriever)

        logging.getLogger("yanque_ai.modules.text_to_sql.nodes").disabled = True
        try:
            response = graph.run(TextToSqlRequest(question="订单"))
        finally:
            logging.getLogger("yanque_ai.modules.text_to_sql.nodes").disabled = False

        self.assertEqual(response.intent, IntentType.AMBIGUOUS)
        self.assertEqual(response.action, "ASK_CLARIFICATION")
        self.assertEqual(response.intent_detail.clarification_question, "意图识别结果不完整，请稍后重试。")
        self.assertFalse(metric_retriever.called)
        self.assertFalse(business_retriever.called)
        self.assertFalse(table_catalog_retriever.called)


if __name__ == "__main__":
    unittest.main()
