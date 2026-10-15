"""Text-to-SQL 总流程图。"""

from __future__ import annotations

from uuid import uuid4
from enum import Enum
from typing import Literal

from pydantic import BaseModel
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from .intent.schemas import IntentAction, IntentRecognitionResult
from .nodes import TextToSqlNodes
from .schemas import TextToSqlQueryTrace, TextToSqlRequest, TextToSqlResponse
from .sql_generation import SqlGenerationAction, SqlGenerationResult
from .state import TextToSqlState
from .table_selection import TableSelectionAction


class TextToSqlGraph:
    """Text-to-SQL 总图。

    当前链路已经覆盖意图识别、上下文检索、选表、SQL 生成、Java 查询中心执行和结果总结。
    这个类只负责“编排流程”：每个 node 的具体业务逻辑都在 nodes.py 里。

    可以把它理解成一张流程图：
    用户问题 -> 意图识别 -> 检索上下文 -> 选表 -> 读取 DDL -> 生成 SQL -> 执行 SQL -> 总结结果

    其中选表和 SQL 生成两个阶段都可能触发 interrupt：
    - 选表阶段澄清：问题太泛，连该查哪些表都不确定。
    - SQL 阶段澄清：表已经确定，但字段、时间口径或条件还不确定。
    """

    def __init__(self, nodes: TextToSqlNodes) -> None:
        self._nodes = nodes
        self._graph = self._build_graph()

    def run(self, request: TextToSqlRequest) -> TextToSqlResponse:
        """执行一次 Text-to-SQL 图，并把内部 State 转成对外响应。"""

        # conversation_id 同时也是 LangGraph checkpoint 的 thread_id。
        # 第一次请求没有 conversation_id 时，这里生成一个新的；
        # 如果前端正在回答澄清问题，会把同一个 conversation_id 传回来，
        # LangGraph 就能从上一次 interrupt 停住的位置继续执行。
        conversation_id = request.conversation_id or uuid4().hex
        config = {"configurable": {"thread_id": conversation_id}}

        # clarification_answer 不区分来自哪个澄清阶段。
        # 图恢复时只需要 Command(resume=...)，具体哪个节点在等答案由 checkpoint 决定：
        # - ask_table_selection_clarification 会把答案写入 table_selection_clarification_answer。
        # - ask_sql_clarification 会把答案写入 clarification_answer。
        if request.clarification_answer:
            state = self._graph.invoke(Command(resume=request.clarification_answer), config=config)
        else:
            state = self._graph.invoke({"request": request}, config=config)

        # invoke 返回的是最终 state 或 interrupt 时的暂停 state。
        # get_state_history 读取同一个 thread_id 的执行历史，用于运行记录页面展示：
        # “每一步哪个节点写入了哪些字段”。
        state_history = _build_state_history(self._graph.get_state_history(config))
        interrupted = _get_interrupt_value(state)

        # request 也会被写进 state。这里优先使用 state 里的 request，
        # 是为了澄清恢复后仍然能拿到第一次提问的原始问题。
        original_request = state.get("request", request)
        result = state["intent_result"]
        error_message = state.get("error_message")
        sql_generation_result = state.get("sql_generation_result")

        # TextToSqlResponse 是给 Java/前端的“投影结果”。
        # 前端主要用 answer/sql/rows/chart 等快捷字段展示；
        # 运行记录则额外保存 state_snapshot 和 state_history，方便复盘完整链路。
        return TextToSqlResponse(
            question=original_request.question,
            intent=result.intent,
            action=state["action"],
            business_domain=result.business_domain,
            message=error_message
            or _message_for_interrupt(interrupted)
            or _message_for_state(
                state["action"],
                result,
                sql_generation_result,
                state.get("executed_sql"),
                state.get("result_summary") is not None,
            ),
            conversation_id=conversation_id,
            need_clarification=interrupted is not None,
            clarification_question=interrupted.get("question") if interrupted else None,
            clarification_reason=interrupted.get("reason") if interrupted else None,
            clarification_answer=state.get("clarification_answer"),
            error_message=error_message,
            answer=state.get("answer"),
            metric_hits=state.get("metric_hits", []),
            metric_context=state.get("metric_context", ""),
            business_context=state.get("business_context", ""),
            table_catalog_context=state.get("table_catalog_context", ""),
            selected_tables=state.get("selected_tables", []),
            table_selection_detail=state.get("table_selection_result"),
            table_ddl_context=state.get("table_ddl_context", ""),
            sql=state.get("sql"),
            executed_sql=state.get("executed_sql"),
            rows=state.get("rows", []),
            result_summary_detail=state.get("result_summary"),
            query_trace=_build_query_trace(original_request, state, result, sql_generation_result),
            chart_type=state.get("result_summary").chart_type if state.get("result_summary") else None,
            chart_data=state.get("result_summary").chart_data if state.get("result_summary") else None,
            echarts_option=state.get("result_summary").echarts_option if state.get("result_summary") else {},
            sql_generation_detail=sql_generation_result,
            sql_execution_detail=state.get("sql_execution_result"),
            state_snapshot=_build_state_snapshot(state),
            state_history=state_history,
            intent_detail=result,
        )

    def _build_graph(self):
        """注册节点和边。

        LangGraph 里的节点只返回自己新增或更新的字段，框架会自动合并到 State。
        所以每个 node 可以写得很小：只关心“我本步产出什么字段”，
        而不用手动复制整个 state。
        """

        graph = StateGraph(TextToSqlState)

        # 1. 注册所有节点。
        # pending 类节点基本不做业务计算，只作为“关口”：
        # 上一步并行任务都结束后，在这里统一判断是否继续、终止或澄清。
        graph.add_node("recognize_intent", self._nodes.recognize_intent)
        graph.add_node("query_planning_pending", self._nodes.query_planning_pending)
        graph.add_node("retrieve_metrics", self._nodes.retrieve_metrics)
        graph.add_node("retrieve_business_context", self._nodes.retrieve_business_context)
        graph.add_node("retrieve_table_catalog", self._nodes.retrieve_table_catalog)
        graph.add_node("context_ready_pending", self._nodes.context_ready_pending)
        graph.add_node("select_tables", self._nodes.select_tables)
        graph.add_node("table_selected_pending", self._nodes.table_selected_pending)
        graph.add_node("retrieve_additional_metrics", self._nodes.retrieve_additional_metrics)
        graph.add_node("retrieve_additional_business_context", self._nodes.retrieve_additional_business_context)
        graph.add_node("ask_table_selection_clarification", self._nodes.ask_table_selection_clarification)
        graph.add_node("retrieve_table_ddl", self._nodes.retrieve_table_ddl)
        graph.add_node("ddl_ready_pending", self._nodes.ddl_ready_pending)
        graph.add_node("generate_sql", self._nodes.generate_sql)
        graph.add_node("sql_generated_pending", self._nodes.sql_generated_pending)
        graph.add_node("ask_sql_clarification", self._nodes.ask_sql_clarification)
        graph.add_node("execute_sql", self._nodes.execute_sql)
        graph.add_node("sql_executed_pending", self._nodes.sql_executed_pending)
        graph.add_node("summarize_result", self._nodes.summarize_result)
        graph.add_node("route_general_chat", self._nodes.route_general_chat)
        graph.add_node("reject_operation", self._nodes.reject_operation)
        graph.add_node("explain_scope", self._nodes.explain_scope)
        graph.add_node("ask_clarification", self._nodes.ask_clarification)
        graph.add_node("stop_with_error", self._nodes.stop_with_error)

        # 2. 入口永远先做意图识别。
        # recognize_intent 会判断这是数据查询、普通问答、越权/写操作，还是需要先澄清。
        graph.add_edge(START, "recognize_intent")
        graph.add_conditional_edges(
            "recognize_intent",
            _route_after_action,
            {
                "query_planning_pending": "query_planning_pending",
                "route_general_chat": "route_general_chat",
                "reject_operation": "reject_operation",
                "explain_scope": "explain_scope",
                "ask_clarification": "ask_clarification",
            },
        )

        # 3. 进入 Text-to-SQL 后，同时准备三类上下文。
        # 这三步互不依赖，所以可以并行：
        # - 指标口径：帮助理解“成交订单数、转化率”等指标。
        # - 业务说明：帮助理解状态、时间字段、去重规则等业务规则。
        # - 全量表目录：轻量目录，只用于选表，不包含完整 DDL。
        graph.add_edge("query_planning_pending", "retrieve_metrics")
        graph.add_edge("query_planning_pending", "retrieve_business_context")
        graph.add_edge("query_planning_pending", "retrieve_table_catalog")
        graph.add_edge(
            ["retrieve_metrics", "retrieve_business_context", "retrieve_table_catalog"],
            "context_ready_pending",
        )

        # 4. 三类上下文都完成后，通过 context_ready_pending 做统一判断。
        # 如果任一检索节点写入 error_message，就进入 stop_with_error；
        # 否则才进入选表节点。
        graph.add_conditional_edges(
            "context_ready_pending",
            _route_after_context_ready,
            {
                "stop_with_error": "stop_with_error",
                "select_tables": "select_tables",
            },
        )

        # 5. 选表阶段。
        # select_tables 只读取轻量表目录，不看完整 DDL。
        # 如果模型认为问题太泛、无法可靠选表，会返回 ASK_CLARIFICATION，
        # table_selected_pending 会把流程导向 ask_table_selection_clarification。
        # 如果模型认为指标口径或业务说明不足，会先补对应上下文，再重新选表。
        graph.add_edge("select_tables", "table_selected_pending")
        graph.add_conditional_edges(
            "table_selected_pending",
            _route_after_table_selected,
            {
                "stop_with_error": "stop_with_error",
                "ask_table_selection_clarification": "ask_table_selection_clarification",
                "retrieve_additional_metrics": "retrieve_additional_metrics",
                "retrieve_additional_business_context": "retrieve_additional_business_context",
                "retrieve_table_ddl": "retrieve_table_ddl",
            },
        )

        # 用户补充选表澄清信息后，不直接进入 DDL。
        # 这里回到 select_tables，是为了让模型基于“原问题 + 补充信息”重新选表。
        graph.add_edge("ask_table_selection_clarification", "select_tables")
        graph.add_edge("retrieve_additional_metrics", "select_tables")
        graph.add_edge("retrieve_additional_business_context", "select_tables")

        # 6. 选表成功后读取完整 DDL。
        # 只有到了这一步，模型才会看到字段、索引、表注释等详细结构，
        # 可以降低“问题没说清就拿着 DDL 硬生成 SQL”的概率。
        graph.add_edge("retrieve_table_ddl", "ddl_ready_pending")
        graph.add_conditional_edges(
            "ddl_ready_pending",
            _route_after_ddl_ready,
            {
                "stop_with_error": "stop_with_error",
                "generate_sql": "generate_sql",
            },
        )

        # 7. SQL 生成阶段。
        # SQL 生成器可能返回：
        # - SQL_READY：SQL 已经可执行。
        # - ASK_CLARIFICATION：表已确定，但字段、时间或统计口径仍不清楚，暂停问用户。
        # 选表、指标和业务上下文不足的问题，统一交给选表阶段及其条件边处理。
        graph.add_edge("generate_sql", "sql_generated_pending")
        graph.add_conditional_edges(
            "sql_generated_pending",
            _route_after_sql_generated,
            {
                "stop_with_error": "stop_with_error",
                "ask_sql_clarification": "ask_sql_clarification",
                "execute_sql": "execute_sql",
            },
        )

        # SQL 阶段澄清后，直接回到 generate_sql。
        # 因为此时表和 DDL 已经准备好了，用户补充的是 SQL 生成所需的口径。
        graph.add_edge("ask_sql_clarification", "generate_sql")

        # 8. SQL 执行和结果总结。
        # Python 不直接连数据库，execute_sql 会调用 Java 查询中心，
        # 由 Java 做 SQL 安全校验、权限校验、EXPLAIN 和真实执行。
        graph.add_edge("execute_sql", "sql_executed_pending")
        graph.add_conditional_edges(
            "sql_executed_pending",
            _route_after_sql_executed,
            {
                "stop_with_error": "stop_with_error",
                "summarize_result": "summarize_result",
            },
        )
        graph.add_edge("summarize_result", END)

        # 这些节点都是终止类节点，执行后直接结束图。
        # 它们不会继续走选表/SQL 生成。
        for node in [
            "route_general_chat",
            "reject_operation",
            "explain_scope",
            "ask_clarification",
            "stop_with_error",
        ]:
            graph.add_edge(node, END)
        return graph.compile(checkpointer=_build_checkpointer())


