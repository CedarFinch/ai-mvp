"""抖音采集接口出入参。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DouyinCollectRequest(BaseModel):
    """Java 管理端提交的一轮采集目标。"""

    keywords: list[str] = Field(default_factory=list, max_length=50)
    accounts: list[str] = Field(default_factory=list, max_length=50)
    max_results_per_target: int = Field(default=5, ge=1, le=50)
    max_videos: int = Field(default=10, ge=1, le=200)

    @field_validator("keywords", "accounts")
    @classmethod
    def normalize_targets(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class DouyinVideo(BaseModel):
    douyin_video_id: str = Field(min_length=1, max_length=64)
    video_url: str
    title: str = ""
    description: str | None = None
    author_sec_user_id: str | None = None
    author_name: str | None = None
    author_url: str | None = None
    cover_url: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    publish_time: datetime | None = None
    matched_keywords: list[str] = Field(default_factory=list)
    like_count: int | None = Field(default=None, ge=0)


class DouyinTargetError(BaseModel):
    target_type: Literal["KEYWORD", "ACCOUNT"]
    target_value: str
    message: str


class DouyinCollectResponse(BaseModel):
    videos: list[DouyinVideo] = Field(default_factory=list)
    errors: list[DouyinTargetError] = Field(default_factory=list)
