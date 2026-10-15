"""Text-to-SQL 总流程里的所有节点。

当前是第十六天课程的 MVP 版本：整张图先只落地“入口意图识别”。
后面的查询规划、表选择、SQL 生成和执行节点会继续加到这个文件里，避免一开始拆太散。
"""

from __future__ import annotations

import logging
import re

from langgraph.types import interrupt

from ...integrations.java.text_to_sql_client import JavaTextToSqlClient, SqlExecutionResult
from .intent.classifier import LangChainIntentClassifier
from .intent.schemas import IntentAction, IntentRecognitionResult, IntentType
from .retrieval import (
    BusinessContextError,
    TableCatalogError,
    TableDdlError,
    TextToSqlBusinessRetriever,
    TextToSqlMetricRetriever,
    TextToSqlTableCatalogRetriever,
    TextToSqlTableDdlRetriever,
)
from .result_summary import ResultSummarizer
from .schemas import MetricHit
from .sql_generation import LangChainSqlGenerator, SqlGenerationAction
from .state import TextToSqlState
from .table_selection import LangChainTableSelector, TableSelectionAction


logger = logging.getLogger(__name__)


MAX_TABLE_SELECTION_CONTEXT_RETRY_COUNT = 2


class SqlExecutor:
    """Text-to-SQL SQL 执行器。

    这个类属于主流程节点层，负责把 execute_sql node 收到的 SQL 交给 Java 查询中心。
    具体 HTTP POST 细节放在 integrations.java.JavaTextToSqlClient 里。
    """

    def __init__(self, java_client: JavaTextToSqlClient) -> None:
        self._java_client = java_client

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
        """请求 Java 查询中心执行 SQL。"""

        return self._java_client.execute_sql(
            sql=sql,
            table_ddl_context=table_ddl_context,
            user_id=user_id,
            roles=roles,
            business_domain=business_domain,
            max_rows=max_rows,
        )


