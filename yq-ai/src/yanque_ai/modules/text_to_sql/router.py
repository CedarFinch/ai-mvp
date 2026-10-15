"""Text-to-SQL 接口。"""

from __future__ import annotations

from fastapi import APIRouter

from ...common.config import get_settings
from .schemas import (
    TextToSqlMetricSearchRequest,
    TextToSqlMetricSearchResponse,
    TextToSqlRequest,
    TextToSqlResponse,
    TextToSqlSemanticJudgeRequest,
    TextToSqlSemanticJudgeResponse,
)
from .service import TextToSqlService


router = APIRouter(prefix="/ai/text-to-sql", tags=["text-to-sql"])

_service: TextToSqlService | None = None


def get_text_to_sql_service() -> TextToSqlService:
    """按需创建 Text-to-SQL 服务，避免 import 阶段读取环境配置。"""
    global _service
    if _service is None:
        _service = TextToSqlService(get_settings())
    return _service


@router.post(
    "/query",
    summary="Text-to-SQL 查询",
    response_model=TextToSqlResponse,
)
def text_to_sql_query(payload: TextToSqlRequest) -> TextToSqlResponse:
    """Text-to-SQL 总入口，后续会返回查询计划、SQL、数据和最终回答。"""
    return get_text_to_sql_service().query(payload)


@router.post(
    "/metrics/search",
    summary="Text-to-SQL 指标口径检索",
    response_model=TextToSqlMetricSearchResponse,
)
def search_text_to_sql_metrics(payload: TextToSqlMetricSearchRequest) -> TextToSqlMetricSearchResponse:
    """从 Milvus 指标知识库检索相关指标口径，供 MCP 动态工具或 Text-to-SQL 流程使用。"""
    return get_text_to_sql_service().search_metrics(payload)


@router.post(
    "/eval/semantic-judge",
    summary="Text-to-SQL 评测语义判断",
    response_model=TextToSqlSemanticJudgeResponse,
)
def text_to_sql_semantic_judge(payload: TextToSqlSemanticJudgeRequest) -> TextToSqlSemanticJudgeResponse:
    """用大模型判断自然语言字段是否符合样本断言。"""
    return get_text_to_sql_service().judge_semantic(payload)
