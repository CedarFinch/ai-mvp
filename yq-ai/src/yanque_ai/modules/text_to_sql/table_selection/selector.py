"""基于 LangChain 的选表器。"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ....common.config import Settings
from ....integrations.java import JavaPromptClient
from ....prompts.codes import TEXT_TO_SQL_SELECT_TABLES_SYSTEM
from .schemas import TableSelectionResult


class LangChainTableSelector:
    """调用模型，从全量轻量表目录中选择后续要读取 DDL 的表。"""

    def __init__(
        self,
        model: ChatOpenAI,
        settings: Settings,
        prompt_client: JavaPromptClient | None = None,
    ) -> None:
        self._prompt_client = prompt_client or JavaPromptClient(settings)
        prompt_code = settings.text_to_sql_select_tables_prompt_code or TEXT_TO_SQL_SELECT_TABLES_SYSTEM
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
                                "全量表目录：",
                                "{table_catalog_context}",
                            ]
                        ),
                    ),
                ]
            )
            | model.with_structured_output(TableSelectionResult)
        )

    def select_tables(
        self,
        *,
        question: str,
        metric_context: str,
        business_context: str,
        table_catalog_context: str,
    ) -> TableSelectionResult:
        """根据问题和三类上下文选择表名。"""

        result = self._chain.invoke(
            {
                "question": question,
                "metric_context": metric_context,
                "business_context": business_context,
                "table_catalog_context": table_catalog_context,
            }
        )
        if not isinstance(result, TableSelectionResult):
            raise TypeError("选表模型没有返回 TableSelectionResult")
        return result
