"""视频素材片段生成接口。"""

from __future__ import annotations

from fastapi import APIRouter

from ...common.config import get_settings
from .index_service import MediaMaterialIndexService
from .schemas import (
    MaterialIndexRequest,
    MaterialIndexResponse,
    MaterialRecallRequest,
    MaterialRecallResponse,
    MaterialSegmentRequest,
    MaterialSegmentResponse,
)
from .service import MediaMaterialService


router = APIRouter(prefix="/ai/media-materials", tags=["media-materials"])

_service: MediaMaterialService | None = None
_index_service: MediaMaterialIndexService | None = None


def get_media_material_service() -> MediaMaterialService:
    """按需创建服务，避免 import 阶段读取模型和提示词配置。"""
    global _service
    if _service is None:
        _service = MediaMaterialService(get_settings())
    return _service


def get_media_material_index_service() -> MediaMaterialIndexService:
    """按需创建视频素材向量服务，避免启动阶段连接 Milvus。"""
    global _index_service
    if _index_service is None:
        _index_service = MediaMaterialIndexService(get_settings())
    return _index_service


@router.post(
    "/segments",
    summary="生成高价值视频素材片段",
    response_model=MaterialSegmentResponse,
)
def generate_material_segments(payload: MaterialSegmentRequest) -> MaterialSegmentResponse:
    """从整理后的完整视频对话中最多选择三条 1～5 分钟片段。"""
    return get_media_material_service().generate_segments(payload)


@router.post(
    "/index",
    summary="写入视频素材向量索引",
    response_model=MaterialIndexResponse,
)
def index_materials(payload: MaterialIndexRequest) -> MaterialIndexResponse:
    """MATERIAL_INDEX 节点按任务覆盖写入全部视频素材。"""
    return get_media_material_index_service().index(payload)


@router.post(
    "/recall",
    summary="混合召回视频素材",
    response_model=MaterialRecallResponse,
)
def recall_materials(payload: MaterialRecallRequest) -> MaterialRecallResponse:
    """使用 Dense Vector 与 BM25 召回视频素材，只返回稳定 material_id。"""
    return get_media_material_index_service().recall(payload)
