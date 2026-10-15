"""视频转写整理业务。"""

from __future__ import annotations

import logging
from math import ceil

from ...common.config import Settings
from ...integrations.langchain_model import build_chat_model
from .refiner import LangChainTranscriptRefiner
from .schemas import (
    RefinedUtterance,
    TranscriptRefinementRequest,
    TranscriptRefinementResponse,
)


logger = logging.getLogger(__name__)


class MediaTranscriptService:
    """视频转写整理服务入口。"""

    BATCH_SIZE = 50
    CONTEXT_SIZE = 10

    def __init__(self, settings: Settings) -> None:
        # 转写整理重在速度和结构化输出，单独使用 Flash 并关闭深度思考。
        model = build_chat_model(
            settings,
            temperature=0.0,
            model=settings.media_transcript_model,
            enable_thinking=settings.media_transcript_enable_thinking,
        )
        self._refiner = LangChainTranscriptRefiner(model, settings)

    def refine(self, request: TranscriptRefinementRequest) -> TranscriptRefinementResponse:
        """整理说话人角色和文字，不保留 ASR 的逐字明细。"""
        logger.info(
            "开始整理视频转写 video_id=%s utterance_count=%s",
            request.video_id,
            len(request.utterances),
        )
        utterances = self._refine_in_batches(request)
        full_text = "\n".join(item.text for item in utterances)
        logger.info(
            "视频转写整理完成 video_id=%s dialogue_count=%s",
            request.video_id,
            len(utterances),
        )
        return TranscriptRefinementResponse(
            full_text=full_text,
            utterances=utterances,
        )

    def _refine_in_batches(
        self,
        request: TranscriptRefinementRequest,
    ) -> list[RefinedUtterance]:
        """按时间顺序分批整理，后一批继承前一批的角色和末尾上下文。"""
        refined: list[RefinedUtterance] = []
        speaker_mapping: dict[str, str] = {}
        total_batches = ceil(len(request.utterances) / self.BATCH_SIZE)

        for batch_index, offset in enumerate(
            range(0, len(request.utterances), self.BATCH_SIZE),
            start=1,
        ):
            batch = request.utterances[offset : offset + self.BATCH_SIZE]
            logger.info(
                "开始整理视频转写批次 video_id=%s batch=%s/%s utterance_count=%s",
                request.video_id,
                batch_index,
                total_batches,
                len(batch),
            )
            result = self._refiner.refine(
                batch,
                speaker_mapping=speaker_mapping,
                previous_context=refined[-self.CONTEXT_SIZE :],
                batch_number=batch_index,
                total_batches=total_batches,
            )
            # 已确认的角色不能被后续批次覆盖，只接收本批新出现的 speaker。
            for speaker, role in result.speaker_mapping.items():
                speaker_mapping.setdefault(speaker, role)
            refined.extend(result.utterances)

        return refined
