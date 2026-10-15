"""抖音公开页面采集接口。"""

from __future__ import annotations

from fastapi import APIRouter

from .collector import DouyinCollector
from .schemas import DouyinCollectRequest, DouyinCollectResponse


router = APIRouter(prefix="/ai/douyin", tags=["douyin"])
_collector = DouyinCollector()


@router.post("/collect", summary="采集抖音 AI 视频", response_model=DouyinCollectResponse)
def collect_douyin_videos(payload: DouyinCollectRequest) -> DouyinCollectResponse:
    return _collector.collect(payload)