def _route_after_action(
    state: TextToSqlState,
) -> Literal[
    "query_planning_pending",
    "route_general_chat",
    "reject_operation",
    "explain_scope",
    "ask_clarification",
]:
    """根据意图识别节点的 action 选择下一跳。

    这里是第一道分流：
    - 数据查询：进入 Text-to-SQL 主流程。
    - 普通问答：交给普通问答/知识库更合适。
    - 写操作或敏感操作：直接拒绝。
    - 超出范围：解释当前支持范围。
    - 意图不清：先问用户，不进入后面的查询链路。
    """

    action = state["action"]
    if action == IntentAction.ENTER_TEXT_TO_SQL:
        return "query_planning_pending"
    if action == IntentAction.ROUTE_GENERAL_CHAT:
        return "route_general_chat"
    if action == IntentAction.REJECT_OPERATION:
        return "reject_operation"
    if action == IntentAction.EXPLAIN_SCOPE:
        return "explain_scope"
    return "ask_clarification"


def _build_checkpointer() -> InMemorySaver:
    """创建 Text-to-SQL interrupt 用的内存 checkpoint。

    interrupt 必须依赖 checkpointer。
    当某个节点调用 interrupt(...) 时，LangGraph 会把当前 state 和下一步执行位置保存起来；
    前端带着 conversation_id 和用户回答回来时，Command(resume=...) 才能继续跑。

    当前先用 InMemorySaver，适合课程演示和单进程开发。
    注意：服务重启后内存 checkpoint 会丢失，生产化可以替换成 Redis/MySQL checkpoint。

    JsonPlusSerializer 的 allowed_msgpack_modules 用来允许自定义 Pydantic 模型和枚举进入 checkpoint。
    如果新增了会写入 state 的模型类型，一般也要在这里补白名单。
    """

    serde = JsonPlusSerializer(
        allowed_msgpack_modules=[
            ("yanque_ai.modules.text_to_sql.schemas", "TextToSqlRequest"),
            ("yanque_ai.modules.text_to_sql.schemas", "MetricHit"),
            ("yanque_ai.modules.text_to_sql.intent.schemas", "IntentType"),
            ("yanque_ai.modules.text_to_sql.intent.schemas", "IntentAction"),
            ("yanque_ai.modules.text_to_sql.intent.schemas", "IntentRecognitionResult"),
            ("yanque_ai.modules.text_to_sql.sql_generation.schemas", "SqlGenerationAction"),
            ("yanque_ai.modules.text_to_sql.sql_generation.schemas", "SqlGenerationResult"),
            ("yanque_ai.modules.text_to_sql.table_selection.schemas", "TableSelectionAction"),
            ("yanque_ai.modules.text_to_sql.table_selection.schemas", "TableSelectionResult"),
        ]
    )
    return InMemorySaver(serde=serde)


