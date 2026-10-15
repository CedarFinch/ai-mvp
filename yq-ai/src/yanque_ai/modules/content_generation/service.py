"""选题工作流服务入口。"""

from __future__ import annotations

from ...common.config import Settings
from .graph import ContentGenerationGraph
from .nodes import ContentGenerationNodes
from .schemas import (
    TopicGenerateRequest,
    TopicResumeRequest,
    TopicWorkflowResponse,
)
from .topic_agent import TopicDiscoveryAgent


class ContentGenerationService:
    """组装选题 Agent、节点和 LangGraph。"""

    def __init__(self, settings: Settings) -> None:
        self._graph = ContentGenerationGraph(
            ContentGenerationNodes(TopicDiscoveryAgent(settings))
        )

    async def generate(self, request: TopicGenerateRequest) -> TopicWorkflowResponse:
        """生成候选选题并等待用户选择。"""

        return await self._graph.generate(request)

    async def resume(
        self,
        conversation_id: str,
        request: TopicResumeRequest,
    ) -> TopicWorkflowResponse:
        """恢复指定选题会话。"""

        return await self._graph.resume(conversation_id, request)
