"""提示词测试接口出入参。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PromptTestRequest(BaseModel):
    """Java 调用 Python 执行提示词测试的请求体。"""

    system_prompt: str = Field(min_length=1, description="系统提示词内容")
    user_prompt: str = Field(min_length=1, description="用户提示词内容")
    variables: dict[str, str] = Field(default_factory=dict, description="用户提示词变量")
    model: str = Field(min_length=1, description="测试模型")
