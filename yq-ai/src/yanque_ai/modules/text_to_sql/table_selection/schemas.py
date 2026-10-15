"""选表节点的结构化结果。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class TableSelectionAction(StrEnum):
    """选表节点下一步动作。"""

    SELECT_TABLES = "SELECT_TABLES"
    NEED_METRIC_CONTEXT = "NEED_METRIC_CONTEXT"
    NEED_BUSINESS_CONTEXT = "NEED_BUSINESS_CONTEXT"
    ASK_CLARIFICATION = "ASK_CLARIFICATION"


class TableSelectionResult(BaseModel):
    """模型从表目录里选出的候选表。"""

    action: TableSelectionAction = Field(
        default=TableSelectionAction.SELECT_TABLES,
        description=(
            "选表结果动作：能确定候选表时返回 SELECT_TABLES；"
            "需要补指标时返回 NEED_METRIC_CONTEXT；需要补业务说明时返回 NEED_BUSINESS_CONTEXT；"
            "需要用户补充信息时返回 ASK_CLARIFICATION"
        ),
    )

    # 后续 retrieve_table_ddl 节点会按这里的表名读取 DDL Resource。
    selected_tables: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="需要读取 DDL 的表名列表",
    )
    # 为什么选这些表。
    reason: str = Field(
        min_length=1,
        max_length=1000,
        description="选表原因",
    )
    clarification_question: str | None = Field(
        default=None,
        max_length=500,
        description="action=ASK_CLARIFICATION 时填写要追问用户的问题",
    )
    metric_query: str | None = Field(
        default=None,
        max_length=500,
        description="action=NEED_METRIC_CONTEXT 时填写需要继续检索指标知识库的问题",
    )
    business_domain: str | None = Field(
        default=None,
        max_length=100,
        description="action=NEED_BUSINESS_CONTEXT 时填写需要继续读取业务说明的业务域编码",
    )
