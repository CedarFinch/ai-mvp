"""选题生成与人工选择 LangGraph。"""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from ...common.errors import AIServiceError
from .nodes import ContentGenerationNodes
from .schemas import (
    TopicCandidate,
    TopicGenerateRequest,
    TopicResumeAction,
    TopicResumeRequest,
    TopicWorkflowResponse,
    TopicWorkflowStatus,
)
from .state import ContentGenerationState


DEFAULT_HOTSPOT_DAYS = 2
DEFAULT_HOTSPOT_LIMIT = 20


class ContentGenerationGraph:
    """编排选题 Agent 和人工选择节点。"""

    def __init__(self, nodes: ContentGenerationNodes) -> None:
        self._graph = self._build_graph(nodes)

    async def generate(self, request: TopicGenerateRequest) -> TopicWorkflowResponse:
        """启动新工作流并运行到选题中断点。"""

        conversation_id = uuid4().hex
        config = _config(conversation_id)
        state = await self._graph.ainvoke(
            {
                "conversation_id": conversation_id,
                "days": DEFAULT_HOTSPOT_DAYS,
                "hotspot_limit": DEFAULT_HOTSPOT_LIMIT,
                "candidate_count": request.candidate_count,
                "generation_round": 0,
                "candidate_topics": [],
                "selected_topic": None,
                "regeneration_feedback": "",
            },
            config=config,
        )
        return _to_response(conversation_id, state)

    async def resume(
        self,
        conversation_id: str,
        request: TopicResumeRequest,
    ) -> TopicWorkflowResponse:
        """校验当前 checkpoint 后恢复人工选择节点。"""

        config = _config(conversation_id)
        snapshot = await self._graph.aget_state(config)
        if not snapshot.values:
            raise AIServiceError("WORKFLOW_NOT_FOUND", "选题会话不存在或已失效。", status_code=404)
        if "topic_selection_node" not in snapshot.next:
            raise AIServiceError("WORKFLOW_NOT_WAITING", "当前选题会话不在等待选择。", status_code=409)

        if request.action == TopicResumeAction.SELECT:
            topic_ids = {
                str(topic.get("topic_id"))
                for topic in snapshot.values.get("candidate_topics", [])
            }
            if request.topic_id not in topic_ids:
                raise AIServiceError(
                    "INVALID_TOPIC_ID",
                    "选择的选题不在当前候选列表中。",
                    status_code=400,
                )

        state = await self._graph.ainvoke(
            Command(resume=request.model_dump(mode="json", exclude_none=True)),
            config=config,
        )
        return _to_response(conversation_id, state)

    @staticmethod
    def _build_graph(nodes: ContentGenerationNodes):
        graph = StateGraph(ContentGenerationState)
        graph.add_node("topic_discovery_agent", nodes.topic_discovery_agent)
        graph.add_node("topic_selection_node", nodes.topic_selection_node)
        graph.add_edge(START, "topic_discovery_agent")
        graph.add_edge("topic_discovery_agent", "topic_selection_node")
        graph.add_conditional_edges(
            "topic_selection_node",
            _route_after_selection,
            {
                "regenerate": "topic_discovery_agent",
                "complete": END,
            },
        )
        return graph.compile(checkpointer=InMemorySaver())


def _route_after_selection(state: ContentGenerationState) -> Literal["regenerate", "complete"]:
    if state.get("resume_action") == TopicResumeAction.REGENERATE.value:
        return "regenerate"
    return "complete"


def _config(conversation_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": conversation_id}}


def _to_response(
    conversation_id: str,
    state: ContentGenerationState,
) -> TopicWorkflowResponse:
    interrupted = bool(state.get("__interrupt__"))
    candidates = [TopicCandidate.model_validate(item) for item in state.get("candidate_topics", [])]
    selected_raw = state.get("selected_topic")
    selected = TopicCandidate.model_validate(selected_raw) if selected_raw else None
    return TopicWorkflowResponse(
        conversation_id=conversation_id,
        status=(
            TopicWorkflowStatus.WAITING_SELECTION
            if interrupted
            else TopicWorkflowStatus.COMPLETED
        ),
        generation_round=state.get("generation_round", 0),
        candidate_topics=candidates,
        selected_topic=selected,
        message=(
            "请选择一个选题，或填写意见重新生成。"
            if interrupted
            else "选题已确认。"
        ),
    )
