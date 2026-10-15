import { Alert, Button, Empty, Form, Input, InputNumber, Modal, Spin, Table, Tag, Typography, message } from 'antd';
import type { TableColumnsType } from 'antd';
import * as echarts from 'echarts';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { textToSqlAnalysisApi } from '../api/system';
import type {
  TextToSqlAnalyzeResult,
  TextToSqlChartData,
  TextToSqlQueryTrace,
  TextToSqlResultSummary,
} from '../types/system';

const { Text } = Typography;

const examples = [
  '昨天支付成功订单量和支付金额是多少？',
  '按支付状态统计最近 7 天订单数量',
  '最近 30 天每天的支付金额趋势',
  '按产品统计本月支付成功订单金额',
];

const chartLabels: Record<string, string> = {
  stat: '指标卡',
  bar: '柱状图',
  line: '折线图',
  pie: '饼图',
  table: '表格',
};

const feedbackMeta: Record<'GOOD' | 'BAD', { text: string; color: string }> = {
  GOOD: { text: '可用', color: 'green' },
  BAD: { text: '有问题', color: 'red' },
};

export default function TextToSqlAnalysisPage() {
  const [form] = Form.useForm<{ question: string; maxRows: number }>();
  const [result, setResult] = useState<TextToSqlAnalyzeResult>();
  const [clarificationAnswer, setClarificationAnswer] = useState('');
  const [feedbackResult, setFeedbackResult] = useState<'GOOD' | 'BAD'>();
  const [feedbackComment, setFeedbackComment] = useState('');
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const summary = normalizeSummary(result?.resultSummaryDetail || result?.result_summary_detail);
  const queryTrace = normalizeTrace(result?.queryTrace || result?.query_trace);
  const rows = result?.rows || [];
  const columns = useMemo(() => buildColumns(rows), [rows]);
  const needClarification = Boolean(result?.needClarification || result?.need_clarification);
  const conversationId = result?.conversationId || result?.conversation_id;
  const clarificationQuestion = result?.clarificationQuestion || result?.clarification_question;
  const clarificationReason = result?.clarificationReason || result?.clarification_reason;
  const runRecordId = result?.runRecordId || result?.run_record_id;

  useEffect(() => {
    form.setFieldsValue({ maxRows: 100 });
  }, [form]);

  async function submit() {
    const values = await form.validateFields();
    setLoading(true);
    try {
      const data = await textToSqlAnalysisApi.analyze({
        question: values.question.trim(),
        maxRows: values.maxRows,
      });
      setResult(data);
      setClarificationAnswer('');
      resetFeedbackState();
      if (data.errorMessage || data.error_message) {
        message.warning(data.errorMessage || data.error_message);
      }
    } finally {
      setLoading(false);
    }
  }

  async function submitClarification() {
    const answer = clarificationAnswer.trim();
    if (!answer) {
      message.warning('请输入补充说明');
      return;
    }
    if (!conversationId) {
      message.warning('缺少澄清会话ID，请重新发起分析');
      return;
    }

    setLoading(true);
    try {
      const values = form.getFieldsValue();
      const data = await textToSqlAnalysisApi.analyze({
        question: values.question || result?.question || answer,
        maxRows: values.maxRows,
        conversationId,
        clarificationAnswer: answer,
      });
      setResult(data);
      setClarificationAnswer('');
      resetFeedbackState();
      if (data.errorMessage || data.error_message) {
        message.warning(data.errorMessage || data.error_message);
      }
    } finally {
      setLoading(false);
    }
  }

  function useExample(question: string) {
    form.setFieldsValue({ question });
  }

  function resetFeedbackState() {
    setFeedbackResult(undefined);
    setFeedbackComment('');
    setFeedbackModalOpen(false);
  }

  async function submitFeedback(nextResult: 'GOOD' | 'BAD') {
    if (!runRecordId) {
      message.warning('缺少运行记录ID，暂时不能反馈');
      return;
    }
    const comment = feedbackComment.trim();
    if (nextResult === 'BAD' && !comment) {
      message.warning('结果有问题时请填写说明');
      return;
    }

    setFeedbackLoading(true);
    try {
      await textToSqlAnalysisApi.feedback(runRecordId, {
        feedbackResult: nextResult,
        feedbackComment: nextResult === 'BAD' ? comment : '',
      });
      setFeedbackResult(nextResult);
      setFeedbackModalOpen(false);
      message.success(nextResult === 'GOOD' ? '已标记为可用' : '已提交问题反馈');
    } finally {
      setFeedbackLoading(false);
    }
  }

  return (
    <div className="text-sql-analysis-page">
      <section className="analysis-hero">
        <div>
          <div className="analysis-kicker">AI 数据分析</div>
          <h2>用业务问题直接看数据</h2>
          <p>输入你想确认的问题，系统返回结论、图表和明细数据。</p>
        </div>
        <div className="analysis-hero-stats">
          <StatPill label="结果行" value={rows.length ? String(rows.length) : '-'} />
          <StatPill label="图表" value={summary?.chartType ? chartLabels[summary.chartType] || summary.chartType : '-'} />
          <StatPill label="业务域" value={queryTrace?.businessDomain || '-'} />
        </div>
      </section>

      <div className="analysis-layout">
        <section className="analysis-query-panel">
          <div className="analysis-panel-title">
            <span>查询输入</span>
            <Tag color="blue">自然语言</Tag>
          </div>
          <Form form={form} layout="vertical">
            <Form.Item name="question" label="你想分析什么？" rules={[{ required: true, whitespace: true, message: '请输入分析问题' }]}>
              <Input.TextArea
                rows={8}
                maxLength={1000}
                showCount
                placeholder="例如：最近 30 天每天的支付金额趋势"
              />
            </Form.Item>
            <Form.Item name="maxRows" label="最大返回行数" rules={[{ required: true, message: '请输入最大返回行数' }]}>
              <InputNumber min={1} max={500} precision={0} style={{ width: '100%' }} />
            </Form.Item>
            <Button type="primary" size="large" block loading={loading} onClick={submit}>
              开始分析
            </Button>
          </Form>

          <div className="analysis-examples">
            <div className="analysis-example-title">常用问题</div>
            {examples.map((item) => (
              <button key={item} type="button" onClick={() => useExample(item)}>
                {item}
              </button>
            ))}
          </div>
        </section>

        <section className="analysis-result-panel">
          <Spin spinning={loading}>
            {!result ? (
              <div className="analysis-empty">
                <Empty description="输入问题后开始分析" />
              </div>
            ) : needClarification ? (
              <ClarificationState
                question={clarificationQuestion || '请补充查询口径或筛选条件。'}
                reason={clarificationReason}
                answer={clarificationAnswer}
                loading={loading}
                onAnswerChange={setClarificationAnswer}
                onSubmit={submitClarification}
              />
            ) : result.errorMessage || result.error_message ? (
              <ErrorState messageText={result.errorMessage || result.error_message || '分析失败'} trace={queryTrace} />
            ) : (
              <div className="analysis-result-stack">
                {runRecordId ? (
                  <ResultMetaBar
                    runRecordId={runRecordId}
                    feedbackResult={feedbackResult}
                    loading={feedbackLoading}
                    onGood={() => submitFeedback('GOOD')}
                    onBad={() => setFeedbackModalOpen(true)}
                  />
                ) : null}
                <ConclusionSection summary={summary} answer={result.answer} />
                <ChartSection summary={summary} />
                <TableSection rows={rows} columns={columns} />
                <TraceSection trace={queryTrace} summary={summary} />
              </div>
            )}
          </Spin>
        </section>
      </div>
      <Modal
        title="结果有问题"
        open={feedbackModalOpen}
        confirmLoading={feedbackLoading}
        okText="提交反馈"
        cancelText="取消"
        onOk={() => submitFeedback('BAD')}
        onCancel={() => setFeedbackModalOpen(false)}
      >
        <Input.TextArea
          rows={4}
          maxLength={1000}
          showCount
          value={feedbackComment}
          onChange={(event) => setFeedbackComment(event.target.value)}
          placeholder="请简单说明哪里不对，例如：结果数值不符合预期、查询口径不对、没有理解问题等"
        />
      </Modal>
    </div>
  );
}