def _route_after_context_ready(state: TextToSqlState) -> Literal["stop_with_error", "select_tables"]:
    """上下文准备完成后的关口。

    retrieve_metrics、retrieve_business_context、retrieve_table_catalog 是并行节点。
    并行节点里任何一个失败，都不会立刻打断其他节点；
    这里统一检查 error_message，决定终止还是继续选表。
    """

    if state.get("error_message"):
        return "stop_with_error"
    return "select_tables"


def _route_after_table_selected(
    state: TextToSqlState,
) -> Literal[
    "stop_with_error",
    "ask_table_selection_clarification",
    "retrieve_additional_metrics",
    "retrieve_additional_business_context",
    "retrieve_table_ddl",
]:
    """选表完成后的关口。

    这里支持选表阶段澄清：
    - 如果 select_tables 返回 ASK_CLARIFICATION，说明连候选表都不能可靠判断。
      这时先 interrupt 问用户，避免过早读取 DDL 后让模型硬凑 SQL。
    - 如果指标或业务上下文不足，先补上下文，再回到 select_tables 重新判断。
    - 如果已经选出表，就继续读取这些表的 DDL。
    """

    if state.get("error_message"):
        return "stop_with_error"
    result = state.get("table_selection_result")
    if result and result.action == TableSelectionAction.ASK_CLARIFICATION:
        return "ask_table_selection_clarification"
    if result and result.action == TableSelectionAction.NEED_METRIC_CONTEXT:
        return "retrieve_additional_metrics"
    if result and result.action == TableSelectionAction.NEED_BUSINESS_CONTEXT:
        return "retrieve_additional_business_context"
    return "retrieve_table_ddl"


