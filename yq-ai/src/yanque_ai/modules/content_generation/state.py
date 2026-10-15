"""选题 LangGraph 的共享状态。"""

from __future__ import annotations

from typing import TypedDict


class ContentGenerationState(TypedDict, total=False):
    """节点间只传递可被 checkpoint 稳定序列化的数据。"""

    conversation_id: str
    days: int
    hotspot_limit: int
    candidate_count: int
    generation_round: int
    candidate_topics: list[dict[str, object]]
    selected_topic: dict[str, object] | None
    regeneration_feedback: str
    resume_action: str
    error_message: str