function ResultMetaBar({
  runRecordId,
  feedbackResult,
  loading,
  onGood,
  onBad,
}: {
  runRecordId: number;
  feedbackResult?: 'GOOD' | 'BAD';
  loading: boolean;
  onGood: () => void;
  onBad: () => void;
}) {
  const disabled = Boolean(feedbackResult);
  return (
    <div className="analysis-result-meta">
      <div className="analysis-run-link">
        <span>运行记录 #{runRecordId}</span>
        <Link to={`/textToSqlRuns?runId=${runRecordId}`}>查看</Link>
      </div>
      <div className="analysis-feedback-actions">
        <span>这次结果是否可用？</span>
        <FeedbackTag result={feedbackResult} />
        <Button size="small" type={feedbackResult === 'GOOD' ? 'primary' : 'default'} loading={loading} disabled={disabled} onClick={onGood}>
          可用
        </Button>
        <Button size="small" danger type={feedbackResult === 'BAD' ? 'primary' : 'default'} loading={loading} disabled={disabled} onClick={onBad}>
          有问题
        </Button>
      </div>
    </div>
  );
}

function FeedbackTag({ result }: { result?: 'GOOD' | 'BAD' }) {
  const meta = result ? feedbackMeta[result] : undefined;
  return <Tag color={meta?.color || 'default'}>{meta?.text || '未反馈'}</Tag>;
}

