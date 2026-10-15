"""使用 LangChain 整理 ASR 对话。"""

from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ...common.config import Settings
from ...integrations.java import JavaPromptClient
from ...prompts.codes import MEDIA_TRANSCRIPT_REFINEMENT_SYSTEM
from .schemas import (
    RefinedUtterance,
    TranscriptRefinementModelOutput,
    TranscriptUtteranceInput,
)


class LangChainTranscriptRefiner:
    """调用大模型完成说话人归类和文字整理。"""

    def __init__(
        self,
        model: ChatOpenAI,
        settings: Settings,
        prompt_client: JavaPromptClient | None = None,
    ) -> None:
        prompt = (prompt_client or JavaPromptClient(settings)).get_active_prompt_content(
            MEDIA_TRANSCRIPT_REFINEMENT_SYSTEM
        )
        self._chain = (
            ChatPromptTemplate.from_messages(
                [
                    ("system", _escape_prompt_template_text(prompt)),
                    (
                        "human",
                        """当前正在顺序整理第 {batch_number}/{total_batches} 批对话。

已确认的 ASR speaker 角色映射：
{speaker_mapping_json}

上一批末尾的对话，仅用于衔接上下文，不要在本批结果中重复返回：
{previous_context_json}

当前批次 ASR 分句：
{utterances_json}

请只返回当前批次的整理结果。已有角色映射不得修改；遇到新的 speaker 时，继续分配新的 CALLER_n，并在 speaker_mapping 中返回完整映射。""",
                    ),
                ]
            )
            | model.with_structured_output(TranscriptRefinementModelOutput)
        )

    def refine(
        self,
        utterances: list[TranscriptUtteranceInput],
        *,
        speaker_mapping: dict[str, str] | None = None,
        previous_context: list[RefinedUtterance] | None = None,
        batch_number: int = 1,
        total_batches: int = 1,
    ) -> TranscriptRefinementModelOutput:
        """整理当前批次，并使用上一批上下文保持角色和语义连续。"""
        result = self._chain.invoke(
            {
                "batch_number": batch_number,
                "total_batches": total_batches,
                "speaker_mapping_json": _to_json(speaker_mapping or {}),
                "previous_context_json": _to_json(
                    [item.model_dump() for item in previous_context or []]
                ),
                "utterances_json": json.dumps(
                    [item.model_dump(exclude_none=True) for item in utterances],
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            }
        )
        if not isinstance(result, TranscriptRefinementModelOutput):
            raise TypeError("转写整理模型没有返回 TranscriptRefinementModelOutput")
        return result


def _escape_prompt_template_text(text: str) -> str:
    """数据库提示词是普通文本，避免其中的大括号被当作模板变量。"""
    return text.replace("{", "{{").replace("}", "}}")


def _to_json(value: object) -> str:
    """生成紧凑 JSON，减少批次间上下文占用的 token。"""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
