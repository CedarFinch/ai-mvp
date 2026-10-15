"""意图识别出入参和内部契约。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class IntentType(StrEnum):
    """模型识别出来的用户问题类型。"""

    # 用户想查已有业务数据，例如“昨天订单量是多少”“最近作业提交率怎么样”。
    DATA_QUERY = "DATA_QUERY"
    # 普通聊天、系统能力询问、业务规则解释，不需要生成 SQL。
    GENERAL_CHAT = "GENERAL_CHAT"
    # 用户想改数据或触发业务动作，例如新增、修改、删除、审批、导出全部数据。
    DATA_OPERATION = "DATA_OPERATION"
    # 问题不属于当前系统支持的数据范围，例如外部平台、天气、股票等。
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    # 问法太短或信息不足，暂时无法判断应该查询数据还是走其他流程。
    AMBIGUOUS = "AMBIGUOUS"


class IntentAction(StrEnum):
    """识别出 intent 后，Text-to-SQL 图下一步要走的动作。"""

    # 进入后续 Text-to-SQL 链路，后面会继续做查询规划、选表、生成 SQL。
    ENTER_TEXT_TO_SQL = "ENTER_TEXT_TO_SQL"
    # 不走 Text-to-SQL，后续可以转给普通问答或知识库问答模块。
    ROUTE_GENERAL_CHAT = "ROUTE_GENERAL_CHAT"
    # 拒绝写操作或高风险操作，避免 Text-to-SQL 直接改业务数据。
    REJECT_OPERATION = "REJECT_OPERATION"
    # 告诉用户当前问题不在系统支持的数据范围内。
    EXPLAIN_SCOPE = "EXPLAIN_SCOPE"
    # 先向用户追问必要信息，等问题明确后再重新进入流程。
    ASK_CLARIFICATION = "ASK_CLARIFICATION"


class IntentRecognitionResult(BaseModel):
    """意图识别的结构化结果。"""

    intent: IntentType = Field(description="固定意图枚举")
    reason: str = Field(min_length=1, max_length=500, description="分类原因")

    # 用户问题属于哪个业务域。
    # 这个字段不只给指标检索用，业务说明、查询注意事项、口径解释也可以按它缩小范围。
    # 例如“昨天订单量是多少”“支付成功金额是多少”“退款金额是多少”都属于“order”。
    business_domain: str | None = Field(
        default=None,
        max_length=100,
        description="用户问题所属业务域",
    )

    # 清理后的问题会继续交给后面的查询规划节点使用。
    # 例如把多余空格、换行去掉，但不改变用户原本的业务含义。
    normalized_question: str = Field(
        min_length=1,
        max_length=8000,
        description="清理后的用户问题",
    )

    # 只有 intent=AMBIGUOUS 时才需要填写，而且必须填写。
    # 例如用户只说“订单”，系统不知道是查订单数据还是问订单规则，就需要追问。
    clarification_question: str | None = Field(
        default=None,
        max_length=500,
        description="需要用户补充说明时的追问问题",
    )
