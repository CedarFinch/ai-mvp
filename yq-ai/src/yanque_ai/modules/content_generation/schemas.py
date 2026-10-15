"""选题工作流的对外契约和模型结构化输出。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class TopicWorkflowStatus(StrEnum):
    """选题工作流当前状态。"""

    WAITING_SELECTION = "WAITING_SELECTION"
    COMPLETED = "COMPLETED"


class TopicResumeAction(StrEnum):
    """用户在选题确认节点可执行的动作。"""

    SELECT = "SELECT"
    REGENERATE = "REGENERATE"


class TopicSourceVideo(BaseModel):
    """支撑候选选题的一条真实热点视频。"""

    video_id: str = Field(min_length=1, description="抖音视频ID")
    title: str | None = Field(default=None, description="视频标题")
    video_url: str | None = Field(default=None, description="视频地址")
    like_count: int | None = Field(default=None, description="最近点赞数")
    like_increase: int | None = Field(default=None, description="最近两次采集的点赞增量")


class TopicDraft(BaseModel):
    """选题 Agent 直接生成的草稿。"""

    title: str = Field(min_length=1, max_length=200, description="选题标题")
    core_event: str = Field(min_length=1, max_length=1000, description="对应热点事件")
    creation_angle: str = Field(min_length=1, max_length=1000, description="创作切入角度")
    target_audience: str = Field(min_length=1, max_length=500, description="目标受众")
    reason: str = Field(min_length=1, max_length=1000, description="当前值得创作的原因")
    source_video_ids: list[str] = Field(min_length=1, description="支撑选题的真实视频ID")


class TopicGenerationResult(BaseModel):
    """选题 Agent 的结构化结果。"""

    topics: list[TopicDraft] = Field(min_length=1, description="候选选题")


class TopicCandidate(BaseModel):
    """返回给前端选择的候选选题。"""

    topic_id: str
    title: str
    core_event: str
    creation_angle: str
    target_audience: str
    reason: str
    source_videos: list[TopicSourceVideo]


class TopicGenerateRequest(BaseModel):
    """启动选题生成工作流。"""

    candidate_count: int = Field(default=5, ge=1, le=10, description="候选选题数量")


class TopicResumeRequest(BaseModel):
    """恢复正在等待人工选择的选题工作流。"""

    action: TopicResumeAction
    topic_id: str | None = Field(default=None, max_length=64)
    feedback: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_action_fields(self) -> "TopicResumeRequest":
        """不同动作只接受自己需要的参数。"""

        if self.action == TopicResumeAction.SELECT and not (self.topic_id or "").strip():
            raise ValueError("SELECT 操作必须提供 topic_id")
        if self.action == TopicResumeAction.REGENERATE and not (self.feedback or "").strip():
            raise ValueError("REGENERATE 操作必须提供 feedback")
        return self


class TopicWorkflowResponse(BaseModel):
    """选题工作流启动或恢复后的统一响应。"""

    conversation_id: str
    status: TopicWorkflowStatus
    generation_round: int
    candidate_topics: list[TopicCandidate] = Field(default_factory=list)
    selected_topic: TopicCandidate | None = None
    message: str
