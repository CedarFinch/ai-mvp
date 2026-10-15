"""视频素材片段生成业务。"""

from __future__ import annotations

import logging

from ...common.config import Settings
from ...integrations.langchain_model import build_chat_model
from .schemas import MaterialSegment, MaterialSegmentRequest, MaterialSegmentResponse
from .selector import LangChainMaterialSegmentSelector


logger = logging.getLogger(__name__)


class MediaMaterialService:
    """从完整视频对话中最多选择三条高价值片段。"""

    def __init__(self, settings: Settings) -> None:
        # 素材筛选使用 Flash 且关闭深度思考，保持与转写整理节点一致。
        model = build_chat_model(
            settings,
            temperature=0.0,
            model=settings.media_material_model,
            enable_thinking=False,
        )
        self._selector = LangChainMaterialSegmentSelector(model, settings)

    def generate_segments(self, request: MaterialSegmentRequest) -> MaterialSegmentResponse:
        """一次提交完整对话，由模型全局选择少量精华片段。"""
        numbered = [
            {"utterance_no": index + 1, **utterance.model_dump()}
            for index, utterance in enumerate(request.utterances)
        ]
        logger.info(
            "开始生成视频素材片段 video_id=%s utterance_count=%s max_segments=%s",
            request.video_id,
            len(numbered),
            request.max_segments,
        )
        segments = self._selector.select_segments(
            numbered,
            min_duration_seconds=request.min_duration_seconds,
            max_duration_seconds=request.max_duration_seconds,
            max_segments=request.max_segments,
        )
        valid_segments = self._valid_segments(request, segments)
        selected = valid_segments[: request.max_segments]
        logger.info(
            "视频素材片段生成完成 video_id=%s valid_count=%s selected_count=%s",
            request.video_id,
            len(valid_segments),
            len(selected),
        )
        return MaterialSegmentResponse(segments=selected)

    def _valid_segments(
        self,
        request: MaterialSegmentRequest,
        segments: list[MaterialSegment],
    ) -> list[MaterialSegment]:
        """过滤模型返回的越界范围和不符合 1～5 分钟约束的候选。"""
        valid: list[MaterialSegment] = []
        seen_ranges: set[tuple[int, int]] = set()
        for segment in segments:
            start_no = segment.start_utterance_no
            end_no = segment.end_utterance_no
            if start_no < 1 or end_no < start_no or end_no > len(request.utterances):
                continue
            duration_seconds = (
                request.utterances[end_no - 1].end_time
                - request.utterances[start_no - 1].start_time
            ) / 1000
            if not request.min_duration_seconds <= duration_seconds <= request.max_duration_seconds:
                continue
            segment_range = (start_no, end_no)
            if segment_range in seen_ranges:
                continue
            seen_ranges.add(segment_range)
            valid.append(segment)
        return valid
