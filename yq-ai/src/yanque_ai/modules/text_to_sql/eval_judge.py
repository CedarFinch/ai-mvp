"""Text-to-SQL 评测裁判。"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .schemas import TextToSqlSemanticJudgeRequest, TextToSqlSemanticJudgeResponse


class TextToSqlSemanticJudge:
    """用大模型判断自然语言结果是否符合样本标准。"""

    def __init__(self, model: ChatOpenAI) -> None:
        self._chain = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "\n".join(
                            [
                                "你是 Text-to-SQL 评测裁判，只判断实际回答是否满足评测标准。",
                                "判断时重点看业务含义是否正确，不要求字面完全一致。",
                                "关键点每行一个；禁用点每行一个。",
                                "如果实际回答命中禁用点，必须判失败。",
                                "如果填写了关键点，关键点没有全部覆盖时应扣分。",
                                "如果没有参考答案也没有关键点，就根据问题和实际回答本身判断回答是否有实质内容。",
                                "score 必须是 0 到 100 的整数，passed 必须等于 score >= min_score 且没有命中禁用点。",
                                "reason 用中文，简短说明主要依据。",
                            ]
                        ),
                    ),
                    (
                        "human",
                        "\n".join(
                            [
                                "原始问题：",
                                "{question}",
                                "",
                                "实际回答：",
                                "{actual_value}",
                                "",
                                "参考答案：",
                                "{reference_answer}",
                                "",
                                "关键点：",
                                "{key_points}",
                                "",
                                "禁用点：",
                                "{forbidden_points}",
                                "",
                                "最低通过分：{min_score}",
                            ]
                        ),
                    ),
                ]
            )
            | model.with_structured_output(TextToSqlSemanticJudgeResponse)
        )

    def judge(self, request: TextToSqlSemanticJudgeRequest) -> TextToSqlSemanticJudgeResponse:
        """调用大模型返回语义断言结果。"""
        result = self._chain.invoke(request.model_dump())
        if not isinstance(result, TextToSqlSemanticJudgeResponse):
            raise TypeError("语义评测模型没有返回 TextToSqlSemanticJudgeResponse")
        passed = result.score >= request.min_score and not result.forbidden_hits
        return result.model_copy(update={"passed": passed})