class TextToSqlNodes:
    """Text-to-SQL 图里的节点实现。

    这里的方法名就是 graph.py 里注册的 node 名。
    当前只真正实现入口意图识别，其他方法先作为“终点占位节点”，方便后续一点点补完整链路。
    """

    def __init__(
        self,
        intent_classifier: LangChainIntentClassifier,
        metric_retriever: TextToSqlMetricRetriever,
        business_retriever: TextToSqlBusinessRetriever,
        table_catalog_retriever: TextToSqlTableCatalogRetriever,
        table_ddl_retriever: TextToSqlTableDdlRetriever,
        table_selector: LangChainTableSelector,
        sql_generator: LangChainSqlGenerator,
        sql_executor: SqlExecutor,
        result_summarizer: ResultSummarizer,
    ) -> None:
        self._intent_classifier = intent_classifier
        self._metric_retriever = metric_retriever
        self._business_retriever = business_retriever
        self._table_catalog_retriever = table_catalog_retriever
        self._table_ddl_retriever = table_ddl_retriever
        self._table_selector = table_selector
        self._sql_generator = sql_generator
        self._sql_executor = sql_executor
        self._result_summarizer = result_summarizer

    def recognize_intent(self, state: TextToSqlState) -> TextToSqlState:
        """入口节点：识别用户问题是否应该进入 Text-to-SQL 查询流程。"""
        request = state["request"]
        normalized = _normalize_question(request.question)

        try:
            result = self._intent_classifier.classify(normalized)
        except ValueError:
            logger.warning("意图识别模型返回结果不完整", exc_info=True)
            return _intent_update(_retry_later_intent(normalized))
        except Exception:
            logger.warning("意图识别模型调用失败", exc_info=True)
            return _intent_update(_fallback_intent(normalized))
        return _intent_update(result)

    def query_planning_pending(self, state: TextToSqlState) -> TextToSqlState:
        """数据查询准备节点：后面并行检索指标口径和业务说明。"""
        return {}

    def retrieve_metrics(self, state: TextToSqlState) -> TextToSqlState:
        """指标检索节点：从 Milvus 指标知识库 HYBRID 召回指标口径。"""

        question = state["intent_result"].normalized_question
        return self._retrieve_metrics_by_question(question)

    def retrieve_additional_metrics(self, state: TextToSqlState) -> TextToSqlState:
        """选表补充指标节点。

        select_tables 觉得指标不够时，会给一个新的 metric_query。
        这里就做一件事：按这个最新查询项检索；有命中就追加到现有指标上下文。
        """

        table_selection_result = state.get("table_selection_result")
        if not table_selection_result or not table_selection_result.metric_query:
            return {"error_message": "选表阶段需要补充指标口径，但没有给出指标检索问题。"}

        search_question = table_selection_result.metric_query
        additional_state = self._retrieve_metrics_by_question(search_question)
        additional_metric_hits = additional_state.get("metric_hits", [])
        retry_count = state.get("table_selection_metric_retry_count", 0) + 1

        if not additional_metric_hits:
            return {
                "table_selection_metric_query": search_question,
                "table_selection_metric_retry_count": retry_count,
            }

        return {
            # metric_hits 是原始召回列表，保留旧命中并追加本次补充命中，方便运行记录复盘。
            "metric_hits": [*state.get("metric_hits", []), *additional_metric_hits],
            # metric_context 是后续选表/SQL 生成真正会读的文本，把补充结果追加到原上下文后面。
            "metric_context": "\n\n".join(
                [
                    state.get("metric_context", ""),
                    f"补充指标上下文（检索问题：{search_question}）：",
                    str(additional_state.get("metric_context", "")),
                ]
            ).strip(),
            "table_selection_metric_query": search_question,
            "table_selection_metric_retry_count": retry_count,
        }

    def _retrieve_metrics_by_question(self, question: str) -> TextToSqlState:
        """按指定问题召回指标口径，并拼成后续节点可读的上下文。"""

        try:
            metric_hits = self._metric_retriever.retrieve(question)
        except Exception:
            logger.warning("Text-to-SQL 指标检索失败，继续使用空指标上下文", exc_info=True)
            metric_hits = []
        return {
            "metric_hits": metric_hits,
            "metric_context": _build_metric_context(metric_hits),
        }

    def retrieve_business_context(self, state: TextToSqlState) -> TextToSqlState:
        """业务说明检索节点：按业务域读取 Bear MCP Resource。"""

        business_domain = state["intent_result"].business_domain
        return self._retrieve_business_context_by_domain(business_domain)

    def retrieve_additional_business_context(self, state: TextToSqlState) -> TextToSqlState:
        """选表补充业务说明节点。

        select_tables 觉得业务说明不够时，必须给一个 business_domain。
        这里就按这个业务域读取；有内容就追加到现有业务上下文。
        """

        table_selection_result = state.get("table_selection_result")
        if not table_selection_result or not table_selection_result.business_domain:
            return {"error_message": "选表阶段需要补充业务说明，但没有给出业务域。"}

        business_domain = table_selection_result.business_domain
        additional_state = self._retrieve_business_context_by_domain(business_domain)
        retry_count = state.get("table_selection_business_retry_count", 0) + 1

        if additional_state.get("error_message"):
            return {
                "error_message": additional_state["error_message"],
                "table_selection_business_domain": business_domain,
                "table_selection_business_retry_count": retry_count,
            }

        additional_business_context = additional_state.get("business_context", "")
        if not additional_business_context:
            return {
                "table_selection_business_domain": business_domain,
                "table_selection_business_retry_count": retry_count,
            }

        return {
            # business_context 是后续选表/SQL 生成会读的文本，把补充说明追加到原上下文后面。
            "business_context": "\n\n".join(
                [
                    state.get("business_context", ""),
                    f"补充业务说明（业务域：{business_domain or '未指定'}）：",
                    str(additional_business_context),
                ]
            ).strip(),
            "table_selection_business_domain": business_domain,
            "table_selection_business_retry_count": retry_count,
        }

    def _retrieve_business_context_by_domain(self, business_domain: str | None) -> TextToSqlState:
        """按指定业务域读取业务说明。"""

        try:
            return {"business_context": self._business_retriever.retrieve(business_domain)}
        except BusinessContextError as exc:
            return {
                "business_context": "",
                "error_message": str(exc),
            }
        except Exception:
            logger.warning("Text-to-SQL 读取业务说明失败", exc_info=True)
            return {
                "business_context": "",
                "error_message": "读取业务说明失败，请检查业务域 Resource 是否存在、已发布且有权限读取。",
            }

    def retrieve_table_catalog(self, state: TextToSqlState) -> TextToSqlState:
        """表目录读取节点：读取全量轻量表目录，供后续选表使用。"""

        try:
            return {"table_catalog_context": self._table_catalog_retriever.retrieve()}
        except TableCatalogError as exc:
            return {
                "table_catalog_context": "",
                "error_message": str(exc),
            }

    def context_ready_pending(self, state: TextToSqlState) -> TextToSqlState:
        """上下文准备完成：后面进入选表节点。"""
        return {}

    def select_tables(self, state: TextToSqlState) -> TextToSqlState:
        """选表节点：基于指标、业务说明和表目录选择需要读取 DDL 的表。"""

        try:
            result = self._table_selector.select_tables(
                question=_build_table_selection_question(
                    state["intent_result"].normalized_question,
                    state.get("table_selection_clarification_answer"),
                ),
                metric_context=state.get("metric_context", ""),
                business_context=state.get("business_context", ""),
                table_catalog_context=state.get("table_catalog_context", ""),
            )
        except Exception:
            logger.warning("Text-to-SQL 选表失败", exc_info=True)
            return {
                "selected_tables": [],
                "error_message": "选表失败，请稍后重试。",
            }
        return {
            "table_selection_result": result,
            "selected_tables": result.selected_tables if result.action == TableSelectionAction.SELECT_TABLES else [],
        }

    def table_selected_pending(self, state: TextToSqlState) -> TextToSqlState:
        """选表完成关口：确认后面是否可以读取 DDL。"""

        if state.get("error_message"):
            return {}
        result = state.get("table_selection_result")
        if result and result.action == TableSelectionAction.ASK_CLARIFICATION:
            return {}
        if result and result.action == TableSelectionAction.NEED_METRIC_CONTEXT:
            if state.get("table_selection_metric_retry_count", 0) >= MAX_TABLE_SELECTION_CONTEXT_RETRY_COUNT:
                return {"error_message": "选表阶段多次要求补充指标口径，已停止继续重试。"}
            return {}
        if result and result.action == TableSelectionAction.NEED_BUSINESS_CONTEXT:
            if state.get("table_selection_business_retry_count", 0) >= MAX_TABLE_SELECTION_CONTEXT_RETRY_COUNT:
                return {"error_message": "选表阶段多次要求补充业务说明，已停止继续重试。"}
            return {}
        if not state.get("selected_tables"):
            return {"error_message": "没有选出可用表，无法读取 DDL Resource。"}
        return {}

    def ask_table_selection_clarification(self, state: TextToSqlState) -> TextToSqlState:
        """暂停图执行，等待用户回答选表阶段的澄清问题。"""

        result = state.get("table_selection_result")
        if not result or result.action != TableSelectionAction.ASK_CLARIFICATION:
            return {}

        question = result.clarification_question or "请补充你想查询的业务范围或统计口径。"
        answer = interrupt(
            {
                "type": "TABLE_SELECTION_CLARIFICATION",
                "question": question,
                "reason": result.reason,
            }
        )

        return {
            "table_selection_clarification_answer": str(answer).strip(),
        }

    def retrieve_table_ddl(self, state: TextToSqlState) -> TextToSqlState:
        """DDL 读取节点：根据选表结果读取更完整的表结构 JSON。"""

        try:
            return {
                "table_ddl_context": self._table_ddl_retriever.retrieve(
                    state.get("selected_tables", [])
                )
            }
        except TableDdlError as exc:
            return {
                "table_ddl_context": "",
                "error_message": str(exc),
            }
        except Exception:
            logger.warning("Text-to-SQL 读取表 DDL 失败", exc_info=True)
            return {
                "table_ddl_context": "",
                "error_message": "读取表 DDL 失败，请稍后重试。",
            }

    def ddl_ready_pending(self, state: TextToSqlState) -> TextToSqlState:
        """DDL 准备完成关口：确认后面是否可以进入 SQL 生成。"""

        if state.get("error_message"):
            return {}
        if not state.get("table_ddl_context"):
            return {"error_message": "没有读取到表 DDL，无法继续生成 SQL。"}
        return {}

    def generate_sql(self, state: TextToSqlState) -> TextToSqlState:
        """SQL 生成节点：只生成 SQL，或发起 SQL 口径澄清。"""

        try:
            result = self._sql_generator.generate_sql(
                question=state["intent_result"].normalized_question,
                metric_context=state.get("metric_context", ""),
                business_context=state.get("business_context", ""),
                table_ddl_context=state.get("table_ddl_context", ""),
                clarification_context=_build_clarification_context(
                    state.get("clarification_answer")
                ),
            )
        except Exception:
            logger.warning("Text-to-SQL 生成 SQL 失败", exc_info=True)
            return {
                "sql": "",
                "error_message": "生成 SQL 失败，请稍后重试。",
            }
        if result.action != SqlGenerationAction.SQL_READY:
            return {
                "sql_generation_result": result,
                "sql": "",
            }
        return {
            "sql_generation_result": result,
            "sql": result.sql or "",
        }

    def ask_sql_clarification(self, state: TextToSqlState) -> TextToSqlState:
        """暂停图执行，等待用户回答 SQL 生成阶段的澄清问题。"""

        result = state.get("sql_generation_result")
        if not result or result.action != SqlGenerationAction.ASK_CLARIFICATION:
            return {}

        question = result.clarification_question or "请补充你想查询的数据口径或筛选条件。"
        answer = interrupt(
            {
                "type": "SQL_CLARIFICATION",
                "question": question,
                "reason": result.reason,
            }
        )

        return {
            "clarification_answer": str(answer).strip(),
        }

    def sql_generated_pending(self, state: TextToSqlState) -> TextToSqlState:
        """SQL 生成完成关口：确认后面是否可以进入 SQL 校验或执行。"""

        if state.get("error_message"):
            return {}
        result = state.get("sql_generation_result")
        if result and result.action != SqlGenerationAction.SQL_READY:
            return {}
        if not state.get("sql"):
            return {"error_message": "没有生成 SQL，无法继续执行查询。"}
        return {}

    def execute_sql(self, state: TextToSqlState) -> TextToSqlState:
        """SQL 执行节点。

        Python 只负责生成 SQL 和进入执行阶段。
        SQL AST 校验、权限控制和真实查询执行由 Java 查询中心负责。
        """

        try:
            request = state["request"]
            intent_result = state.get("intent_result")
            result = self._sql_executor.execute_sql(
                sql=state.get("sql", ""),
                table_ddl_context=state.get("table_ddl_context", ""),
                user_id=request.user_id,
                roles=request.roles,
                business_domain=intent_result.business_domain if intent_result else None,
                max_rows=request.max_rows,
            )
        except Exception:
            logger.warning("Text-to-SQL 调用 Java 查询中心失败", exc_info=True)
            return {
                "executed_sql": state.get("sql", ""),
                "rows": [],
                "error_message": "SQL 执行失败，请稍后重试。",
            }

        if not result.success:
            return {
                "executed_sql": result.sql or state.get("sql", ""),
                "rows": [],
                "sql_execution_result": result,
                "error_message": result.message or "SQL 未通过查询中心校验。",
            }

        return {
            "executed_sql": result.sql or state.get("sql", ""),
            "rows": result.rows,
            "sql_execution_result": result,
        }

    def sql_executed_pending(self, state: TextToSqlState) -> TextToSqlState:
        """SQL 执行完成关口：确认 Java 查询中心是否返回了结果。"""

        if state.get("error_message"):
            return {}
        if not state.get("executed_sql"):
            return {"error_message": "SQL 未进入执行阶段，无法返回查询结果。"}
        return {}

    def summarize_result(self, state: TextToSqlState) -> TextToSqlState:
        """结果总结节点：把 rows 转成结论、图表建议和展示依据。

        这个节点只分析 Java 已返回的数据，不再查询数据库。
        前端主要读取 answer、chart_type、chart_data、echarts_option 和 result_summary_detail。
        """

        try:
            request = state["request"]
            summary = self._result_summarizer.summarize(
                question=request.question,
                sql=state.get("executed_sql") or state.get("sql"),
                rows=state.get("rows", []),
                sql_execution_result=state.get("sql_execution_result"),
                metric_context=state.get("metric_context", ""),
                business_context=state.get("business_context", ""),
            )
        except Exception:
            logger.warning("Text-to-SQL 查询结果总结失败", exc_info=True)
            return {
                "error_message": "查询结果总结失败，请稍后重试。",
            }

        return {
            "answer": summary.conclusion,
            "result_summary": summary,
        }

    def stop_with_error(self, state: TextToSqlState) -> TextToSqlState:
        """前置上下文缺失：直接终止，不继续生成 SQL。"""
        return {}

    def route_general_chat(self, state: TextToSqlState) -> TextToSqlState:
        """普通问答：不生成 SQL，后续可以交给知识库问答或聊天模块。"""
        return {}

    def reject_operation(self, state: TextToSqlState) -> TextToSqlState:
        """写操作或敏感操作：Text-to-SQL 只做只读查询，所以直接拒绝。"""
        return {}

    def explain_scope(self, state: TextToSqlState) -> TextToSqlState:
        """范围外问题：当前业务数据源不支持，给出范围说明。"""
        return {}

    def ask_clarification(self, state: TextToSqlState) -> TextToSqlState:
        """问题不清楚：先追问，避免猜错后直接生成 SQL。"""
        return {}


