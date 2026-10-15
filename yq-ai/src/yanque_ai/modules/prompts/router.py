"""提示词测试接口。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ...common.config import get_settings
from ...integrations.bailian.client import BailianClient
from .schemas import PromptTestRequest
from .service import PromptTestService


router = APIRouter(prefix="/ai/prompts", tags=["prompts"])

_client: BailianClient | None = None
_service: PromptTestService | None = None


def get_prompt_test_service() -> PromptTestService:
    """按需创建提示词测试服务。"""
    global _client, _service
    if _service is None:
        _client = BailianClient(get_settings())
        _service = PromptTestService(_client)
    return _service


@router.post("/test/stream", summary="提示词测试（流式 SSE）", response_class=StreamingResponse)
def stream_prompt_test(payload: PromptTestRequest) -> StreamingResponse:
    """使用传入的系统提示词、用户提示词和变量执行模型测试。"""
    return StreamingResponse(
        get_prompt_test_service().stream_test(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
