"""意图识别的 LangChain 模型分类器。"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ....common.config import Settings
from ....integrations.java import JavaPromptClient
from ....prompts.codes import TEXT_TO_SQL_INTENT_SYSTEM
from .schemas import IntentRecognitionResult, IntentType


DEFAULT_BUSINESS_DOMAINS = [
    "order",
    "student",
    "teaching",
    "learning",
    "homework",
    "exam",
    "ai",
]


class LangChainIntentClassifier:
    """用 LangChain 调模型，返回结构化意图。

    这个类只负责“怎么问模型”和“怎么拿到结构化结果”。
    它不决定下一步走哪个 node，路由判断放在 graph.py 里。
    """

    def __init__(
        self,
        model: ChatOpenAI,
        settings: Settings,
        prompt_client: JavaPromptClient | None = None,
    ) -> None:
        self._settings = settings
        self._prompt_client = prompt_client or JavaPromptClient(settings)
        prompt_code = settings.text_to_sql_intent_prompt_code or TEXT_TO_SQL_INTENT_SYSTEM
        system_prompt = self._prompt_client.get_active_prompt_content(prompt_code)
        # with_structured_output 会让模型尽量直接返回 IntentRecognitionResult。
        # 这样代码更短，也不用手写 JSON 解析逻辑。
        self._chain = (
            ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    ("human", "用户问题：{question}"),
                ]
            )
            | model.with_structured_output(IntentRecognitionResult)
        )

    def classify(
        self,
        question: str,
        *,
        business_domains: list[str] | None = None,
    ) -> IntentRecognitionResult:
        """识别一个问题的意图。

        business_domains 用来告诉模型当前系统支持哪些业务范围，不传就使用课程 MVP 默认值。
        """

        domains = business_domains or DEFAULT_BUSINESS_DOMAINS
        result = self._chain.invoke(
            {
                "question": question,
                "business_domains": "、".join(domains),
            }
        )
        # 正常情况下会返回 IntentRecognitionResult。这里再判断一次，避免异常输出继续往后走。
        if not isinstance(result, IntentRecognitionResult):
            raise TypeError("意图识别模型没有返回 IntentRecognitionResult")
        return self._check_result(result)

    def _check_result(self, result: IntentRecognitionResult) -> IntentRecognitionResult:
        """检查模型返回的意图识别结果是否完整。

        这个检查放在分类器里，nodes.py 就只需要关心“调用分类器”和“根据结果路由”。
        """

        if result.intent == IntentType.AMBIGUOUS and not result.clarification_question:
            raise ValueError("AMBIGUOUS 意图必须包含 clarification_question")
        return result
