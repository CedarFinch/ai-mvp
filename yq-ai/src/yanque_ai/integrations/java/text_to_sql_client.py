"""Java Text-to-SQL 查询中心客户端。"""

from __future__ import annotations

from dataclasses import dataclass, field

from ...common.config import Settings
from ..http_client import HttpJsonClient, HttpJsonError


class TextToSqlExecuteError(RuntimeError):
    """调用 Java 查询中心失败。"""


@dataclass(frozen=True)
class SqlExecutionResult:
    """Java 查询中心返回的 SQL 执行结果。"""

    success: bool
    message: str
    sql: str | None = None
    rows: list[dict[str, object]] = field(default_factory=list)
    row_count: int = 0
    validation: dict[str, object] | None = None
    permission: dict[str, object] | None = None
    explain: dict[str, object] | None = None


class JavaTextToSqlClient:
    """通过 Java 内部接口执行 Text-to-SQL 生成的 SQL。"""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.yanque_admin_base_url.rstrip("/")
        self._http_client = HttpJsonClient(
            timeout_seconds=settings.prompt_query_timeout_seconds,
            user_agent="YanQue-AI/text-to-sql-client",
        )

    def execute_sql(
        self,
        *,
        sql: str,
        table_ddl_context: str,
        user_id: str | None = None,
        roles: list[str] | None = None,
        business_domain: str | None = None,
        max_rows: int = 100,
    ) -> SqlExecutionResult:
        """调用 Java 查询中心执行 SQL。

        Java 会按 AST 安全校验、角色数据权限校验、真实查询的顺序执行。
        """

        url = f"{self._base_url}/yq-admin/internal/ai/text-to-sql/sql/execute"
        try:
            payload = self._http_client.post_json(
                url,
                {
                    "sql": sql,
                    "tableDdlContext": table_ddl_context,
                    "userId": _parse_long(user_id),
                    "roleCodes": roles or [],
                    "businessDomain": business_domain,
                    "maxRows": max_rows,
                },
            )
        except HttpJsonError as exc:
            raise TextToSqlExecuteError(f"Text-to-SQL执行接口调用失败: {exc}") from exc

        if int(payload.get("code") or 0) != 200:
            raise TextToSqlExecuteError(f"Text-to-SQL执行业务失败: message={payload.get('message')}")

        data = payload.get("data") or {}
        rows = data.get("rows") or []
        return SqlExecutionResult(
            success=bool(data.get("success")),
            message=str(data.get("message") or ""),
            sql=data.get("sql"),
            rows=rows if isinstance(rows, list) else [],
            row_count=int(data.get("rowCount") or 0),
            validation=data.get("validation"),
            permission=data.get("permission"),
            explain=data.get("explain"),
        )


def _parse_long(value: str | None) -> int | None:
    """Java 的 userId 是 Long；非数字 ID 不传，避免反序列化失败。"""

    if value is None:
        return None
    text = value.strip()
    return int(text) if text.isdigit() else None
