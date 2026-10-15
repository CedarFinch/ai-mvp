"""AI 服务配置。

所有配置只从环境变量读取，模型 Key 只存在于这一层，不会出现在 Java 侧。
本地开发可以在项目根目录放一个 .env 文件，参考 .env.example。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv(override=False)

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3.7-plus"


class ConfigError(RuntimeError):
    """配置缺失或不合法。"""


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    temperature: float
    max_tokens: int | None
    timeout_seconds: float
    max_retries: int
    media_transcript_model: str
    media_transcript_enable_thinking: bool
    media_material_model: str
    media_material_collection: str
    yanque_admin_base_url: str
    prompt_query_timeout_seconds: float
    max_history_messages: int
    chat_rag_enabled: bool
    chat_rag_collection: str
    chat_rag_recall_mode: str
    chat_rag_top_k: int
    chat_rag_recall_top_k: int
    chat_rag_rerank_enabled: bool
    chat_rag_rerank_model: str
    chat_rag_rerank_base_url: str
    chat_rag_rerank_min_score: float
    text_to_sql_intent_prompt_code: str
    text_to_sql_select_tables_prompt_code: str
    text_to_sql_generate_sql_prompt_code: str
    text_to_sql_result_summary_prompt_code: str
    text_to_sql_metric_collection: str
    text_to_sql_metric_top_k: int
    text_to_sql_metric_recall_top_k: int
    text_to_sql_rerank_enabled: bool
    text_to_sql_rerank_min_score: float
    bear_mcp_url: str
    bear_mcp_token: str
    content_topic_discovery_prompt_code: str
    content_topic_timeout_seconds: float

    @property
    def masked_api_key(self) -> str:
        """日志里只打掩码，绝不打印完整 Key。"""
        if len(self.api_key) <= 8:
            return "***"
        return f"{self.api_key[:4]}****{self.api_key[-4:]}"


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"环境变量 {name} 必须是数字，当前值：{raw}") from exc


def _get_int(name: str, default: int | None) -> int | None:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"环境变量 {name} 必须是整数，当前值：{raw}") from exc


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if not raw:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ConfigError(f"环境变量 {name} 必须是布尔值，当前值：{raw}")


def _build_base_url() -> str:
    """优先用显式 BASE_URL；配了业务空间就用业务空间域名；都没有就用公共入口。"""
    base_url = os.getenv("BAILIAN_BASE_URL")
    if base_url:
        return base_url.rstrip("/")

    workspace_id = os.getenv("BAILIAN_WORKSPACE_ID")
    if workspace_id:
        return f"https://{workspace_id}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"

    return DEFAULT_BASE_URL


def _build_rerank_base_url() -> str:
    """qwen3-rerank 使用 compatible-api/v1，和 chat 的 compatible-mode/v1 不同。"""
    base_url = os.getenv("BAILIAN_RERANK_BASE_URL")
    if base_url:
        return base_url.rstrip("/")

    return _build_base_url().replace("/compatible-mode/v1", "/compatible-api/v1")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """读取配置，进程内只解析一次。"""
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError(
            "未配置 DASHSCOPE_API_KEY。请在 .env 或环境变量里设置百炼 API Key。"
        )

    return Settings(
        api_key=api_key,
        base_url=_build_base_url(),
        model=os.getenv("BAILIAN_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        temperature=_get_float("BAILIAN_TEMPERATURE", 0.7),
        max_tokens=_get_int("BAILIAN_MAX_TOKENS", None),
        timeout_seconds=_get_float("BAILIAN_TIMEOUT_SECONDS", 180.0),
        max_retries=_get_int("BAILIAN_MAX_RETRIES", 2) or 0,
        media_transcript_model=os.getenv(
            "MEDIA_TRANSCRIPT_MODEL",
            "qwen3.8-flash",
        ).strip()
        or "qwen3.8-flash",
        media_transcript_enable_thinking=_get_bool(
            "MEDIA_TRANSCRIPT_ENABLE_THINKING",
            False,
        ),
        media_material_model=os.getenv(
            "MEDIA_MATERIAL_MODEL",
            "qwen3.8-flash",
        ).strip()
        or "qwen3.8-flash",
        media_material_collection=os.getenv(
            "MEDIA_MATERIAL_COLLECTION",
            "media_material",
        ).strip()
        or "media_material",
        yanque_admin_base_url=os.getenv("YANQUE_ADMIN_BASE_URL", "http://localhost:8080").strip()
        or "http://localhost:8080",
        prompt_query_timeout_seconds=_get_float("PROMPT_QUERY_TIMEOUT_SECONDS", 5.0),
        max_history_messages=_get_int("BAILIAN_MAX_HISTORY_MESSAGES", 20) or 20,
        chat_rag_enabled=_get_bool("AI_CHAT_RAG_ENABLED", True),
        chat_rag_collection=os.getenv("AI_CHAT_RAG_COLLECTION", "student_qa").strip() or "student_qa",
        chat_rag_recall_mode=os.getenv("AI_CHAT_RAG_RECALL_MODE", "HYBRID").strip().upper()
        or "HYBRID",
        chat_rag_top_k=_get_int("AI_CHAT_RAG_TOP_K", 5) or 5,
        chat_rag_recall_top_k=_get_int("AI_CHAT_RAG_RECALL_TOP_K", 20) or 20,
        chat_rag_rerank_enabled=_get_bool("AI_CHAT_RAG_RERANK_ENABLED", True),
        chat_rag_rerank_model=os.getenv("AI_CHAT_RAG_RERANK_MODEL", "qwen3-rerank").strip()
        or "qwen3-rerank",
        chat_rag_rerank_base_url=_build_rerank_base_url(),
        chat_rag_rerank_min_score=_get_float("AI_CHAT_RAG_RERANK_MIN_SCORE", 0.6),
        text_to_sql_intent_prompt_code=os.getenv(
            "TEXT_TO_SQL_INTENT_PROMPT_CODE",
            "text_to_sql_intent_system",
        ).strip()
        or "text_to_sql_intent_system",
        text_to_sql_select_tables_prompt_code=os.getenv(
            "TEXT_TO_SQL_SELECT_TABLES_PROMPT_CODE",
            "text_to_sql_select_tables_system",
        ).strip()
        or "text_to_sql_select_tables_system",
        text_to_sql_generate_sql_prompt_code=os.getenv(
            "TEXT_TO_SQL_GENERATE_SQL_PROMPT_CODE",
            "text_to_sql_generate_sql_system",
        ).strip()
        or "text_to_sql_generate_sql_system",
        text_to_sql_result_summary_prompt_code=os.getenv(
            "TEXT_TO_SQL_RESULT_SUMMARY_PROMPT_CODE",
            "text_to_sql_result_summary_system",
        ).strip()
        or "text_to_sql_result_summary_system",
        text_to_sql_metric_collection=os.getenv(
            "TEXT_TO_SQL_METRIC_COLLECTION",
            "text_to_sql_metrics",
        ).strip()
        or "text_to_sql_metrics",
        text_to_sql_metric_top_k=_get_int("TEXT_TO_SQL_METRIC_TOP_K", 5) or 5,
        text_to_sql_metric_recall_top_k=_get_int("TEXT_TO_SQL_METRIC_RECALL_TOP_K", 20) or 20,
        text_to_sql_rerank_enabled=_get_bool("TEXT_TO_SQL_RERANK_ENABLED", True),
        text_to_sql_rerank_min_score=_get_float("TEXT_TO_SQL_RERANK_MIN_SCORE", 0.6),
        bear_mcp_url=os.getenv("BEAR_MCP_URL", "http://localhost:8090/mcp").strip()
        or "http://localhost:8090/mcp",
        bear_mcp_token=os.getenv("BEAR_MCP_TOKEN", "mcp_dev_token").strip() or "mcp_dev_token",
        content_topic_discovery_prompt_code=os.getenv(
            "CONTENT_TOPIC_DISCOVERY_PROMPT_CODE",
            "content_topic_discovery_system",
        ).strip()
        or "content_topic_discovery_system",
        content_topic_timeout_seconds=_get_float("CONTENT_TOPIC_TIMEOUT_SECONDS", 30.0),
    )
