from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from yanque_ai.integrations.java.text_to_sql_client import JavaTextToSqlClient
from yanque_ai.modules.text_to_sql.intent.schemas import IntentRecognitionResult, IntentType
from yanque_ai.modules.text_to_sql.nodes import SqlExecutor, TextToSqlNodes
from yanque_ai.modules.text_to_sql.result_summary import ResultChartData, ResultSummary
from yanque_ai.modules.text_to_sql.schemas import TextToSqlRequest


class JavaTextToSqlClientTest(unittest.TestCase):
    def test_text_to_sql_node_posts_to_java_query_center(self) -> None:
        server = _TestHttpServer()
        server.start()
        try:
            nodes = TextToSqlNodes(
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                SqlExecutor(JavaTextToSqlClient(_Settings(server.base_url))),
                _FakeResultSummarizer(),
            )
            update = nodes.execute_sql(
                {
                    "request": TextToSqlRequest(
                        question="昨天订单量是多少",
                        user_id="9",
                        roles=["ADVISOR"],
                    ),
                    "intent_result": IntentRecognitionResult(
                        intent=IntentType.DATA_QUERY,
                        reason="查询订单数据。",
                        business_domain="order",
                        normalized_question="昨天订单量是多少",
                    ),
                    "sql": "select count(distinct order_no) from order_payment where status = 'SUCCESS'",
                    "table_ddl_context": '{"table_name":"order_payment","columns":[{"name":"order_no"}]}',
                }
            )
        finally:
            server.stop()

        self.assertEqual(update["rows"], [{"order_count": 12}])
        self.assertEqual(
            update["executed_sql"],
            "select count(distinct order_no) from order_payment where status = 'SUCCESS'",
        )
        self.assertTrue(update["sql_execution_result"].success)
        self.assertEqual(update["sql_execution_result"].row_count, 1)
        self.assertEqual(server.path, "/yq-admin/internal/ai/text-to-sql/sql/execute")
        self.assertEqual(server.body["userId"], 9)
        self.assertEqual(server.body["roleCodes"], ["ADVISOR"])
        self.assertEqual(server.body["businessDomain"], "order")
        self.assertEqual(server.body["maxRows"], 100)
        self.assertIn("order_payment", server.body["tableDdlContext"])


class _Settings:
    def __init__(self, base_url: str) -> None:
        self.yanque_admin_base_url = base_url
        self.prompt_query_timeout_seconds = 2.0


class _FakeResultSummarizer:
    def summarize(
        self,
        *,
        question: str,
        sql: str | None,
        rows: list[dict[str, object]],
        sql_execution_result=None,
        metric_context: str = "",
        business_context: str = "",
    ) -> ResultSummary:
        return ResultSummary(
            conclusion="查询成功。",
            data_description="单行指标结果。",
            key_findings=["order_count 为 12。"],
            cautions=[],
            chart_type="stat",
            chart_title="订单量",
            chart_reason="单行指标。",
            chart_data=ResultChartData(chart_type="stat", y_fields=["order_count"], rows=rows),
            echarts_option={},
            basis=[f"执行 SQL：{sql}"],
            sql=sql,
            row_count=len(rows),
        )


class _TestHttpServer:
    def __init__(self) -> None:
        self.path = ""
        self.body: dict[str, object] = {}
        self._server = HTTPServer(("127.0.0.1", 0), self._handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self.base_url = f"http://127.0.0.1:{self._server.server_port}"

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                parent.path = self.path
                parent.body = json.loads(self.rfile.read(length).decode("utf-8"))
                response = {
                    "code": 200,
                    "message": "操作成功",
                    "data": {
                        "success": True,
                        "message": "SQL执行成功。",
                        "sql": parent.body["sql"],
                        "rows": [{"order_count": 12}],
                        "rowCount": 1,
                        "validation": {"valid": True},
                        "permission": {"allowed": True},
                        "explain": {"allowed": True},
                    },
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode("utf-8"))

            def log_message(self, format: str, *args: object) -> None:
                return

        return Handler


if __name__ == "__main__":
    unittest.main()
