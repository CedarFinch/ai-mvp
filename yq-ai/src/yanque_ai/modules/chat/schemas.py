"""聊天模块出入参定义。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """一条历史消息，对应消息表的一行。"""

    role: Role = Field(description="user 用户，assistant AI")
    content: str = Field(description="消息内容")


class ChatRequest(BaseModel):
    """Java 调用 AI 服务的请求体。"""

    question: str = Field(min_length=1, max_length=8000, description="学生本次的提问")
    history: list[ChatMessage] = Field(
        default_factory=list, description="历史消息，按时间正序，不含本次提问"
    )
    summary: str | None = Field(
        default=None, max_length=8000, description="历史对话摘要，对应会话表的 summary"
    )


class SummaryRequest(BaseModel):
    """Java 压缩对话时传给 AI 服务的请求体。"""

    summary: str | None = Field(default=None, max_length=8000, description="旧摘要，可以为空")
    messages: list[ChatMessage] = Field(description="这次需要压缩进摘要的消息")


class SummaryResponse(BaseModel):
    """压缩后的新摘要。"""

    summary: str = Field(description="合并旧摘要和本批消息之后的新摘要")


