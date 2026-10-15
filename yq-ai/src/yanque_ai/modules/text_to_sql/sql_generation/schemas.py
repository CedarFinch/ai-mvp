"""SQL 生成节点的结构化结果。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SqlGenerationAction(StrEnum):
    """SQL 生成节点判断出来的下一步动作。"""

    # 上下文足够，已经生成 SQL。
    SQL_READY = "SQL_READY"
    # SQL 口径不够明确，需要先追问用户。
    ASK_CLARIFICATION = "ASK_CLARIFICATION"


class SqlGenerationResult(BaseModel):
    """模型根据上下文生成 SQL，或发起 SQL 口径澄清。"""

    # SQL 生成节点的判断结果：能生成 SQL，还是需要用户补充 SQL 口径。
    action: SqlGenerationAction = Field(description="SQL 生成节点的下一步动作")
    # 只有 action = SQL_READY 时才填写 SQL；ASK_CLARIFICATION 时保持为空。
    sql: str | None = Field(
        default=None,
        max_length=12000,
        description="根据问题、指标、业务说明和 DDL 生成的一条只读 SQL",
    )
    # 模型为什么这样判断或为什么这样写 SQL。
    reason: str = Field(
        min_length=1,
        max_length=1000,
        description="SQL 生成依据或无法生成 SQL 的原因",
    )
    # action = ASK_CLARIFICATION 时填写要追问用户的问题。
    clarification_question: str | None = Field(
        default=None,
        max_length=500,
        description="需要向用户追问的问题",
    )
