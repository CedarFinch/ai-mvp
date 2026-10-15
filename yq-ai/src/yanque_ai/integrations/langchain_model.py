"""LangChain 模型工厂。"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from ..common.config import Settings


def build_chat_model(
    settings: Settings,
    *,
    temperature: float | None = None,
    model: str | None = None,
    enable_thinking: bool | None = None,
) -> ChatOpenAI:
    """创建接入百炼 OpenAI 兼容接口的 LangChain ChatModel。"""
    extra_body = None
    if enable_thinking is not None:
        extra_body = {"enable_thinking": enable_thinking}

    return ChatOpenAI(
        model=model or settings.model,
        api_key=settings.api_key,
        base_url=settings.base_url,
        temperature=settings.temperature if temperature is None else temperature,
        max_tokens=settings.max_tokens,
        timeout=settings.timeout_seconds,
        max_retries=settings.max_retries,
        extra_body=extra_body,
    )