function ClarificationState({
  question,
  reason,
  answer,
  loading,
  onAnswerChange,
  onSubmit,
}: {
  question: string;
  reason?: string;
  answer: string;
  loading: boolean;
  onAnswerChange: (value: string) => void;
  onSubmit: () => void;
}) {
  return (
    <section className="analysis-card analysis-clarification-card">
      <div className="analysis-section-head">
        <div>
          <span>需要确认</span>
          <strong>补充查询口径</strong>
        </div>
        <Tag color="gold">等待回答</Tag>
      </div>
      <Alert message={question} description={reason || undefined} type="warning" showIcon />
      <Input.TextArea
        rows={4}
        value={answer}
        onChange={(event) => onAnswerChange(event.target.value)}
        placeholder="例如：按支付成功订单数统计"
      />
      <Button type="primary" loading={loading} onClick={onSubmit}>
        继续分析
      </Button>
    </section>
  );
}

function ConclusionSection({ summary, answer }: { summary?: NormalizedSummary; answer?: string }) {
  if (!summary && !answer) {
    return null;
  }
  const conclusionText = answer || summary?.conclusion || '';
  return (
    <section className="analysis-card analysis-conclusion-card">
      <div className="analysis-section-head">
        <div>
          <span>分析结论</span>
          <strong>核心结论</strong>
        </div>
        {summary?.chartType ? <Tag color="cyan">{chartLabels[summary.chartType] || summary.chartType}</Tag> : null}
      </div>
      {summary?.dataDescription ? <div className="analysis-data-scope">{summary.dataDescription}</div> : null}
      <p className="analysis-conclusion">{conclusionText}</p>
      {summary?.keyFindings.length ? (
        <div className="analysis-finding-list">
          {summary.keyFindings.map((item, index) => (
            <div className="analysis-finding" key={item}>
              <span>{index + 1}</span>
              <strong>
              {item}
              </strong>
            </div>
          ))}
        </div>
      ) : null}
      {summary?.cautions.length ? (
        <div className="analysis-cautions">
          <span>口径提醒</span>
          {summary.cautions.map((item) => (
            <Tag color="gold" key={item}>
              {item}
            </Tag>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function ChartSection({ summary }: { summary?: NormalizedSummary }) {
  return (
    <section className="analysis-card">
      <div className="analysis-section-head">
        <div>
          <span>图表展示</span>
          <strong>{summary?.chartTitle || '等待图表建议'}</strong>
        </div>
        {summary?.chartReason ? <Text type="secondary">{summary.chartReason}</Text> : null}
      </div>
      {summary?.chartType === 'stat' ? (
        <StatChart chartData={summary.chartData} />
      ) : summary?.echartsOption && Object.keys(summary.echartsOption).length > 0 ? (
        <EchartsBox option={summary.echartsOption} />
      ) : (
        <div className="analysis-chart-empty">
          <Empty description="当前结果更适合查看明细表" />
        </div>
      )}
    </section>
  );
}

function StatChart({ chartData }: { chartData?: TextToSqlChartData }) {
  const row = chartData?.rows?.[0] || {};
  const yFields = chartData?.yFields || chartData?.y_fields || Object.keys(row);
  return (
    <div className="analysis-stat-chart">
      {yFields.map((field) => (
        <div className="analysis-stat-block" key={field}>
          <span>{field}</span>
          <strong>{formatValue(row[field])}</strong>
        </div>
      ))}
    </div>
  );
}

function EchartsBox({ option }: { option: Record<string, unknown> }) {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current) {
      return undefined;
    }
    const chart = echarts.init(chartRef.current);
    chart.setOption(option);
    const resize = () => chart.resize();
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      chart.dispose();
    };
  }, [option]);

  return <div className="analysis-echarts" ref={chartRef} />;
}

function TableSection({ rows, columns }: { rows: Array<Record<string, unknown>>; columns: TableColumnsType<Record<string, unknown>> }) {
  return (
    <section className="analysis-card">
      <div className="analysis-section-head">
        <div>
          <span>结果明细</span>
          <strong>{rows.length} 行数据</strong>
        </div>
      </div>
      <Table
        size="small"
        rowKey={(_, index) => String(index)}
        columns={columns}
        dataSource={rows}
        scroll={{ x: 'max-content' }}
        pagination={{ pageSize: 8, showSizeChanger: false }}
      />
    </section>
  );
}

function TraceSection({ trace, summary }: { trace?: NormalizedTrace; summary?: NormalizedSummary }) {
  if (!trace) {
    return null;
  }
  return (
    <section className="analysis-card analysis-trace-card">
      <div className="analysis-section-head">
        <div>
          <span>查询依据</span>
          <strong>SQL 与生成依据</strong>
        </div>
        <div className="analysis-trace-tags">
          {trace.businessDomain ? <Tag color="geekblue">{trace.businessDomain}</Tag> : null}
          {trace.selectedTables.map((table) => (
            <Tag key={table}>{table}</Tag>
          ))}
        </div>
      </div>
      <pre className="analysis-sql-preview">{trace.executedSql || trace.generatedSql || '-'}</pre>
      {trace.sqlGenerationReason ? <p className="analysis-sql-reason">{trace.sqlGenerationReason}</p> : null}
      {summary?.basis?.length ? (
        <div className="analysis-basis-list">
          {summary.basis.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function ErrorState({ messageText, trace }: { messageText: string; trace?: NormalizedTrace }) {
  return (
    <section className="analysis-card analysis-error-card">
      <Empty description={messageText} />
      {trace?.generatedSql ? (
        <pre className="analysis-sql-preview">{trace.generatedSql}</pre>
      ) : null}
    </section>
  );
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="analysis-stat-pill">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function buildColumns(rows: Array<Record<string, unknown>>): TableColumnsType<Record<string, unknown>> {
  const first = rows[0];
  if (!first) {
    return [];
  }
  return Object.keys(first).map((key) => ({
    title: key,
    dataIndex: key,
    key,
    ellipsis: true,
    render: (value: unknown) => formatValue(value),
  }));
}

function formatValue(value: unknown) {
  if (value === null || value === undefined) {
    return '-';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

interface NormalizedSummary {
  conclusion: string;
  dataDescription: string;
  keyFindings: string[];
  cautions: string[];
  chartType: string;
  chartTitle: string;
  chartReason: string;
  chartData?: TextToSqlChartData;
  echartsOption: Record<string, unknown>;
  basis: string[];
}

interface NormalizedTrace {
  originalQuestion: string;
  normalizedQuestion: string;
  businessDomain: string;
  selectedTables: string[];
  tableSelectionReason: string;
  generatedSql: string;
  sqlGenerationReason: string;
  executedSql: string;
  rowCount: number;
  validation?: Record<string, unknown>;
  permission?: Record<string, unknown>;
  explain?: Record<string, unknown>;
  metricContext: string;
  businessContext: string;
}

function normalizeSummary(summary?: TextToSqlResultSummary): NormalizedSummary | undefined {
  if (!summary) {
    return undefined;
  }
  return {
    conclusion: summary.conclusion,
    dataDescription: summary.dataDescription || summary.data_description || '',
    keyFindings: summary.keyFindings || summary.key_findings || [],
    cautions: summary.cautions || [],
    chartType: summary.chartType || summary.chart_type || 'table',
    chartTitle: summary.chartTitle || summary.chart_title || '查询结果',
    chartReason: summary.chartReason || summary.chart_reason || '',
    chartData: summary.chartData || summary.chart_data,
    echartsOption: summary.echartsOption || summary.echarts_option || {},
    basis: summary.basis || [],
  };
}

function normalizeTrace(trace?: TextToSqlQueryTrace): NormalizedTrace | undefined {
  if (!trace) {
    return undefined;
  }
  return {
    originalQuestion: trace.originalQuestion || trace.original_question || '',
    normalizedQuestion: trace.normalizedQuestion || trace.normalized_question || '',
    businessDomain: trace.businessDomain || trace.business_domain || '',
    selectedTables: trace.selectedTables || trace.selected_tables || [],
    tableSelectionReason: trace.tableSelectionReason || trace.table_selection_reason || '',
    generatedSql: trace.generatedSql || trace.generated_sql || '',
    sqlGenerationReason: trace.sqlGenerationReason || trace.sql_generation_reason || '',
    executedSql: trace.executedSql || trace.executed_sql || '',
    rowCount: trace.rowCount || trace.row_count || 0,
    validation: trace.validation,
    permission: trace.permission,
    explain: trace.explain,
    metricContext: trace.metricContext || trace.metric_context || '',
    businessContext: trace.businessContext || trace.business_context || '',
  };
}
