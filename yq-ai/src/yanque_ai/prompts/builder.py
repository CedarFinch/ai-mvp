"""通用提示词消息组装。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..common.config import Settings
from ..integrations.java import JavaPromptClient
from .codes import (
    CHAT_SUMMARY_SYSTEM,
    CHAT_SUMMARY_USER,
    KNOWLEDGE_QA_SYSTEM,
    KNOWLEDGE_QA_USER,
    STUDENT_CHAT_NO_RAG_USER,
    STUDENT_CHAT_RAG_USER,
    STUDENT_CHAT_SUMMARY_CONTEXT,
    STUDENT_CHAT_SYSTEM,
)
from .renderer import render_prompt


class MessageLike(Protocol):
    """可转换为模型消息的历史消息对象。"""

    role: str
    content: str


@dataclass(frozen=True)
class PromptSpec:
    """一段需要读取并渲染的提示词。"""

    code: str
    role: str
    variables: dict[str, str] | None = None


class PromptBuilder:
    """统一读取数据库提示词并组装模型 messages。"""

    def __init__(self, settings: Settings, prompt_client: JavaPromptClient | None = None) -> None:
        self._prompt_client = prompt_client or JavaPromptClient(settings)

    def build_messages(
        self,
        prompt_specs: list[PromptSpec],
        *,
        history: list[MessageLike] | None = None,
    ) -> list[dict[str, str]]:
        """按提示词规格读取、渲染并组装 OpenAI-compatible messages。"""
        messages: list[dict[str, str]] = []
        inserted_history = False
        last_user_index = self._last_user_spec_index(prompt_specs)

        for index, spec in enumerate(prompt_specs):
            if not inserted_history and history and index == last_user_index:
                messages.extend(self._history_messages(history))
                inserted_history = True

            template = self._prompt_client.get_active_prompt_content(spec.code)
            messages.append(
                {
                    "role": spec.role,
                    "content": render_prompt(template, spec.variables).strip(),
                }
            )

        if not inserted_history and history:
            messages.extend(self._history_messages(history))

        return messages

    def build_student_chat_messages(
        self,
        question: str,
        history: list[MessageLike],
        *,
        summary: str | None,
        citations: list[dict] | None,
        max_history_messages: int,
    ) -> list[dict[str, str]]:
        """组装学生问答 messages。"""
        prompt_specs = [PromptSpec(code=STUDENT_CHAT_SYSTEM, role="system")]
        if summary and summary.strip():
            prompt_specs.append(
                PromptSpec(
                    code=STUDENT_CHAT_SUMMARY_CONTEXT,
                    role="system",
                    variables={"summary": summary.strip()},
                )
            )
        if citations is None:
            messages = self.build_messages(
                prompt_specs,
                history=self._recent_history(history, max_history_messages),
            )
            messages.append({"role": "user", "content": question})
            return messages

        prompt_specs.append(self._student_user_prompt_spec(question, citations))
        return self.build_messages(
            prompt_specs,
            history=self._recent_history(history, max_history_messages),
        )

    def build_summary_messages(
        self,
        old_summary: str | None,
        messages_to_compress: list[MessageLike],
    ) -> list[dict[str, str]]:
        """组装对话摘要 messages。"""
        return self.build_messages(
            [
                PromptSpec(code=CHAT_SUMMARY_SYSTEM, role="system"),
                PromptSpec(
                    code=CHAT_SUMMARY_USER,
                    role="user",
                    variables={
                        "summary": (old_summary or "").strip() or "无",
                        "messages": self._summary_messages_text(messages_to_compress),
                    },
                ),
            ]
        )

    def build_knowledge_qa_messages(self, question: str, citations: list[dict]) -> list[dict[str, str]]:
        """组装知识库问答测试 messages。"""
        return self.build_messages(
            [
                PromptSpec(code=KNOWLEDGE_QA_SYSTEM, role="system"),
                PromptSpec(
                    code=KNOWLEDGE_QA_USER,
                    role="user",
                    variables={"question": question, "context": self._citations_context(citations)},
                ),
            ]
        )

    def _student_user_prompt_spec(self, question: str, citations: list[dict]) -> PromptSpec:
        """根据 RAG 结果选择学生问答 user prompt。"""
        if not citations:
            return PromptSpec(code=STUDENT_CHAT_NO_RAG_USER, role="user", variables={"question": question})
        return PromptSpec(
            code=STUDENT_CHAT_RAG_USER,
            role="user",
            variables={"question": question, "context": self._citations_context(citations)},
        )

    def _recent_history(self, history: list[MessageLike], max_history_messages: int) -> list[MessageLike]:
        """截取最近历史，并避免 assistant 消息作为第一条历史。"""
        recent = list(history[-max_history_messages:] if max_history_messages > 0 else [])
        while recent and recent[0].role == "assistant":
            recent.pop(0)
        return recent

    def _history_messages(self, history: list[MessageLike]) -> list[dict[str, str]]:
        """把历史对象转成模型消息。"""
        return [{"role": item.role, "content": item.content} for item in history if item.content.strip()]

    def _citations_context(self, citations: list[dict]) -> str:
        """把召回结果转换成提示词上下文。"""
        return "\n\n".join(
            f"[{item.get('rank', index + 1)}] 文档编码：{item.get('document_code', '')}，"
            f"chunk：{int(item.get('chunk_index') or 0) + 1}\n{item.get('content', '')}"
            for index, item in enumerate(citations)
        )

    def _summary_messages_text(self, messages_to_compress: list[MessageLike]) -> str:
        """把待压缩消息转换成摘要提示词文本。"""
        lines: list[str] = []
        for item in messages_to_compress:
            role_name = "学生" if item.role == "user" else "AI"
            lines.append(f"{role_name}：{item.content}")
        return "\n".join(lines)

    def _last_user_spec_index(self, prompt_specs: list[PromptSpec]) -> int:
        """找到最后一个 user 提示词段，history 插到它前面。"""
        for index in range(len(prompt_specs) - 1, -1, -1):
            if prompt_specs[index].role == "user":
                return index
        return len(prompt_specs)
