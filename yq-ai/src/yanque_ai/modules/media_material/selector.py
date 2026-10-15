"""使用 LangChain 从完整对话中筛选高价值视频片段。"""

from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ...common.config import Settings
from ...integrations.java import JavaPromptClient
from ...prompts.codes import MEDIA_MATERIAL_SEGMENT_SYSTEM
from .schemas import MaterialSegment, MaterialSegmentResponse


class LangChainMaterialSegmentSelector:
    """一次读取完整对话，直接返回最终素材方案。"""

    def __init__(
        self,
        model: ChatOpenAI,
        settings: Settings,
        prompt_client: JavaPromptClient | None = None,
    ) -> None:
        system_prompt = (prompt_client or JavaPromptClient(settings)).get_active_prompt_content(
            MEDIA_MATERIAL_SEGMENT_SYSTEM
        )
        safe_system_prompt = _escape_prompt_template_text(system_prompt)
        self._chain = (
            ChatPromptTemplate.from_messages(
                [
                    ("system", safe_system_prompt),
                    (
                        "human",
                        """下面是当前视频的完整整理后对话。

片段时长范围：{min_duration_seconds}～{max_duration_seconds} 秒。
整段视频最多返回 {max_segments} 条最有价值的片段，普通闲聊可以不返回。
请直接在全局范围内比较、去重和择优；宁缺毋滥，不要为了凑数量选择普通内容。
utterance_no 是全视频中的稳定分句编号，只能使用输入中存在的编号。

完整对话：
{utterances_json}""",
                    ),
                ]
            )
            | model.with_structured_output(MaterialSegmentResponse)
        )

    def select_segments(
        self,
        utterances: list[dict],
        *,
        min_duration_seconds: int,
        max_duration_seconds: int,
        max_segments: int,
    ) -> list[MaterialSegment]:
        """把完整对话交给模型并返回最终选择。"""
        result = self._chain.invoke(
            {
                "min_duration_seconds": min_duration_seconds,
                "max_duration_seconds": max_duration_seconds,
                "max_segments": max_segments,
                "utterances_json": _to_json(utterances),
            }
        )
        if not isinstance(result, MaterialSegmentResponse):
            raise TypeError("素材分段模型没有返回 MaterialSegmentResponse")
        return result.segments


def _escape_prompt_template_text(text: str) -> str:
    """数据库提示词是普通文本，避免大括号被当作模板变量。"""
    return text.replace("{", "{{").replace("}", "}}")


def _to_json(value: object) -> str:
    """生成紧凑 JSON，控制长视频的 token 占用。"""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
