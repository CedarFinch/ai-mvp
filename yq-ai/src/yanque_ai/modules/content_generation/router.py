"""内容生成选题接口。"""

from __future__ import annotations

from fastapi import APIRouter

from ...common.config import get_settings
from .schemas import TopicGenerateRequest, TopicResumeRequest, TopicWorkflowResponse
from .service import ContentGenerationService


router = APIRouter(prefix="/ai/content-generation/topics", tags=["content-generation"])

_service: ContentGenerationService | None = None


def get_content_generation_service() -> ContentGenerationService:
    """按需创建单例服务，确保内存 checkpoint 可被后续请求恢复。"""

    global _service
    if _service is None:
        _service = ContentGenerationService(get_settings())
    return _service


@router.post(
    "/generate",
    summary="生成热点候选选题",
    response_model=TopicWorkflowResponse,
)
async def generate_topics(payload: TopicGenerateRequest) -> TopicWorkflowResponse:
    """调用 Bear MCP 热点工具生成候选选题，并暂停等待人工选择。"""

    return await get_content_generation_service().generate(payload)


@router.post(
    "/{conversation_id}/resume",
    summary="恢复选题人工确认",
    response_model=TopicWorkflowResponse,
)
async def resume_topic_selection(
    conversation_id: str,
    payload: TopicResumeRequest,
) -> TopicWorkflowResponse:
    """选择一个候选选题，或携带反馈重新生成。"""

    return await get_content_generation_service().resume(conversation_id, payload)
