"""基于 LangChain 的 SQL 生成器。"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ....common.config import Settings
from ....integrations.java import JavaPromptClient
from ....prompts.codes import TEXT_TO_SQL_GENERATE_SQL_SYSTEM
from .schemas import SqlGenerationResult


class LangChainSqlGenerator:
    """调用模型，判断是否可以生成 SQL，并返回结构化结果。"""

    def __init__(
        self,
        model: ChatOpenAI,
        settings: Settings,
        prompt_client: JavaPromptClient | None = None,
    ) -> None:
        self._prompt_client = prompt_client or JavaPromptClient(settings)
        prompt_code = settings.text_to_sql_generate_sql_prompt_code or TEXT_TO_SQL_GENERATE_SQL_SYSTEM
        system_prompt = self._prompt_client.get_active_prompt_content(prompt_code)
        self._chain = (
            ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    (
                        "human",
                        "\n".join(
                            [
                                "用户问题：{question}",
                                "",
                                "指标上下文：",
                                "{metric_context}",
                                "",
                                "业务说明：",
                                "{business_context}",
                                "",
                                "用户补充的澄清信息：",
                                "{clarification_context}",
                                "",
                                "选中表 DDL：",
                                "{table_ddl_context}",
                            ]
                        ),
                    ),
                ]
            )
            | model.with_structured_output(SqlGenerationResult)
        )

    def generate_sql(
        self,
        *,
        question: str,
        metric_context: str,
        business_context: str,
        table_ddl_context: str,
        clarification_context: str = "",
    ) -> SqlGenerationResult:
        """根据问题和上下文生成 SQL，或说明还缺什么。"""

        result = self._chain.invoke(
            {
                "question": question,
                "metric_context": metric_context,
                "business_context": business_context,
                "clarification_context": clarification_context or "暂无。",
                "table_ddl_context": table_ddl_context,
            }
        )
        if not isinstance(result, SqlGenerationResult):
            raise TypeError("SQL 生成模型没有返回 SqlGenerationResult")
        return result