def _normalize_question(question: str) -> str:
    """做最小清理，只压缩空白，不改写用户的业务含义。"""

    return re.sub(r"\s+", " ", question).strip()


def _intent_update(result: IntentRecognitionResult) -> TextToSqlState:
    """把模型分类结果转换成图下一步动作。

    这里是唯一维护 intent -> action 映射的地方。
    graph.py 只看 action 做条件边，不再重复判断 intent。
    """

    if result.intent == IntentType.DATA_QUERY:
        action = IntentAction.ENTER_TEXT_TO_SQL
    elif result.intent == IntentType.GENERAL_CHAT:
        action = IntentAction.ROUTE_GENERAL_CHAT
    elif result.intent == IntentType.DATA_OPERATION:
        action = IntentAction.REJECT_OPERATION
    elif result.intent == IntentType.OUT_OF_SCOPE:
        action = IntentAction.EXPLAIN_SCOPE
    else:
        action = IntentAction.ASK_CLARIFICATION
    return {"intent_result": result, "action": action}


def _build_metric_context(metric_hits: list[MetricHit]) -> str:
    """把指标召回结果拼成后续 SQL 生成节点可读的上下文。"""

    if not metric_hits:
        return "未检索到相关指标口径。"
    return "\n\n".join(
        f"[{hit.rank}] 文档：{hit.document_code}，chunk：{hit.chunk_index}\n{hit.content}"
        for hit in metric_hits
    )


