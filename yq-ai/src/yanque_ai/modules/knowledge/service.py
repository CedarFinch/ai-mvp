"""知识库管理业务编排。"""

from __future__ import annotations

import logging
import json
from collections.abc import Iterator
from urllib.request import Request, urlopen

from ...common.config import Settings, get_settings
from ...common.errors import AIServiceError
from ...integrations.bailian.client import BailianClient
from ...prompts import PromptBuilder
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
from .vector_store import KnowledgeVectorStore, build_collection_name, load_milvus_config


log = logging.getLogger(__name__)


class KnowledgeService:
    """封装知识库向量侧初始化和删除逻辑。"""

    def __init__(self) -> None:
        self.vector_store = KnowledgeVectorStore(load_milvus_config())
        self._settings: Settings | None = None
        self._client: BailianClient | None = None
        self._prompt_builder: PromptBuilder | None = None

    def create_knowledge_base(
        self, payload: KnowledgeBaseCreateRequest
    ) -> KnowledgeBaseCreateResponse:
        """为新知识库创建 Milvus Collection。"""
        collection_name = build_collection_name(payload.code)
        try:
            self.vector_store.create_collection(collection_name)
        except Exception as exc:
            log.exception("Milvus Collection 初始化失败: %s", collection_name)
            raise AIServiceError(
                code="KNOWLEDGE_BASE_COLLECTION_INIT_FAILED",
                message=f"知识库向量表初始化失败：{exc}",
                status_code=502,
            ) from exc

        return KnowledgeBaseCreateResponse(
            collection_name=collection_name,
        )

    def delete_knowledge_base(
        self, payload: KnowledgeBaseDeleteRequest
    ) -> KnowledgeBaseDeleteResponse:
        """删除知识库对应的 Milvus Collection。"""
        collection_name = build_collection_name(payload.code)
        try:
            deleted = self.vector_store.drop_collection(collection_name)
        except Exception as exc:
            log.exception("Milvus Collection 删除失败: %s", collection_name)
            raise AIServiceError(
                code="KNOWLEDGE_BASE_COLLECTION_DELETE_FAILED",
                message=f"知识库向量表删除失败：{exc}",
                status_code=502,
            ) from exc

        return KnowledgeBaseDeleteResponse(
            collection_name=collection_name,
            deleted=deleted,
        )

    def index_knowledge_document(
        self, payload: KnowledgeDocumentIndexRequest
    ) -> KnowledgeDocumentIndexResponse:
        """下载知识库文档，按文件类型和切分策略写入 Milvus。"""
        collection_name = build_collection_name(payload.knowledge_base_code)
        try:
            document_text = self._download_document(payload)
            chunk_count = self.vector_store.index_document(
                collection_name,
                payload,
                document_text,
            )
        except Exception as exc:
            log.exception("知识库文档入库失败: collection=%s, document_id=%s", collection_name, payload.document_id)
            raise AIServiceError(
                code="KNOWLEDGE_DOCUMENT_INDEX_FAILED",
                message=f"知识库文档入库失败：{exc}",
                status_code=502,
            ) from exc

        return KnowledgeDocumentIndexResponse(
            collection_name=collection_name,
            chunk_count=chunk_count,
        )

    def query_knowledge_document_chunks(
        self, payload: KnowledgeDocumentChunkQueryRequest
    ) -> KnowledgeDocumentChunkQueryResponse:
        """从 Milvus 查询指定文档当前版本的 chunk 列表。"""
        collection_name = build_collection_name(payload.knowledge_base_code)
        try:
            records = self.vector_store.query_document_chunks(
                collection_name,
                payload.document_code,
                payload.document_version,
                payload.page_num,
                payload.page_size,
            )
        except Exception as exc:
            log.exception("知识库文档 chunk 查询失败: collection=%s, document_code=%s", collection_name, payload.document_code)
            raise AIServiceError(
                code="KNOWLEDGE_DOCUMENT_CHUNK_QUERY_FAILED",
                message=f"知识库文档分段查询失败：{exc}",
                status_code=502,
            ) from exc

        return KnowledgeDocumentChunkQueryResponse(
            collection_name=collection_name,
            records=records,
        )

    def get_knowledge_document_chunk_detail(
        self, payload: KnowledgeDocumentChunkDetailRequest
    ) -> KnowledgeDocumentChunkDetailResponse:
        """从 Milvus 查询指定文档 chunk 的完整内容。"""
        collection_name = build_collection_name(payload.knowledge_base_code)
        try:
            detail = self.vector_store.get_document_chunk_detail(
                collection_name,
                payload.document_code,
                payload.document_version,
                payload.chunk_index,
            )
        except Exception as exc:
            log.exception("知识库文档 chunk 详情查询失败: collection=%s, document_code=%s", collection_name, payload.document_code)
            raise AIServiceError(
                code="KNOWLEDGE_DOCUMENT_CHUNK_DETAIL_FAILED",
                message=f"知识库文档分段详情查询失败：{exc}",
                status_code=502,
            ) from exc
        if detail is None:
            raise AIServiceError(
                code="KNOWLEDGE_DOCUMENT_CHUNK_NOT_FOUND",
                message="知识库文档分段不存在",
                status_code=404,
            )

        return KnowledgeDocumentChunkDetailResponse(
            collection_name=collection_name,
            **detail,
        )

    def delete_knowledge_document(
        self, payload: KnowledgeDocumentDeleteRequest
    ) -> KnowledgeDocumentDeleteResponse:
        """删除指定文档在 Milvus 中的全部向量。"""
        collection_name = build_collection_name(payload.knowledge_base_code)
        try:
            deleted = self.vector_store.delete_document_vectors(collection_name, payload.document_code)
        except Exception as exc:
            log.exception("知识库文档向量删除失败: collection=%s, document_code=%s", collection_name, payload.document_code)
            raise AIServiceError(
                code="KNOWLEDGE_DOCUMENT_VECTOR_DELETE_FAILED",
                message=f"知识库文档向量删除失败：{exc}",
                status_code=502,
            ) from exc

        return KnowledgeDocumentDeleteResponse(
            collection_name=collection_name,
            deleted=deleted,
        )

    def recall_knowledge_base(self, payload: KnowledgeRecallRequest) -> KnowledgeRecallResponse:
        """从 Milvus 执行知识库召回测试。"""
        collection_name = build_collection_name(payload.knowledge_base_code)
        mode = payload.mode.upper()
        try:
            records = self.vector_store.recall(collection_name, payload.query.strip(), mode, payload.top_k)
        except Exception as exc:
            log.exception("知识库召回失败: collection=%s, mode=%s", collection_name, mode)
            raise AIServiceError(
                code="KNOWLEDGE_RECALL_FAILED",
                message=f"知识库召回失败：{exc}",
                status_code=502,
            ) from exc

        return KnowledgeRecallResponse(
            query=payload.query,
            mode=mode,
            top_k=payload.top_k,
            records=records,
        )

    def stream_knowledge_base_qa(self, payload: KnowledgeQaStreamRequest) -> Iterator[str]:
        """先召回知识库 chunk，再用百炼模型流式生成问答测试结果。"""
        collection_name = build_collection_name(payload.knowledge_base_code)
        mode = payload.recall_mode.upper()
        question = payload.question.strip()

        try:
            citations = self.vector_store.recall(collection_name, question, mode, payload.top_k)
        except Exception as exc:
            log.exception("知识库问答召回失败: collection=%s, mode=%s", collection_name, mode)
            yield _sse("error", {"code": "KNOWLEDGE_QA_RECALL_FAILED", "message": f"知识库问答召回失败：{exc}"})
            return

        yield _sse("citations", {"citations": citations})
        if not citations:
            yield _sse("delta", {"content": "知识库中未找到足够依据，无法回答该问题。"})
            yield _sse("done", {"model": self._model_name(), "finish_reason": "no_citations", "usage": None})
            return

        try:
            for chunk in self._llm_client().stream_chat(self._build_qa_messages(question, citations)):
                if chunk.done:
                    yield _sse("done", {
                        "model": self._model_name(),
                        "finish_reason": chunk.finish_reason,
                        "truncated": chunk.finish_reason == "length",
                        "usage": (chunk.usage or None) and chunk.usage.model_dump(),
                    })
                else:
                    yield _sse("delta", {"content": chunk.delta})
        except AIServiceError as exc:
            log.warning("知识库问答模型调用失败 code=%s message=%s", exc.code, exc.message)
            yield _sse("error", {"code": exc.code, "message": exc.message})
        except Exception as exc:
            log.exception("知识库问答未知异常")
            yield _sse("error", {"code": "KNOWLEDGE_QA_FAILED", "message": str(exc)})

    def _download_document(self, payload: KnowledgeDocumentIndexRequest) -> str:
        """通过 Java 提供的 TOS 预签名地址下载 UTF-8 文档原文。"""
        suffix = "." + payload.file_type
        if not payload.object_key.lower().endswith(suffix):
            raise ValueError(f"文档对象 Key 和文件类型不一致：{payload.file_type}")

        request = Request(payload.download_url, headers={"User-Agent": "YanQue-AI/knowledge-indexer"})
        with urlopen(request, timeout=60) as response:
            content = response.read()
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("知识库文档必须使用 UTF-8 编码") from exc

    def _llm_client(self) -> BailianClient:
        """按需创建百炼客户端，避免普通知识库操作依赖模型配置。"""
        if self._client is None:
            self._settings = get_settings()
            self._client = BailianClient(self._settings)
        return self._client

    def _prompt_builder_instance(self) -> PromptBuilder:
        """按需创建提示词组装器。"""
        if self._prompt_builder is None:
            if self._settings is None:
                self._settings = get_settings()
            self._prompt_builder = PromptBuilder(self._settings)
        return self._prompt_builder

    def _model_name(self) -> str:
        """返回当前问答测试使用的模型名称。"""
        if self._settings is None:
            self._settings = get_settings()
        return self._settings.model

    def _build_qa_messages(self, question: str, citations: list[dict]) -> list[dict[str, str]]:
        """把召回 chunk 组装成 RAG 问答 prompt。"""
        return self._prompt_builder_instance().build_knowledge_qa_messages(question, citations)


def _sse(event: str, data: dict) -> str:
    """拼接一条 SSE 报文。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
