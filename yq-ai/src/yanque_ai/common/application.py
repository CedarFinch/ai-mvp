"""FastAPI 应用组装。"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..modules.chat import router as chat_router
from ..modules.content_generation import router as content_generation_router
from ..modules.douyin import router as douyin_router
from ..modules.health import router as health_router
from ..modules.knowledge import router as knowledge_router
from ..modules.media_material import router as media_material_router
from ..modules.media_transcript import router as media_transcript_router
from ..modules.prompts import router as prompts_router
from ..modules.text_to_sql import router as text_to_sql_router
from .config import ConfigError
from .errors import AIServiceError


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    app = FastAPI(title="YanQue AI", version="0.1.0")
    register_exception_handlers(app)
    register_routes(app)
    return app


def register_exception_handlers(app: FastAPI) -> None:
    """注册统一异常响应。"""

    @app.exception_handler(AIServiceError)
    async def handle_ai_service_error(
        _: Request, exc: AIServiceError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )

    @app.exception_handler(ConfigError)
    async def handle_config_error(_: Request, exc: ConfigError) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"code": "CONFIG_MISSING", "message": str(exc)},
        )


def register_routes(app: FastAPI) -> None:
    """注册业务路由。"""
    app.include_router(health_router.router)
    app.include_router(chat_router.router)
    app.include_router(content_generation_router.router)
    app.include_router(douyin_router.router)
    app.include_router(knowledge_router.router)
    app.include_router(media_material_router.router)
    app.include_router(media_transcript_router.router)
    app.include_router(prompts_router.router)
    app.include_router(text_to_sql_router.router)
