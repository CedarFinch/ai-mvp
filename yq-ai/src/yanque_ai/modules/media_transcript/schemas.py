"""视频转写整理接口出入参。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TranscriptUtteranceInput(BaseModel):
    """ASR 生成的一条精简分句。"""

    start_time: int = Field(ge=0, description="分句开始时间，单位毫秒")
    end_time: int = Field(ge=0, description="分句结束时间，单位毫秒")
    text: str = Field(min_length=1, description="ASR 原始分句文字")
    speaker: str | None = Field(default=None, description="ASR 说话人标识")


class TranscriptRefinementRequest(BaseModel):
    """Java 请求大模型整理转写的参数。"""

    video_id: int
    utterances: list[TranscriptUtteranceInput] = Field(min_length=1)


class RefinedUtterance(BaseModel):
    """整理完成后用于页面展示的一条对话。"""

    start_time: int = Field(ge=0, description="对话开始时间，单位毫秒")
    end_time: int = Field(ge=0, description="对话结束时间，单位毫秒")
    text: str = Field(min_length=1, description="整理后的对话文字")
    speaker: str = Field(
        pattern=r"^(HOST|CALLER_[1-9][0-9]*)$",
        description="说话人角色，HOST 表示主播，CALLER_n 表示第 n 位连麦用户",
    )


class TranscriptRefinementModelOutput(BaseModel):
    """LangChain 约束大模型返回的结构。"""

    speaker_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="当前已确认的 ASR speaker 与 HOST/CALLER_n 角色映射",
    )
    utterances: list[RefinedUtterance] = Field(min_length=1)


class TranscriptRefinementResponse(BaseModel):
    """返回给 Java 的最终整理结果。"""

    full_text: str
    utterances: list[RefinedUtterance]