def _route_after_ddl_ready(state: TextToSqlState) -> Literal["stop_with_error", "generate_sql"]:
    """DDL 读取完成后的关口。

    retrieve_table_ddl 会把 selected_tables 对应的完整表结构读出来。
    如果读取失败或没有读到 DDL，后续 SQL 生成没有可靠依据，所以直接终止。
    """

    if state.get("error_message"):
        return "stop_with_error"
    return "generate_sql"


def _route_after_sql_generated(
    state: TextToSqlState,
) -> Literal["stop_with_error", "ask_sql_clarification", "execute_sql"]:
    """SQL 生成后的关口。

    - SQL_READY：进入 Java 查询中心执行。
    - ASK_CLARIFICATION：字段、时间或业务口径不明确，问用户。

    这里不再回头补表、补指标或补业务说明。
    如果这些上下文不足，前面的选表阶段应该先澄清或终止。
    """

    if state.get("error_message"):
        return "stop_with_error"
    result = state.get("sql_generation_result")
    if result and result.action == SqlGenerationAction.ASK_CLARIFICATION:
        return "ask_sql_clarification"
    return "execute_sql"


def _route_after_sql_executed(state: TextToSqlState) -> Literal["stop_with_error", "summarize_result"]:
    """SQL 执行后的关口。

    Java 查询中心会返回执行结果，也可能返回校验/权限/EXPLAIN/执行错误。
    如果 execute_sql 节点已经写入 error_message，就不再总结；
    否则进入 summarize_result，把 rows 转成自然语言结论和图表建议。
    """

    if state.get("error_message"):
        return "stop_with_error"
    return "summarize_result"


