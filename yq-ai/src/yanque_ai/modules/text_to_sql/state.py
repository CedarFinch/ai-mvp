"""Text-to-SQL 图里流转的 State。"""

from __future__ import annotations

from typing import TypedDict

from ...integrations.java.text_to_sql_client import SqlExecutionResult
from .intent.schemas import IntentAction, IntentRecognitionResult
from .schemas import MetricHit, TextToSqlRequest
from .result_summary import ResultSummary
from .sql_generation import SqlGenerationResult
from .table_selection import TableSelectionResult


class TextToSqlState(TypedDict, total=False):
    """Text-to-SQL 图内部流转的状态。

    State 是 LangGraph 每个 node 之间共享的数据包，只保存本次查询链路需要继续传递的数据。
    """

    # Java/前端传进来的原始请求。
    request: TextToSqlRequest
    # recognize_intent 节点产出的分类结果。
    intent_result: IntentRecognitionResult
    # recognize_intent 节点根据分类结果决定下一步动作，graph.py 直接用它做条件边。
    action: IntentAction
    # retrieve_metrics 节点从 Milvus 指标知识库召回的原始结果。
    metric_hits: list[MetricHit]
    # 召回结果拼成一段文本，后续 SQL 生成节点直接把它放进提示词。
    metric_context: str
    # retrieve_business_context 节点从 Bear MCP Resource 读取到的业务说明。
    business_context: str
    # retrieve_table_catalog 节点从 Bear MCP Resource 读取到的全量轻量表目录。
    table_catalog_context: str
    # select_tables 节点根据三类上下文选出的候选表。
    table_selection_result: TableSelectionResult
    # 后续 retrieve_table_ddl 节点会按这些表名读取 DDL Resource。
    selected_tables: list[str]
    # SQL 生成器返回 ASK_CLARIFICATION 后，interrupt 收到的用户回答。
    clarification_answer: str
    # 选表节点返回 ASK_CLARIFICATION 后，interrupt 收到的用户回答。
    table_selection_clarification_answer: str
    # 选表节点要求补指标时，记录补充检索问题和次数。
    table_selection_metric_query: str
    table_selection_metric_retry_count: int
    # 选表节点要求补业务说明时，记录补充业务域和次数。
    table_selection_business_domain: str
    table_selection_business_retry_count: int
    # retrieve_table_ddl 节点按 selected_tables 读取到的 DDL JSON 上下文。
    table_ddl_context: str
    # generate_sql 节点产出的结构化 SQL 结果。
    sql_generation_result: SqlGenerationResult
    # generate_sql 节点生成的一条只读 SQL。
    sql: str
    # execute_sql 节点交给 Java 查询中心处理的 SQL。
    executed_sql: str
    # execute_sql 节点返回的查询结果行。
    rows: list[dict[str, object]]
    # Java 查询中心返回的完整执行结果。
    sql_execution_result: SqlExecutionResult
    # summarize_result 节点产出的结论、图表建议、ECharts 数据和生成依据。
    result_summary: ResultSummary
    # 最终给用户看的自然语言结论。
    answer: str
    # 任一前置节点发现不能继续生成 SQL 时，把原因写到这里，图会进入终止节点。
    error_message: str
