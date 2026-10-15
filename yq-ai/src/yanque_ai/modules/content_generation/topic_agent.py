"""通过 Bear MCP 热点工具生成结构化候选选题。"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool

from ...common.config import Settings
from ...common.errors import AIServiceError
from ...integrations.java import JavaPromptClient
from ...integrations.langchain_model import build_chat_model
from ...integrations.mcp import McpToolClient
from ...prompts.codes import CONTENT_TOPIC_DISCOVERY_SYSTEM
from .schemas import (
    TopicCandidate,
    TopicGenerationResult,
    TopicSourceVideo,
)


HOTSPOT_TOOL_NAME = "query_douyin_hotspots"


class TopicDiscoveryAgent:
    """只拥有热点查询工具的选题 Agent。"""

    def __init__(
        self,
        settings: Settings,
        *,
        mcp_client: McpToolClient | None = None,
        model: BaseChatModel | None = None,
        prompt_client: JavaPromptClient | None = None,
    ) -> None:
        self._settings = settings
        self._mcp_client = mcp_client or McpToolClient(settings)
        self._model = model or build_chat_model(
            settings,
            temperature=0.2,
            enable_thinking=False,
        )
        prompt_code = settings.content_topic_discovery_prompt_code or CONTENT_TOPIC_DISCOVERY_SYSTEM
        self._system_prompt = (prompt_client or JavaPromptClient(settings)).get_active_prompt_content(
            prompt_code
        )

    async def generate(
        self,
        *,
        days: int,
        hotspot_limit: int,
        candidate_count: int,
        regeneration_feedback: str,
    ) -> list[TopicCandidate]:
        """调用热点工具并生成经过来源校验的候选选题。"""

        try:
            return await asyncio.wait_for(
                self._generate(
                    days=days,
                    hotspot_limit=hotspot_limit,
                    candidate_count=candidate_count,
                    regeneration_feedback=regeneration_feedback,
                ),
                timeout=self._settings.content_topic_timeout_seconds,
            )
        except TimeoutError as exc:
            raise AIServiceError(
                "CONTENT_TOPIC_TIMEOUT",
                "选题生成超时，请稍后重试。",
                status_code=504,
            ) from exc
        except AIServiceError:
            raise
        except Exception as exc:
            raise AIServiceError(
                "CONTENT_TOPIC_GENERATION_FAILED",
                "选题 Agent 调用失败，请稍后重试。",
                status_code=502,
            ) from exc

    async def _generate(
        self,
        *,
        days: int,
        hotspot_limit: int,
        candidate_count: int,
        regeneration_feedback: str,
    ) -> list[TopicCandidate]:
        tool = await self._load_hotspot_tool()
        agent = create_agent(
            model=self._model,
            tools=[tool],
            system_prompt=self._system_prompt,
            response_format=ToolStrategy(TopicGenerationResult),
            name="topic_discovery_agent",
        )
        result = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": _build_user_message(
                            days=days,
                            hotspot_limit=hotspot_limit,
                            candidate_count=candidate_count,
                            regeneration_feedback=regeneration_feedback,
                        ),
                    }
                ]
            }
        )
        hotspots = _extract_hotspots(result.get("messages", []))
        structured = result.get("structured_response")
        if not isinstance(structured, TopicGenerationResult):
            raise AIServiceError(
                "CONTENT_TOPIC_INVALID_OUTPUT",
                "选题 Agent 未返回正确的结构化结果。",
                status_code=502,
            )
        return _validate_and_enrich_topics(structured, hotspots, candidate_count)

    async def _load_hotspot_tool(self) -> BaseTool:
        """区分工具未发布和 Bear MCP 无法连接两类错误。"""

        try:
            return await self._mcp_client.get_tool(HOTSPOT_TOOL_NAME)
        except LookupError as exc:
            raise AIServiceError(
                "BEAR_MCP_TOOL_NOT_FOUND",
                f"Bear MCP 未找到 {HOTSPOT_TOOL_NAME} 工具。",
                status_code=502,
            ) from exc
        except Exception as exc:
            raise AIServiceError(
                "BEAR_MCP_CONNECTION_FAILED",
                "无法连接 Bear MCP 或加载抖音热点工具。",
                status_code=502,
            ) from exc


def _build_user_message(
    *,
    days: int,
    hotspot_limit: int,
    candidate_count: int,
    regeneration_feedback: str,
) -> str:
    """把本轮确定性约束交给 Agent。"""

    return (
        f"重新生成反馈：{regeneration_feedback.strip() or '无'}\n"
        f"请先调用 {HOTSPOT_TOOL_NAME}，参数 days={days}、limit={hotspot_limit}。\n"
        f"然后严格基于工具返回的视频生成 {candidate_count} 个不同候选选题。"
        "每个选题至少引用一个真实 video_id，不得编造热点、数据或视频ID。"
    )


def _extract_hotspots(messages: list[Any]) -> dict[str, dict[str, Any]]:
    """从真实 ToolMessage 中提取热点，并建立视频 ID 索引。"""

    tool_messages = [
        message
        for message in messages
        if isinstance(message, ToolMessage)
        and getattr(message, "name", None) == HOTSPOT_TOOL_NAME
    ]
    if not tool_messages:
        raise AIServiceError(
            "BEAR_MCP_TOOL_NOT_CALLED",
            "选题 Agent 没有调用抖音热点工具，已停止生成。",
            status_code=502,
        )

    envelope: dict[str, Any] | None = None
    for message in reversed(tool_messages):
        envelope = _find_hotspot_envelope(getattr(message, "artifact", None))
        if envelope is None:
            envelope = _find_hotspot_envelope(message.content)
        if envelope is not None:
            break
    if envelope is None:
        raise AIServiceError(
            "BEAR_MCP_INVALID_RESPONSE",
            "抖音热点工具返回格式无法识别。",
            status_code=502,
        )
    if envelope.get("success") is False:
        raise AIServiceError(
            "BEAR_MCP_TOOL_ERROR",
            str(envelope.get("message") or "抖音热点工具调用失败。"),
            status_code=502,
        )

    rows = envelope.get("hotspots")
    if not isinstance(rows, list) or not rows:
        raise AIServiceError(
            "NO_HOTSPOT_DATA",
            "最近时间范围内没有可用于选题的热点视频。",
            status_code=422,
        )
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        video_id = str(row.get("video_id") or "").strip()
        if video_id:
            index[video_id] = row
    if not index:
        raise AIServiceError(
            "NO_HOTSPOT_DATA",
            "热点工具没有返回有效的视频ID。",
            status_code=422,
        )
    return index


def _find_hotspot_envelope(value: Any) -> dict[str, Any] | None:
    """兼容 MCP 文本块、structuredContent 和普通 JSON。"""

    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return _find_hotspot_envelope(value.model_dump(mode="json"))
    if isinstance(value, str):
        try:
            return _find_hotspot_envelope(json.loads(value))
        except (json.JSONDecodeError, TypeError):
            return None
    if isinstance(value, list):
        for item in value:
            found = _find_hotspot_envelope(item)
            if found is not None:
                return found
        return None
    if not isinstance(value, dict):
        return None
    if "hotspots" in value:
        return value
    for key in ("structuredContent", "structured_content", "result", "data", "content", "text"):
        if key in value:
            found = _find_hotspot_envelope(value[key])
            if found is not None:
                return found
    return None


def _validate_and_enrich_topics(
    result: TopicGenerationResult,
    hotspots: dict[str, dict[str, Any]],
    candidate_count: int,
) -> list[TopicCandidate]:
    """校验数量和引用来源，并使用工具原始值覆盖展示字段。"""

    if len(result.topics) != candidate_count:
        raise AIServiceError(
            "CONTENT_TOPIC_COUNT_MISMATCH",
            f"选题 Agent 应返回 {candidate_count} 个选题，实际返回 {len(result.topics)} 个。",
            status_code=502,
        )

    candidates: list[TopicCandidate] = []
    for index, draft in enumerate(result.topics, start=1):
        unique_ids = list(
            dict.fromkeys(
                str(item).strip()
                for item in draft.source_video_ids
                if str(item).strip()
            )
        )
        invalid_ids = [video_id for video_id in unique_ids if video_id not in hotspots]
        if not unique_ids or invalid_ids:
            raise AIServiceError(
                "CONTENT_TOPIC_INVALID_SOURCE",
                "选题 Agent 引用了热点工具结果中不存在的视频ID。",
                status_code=502,
            )
        sources = [
            TopicSourceVideo(
                video_id=video_id,
                title=_optional_text(hotspots[video_id].get("title")),
                video_url=_optional_text(hotspots[video_id].get("video_url")),
                like_count=_optional_int(hotspots[video_id].get("like_count")),
                like_increase=_optional_int(hotspots[video_id].get("like_increase")),
            )
            for video_id in unique_ids
        ]
        candidates.append(
            TopicCandidate(
                topic_id=f"topic-{index}",
                title=draft.title,
                core_event=draft.core_event,
                creation_angle=draft.creation_angle,
                target_audience=draft.target_audience,
                reason=draft.reason,
                source_videos=sources,
            )
        )
    return candidates


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
