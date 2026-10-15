"""Text-to-SQL 查询结果总结模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ResultChartData(BaseModel):
    """前端画图需要的整理后数据。"""

    chart_type: str = Field(description="建议图表类型：stat/bar/line/pie/table")
    x_field: str | None = Field(default=None, description="横轴字段，表格或指标卡可为空")
    y_fields: list[str] = Field(default_factory=list, description="纵轴指标字段")
    categories: list[object] = Field(default_factory=list, description="横轴类目")
    series: list[dict[str, object]] = Field(default_factory=list, description="图表序列数据")
    rows: list[dict[str, object]] = Field(default_factory=list, description="原始结果行，供表格兜底展示")


class ResultSummary(BaseModel):
    """SQL 执行成功后的分析结果。"""

    conclusion: str = Field(description="基于 rows 得出的业务结论")
    data_description: str = Field(description="本次结果集代表什么数据、统计粒度是什么")
    key_findings: list[str] = Field(default_factory=list, description="适合前端展示的关键发现")
    cautions: list[str] = Field(default_factory=list, description="口径限制、样本限制或需要提醒用户的事项")
    chart_type: str = Field(description="推荐给前端展示的图表类型")
    chart_title: str = Field(description="图表标题")
    chart_reason: str = Field(description="为什么推荐这个图表")
    chart_data: ResultChartData = Field(description="图表结构化数据")
    echarts_option: dict[str, object] = Field(default_factory=dict, description="ECharts option")
    basis: list[str] = Field(default_factory=list, description="生成依据，给前端展示和排查")
    sql: str | None = Field(default=None, description="本次实际执行 SQL")
    row_count: int = Field(default=0, description="返回结果行数")
