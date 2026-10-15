"""提示词测试业务。"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator

from ...common.errors import AIServiceError
from ...integrations.bailian.client import BailianClient
from ...prompts import render_prompt
from .schemas import PromptTestRequest


logger = logging.getLogger(__name__)


class PromptTestService:
    """组装测试提示词并流式调用模型。"""

    def __init__(self, client: BailianClient) -> None:
        self._client = client

    def stream_test(self, request: PromptTestRequest) -> Iterator[str]:
        """执行提示词流式测试。"""
        try:
            messages = [
                {"role": "system", "content": request.system_prompt.strip()},
                {
                    "role": "user",
                    "content": render_prompt(request.user_prompt.strip(), request.variables),
                },
            ]
            for chunk in self._client.stream_chat(messages, model=request.model.strip()):
                if chunk.done:
                    yield _sse(
                        "done",
                        {
                            "model": request.model.strip(),
                            "finish_reason": chunk.finish_reason,
                            "truncated": chunk.finish_reason == "length",
                            "usage": (chunk.usage or None) and chunk.usage.model_dump(),
                        },
                    )
                else:
                    yield _sse("delta", {"content": chunk.delta})
        except AIServiceError as exc:
            logger.warning("提示词测试失败 code=%s message=%s", exc.code, exc.message)
            yield _sse("error", {"code": exc.code, "message": exc.message})
        except Exception as exc:
            logger.exception("提示词测试未知异常")
            yield _sse("error", {"code": "PROMPT_TEST_FAILED", "message": str(exc)})


def _sse(event: str, data: dict) -> str:
    """拼接一条 SSE 报文。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
