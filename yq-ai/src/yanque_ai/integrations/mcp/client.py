"""Bear MCP Resource 和 Tool 客户端封装。"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TypeVar

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool

from ...common.config import Settings


T = TypeVar("T")


def _build_bear_client(settings: Settings) -> MultiServerMCPClient:
    """创建带 Bear Token 的 Streamable HTTP 客户端。"""

    return MultiServerMCPClient(
        {
            "bear": {
                "transport": "streamable_http",
                "url": settings.bear_mcp_url,
                "headers": {
                    "Authorization": f"Bearer {settings.bear_mcp_token}",
                },
            }
        }
    )


class McpResourceClient:
    """读取 Bear MCP Server 暴露的 Resource。"""

    def __init__(self, settings: Settings) -> None:
        self._client = _build_bear_client(settings)

    def read_text(self, uri: str) -> str:
        """读取指定 Resource URI 的 Markdown 正文。"""

        return _run_async(self._read_text(uri))

    async def _read_text(self, uri: str) -> str:
        resources = await self._client.get_resources("bear", uris=uri)
        if not resources:
            return ""
        return resources[0].as_string()


class McpToolClient:
    """加载 Bear MCP Server 暴露的 LangChain Tool。"""

    def __init__(
        self,
        settings: Settings,
        client: MultiServerMCPClient | None = None,
    ) -> None:
        self._client = client or _build_bear_client(settings)

    async def get_tool(self, tool_name: str) -> BaseTool:
        """按精确名称加载一个工具，防止 Agent 获得无关能力。"""

        normalized_name = tool_name.strip()
        tools = await self._client.get_tools(server_name="bear")
        for tool in tools:
            if tool.name == normalized_name:
                return tool
        raise LookupError(f"Bear MCP 未提供工具：{normalized_name}")


def _run_async(awaitable: Awaitable[T]) -> T:
    """在当前同步 Text-to-SQL 图里执行一个 async MCP 调用。"""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    raise RuntimeError("当前 Text-to-SQL 图是同步执行，不能在已有事件循环里调用 MCP Resource")