def _build_clarification_context(answer: str | None) -> str:
    """把用户最近一次澄清回答拼成 SQL 生成模型能读懂的上下文。"""

    if not answer:
        return "暂无。"
    return f"用户补充的澄清回答：{answer.strip()}"


def _build_table_selection_question(question: str, clarification_answer: str | None) -> str:
    """把选表阶段的澄清回答拼回问题，便于重新选表。"""

    if not clarification_answer or not clarification_answer.strip():
        return question
    return "\n".join(
        [
            question,
            "",
            f"用户补充的选表澄清信息：{clarification_answer.strip()}",
        ]
    )


def _fallback_intent(question: str) -> IntentRecognitionResult:
    """模型异常时的保守兜底：宁愿追问，也不冒险进入 SQL 生成。"""

    return IntentRecognitionResult(
        intent=IntentType.AMBIGUOUS,
        reason="当前无法可靠判断用户意图，需要先澄清。",
        business_domain=None,
        normalized_question=question or " ",
        clarification_question="你是想查询业务数据，还是想了解相关业务规则？",
    )


def _retry_later_intent(question: str) -> IntentRecognitionResult:
    """模型结果不完整时，返回一个明确的重试提示。"""

    return IntentRecognitionResult(
        intent=IntentType.AMBIGUOUS,
        reason="意图识别结果不完整，请稍后重试。",
        business_domain=None,
        normalized_question=question or " ",
        clarification_question="意图识别结果不完整，请稍后重试。",
    )
