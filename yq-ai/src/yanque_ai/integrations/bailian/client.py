"""阿里云百炼模型客户端。"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass

import openai
from openai import OpenAI

from ...common.config import Settings
from ...common.errors import (
    UpstreamAuthError,
    UpstreamCallError,
    UpstreamRateLimitError,
    UpstreamTimeoutError,
)
from ...common.schemas import TokenUsage


logger = logging.getLogger(__name__)


@dataclass
class StreamChunk:
    """模型流式返回的一片数据。"""

    delta: str = ""
    done: bool = False
    finish_reason: str | None = None
    usage: TokenUsage | None = None


@dataclass(frozen=True)
class RerankResult:
    """重排序返回的一条结果。"""

    index: int
    score: float


def _to_usage(raw: object) -> TokenUsage:
    """把 OpenAI SDK 的 usage 对象转成本项目自己的 TokenUsage。"""
    if raw is None:
        return TokenUsage()

    return TokenUsage(
        prompt_tokens=getattr(raw, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(raw, "completion_tokens", 0) or 0,
        total_tokens=getattr(raw, "total_tokens", 0) or 0,
    )


def _translate(exc: Exception) -> Exception:
    """把 OpenAI SDK 异常翻译成项目统一错误。"""
    if isinstance(exc, openai.APITimeoutError):
        return UpstreamTimeoutError()
    if isinstance(exc, openai.RateLimitError):
        return UpstreamRateLimitError()
    if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return UpstreamAuthError()
    if isinstance(exc, openai.APIStatusError):
        return UpstreamCallError(f"模型返回错误 {exc.status_code}：{exc.message}")
    if isinstance(exc, openai.APIConnectionError):
        return UpstreamCallError("无法连接模型服务，请检查网络或 base_url")
    return UpstreamCallError(f"模型调用失败：{exc}")


class BailianClient:
    """百炼流式问答客户端。"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
        )
        self._rerank_client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.chat_rag_rerank_base_url,
        )
        logger.info(
            "百炼客户端就绪 base_url=%s model=%s key=%s",
            settings.base_url,
            settings.model,
            settings.masked_api_key,
        )

    def close(self) -> None:
        """释放底层 HTTP 连接。"""
        self._client.close()
        self._rerank_client.close()

    def _build_request(self, messages: list[dict[str, str]], model: str | None = None) -> dict:
        """生成百炼接口请求参数。"""
        params: dict = {
            "model": model or self._settings.model,
            "messages": messages,
            "temperature": self._settings.temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        if self._settings.max_tokens is not None:
            params["max_tokens"] = self._settings.max_tokens

        return params

    def stream_chat(self, messages: list[dict[str, str]], model: str | None = None) -> Iterator[StreamChunk]:
        """调用百炼流式问答接口。"""
        finish_reason: str | None = None
        usage = TokenUsage()

        try:
            request = self._build_request(messages, model)
            stream = self._client.chat.completions.create(**request)

            for chunk in stream:
                if chunk.usage is not None:
                    usage = _to_usage(chunk.usage)

                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                if choice.finish_reason:
                    finish_reason = choice.finish_reason

                delta = getattr(choice.delta, "content", None)
                if delta:
                    yield StreamChunk(delta=delta)
        except Exception as exc:
            logger.warning("模型流式调用失败：%s", exc)
            raise _translate(exc) from exc

        yield StreamChunk(done=True, finish_reason=finish_reason, usage=usage)

    def summarize(self, messages: list[dict[str, str]]) -> str:
        """调用模型生成对话摘要。"""
        try:
            response = self._client.chat.completions.create(
                model=self._settings.model,
                messages=messages,
                temperature=0.2,
            )
            content = response.choices[0].message.content or ""
            return content.strip()
        except Exception as exc:
            logger.warning("模型摘要调用失败：%s", exc)
            raise _translate(exc) from exc

    def rerank(self, query: str, documents: list[str], top_n: int) -> list[RerankResult]:
        """调用 qwen3-rerank 对候选文档重排。"""
        if not documents:
            return []

        try:
            response = self._rerank_client.post(
                "/reranks",
                body={
                    "model": self._settings.chat_rag_rerank_model,
                    "query": query,
                    "documents": documents,
                    "top_n": min(max(top_n, 1), len(documents)),
                },
                cast_to=object,
            )
            return _parse_rerank_response(response)
        except Exception as exc:
            logger.warning("重排序调用失败：%s", exc)
            raise _translate(exc) from exc


def _parse_rerank_response(response: object) -> list[RerankResult]:
    """兼容 dict 和 OpenAI SDK 对象两种响应形态。"""
    results = _get_response_value(response, "results")
    if results is None:
        output = _get_response_value(response, "output") or {}
        results = _get_response_value(output, "results")
    if not results:
        return []

    parsed: list[RerankResult] = []
    for item in results:
        index = _get_response_value(item, "index")
        score = _get_response_value(item, "relevance_score")
        if score is None:
            score = _get_response_value(item, "score")
        if index is None or score is None:
            continue
        parsed.append(RerankResult(index=int(index), score=float(score)))
    return parsed


def _get_response_value(source: object, key: str) -> object:
    """从 dict 或 SDK 响应对象中读取字段。"""
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)
