"""视频素材片段生成接口出入参。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


ClipType = Literal["Q_AND_A", "VIEWPOINT", "KNOWLEDGE", "STORY", "CASE", "TUTORIAL"]


class MaterialUtteranceInput(BaseModel):
    """一条已经完成文字和角色整理的对话。"""

    start_time: int = Field(ge=0, description="分句开始时间，单位毫秒")
    end_time: int = Field(ge=0, description="分句结束时间，单位毫秒")
    text: str = Field(min_length=1)
    speaker: str = Field(min_length=1)


class MaterialSegmentRequest(BaseModel):
    """Java 请求生成高价值视频片段的参数。"""

    video_id: int
    utterances: list[MaterialUtteranceInput] = Field(min_length=1)
    min_duration_seconds: int = Field(default=60, ge=1)
    max_duration_seconds: int = Field(default=300, ge=1)
    max_segments: int = Field(default=3, ge=1, le=3)

    @model_validator(mode="after")
    def validate_duration_range(self) -> "MaterialSegmentRequest":
        if self.min_duration_seconds > self.max_duration_seconds:
            raise ValueError("min_duration_seconds 不能大于 max_duration_seconds")
        return self


class MaterialSegment(BaseModel):
    """大模型发现的一条候选片段，也是最终接口返回结构。"""

    start_utterance_no: int = Field(ge=1)
    end_utterance_no: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=500)
    core_viewpoint: str = Field(min_length=1, max_length=500)
    clip_type: ClipType
    value_reason: str = Field(min_length=1, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=8)
    speakers: list[str] = Field(default_factory=list, max_length=8)


class MaterialSegmentResponse(BaseModel):
    """从完整视频中最终选中的少量精华片段。"""

    segments: list[MaterialSegment] = Field(default_factory=list, max_length=3)


class MaterialIndexItem(BaseModel):
    """一条已经生成真实视频文件、准备写入 Milvus 的素材。"""

    material_id: int = Field(gt=0)
    video_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=1000)
    core_viewpoint: str = Field(min_length=1, max_length=1000)
    clip_type: ClipType
    value_reason: str = Field(min_length=1, max_length=1000)
    tags: list[str] = Field(default_factory=list, max_length=8)
    speakers: list[str] = Field(default_factory=list, max_length=8)
    transcript_text: str = Field(min_length=1)
    duration_ms: int = Field(gt=0)


class MaterialIndexRequest(BaseModel):
    """Java 在 MATERIAL_INDEX 节点提交的全部素材。"""

    task_id: int = Field(gt=0)
    materials: list[MaterialIndexItem] = Field(default_factory=list)


class MaterialIndexResponse(BaseModel):
    """视频素材批量入库结果。"""

    collection_name: str
    indexed_count: int


RecallMode = Literal["SEMANTIC", "KEYWORD", "HYBRID"]


class MaterialRecallRequest(BaseModel):
    """视频素材混合召回请求。"""

    query: str = Field(min_length=1)
    mode: RecallMode = "HYBRID"
    top_k: int = Field(default=5, ge=1, le=20)
    video_id: int | None = Field(default=None, gt=0)
    clip_type: ClipType | None = None
    speaker: str | None = Field(default=None, pattern=r"^(HOST|CALLER_[1-9][0-9]*)$")
    min_duration_ms: int | None = Field(default=None, ge=0)
    max_duration_ms: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_duration_filter(self) -> "MaterialRecallRequest":
        if (
            self.min_duration_ms is not None
            and self.max_duration_ms is not None
            and self.min_duration_ms > self.max_duration_ms
        ):
            raise ValueError("min_duration_ms 不能大于 max_duration_ms")
        return self


class MaterialRecallItem(BaseModel):
    """Milvus 返回的一条视频素材候选。"""

    rank: int
    score: float
    material_id: int
    video_id: int
    clip_type: str
    duration_ms: int
    tags: list[str]
    speakers: list[str]
    content: str


class MaterialRecallResponse(BaseModel):
    """视频素材召回结果。"""

    query: str
    mode: str
    records: list[MaterialRecallItem]
