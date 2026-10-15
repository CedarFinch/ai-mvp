"""视频转写整理接口。"""

from __future__ import annotations

from fastapi import APIRouter

from ...common.config import get_settings
from .schemas import TranscriptRefinementRequest, TranscriptRefinementResponse
from .service import MediaTranscriptService


router = APIRouter(prefix="/ai/media-transcripts", tags=["media-transcripts"])

_service: MediaTranscriptService | None = None


def get_media_transcript_service() -> MediaTranscriptService:
    """按需创建服务，避免 import 阶段读取模型配置。"""
    global _service
    if _service is None:
        _service = MediaTranscriptService(get_settings())
    return _service


@router.post(
    "/refine",
    summary="整理视频转写对话",
    response_model=TranscriptRefinementResponse,
)
def refine_transcript(payload: TranscriptRefinementRequest) -> TranscriptRefinementResponse:
    """使用 LangChain 调用大模型，整理说话人角色和 ASR 文字。"""
    return get_media_transcript_service().refine(payload)
