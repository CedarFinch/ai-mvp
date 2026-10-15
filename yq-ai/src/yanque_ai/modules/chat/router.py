"""聊天问答接口。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ...common.config import get_settings
from ...integrations.bailian.client import BailianClient
from .schemas import ChatRequest, SummaryRequest, SummaryResponse
from .service import ChatService


router = APIRouter(prefix="/ai", tags=["chat"])

_client: BailianClient | None = None
_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    """按需创建模型服务，避免 import 阶段读取环境配置。"""
    global _client, _chat_service

    if _chat_service is None:
        settings = get_settings()
        _client = BailianClient(settings)
        _chat_service = ChatService(_client, settings)

    return _chat_service


@router.post(
    "/chat/stream",
    summary="通用问答（流式 SSE）",
    response_class=StreamingResponse,
)
def chat_stream(payload: ChatRequest) -> StreamingResponse:
    """边生成边推送，Java 一边转发给前端，一边把碎片拼成整段落库。"""
    chat_service = get_chat_service()
    return StreamingResponse(
        chat_service.stream_chat(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/summary", summary="生成对话摘要", response_model=SummaryResponse)
def chat_summary(payload: SummaryRequest) -> SummaryResponse:
    """内部接口：Java 会话压缩时调用，前端不直接访问。"""
    chat_service = get_chat_service()
    return SummaryResponse(summary=chat_service.summarize(payload))
