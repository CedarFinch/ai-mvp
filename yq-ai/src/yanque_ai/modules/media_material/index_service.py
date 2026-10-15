"""视频素材向量入库与召回业务。"""

from __future__ import annotations

import logging

from ...common.config import Settings
from ...common.errors import AIServiceError
from ..knowledge.vector_store import build_collection_name, load_milvus_config
from .schemas import (
    MaterialIndexRequest,
    MaterialIndexResponse,
    MaterialRecallRequest,
    MaterialRecallResponse,
)
from .vector_store import MediaMaterialVectorStore


logger = logging.getLogger(__name__)


class MediaMaterialIndexService:
    """编排视频素材专用 Collection，不依赖文档上传和切分流程。"""

    def __init__(
        self,
        settings: Settings,
        vector_store: MediaMaterialVectorStore | None = None,
    ) -> None:
        self.collection_name = build_collection_name(settings.media_material_collection)
        self.vector_store = vector_store or MediaMaterialVectorStore(load_milvus_config())

    def index(self, request: MaterialIndexRequest) -> MaterialIndexResponse:
        """按处理任务覆盖写入素材索引。"""
        logger.info(
            "开始写入视频素材索引 task_id=%s material_count=%s collection=%s",
            request.task_id,
            len(request.materials),
            self.collection_name,
        )
        try:
            count = self.vector_store.replace_task_materials(
                self.collection_name,
                request.task_id,
                request.materials,
            )
        except Exception as exc:
            logger.exception("视频素材索引写入失败 task_id=%s", request.task_id)
            raise AIServiceError(
                code="MEDIA_MATERIAL_INDEX_FAILED",
                message=f"视频素材索引写入失败：{exc}",
                status_code=502,
            ) from exc
        logger.info("视频素材索引写入完成 task_id=%s indexed_count=%s", request.task_id, count)
        return MaterialIndexResponse(collection_name=self.collection_name, indexed_count=count)

    def recall(self, request: MaterialRecallRequest) -> MaterialRecallResponse:
        """从视频素材 Collection 执行混合召回。"""
        try:
            records = self.vector_store.recall(self.collection_name, request)
        except Exception as exc:
            logger.exception("视频素材召回失败 mode=%s", request.mode)
            raise AIServiceError(
                code="MEDIA_MATERIAL_RECALL_FAILED",
                message=f"视频素材召回失败：{exc}",
                status_code=502,
            ) from exc
        return MaterialRecallResponse(query=request.query, mode=request.mode, records=records)
