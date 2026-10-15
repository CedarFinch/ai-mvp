"""Text-to-SQL 查询结果总结器。"""

from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ....common.config import Settings
from ....integrations.java import JavaPromptClient
from ....integrations.java.text_to_sql_client import SqlExecutionResult
from ....prompts.codes import TEXT_TO_SQL_RESULT_SUMMARY_SYSTEM
from .schemas import ResultSummary


MAX_ROWS_FOR_SUMMARY = 200


class ResultSummarizer:
    """调用大模型，把 SQL rows 总结成结论和前端图表数据。"""

    def __init__(
        self,
        model: ChatOpenAI,
        settings: Settings,
        prompt_client: JavaPromptClient | None = None,
    ) -> None:
        self._prompt_client = prompt_client or JavaPromptClient(settings)
        prompt_code = settings.text_to_sql_result_summary_prompt_code or TEXT_TO_SQL_RESULT_SUMMARY_SYSTEM
        system_prompt = self._prompt_client.get_active_prompt_content(prompt_code)
        safe_system_prompt = _escape_prompt_template_text(system_prompt)
        self._chain = (
            ChatPromptTemplate.from_messages(
                [
                    ("system", safe_system_prompt),
                    (
                        "human",
                        "\n".join(
                            [
                                "用户问题：{question}",
                                "",
                                "执行 SQL：",
                                "{sql}",
                                "",
                                "返回行数：{row_count}",
                                "",
                                "查询结果 rows JSON：",
                                "{rows_json}",
                                "",
                                "指标口径上下文：",
                                "{metric_context}",
                                "",
                                "业务说明上下文：",
                                "{business_context}",
                                "",
                                "Java 查询中心执行细节 JSON：",
                                "{execution_detail_json}",
                            ]
                        ),
                    ),
                ]
            )
            | model.with_structured_output(ResultSummary)
        )

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
        """调用模型分析结果。

        rows 可能很多，发给模型前只截取前 200 行，避免结果集过大拖慢总结节点。
        原始 rows 仍然会在 TextToSqlResponse.rows 返回给前端。
        """

        row_count = len(rows)
        result = self._chain.invoke(
            {
                "question": question,
                "sql": sql or "",
                "row_count": row_count,
                "rows_json": json.dumps(rows[:MAX_ROWS_FOR_SUMMARY], ensure_ascii=False, default=str),
                "metric_context": metric_context,
                "business_context": business_context,
                "execution_detail_json": json.dumps(
                    _execution_detail(sql_execution_result),
                    ensure_ascii=False,
                    default=str,
                ),
            }
        )
        if not isinstance(result, ResultSummary):
            raise TypeError("结果总结模型没有返回 ResultSummary")
        return result


def _execution_detail(result: SqlExecutionResult | None) -> dict[str, object]:
    if result is None:
        return {}
    return {
        "success": result.success,
        "message": result.message,
        "row_count": result.row_count,
        "validation": result.validation,
        "permission": result.permission,
        "explain": result.explain,
    }


def _escape_prompt_template_text(text: str) -> str:
    """平台提示词是普通文本，里面的 JSON 大括号不能被 LangChain 当成变量。"""

    return text.replace("{", "{{").replace("}", "}}")
