"""健康检查接口。"""

from __future__ import annotations

from fastapi import APIRouter

from ...common.config import get_settings


router = APIRouter(tags=["health"])


@router.get("/health", summary="服务健康检查")
def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "model": settings.model}