def _message_for_state(
    action: IntentAction,
    result: IntentRecognitionResult,
    sql_generation_result: SqlGenerationResult | None,
    executed_sql: str | None,
    has_result_summary: bool,
) -> str:
    """把内部执行状态转成接口层展示文案。

    这个 message 只是给前端的简短提示，不参与流程决策。
    真正的流程决策都在 route_* 函数里完成。
    """

    if action == IntentAction.ENTER_TEXT_TO_SQL:
        if has_result_summary:
            return "SQL 已执行完成，并已生成结果分析。"
        if executed_sql:
            return "SQL 已生成，已进入 Java 查询中心执行阶段。"
        if sql_generation_result:
            return _message_for_sql_generation(sql_generation_result)
        return "已识别为数据查询请求，当前正在准备 SQL 生成上下文。"
    if action == IntentAction.ROUTE_GENERAL_CHAT:
        return "该问题更适合走普通问答或知识库问答。"
    if action == IntentAction.REJECT_OPERATION:
        return "该请求涉及写操作或敏感操作，Text-to-SQL 不会直接执行。"
    if action == IntentAction.EXPLAIN_SCOPE:
        return "该问题超出当前 Text-to-SQL 支持的数据范围。"
    return result.clarification_question or "请补充你想查询的数据或业务问题。"


def _get_interrupt_value(state: TextToSqlState) -> dict[str, str] | None:
    """从 LangGraph interrupt 返回结构里取出前端要展示的澄清问题。

    interrupt 发生时，invoke 返回的 state 里会包含 __interrupt__。
    节点传给 interrupt(...) 的字典会放在 interrupt.value 里。
    前端只需要 type/question/reason，就能展示统一的澄清输入框。
    """

    interrupts = state.get("__interrupt__")
    if not interrupts:
        return None
    first_interrupt = interrupts[0]
    value = getattr(first_interrupt, "value", None)
    if not isinstance(value, dict):
        return None
    return {
        "type": str(value.get("type") or ""),
        "question": str(value.get("question") or ""),
        "reason": str(value.get("reason") or ""),
    }


def _message_for_interrupt(interrupted: dict[str, str] | None) -> str | None:
    """interrupt 暂停时给接口层的一句话说明。

    选表澄清和 SQL 澄清共用同一个前端 UI，
    但 message 可以区分是哪一阶段需要补充信息。
    """

    if interrupted:
        if interrupted.get("type") == "TABLE_SELECTION_CLARIFICATION":
            return "选表前需要补充信息。"
        return "生成 SQL 前需要补充信息。"
    return None


