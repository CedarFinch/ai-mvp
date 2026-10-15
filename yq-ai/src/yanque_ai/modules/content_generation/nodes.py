"""选题工作流节点。"""

from __future__ import annotations

from langgraph.types import interrupt

from ...common.errors import AIServiceError
from .schemas import TopicResumeAction
from .state import ContentGenerationState
from .topic_agent import TopicDiscoveryAgent


class ContentGenerationNodes:
    """实现选题生成和人工选择两个节点。"""

    def __init__(self, topic_agent: TopicDiscoveryAgent) -> None:
        self._topic_agent = topic_agent

    async def topic_discovery_agent(
        self,
        state: ContentGenerationState,
    ) -> ContentGenerationState:
        """调用只绑定热点工具的 Agent，生成新一轮候选选题。"""

        topics = await self._topic_agent.generate(
            days=state["days"],
            hotspot_limit=state["hotspot_limit"],
            candidate_count=state["candidate_count"],
            regeneration_feedback=state.get("regeneration_feedback", ""),
        )
        return {
            "candidate_topics": [topic.model_dump(mode="json") for topic in topics],
            "selected_topic": None,
            "resume_action": "",
            "generation_round": state.get("generation_round", 0) + 1,
        }

    async def topic_selection_node(
        self,
        state: ContentGenerationState,
    ) -> ContentGenerationState:
        """暂停流程，恢复后记录选择或将反馈送回选题 Agent。"""

        resume_value = interrupt(
            {
                "type": "TOPIC_SELECTION",
                "message": "请选择一个选题，或填写意见重新生成。",
                "generation_round": state.get("generation_round", 1),
                "candidate_topics": state.get("candidate_topics", []),
            }
        )
        action = str((resume_value or {}).get("action") or "").upper()
        if action == TopicResumeAction.REGENERATE.value:
            return {
                "resume_action": action,
                "regeneration_feedback": str((resume_value or {}).get("feedback") or "").strip(),
                "candidate_topics": [],
                "selected_topic": None,
            }
        if action != TopicResumeAction.SELECT.value:
            raise AIServiceError("INVALID_RESUME_ACTION", "不支持的选题恢复操作。", status_code=400)

        topic_id = str((resume_value or {}).get("topic_id") or "").strip()
        selected = next(
            (topic for topic in state.get("candidate_topics", []) if topic.get("topic_id") == topic_id),
            None,
        )
        if selected is None:
            raise AIServiceError("INVALID_TOPIC_ID", "选择的选题不在当前候选列表中。", status_code=400)
        return {
            "resume_action": action,
            "selected_topic": selected,
        }
