"""通用数据模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token 用量，Java 存进消息表的 tokens 字段做成本统计。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ErrorResponse(BaseModel):
    code: str = Field(description="错误码，便于 Java 侧分支处理")
    message: str = Field(description="面向排查的错误说明")

