"""知识库管理内部接口。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from .schemas import (
    KnowledgeBaseCreateRequest,
    KnowledgeBaseCreateResponse,
    KnowledgeBaseDeleteRequest,
    KnowledgeBaseDeleteResponse,
    KnowledgeDocumentChunkDetailRequest,
    KnowledgeDocumentChunkDetailResponse,
    KnowledgeDocumentChunkQueryRequest,
    KnowledgeDocumentChunkQueryResponse,
    KnowledgeDocumentDeleteRequest,
    KnowledgeDocumentDeleteResponse,
    KnowledgeDocumentIndexRequest,
    KnowledgeDocumentIndexResponse,
    KnowledgeRecallRequest,
    KnowledgeRecallResponse,
    KnowledgeQaStreamRequest,
)
from .service import KnowledgeService


router = APIRouter(prefix="/ai/knowledge-bases", tags=["knowledge"])

_knowledge_service: KnowledgeService | None = None


def get_knowledge_service() -> KnowledgeService:
    """按需创建知识库服务，避免 import 阶段就连接 Milvus。"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service


@router.post("/create", summary="初始化知识库向量表", response_model=KnowledgeBaseCreateResponse)
def create_knowledge_base(payload: KnowledgeBaseCreateRequest) -> KnowledgeBaseCreateResponse:
    """Java 新建知识库成功后调用，用于创建 Milvus Collection。"""
    return get_knowledge_service().create_knowledge_base(payload)


@router.post("/delete", summary="删除知识库向量表", response_model=KnowledgeBaseDeleteResponse)
def delete_knowledge_base(payload: KnowledgeBaseDeleteRequest) -> KnowledgeBaseDeleteResponse:
    """Java 物理删除知识库前调用，用于删除 Milvus Collection。"""
    return get_knowledge_service().delete_knowledge_base(payload)


@router.post("/documents/index", summary="入库知识库文档", response_model=KnowledgeDocumentIndexResponse)
def index_knowledge_document(payload: KnowledgeDocumentIndexRequest) -> KnowledgeDocumentIndexResponse:
    """Java 新增或重建文档时调用，用于下载 Markdown、切分并写入 Milvus。"""
    return get_knowledge_service().index_knowledge_document(payload)


@router.post("/documents/chunks/query", summary="查询知识库文档分段", response_model=KnowledgeDocumentChunkQueryResponse)
def query_knowledge_document_chunks(payload: KnowledgeDocumentChunkQueryRequest) -> KnowledgeDocumentChunkQueryResponse:
    """Java 查看文档分段列表时调用，用于从 Milvus 查询 chunk 摘要。"""
    return get_knowledge_service().query_knowledge_document_chunks(payload)


@router.post("/documents/chunks/detail", summary="查询知识库文档分段详情", response_model=KnowledgeDocumentChunkDetailResponse)
def get_knowledge_document_chunk_detail(
    payload: KnowledgeDocumentChunkDetailRequest,
) -> KnowledgeDocumentChunkDetailResponse:
    """Java 查看文档分段详情时调用，用于从 Milvus 查询 chunk 完整内容。"""
    return get_knowledge_service().get_knowledge_document_chunk_detail(payload)


@router.post("/documents/delete", summary="删除知识库文档向量", response_model=KnowledgeDocumentDeleteResponse)
def delete_knowledge_document(payload: KnowledgeDocumentDeleteRequest) -> KnowledgeDocumentDeleteResponse:
    """Java 物理删除文档前调用，用于删除该文档在 Milvus 中的向量。"""
    return get_knowledge_service().delete_knowledge_document(payload)


@router.post("/recall", summary="知识库召回测试", response_model=KnowledgeRecallResponse)
def recall_knowledge_base(payload: KnowledgeRecallRequest) -> KnowledgeRecallResponse:
    """Java 管理端召回测试时调用，用于从 Milvus 检索相关 chunk。"""
    return get_knowledge_service().recall_knowledge_base(payload)


@router.post("/qa/stream", summary="知识库问答测试（流式 SSE）", response_class=StreamingResponse)
def stream_knowledge_base_qa(payload: KnowledgeQaStreamRequest) -> StreamingResponse:
    """Java 管理端问答测试时调用，用于返回引用分段和流式回答。"""
    return StreamingResponse(
        get_knowledge_service().stream_knowledge_base_qa(payload),
        media_type="text/event-stream",
    )
