"""Text-to-SQL 对外契约。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...integrations.java.text_to_sql_client import SqlExecutionResult
from .result_summary import ResultChartData, ResultSummary
from .intent.schemas import (
    IntentAction,
    IntentRecognitionResult,
    IntentType,
)
from .sql_generation import SqlGenerationAction, SqlGenerationResult
from .table_selection import TableSelectionResult


class MetricHit(BaseModel):
    """从指标知识库召回的一条指标片段。"""

    rank: int = Field(description="召回排序，从 1 开始")
    score: float = Field(description="相关性分数，开启重排时为 rerank 分数")
    document_code: str = Field(description="指标文档编码")
    document_version: int = Field(description="指标文档版本")
    chunk_index: int = Field(description="命中的文档分块序号")
    content: str = Field(description="命中的指标口径内容")


class TextToSqlRequest(BaseModel):
    """Java 调用 Text-to-SQL 总接口的请求体。"""

    # 用户输入的原始问题。后续节点可以生成 normalized_question，但这里始终保留原文。
    question: str = Field(min_length=1, max_length=8000, description="用户原始问题")
    # 当前登录用户信息，MVP 阶段先接收不使用；后续做权限、数据范围过滤时会用到。
    user_id: str | None = Field(default=None, max_length=128, description="当前登录用户ID")
    # 用户角色，后续可用于判断能否查询某些业务数据。
    roles: list[str] = Field(default_factory=list, description="当前用户角色")
    # 明细查询最大返回行数；真正上限仍由 Java 查询中心控制。
    max_rows: int = Field(default=100, ge=1, le=500, description="最大返回行数")
    # LangGraph interrupt 暂停/恢复用的会话 ID。第一次请求可不传，接口会返回一个新的 ID。
    conversation_id: str | None = Field(default=None, max_length=128, description="Text-to-SQL 澄清会话ID")
    # 用户对上一次澄清问题的回答。传入后会用同一个 conversation_id 恢复图执行。
    clarification_answer: str | None = Field(default=None, max_length=8000, description="用户补充的澄清回答")


class TextToSqlMetricSearchRequest(BaseModel):
    """Text-to-SQL 指标口径检索请求。"""

    query: str = Field(min_length=1, max_length=8000, description="要检索的指标问题或关键词")
    top_k: int = Field(default=5, ge=1, le=20, description="返回指标片段数量")


class TextToSqlMetricSearchResponse(BaseModel):
    """Text-to-SQL 指标口径检索响应。"""

    query: str = Field(description="本次检索问题")
    collection_name: str = Field(description="Milvus 指标 Collection 名称")
    top_k: int = Field(description="本次返回数量上限")
    records: list[MetricHit] = Field(default_factory=list, description="命中的指标片段")
    metric_context: str = Field(description="拼接后的指标上下文，可直接交给 Text-to-SQL 后续步骤")


class TextToSqlSemanticJudgeRequest(BaseModel):
    """Text-to-SQL 评测里的语义断言请求。"""

    question: str = Field(min_length=1, max_length=8000, description="原始评测问题")
    actual_value: str = Field(default="", max_length=20000, description="本次运行产出的实际回答")
    reference_answer: str = Field(default="", max_length=20000, description="人工整理的参考答案")
    key_points: str = Field(default="", max_length=10000, description="必须覆盖的关键点，每行一个")
    forbidden_points: str = Field(default="", max_length=10000, description="不能出现的错误点，每行一个")
    min_score: int = Field(default=80, ge=0, le=100, description="最低通过分")


class TextToSqlSemanticJudgeResponse(BaseModel):
    """Text-to-SQL 语义断言的大模型裁判结果。"""

    passed: bool = Field(description="是否通过")
    score: int = Field(ge=0, le=100, description="语义评分，0-100")
    reason: str = Field(description="简短说明为什么通过或失败")
    hit_key_points: list[str] = Field(default_factory=list, description="命中的关键点")
    missing_key_points: list[str] = Field(default_factory=list, description="缺失的关键点")
    forbidden_hits: list[str] = Field(default_factory=list, description="命中的禁用点")


class TextToSqlQueryTrace(BaseModel):
    """前端展示和排查用的原始查询链路信息。

    这里的信息来自 Python/Java 真实执行过程，不由总结模型编造。
    """

    original_question: str = Field(description="用户原始问题")
    normalized_question: str | None = Field(default=None, description="意图识别后的规范化问题")
    business_domain: str | None = Field(default=None, description="识别出的业务域")
    selected_tables: list[str] = Field(default_factory=list, description="选表节点选中的表")
    table_selection_reason: str | None = Field(default=None, description="选表原因")
    generated_sql: str | None = Field(default=None, description="SQL 生成节点产出的原始 SQL")
    sql_generation_reason: str | None = Field(default=None, description="SQL 生成原因")
    executed_sql: str | None = Field(default=None, description="Java 查询中心实际执行 SQL")
    row_count: int = Field(default=0, description="返回行数")
    validation: dict[str, object] | None = Field(default=None, description="SQL AST 安全校验结果")
    permission: dict[str, object] | None = Field(default=None, description="角色数据权限校验结果")
    explain: dict[str, object] | None = Field(default=None, description="EXPLAIN 检查结果")
    metric_context: str = Field(default="", description="指标口径上下文")
    business_context: str = Field(default="", description="业务说明上下文")
    table_ddl_context: str = Field(default="", description="选中表 DDL 上下文")
    clarification_answer: str | None = Field(default=None, description="SQL 生成阶段最近一次澄清回答")


class TextToSqlResponse(BaseModel):
    """Text-to-SQL 总接口响应。"""

    # 原始问题直接透传，方便调用方把响应和请求对应起来。
    question: str = Field(description="用户原始问题")
    # 入口 node 的分类结果，例如 DATA_QUERY / GENERAL_CHAT。
    intent: IntentType = Field(description="意图识别结果")
    # 图根据 intent 得出的下一步动作，例如进入查询规划或要求澄清。
    action: IntentAction = Field(description="当前阶段决定的下一步动作")
    # 意图识别判断出来的业务域，后续指标、业务说明、注意事项检索都可以用它缩小范围。
    business_domain: str | None = Field(default=None, description="用户问题所属业务域")
    # 面向调用方展示的一句话说明。
    message: str = Field(description="当前阶段给调用方的说明")
    # 本次 Text-to-SQL 图执行的会话 ID。遇到澄清中断时，下一次请求要原样带回。
    conversation_id: str | None = Field(default=None, description="Text-to-SQL 澄清会话ID")
    # 是否正在等待用户回答澄清问题。
    need_clarification: bool = Field(default=False, description="是否需要用户补充澄清信息")
    # 需要展示给用户的澄清问题。
    clarification_question: str | None = Field(default=None, description="澄清问题")
    # 为什么需要澄清。
    clarification_reason: str | None = Field(default=None, description="需要澄清的原因")
    # 用户对上一次澄清问题的回答。恢复执行成功后返回，方便前端确认本次补充内容。
    clarification_answer: str | None = Field(default=None, description="用户补充的澄清回答")
    # 链路提前终止时的错误原因；没有错误时为空。
    error_message: str | None = Field(default=None, description="提前终止原因")
    # SQL 执行成功后由 summarize_result 节点生成的自然语言结论。
    answer: str | None = Field(default=None, description="最终自然语言结论")
    sql: str | None = Field(default=None, description="生成的 SQL，后续阶段补充")
    # 进入执行节点的 SQL。SQL AST 校验和真实查询由 Java 查询中心负责。
    executed_sql: str | None = Field(default=None, description="进入 Java 查询中心执行阶段的 SQL")
    rows: list[dict[str, object]] = Field(default_factory=list, description="查询结果")
    # 下面三个字段是给前端展示图表的快捷字段；完整依据在 result_summary_detail。
    chart_type: str | None = Field(default=None, description="建议图表类型：stat/bar/line/pie/table")
    chart_data: ResultChartData | None = Field(default=None, description="前端图表数据")
    echarts_option: dict[str, object] = Field(default_factory=dict, description="ECharts option")
    result_summary_detail: ResultSummary | None = Field(default=None, description="结果分析、图表建议和生成依据")
    query_trace: TextToSqlQueryTrace | None = Field(default=None, description="原始查询信息和执行链路信息")
    # Java 查询中心返回的完整执行结果，便于调试校验和执行状态。
    sql_execution_detail: SqlExecutionResult | None = Field(default=None, description="SQL 执行节点结果")
    # LangGraph 内部 State 的可序列化快照，用于运行记录和评测复盘。
    state_snapshot: dict[str, object] = Field(default_factory=dict, description="Text-to-SQL内部State快照")
    # LangGraph State 历史里的节点写入记录，用于查看每个节点产生了什么数据。
    state_history: list[dict[str, object]] = Field(default_factory=list, description="Text-to-SQL节点写入历史")
    # 指标检索节点召回的原始片段，方便先验证“指标口径有没有找对”。
    metric_hits: list[MetricHit] = Field(default_factory=list, description="指标检索命中的片段")
    # 把命中的指标片段拼成上下文，后续 SQL 生成节点会读取这个字段。
    metric_context: str = Field(default="", description="拼接后的指标上下文")
    # Bear MCP Resource 读取到的业务说明，后续 SQL 生成节点会读取这个字段。
    business_context: str = Field(default="", description="业务说明、查询注意事项和口径解释")
    # Bear MCP Resource 读取到的全量轻量表目录，后续选表节点会读取这个字段。
    table_catalog_context: str = Field(default="", description="全量轻量表目录，用于选表")
    # 选表节点输出的表名列表，下一步会用它们读取 DDL。
    selected_tables: list[str] = Field(default_factory=list, description="选中的候选表名")
    # 选表节点的完整结构化结果，便于调试为什么选择这些表。
    table_selection_detail: TableSelectionResult | None = Field(default=None, description="选表节点结果")
    # 按 selected_tables 读取到的 DDL JSON，上线早期便于确认选表后是否拿到了详细表结构。
    table_ddl_context: str = Field(default="", description="选中表的 DDL JSON 上下文")
    # SQL 生成节点的完整结构化结果，便于调试 SQL 是怎么来的。
    sql_generation_detail: SqlGenerationResult | None = Field(default=None, description="SQL 生成节点结果")
    # 保留入口 node 的完整结构化结果，便于排查为什么进入某个分支。
    intent_detail: IntentRecognitionResult = Field(description="意图识别节点的结构化结果")

__all__ = [
    "IntentAction",
    "IntentRecognitionResult",
    "IntentType",
    "MetricHit",
    "SqlGenerationAction",
    "SqlGenerationResult",
    "TextToSqlSemanticJudgeRequest",
    "TextToSqlSemanticJudgeResponse",
    "TextToSqlQueryTrace",
    "TextToSqlMetricSearchRequest",
    "TextToSqlMetricSearchResponse",
    "TextToSqlRequest",
    "TextToSqlResponse",
]
