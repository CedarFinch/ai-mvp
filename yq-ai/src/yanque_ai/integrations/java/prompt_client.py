"""Java 提示词中心客户端。"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from ...common.config import Settings
from ...common.errors import PromptLoadError
from ..http_client import HttpJsonClient, HttpJsonError


@dataclass(frozen=True)
class PromptTemplate:
    """当前启用提示词。"""

    code: str
    name: str
    agent_code: str
    prompt_type: str
    scene_code: str | None
    version_id: int
    version_no: int
    content: str
    variables: str | None
    update_time: str | None


class JavaPromptClient:
    """通过 Java 内部接口读取当前启用提示词。"""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.yanque_admin_base_url.rstrip("/")
        self._http_client = HttpJsonClient(
            timeout_seconds=settings.prompt_query_timeout_seconds,
            user_agent="YanQue-AI/prompt-client",
        )

    def get_active_prompt(self, code: str) -> PromptTemplate:
        """按编码读取当前启用提示词。"""
        normalized_code = code.strip()
        if not normalized_code:
            raise PromptLoadError("提示词编码不能为空")

        url = f"{self._base_url}/yq-admin/internal/ai/prompts/active?{urlencode({'code': normalized_code})}"
        try:
            payload = self._http_client.get_json(url)
        except HttpJsonError as exc:
            raise PromptLoadError(f"提示词查询接口调用失败: code={normalized_code}, {exc}") from exc

        if int(payload.get("code") or 0) != 200:
            raise PromptLoadError(f"提示词查询业务失败: code={normalized_code}, message={payload.get('message')}")

        data = payload.get("data") or {}
        content = str(data.get("content") or "").strip()
        if not content:
            raise PromptLoadError(f"提示词内容为空: code={normalized_code}")

        return PromptTemplate(
            code=str(data.get("code") or normalized_code),
            name=str(data.get("name") or ""),
            agent_code=str(data.get("agentCode") or ""),
            prompt_type=str(data.get("promptType") or ""),
            scene_code=data.get("sceneCode"),
            version_id=int(data.get("versionId") or 0),
            version_no=int(data.get("versionNo") or 0),
            content=content,
            variables=data.get("variables"),
            update_time=data.get("updateTime"),
        )

    def get_active_prompt_content(self, code: str) -> str:
        """按编码读取当前启用提示词内容。"""
        return self.get_active_prompt(code).content
