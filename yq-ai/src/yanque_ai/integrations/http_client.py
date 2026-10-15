"""外部服务 HTTP JSON 调用工具。

业务模块不要直接写 urlopen / headers / JSON 解析这些细节。
统一放在这里，后续接 Java、Bear 或其它内部服务时都复用这一层。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class HttpJsonError(RuntimeError):
    """HTTP JSON 调用失败。"""


@dataclass(frozen=True)
class HttpJsonClient:
    """最小 HTTP JSON 客户端。

    这里只负责外部服务调用的公共动作：
    1. 拼 JSON 请求体；
    2. 设置通用请求头；
    3. 发起 HTTP 请求；
    4. 把响应解析成 dict。
    """

    timeout_seconds: float
    user_agent: str = "YanQue-AI/http-client"

    def get_json(self, url: str) -> dict[str, object]:
        """发送 GET 请求，并把响应体解析成 JSON 对象。"""

        request = Request(url, headers=self._headers())
        return self._send(request)

    def post_json(self, url: str, body: dict[str, object]) -> dict[str, object]:
        """发送 POST JSON 请求，并把响应体解析成 JSON 对象。"""

        request = Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(content_type=True),
            method="POST",
        )
        return self._send(request)

    def _headers(self, *, content_type: bool = False) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if content_type:
            headers["Content-Type"] = "application/json; charset=UTF-8"
        return headers

    def _send(self, request: Request) -> dict[str, object]:
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise HttpJsonError(f"HTTP请求失败: status={exc.code}") from exc
        except URLError as exc:
            raise HttpJsonError(f"HTTP连接失败: error={exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise HttpJsonError("HTTP响应不是合法JSON。") from exc
        except Exception as exc:
            raise HttpJsonError(f"HTTP调用失败: error={exc}") from exc
