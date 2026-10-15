"""聊天问答编排服务。"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator

from ...common.config import Settings
from ...common.errors import AIServiceError
from ...integrations.bailian.client import BailianClient, RerankResult
from ...prompts import PromptBuilder
from ..knowledge.vector_store import KnowledgeVectorStore, load_milvus_config
from .schemas import ChatRequest, SummaryRequest


logger = logging.getLogger(__name__)


class ChatService:
    """把 Java 传来的上下文转成模型消息，再整理成 Java 可转发的 SSE。"""

    def __init__(self, client: BailianClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings
        self._prompt_builder = PromptBuilder(settings)
        self._vector_store: KnowledgeVectorStore | None = None

    def _messages(self, request: ChatRequest) -> list[dict[str, str]]:
        """把请求体转成模型需要的 messages。"""
        citations = self._recall_qa_context(request.question)
        return self._prompt_builder.build_student_chat_messages(
            request.question,
            list(request.history),
            summary=request.summary,
            citations=citations,
            max_history_messages=self._settings.max_history_messages,
        )



    def _recall_qa_context(self, question: str) -> list[dict] | None:
        """从固定 QA Collection 召回参考资料；失败时降级为普通问答。"""
        if not self._settings.chat_rag_enabled:
            return None

        try:
            candidates = self._knowledge_vector_store().recall(
                self._settings.chat_rag_collection,
                question.strip(),
                self._settings.chat_rag_recall_mode,
                self._rag_recall_top_k(),
            )
            return self._rerank_qa_context(question.strip(), candidates)
        except Exception:
            logger.warning(
                "学生问答RAG召回失败，降级为普通问答: collection=%s mode=%s",
                self._settings.chat_rag_collection,
                self._settings.chat_rag_recall_mode,
                exc_info=True,
            )
            return None

    def _rerank_qa_context(self, question: str, candidates: list[dict]) -> list[dict]:
        """使用 qwen3-rerank 重排候选，并过滤低相关分数。"""
        if not candidates:
            return []
        if not self._settings.chat_rag_rerank_enabled:
            return candidates[: self._rag_top_k()]

        try:
            indexed_documents = [
                (index, content)
                for index, item in enumerate(candidates)
                if (content := str(item.get("content") or "").strip())
            ]
            if not indexed_documents:
                return []
            documents = [content for _, content in indexed_documents]
            reranked = self._client.rerank(question, documents, top_n=len(documents))
        except Exception:
            logger.warning("学生问答RAG重排失败，使用原始召回顺序", exc_info=True)
            return candidates[: self._rag_top_k()]

        selected: list[dict] = []
        for result in reranked:
            if not self._passes_rerank_threshold(result):
                continue
            if result.index < 0 or result.index >= len(indexed_documents):
                continue
            original_index = indexed_documents[result.index][0]
            item = dict(candidates[original_index])
            item["rerank_score"] = result.score
            item["rank"] = len(selected) + 1
            selected.append(item)
            if len(selected) >= self._rag_top_k():
                break

        logger.info(
            "学生问答RAG重排完成: candidates=%d selected=%d min_score=%.3f",
            len(candidates),
            len(selected),
            self._settings.chat_rag_rerank_min_score,
        )
        return selected

    def _passes_rerank_threshold(self, result: RerankResult) -> bool:
        """判断重排分数是否达到入模阈值。"""
        return result.score >= self._settings.chat_rag_rerank_min_score

    def _knowledge_vector_store(self) -> KnowledgeVectorStore:
        """按需创建向量库客户端，避免关闭 RAG 时初始化知识库依赖。"""
        if self._vector_store is None:
            self._vector_store = KnowledgeVectorStore(load_milvus_config())
        return self._vector_store

    def _rag_top_k(self) -> int:
        """限制召回数量，保持和知识库召回接口相同的范围。"""
        return min(max(self._settings.chat_rag_top_k, 1), 20)

    def _rag_recall_top_k(self) -> int:
        """重排前召回更多候选，但仍限制在知识库召回接口允许范围内。"""
        return min(max(self._settings.chat_rag_recall_top_k, self._rag_top_k()), 20)

    def stream_chat(self, request: ChatRequest) -> Iterator[str]:
        """流式问答，产出 SSE 报文。"""
        try:
            messages = self._messages(request)
            model = self._settings.model
            for chunk in self._client.stream_chat(messages):
                if chunk.done:
                    payload = {
                        "model": model,
                        "finish_reason": chunk.finish_reason,
                        "truncated": chunk.finish_reason == "length",
                        "usage": (chunk.usage or None)
                        and chunk.usage.model_dump(),
                    }
                    logger.info("Python发送done")
                    yield _sse("done", payload)
                else:
                    logger.info("Python发送delta 长度=%d 内容=%s", len(chunk.delta), chunk.delta[:20])
                    yield _sse("delta", {"content": chunk.delta})
        except AIServiceError as exc:
            logger.warning("流式问答失败 code=%s message=%s", exc.code, exc.message)
            yield _sse("error", {"code": exc.code, "message": exc.message})
        except Exception as exc:
            logger.exception("流式问答未知异常")
            yield _sse("error", {"code": "INTERNAL_ERROR", "message": str(exc)})

    def summarize(self, request: SummaryRequest) -> str:
        """生成压缩摘要，供 Java 的会话压缩流程调用。"""
        messages = self._prompt_builder.build_summary_messages(
            request.summary,
            list(request.messages),
        )
        return self._client.summarize(messages)


def _sse(event: str, data: dict) -> str:
    """拼一条 SSE 报文，注意结尾必须是空行。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