def _build_query_trace(
    request: TextToSqlRequest,
    state: TextToSqlState,
    intent_result: IntentRecognitionResult,
    sql_generation_result: SqlGenerationResult | None,
) -> TextToSqlQueryTrace:
    """整理前端展示用的原始查询链路信息。

    query_trace 是“给页面快速展示的摘要”，不是完整运行记录。
    完整运行记录看 state_snapshot 和 state_history：
    - state_snapshot：最终完整 state。
    - state_history：每一步节点写入了什么。
    """

    sql_execution_result = state.get("sql_execution_result")
    table_selection_result = state.get("table_selection_result")
    return TextToSqlQueryTrace(
        original_question=request.question,
        normalized_question=intent_result.normalized_question,
        business_domain=intent_result.business_domain,
        selected_tables=state.get("selected_tables", []),
        table_selection_reason=table_selection_result.reason if table_selection_result else None,
        generated_sql=state.get("sql"),
        sql_generation_reason=sql_generation_result.reason if sql_generation_result else None,
        executed_sql=state.get("executed_sql"),
        row_count=len(state.get("rows", [])),
        validation=sql_execution_result.validation if sql_execution_result else None,
        permission=sql_execution_result.permission if sql_execution_result else None,
        explain=sql_execution_result.explain if sql_execution_result else None,
        metric_context=state.get("metric_context", ""),
        business_context=state.get("business_context", ""),
        table_ddl_context=state.get("table_ddl_context", ""),
        clarification_answer=state.get("clarification_answer"),
    )


def _build_state_snapshot(state: TextToSqlState) -> dict[str, object]:
    """把 LangGraph State 转成 JSON 友好的最终快照。

    这里会过滤掉 LangGraph 内部字段，例如 __interrupt__。
    运行记录里的 state_snapshot_json 就来自这里，
    用于查看一次运行结束或暂停时，图里最终留下了哪些数据。
    """

    return {key: _to_jsonable(value) for key, value in state.items() if not key.startswith("__")}


def _build_state_history(history: object) -> list[dict[str, object]]:
    """整理 LangGraph checkpoint history，保留每个节点的写入数据。

    不同 LangGraph 版本的 history 结构略有差异。
    当前项目版本里，节点产出不在 metadata.writes，而在 snapshot.tasks[*].result。
    所以这里遍历每个 snapshot 的 tasks，把每个 task 的：
    - name：节点名。
    - result：这个节点本步写入 state 的字段。
    - error / interrupts：异常或中断信息。

    运行记录页左侧的“Step + 节点名”就是从这里来的。
    """

    entries: list[dict[str, object]] = []
    for snapshot in history:
        metadata = getattr(snapshot, "metadata", None) or {}
        tasks = getattr(snapshot, "tasks", None) or ()
        node_writes = []
        for task in tasks:
            result = getattr(task, "result", None)
            if result is None:
                continue
            node_writes.append(
                {
                    "node": getattr(task, "name", None),
                    "result": _to_jsonable(result),
                    "error": _to_jsonable(getattr(task, "error", None)),
                    "interrupts": _to_jsonable(getattr(task, "interrupts", None)),
                }
            )
        if not node_writes:
            continue
        entries.append(
            {
                "step": metadata.get("step"),
                "source": metadata.get("source"),
                "writes": node_writes,
                "next": _to_jsonable(getattr(snapshot, "next", None)),
                "created_at": getattr(snapshot, "created_at", None),
            }
        )
    entries.reverse()
    return entries


def _to_jsonable(value: object) -> object:
    """把 state/history 里的对象递归转换成 JSON 可序列化结构。

    State 里会混有 Pydantic 模型、枚举、datetime、tuple 等对象；
    Java 运行记录只适合保存 JSON，所以这里统一转成 dict/list/str/number/bool/null。
    """
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _message_for_sql_generation(result: SqlGenerationResult) -> str:
    """把 SQL 生成节点的动作转成接口提示。"""

    if result.action == SqlGenerationAction.SQL_READY:
        return "已生成 SQL。"
    return result.clarification_question or "生成 SQL 前需要先补充查询条件。"
