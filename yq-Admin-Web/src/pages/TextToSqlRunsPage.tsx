import { Alert, Button, Descriptions, Drawer, Empty, Form, Input, Select, Space, Table, Tabs, Tag, Typography, message } from 'antd';
import type { TableColumnsType } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { textToSqlAnalysisApi, textToSqlEvalQuestionApi } from '../api/system';
import type { PageResult, TextToSqlRunItem, TextToSqlRunPageParams } from '../types/system';

const { Text } = Typography;

const statusMeta: Record<string, { text: string; color: string }> = {
  RUNNING: { text: '运行中', color: 'processing' },
  WAITING_CLARIFICATION: { text: '待澄清', color: 'gold' },
  COMPLETED: { text: '已完成', color: 'green' },
  FAILED: { text: '失败', color: 'red' },
};

const feedbackMeta: Record<string, { text: string; color: string }> = {
  GOOD: { text: '可用', color: 'green' },
  BAD: { text: '有问题', color: 'red' },
};

export default function TextToSqlRunsPage() {
  const [form] = Form.useForm<TextToSqlRunPageParams>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [page, setPage] = useState<PageResult<TextToSqlRunItem>>({
    total: 0,
    pageNum: 1,
    pageSize: 10,
    records: [],
  });
  const [detail, setDetail] = useState<TextToSqlRunItem>();

  const stats = useMemo(() => {
    const records = page.records;
    return [
      { label: '记录总数', value: String(page.total) },
      { label: '本页完成', value: String(records.filter((item) => item.status === 'COMPLETED').length) },
      { label: '本页待处理', value: String(records.filter((item) => item.status === 'RUNNING' || item.status === 'WAITING_CLARIFICATION').length) },
      { label: '本页反馈', value: String(records.filter((item) => item.feedbackResult).length) },
    ];
  }, [page]);

  useEffect(() => {
    load();
    const runId = Number(searchParams.get('runId'));
    if (runId > 0) {
      openDetail(runId);
    }
  }, []);

  async function load(next?: Partial<TextToSqlRunPageParams>) {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      const params: TextToSqlRunPageParams = {
        ...values,
        ...next,
        pageNum: next?.pageNum || page.pageNum || 1,
        pageSize: next?.pageSize || page.pageSize || 10,
      };
      const data = await textToSqlAnalysisApi.runs(cleanParams(params));
      setPage(data);
    } finally {
      setLoading(false);
    }
  }

  async function openDetail(id: number) {
    setDetailLoading(true);
    try {
      const data = await textToSqlAnalysisApi.runDetail(id);
      setDetail(data);
    } catch {
      message.error('运行记录详情加载失败');
    } finally {
      setDetailLoading(false);
    }
  }

  function reset() {
    form.resetFields();
    load({ pageNum: 1 });
  }

  async function saveFeedback(record: TextToSqlRunItem, feedbackResult: 'GOOD' | 'BAD', feedbackComment?: string) {
    const comment = feedbackComment?.trim() || '';
    if (feedbackResult === 'BAD' && !comment) {
      message.warning('结果有问题时请填写反馈说明');
      return;
    }

    setFeedbackLoading(true);
    try {
      const updated = await textToSqlAnalysisApi.feedback(record.id, {
        feedbackResult,
        feedbackComment: feedbackResult === 'BAD' ? comment : '',
      });
      setDetail(updated);
      setPage((current) => ({
        ...current,
        records: current.records.map((item) => (item.id === updated.id ? updated : item)),
      }));
      message.success(feedbackResult === 'GOOD' ? '已标记为可用' : '已保存问题反馈');
    } finally {
      setFeedbackLoading(false);
    }
  }

  async function createEvalQuestion(record: TextToSqlRunItem) {
    const data = await textToSqlEvalQuestionApi.fromRun(record.id);
    message.success('已加入评测样本');
    navigate(`/textToSqlEvalQuestions?id=${data.id}`);
  }

  const columns: TableColumnsType<TextToSqlRunItem> = [
    {
      title: '问题',
      dataIndex: 'originalQuestion',
      width: 300,
      fixed: 'left',
      render: (_, record) => (
        <div className="run-question-cell">
          <strong>{record.originalQuestion}</strong>
          <span>{record.conversationId}</span>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 110,
      render: (value: string) => <StatusTag status={value} />,
    },
    {
      title: '反馈',
      dataIndex: 'feedbackResult',
      width: 110,
      render: (value?: string) => <FeedbackTag result={value} />,
    },
    {
      title: '耗时',
      dataIndex: 'durationMs',
      width: 100,
      render: (value?: number) => formatDuration(value),
    },
    {
      title: '提问时间',
      dataIndex: 'createdAt',
      width: 180,
      render: (value?: string) => formatTime(value),
    },
    {
      title: '操作',
      width: 90,
      fixed: 'right',
      render: (_, record) => (
        <Button type="link" onClick={() => openDetail(record.id)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <div className="text-sql-runs-page">
      <section className="run-hero">
        <div>
          <div className="run-kicker">Text-to-SQL Run Records</div>
          <h2>运行记录</h2>
          <p>每次自然语言分析只保存基础记录和完整 State 快照，方便排查与课堂复盘。</p>
        </div>
        <div className="run-stat-grid">
          {stats.map((item) => (
            <div className="run-stat" key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="run-filter-band">
        <Form form={form} layout="inline">
          <Form.Item name="keyword">
            <Input.Search placeholder="问题 / 失败原因" allowClear onSearch={() => load({ pageNum: 1 })} />
          </Form.Item>
          <Form.Item name="status">
            <Select
              placeholder="状态"
              allowClear
              style={{ width: 150 }}
              options={[
                { value: 'COMPLETED', label: '已完成' },
                { value: 'WAITING_CLARIFICATION', label: '待澄清' },
                { value: 'FAILED', label: '失败' },
                { value: 'RUNNING', label: '运行中' },
              ]}
            />
          </Form.Item>
          <Form.Item name="feedbackResult">
            <Select
              placeholder="反馈"
              allowClear
              style={{ width: 150 }}
              options={[
                { value: 'UNFEEDBACK', label: '未反馈' },
                { value: 'GOOD', label: '可用' },
                { value: 'BAD', label: '有问题' },
              ]}
            />
          </Form.Item>
          <Space>
            <Button type="primary" onClick={() => load({ pageNum: 1 })}>
              查询
            </Button>
            <Button onClick={reset}>重置</Button>
          </Space>
        </Form>
      </section>

      <section className="run-table-band">
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={page.records}
          scroll={{ x: 900 }}
          pagination={{
            current: page.pageNum,
            pageSize: page.pageSize,
            total: page.total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (pageNum, pageSize) => load({ pageNum, pageSize }),
          }}
        />
      </section>

      <RunDetailDrawer
        loading={detailLoading}
        feedbackLoading={feedbackLoading}
        record={detail}
        onFeedback={saveFeedback}
        onCreateEvalQuestion={createEvalQuestion}
        onClose={() => setDetail(undefined)}
      />
    </div>
  );
}

function RunDetailDrawer({
  loading,
  feedbackLoading,
  record,
  onFeedback,
  onCreateEvalQuestion,
  onClose,
}: {
  loading: boolean;
  feedbackLoading: boolean;
  record?: TextToSqlRunItem;
  onFeedback: (record: TextToSqlRunItem, feedbackResult: 'GOOD' | 'BAD', feedbackComment?: string) => Promise<void>;
  onCreateEvalQuestion: (record: TextToSqlRunItem) => void;
  onClose: () => void;
}) {
  const state = parseJson<Record<string, unknown>>(record?.stateSnapshotJson, {});
  const history = parseJson<Array<Record<string, unknown>>>(record?.stateHistoryJson, []);
  const nodeSteps = flattenHistory(history);
  const [activeNodeStepKey, setActiveNodeStepKey] = useState<string>();
  const activeNodeStep = nodeSteps.find((item) => item.key === activeNodeStepKey) || nodeSteps[0];
  const selectedTables = asStringArray(state.selected_tables);
  const rowSample = asRows(state.rows).slice(0, 20);
  const summary = asRecord(state.result_summary);
  const execution = asRecord(state.sql_execution_result);
  const sqlGeneration = asRecord(state.sql_generation_result);
  const intent = asRecord(state.intent_result);
  const businessDomain = typeof intent.business_domain === 'string' ? intent.business_domain : '';
  const sql = typeof state.executed_sql === 'string' ? state.executed_sql : typeof state.sql === 'string' ? state.sql : '';
  const answer = typeof state.answer === 'string' ? state.answer : '';
  const rowCount = asRows(state.rows).length;
  const sampleColumns = buildSampleColumns(rowSample);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [feedbackEditing, setFeedbackEditing] = useState(false);

  useEffect(() => {
    setActiveNodeStepKey(undefined);
    setFeedbackComment(record?.feedbackComment || '');
    setFeedbackEditing(!record?.feedbackResult);
  }, [record?.id, record?.feedbackComment]);

  async function submitFeedback(feedbackResult: 'GOOD' | 'BAD') {
    if (!record) {
      return;
    }
    await onFeedback(record, feedbackResult, feedbackComment);
    setFeedbackEditing(false);
  }

  return (
    <Drawer
      title={record ? `运行记录 #${record.id}` : '运行记录'}
      open={Boolean(record) || loading}
      onClose={onClose}
      width={980}
      className="run-detail-drawer"
    >
      {record ? (
        <div className="run-detail">
          <div className="run-detail-head">
            <div>
              <Text type="secondary">原始问题</Text>
              <h3>{record.originalQuestion}</h3>
            </div>
            <Space>
              <Button onClick={() => onCreateEvalQuestion(record)}>
                加入评测样本
              </Button>
              <FeedbackTag result={record.feedbackResult} />
              <StatusTag status={record.status} />
            </Space>
          </div>
          <Descriptions column={4} size="small" bordered>
            <Descriptions.Item label="业务域">{businessDomain || '-'}</Descriptions.Item>
            <Descriptions.Item label="意图">{typeof intent.intent === 'string' ? intent.intent : '-'}</Descriptions.Item>
            <Descriptions.Item label="行数">{rowCount || '-'}</Descriptions.Item>
            <Descriptions.Item label="耗时">{formatDuration(record.durationMs)}</Descriptions.Item>
            <Descriptions.Item label="会话ID" span={2}>{record.conversationId}</Descriptions.Item>
            <Descriptions.Item label="创建人">{record.createdBy || '-'}</Descriptions.Item>
            <Descriptions.Item label="时间">{formatTime(record.createdAt)}</Descriptions.Item>
            <Descriptions.Item label="反馈">{feedbackLabel(record.feedbackResult)}</Descriptions.Item>
            <Descriptions.Item label="反馈时间">{formatTime(record.feedbackAt)}</Descriptions.Item>
          </Descriptions>

          {record.feedbackResult && !feedbackEditing ? (
            <div className="run-feedback-summary">
              <div>
                <span>结果反馈</span>
                <strong>{feedbackLabel(record.feedbackResult)}</strong>
                {record.feedbackComment ? <p>{record.feedbackComment}</p> : null}
              </div>
              <Button onClick={() => setFeedbackEditing(true)}>修改反馈</Button>
            </div>
          ) : (
            <div className="run-feedback-panel">
              <div className="run-feedback-copy">
                <span>结果反馈</span>
                <strong>这次结果是否可用？</strong>
                <p>这里只保存最新一次反馈，方便后面整理评测样本。</p>
              </div>
              <div className="run-feedback-form">
                <Input.TextArea
                  rows={3}
                  maxLength={1000}
                  showCount
                  value={feedbackComment}
                  onChange={(event) => setFeedbackComment(event.target.value)}
                  placeholder="结果有问题时写一句说明"
                />
                <Space>
                  <Button
                    type={record.feedbackResult === 'GOOD' ? 'primary' : 'default'}
                    loading={feedbackLoading}
                    onClick={() => submitFeedback('GOOD')}
                  >
                    结果可用
                  </Button>
                  <Button
                    danger
                    type={record.feedbackResult === 'BAD' ? 'primary' : 'default'}
                    loading={feedbackLoading}
                    onClick={() => submitFeedback('BAD')}
                  >
                    结果有问题
                  </Button>
                  {record.feedbackResult ? (
                    <Button onClick={() => setFeedbackEditing(false)}>取消</Button>
                  ) : null}
                </Space>
              </div>
            </div>
          )}

          {record.errorMessage ? (
            <Alert
              type="error"
              showIcon
              message={record.errorMessage}
              className="run-detail-alert"
            />
          ) : null}

          <Tabs
            items={[
              {
                key: 'overview',
                label: '结果概览',
                children: (
                  <div className="run-detail-section">
                    <p className="run-answer">{answer || record.errorMessage || '暂无最终回答'}</p>
                    <div className="run-tag-row">
                      {selectedTables.map((table) => <Tag key={table}>{table}</Tag>)}
                      {typeof summary.chart_type === 'string' ? <Tag color="cyan">{summary.chart_type}</Tag> : null}
                    </div>
                    <JsonBlock title="State.result_summary" value={summary} />
                  </div>
                ),
              },
              {
                key: 'sql',
                label: 'SQL 与数据',
                children: (
                  <div className="run-detail-section">
                    <Text type="secondary">执行 SQL</Text>
                    <pre className="run-sql-block">{sql || '-'}</pre>
                    {typeof sqlGeneration.reason === 'string' ? <p className="run-reason">{sqlGeneration.reason}</p> : null}
                    {rowSample.length ? (
                      <Table
                        size="small"
                        rowKey={(_, index) => String(index)}
                        columns={sampleColumns}
                        dataSource={rowSample}
                        scroll={{ x: 'max-content' }}
                        pagination={false}
                      />
                    ) : (
                      <Empty description="没有结果样例" />
                    )}
                  </div>
                ),
              },
              {
                key: 'trace',
                label: '节点历史',
                children: (
                  <NodeHistoryPanel
                    steps={nodeSteps}
                    activeStep={activeNodeStep}
                    onStepChange={setActiveNodeStepKey}
                  />
                ),
              },
              {
                key: 'state',
                label: '完整 State',
                children: <JsonBlock title="完整 State 快照" value={state} />,
              },
            ]}
          />
        </div>
      ) : (
        <Empty description="请选择一条运行记录" />
      )}
    </Drawer>
  );
}

function StatusTag({ status }: { status?: string }) {
  const meta = status ? statusMeta[status] : undefined;
  return <Tag color={meta?.color || 'default'}>{meta?.text || status || '-'}</Tag>;
}

function FeedbackTag({ result }: { result?: string }) {
  const meta = result ? feedbackMeta[result] : undefined;
  return <Tag color={meta?.color || 'default'}>{meta?.text || '未反馈'}</Tag>;
}

function feedbackLabel(result?: string) {
  return result ? feedbackMeta[result]?.text || result : '未反馈';
}

function JsonBlock({ title, value }: { title: string; value: Record<string, unknown> }) {
  if (!value || Object.keys(value).length === 0) {
    return null;
  }
  return (
    <div className="run-json-block">
      <Text type="secondary">{title}</Text>
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </div>
  );
}

function NodeHistoryPanel({
  steps,
  activeStep,
  onStepChange,
}: {
  steps: NodeStep[];
  activeStep?: NodeStep;
  onStepChange: (key: string) => void;
}) {
  if (!steps.length) {
    return <Empty description="没有节点历史" />;
  }
  return (
    <div className="run-node-history">
      <div className="run-node-list">
        {steps.map((step) => (
          <button
            key={step.key}
            type="button"
            className={activeStep?.key === step.key ? 'active' : undefined}
            onClick={() => onStepChange(step.key)}
          >
            <span>Step {step.step ?? '-'}</span>
            <strong>{step.node}</strong>
            <em>{step.fieldCount} 个字段</em>
          </button>
        ))}
      </div>
      <div className="run-node-detail">
        {activeStep ? (
          <>
            <div className="run-node-detail-head">
              <div>
                <Text type="secondary">节点产出</Text>
                <h4>{activeStep.node}</h4>
              </div>
              <Tag color="blue">Step {activeStep.step ?? '-'}</Tag>
            </div>
            <Descriptions column={3} size="small" bordered>
              <Descriptions.Item label="下一步">{activeStep.next.length ? activeStep.next.join(', ') : '-'}</Descriptions.Item>
              <Descriptions.Item label="写入字段">{activeStep.fieldCount}</Descriptions.Item>
              <Descriptions.Item label="时间">{formatTime(activeStep.createdAt)}</Descriptions.Item>
            </Descriptions>
            {activeStep.error ? <Alert type="error" showIcon message={String(activeStep.error)} /> : null}
            <pre>{JSON.stringify(normalizeNestedJson(activeStep.result), null, 2)}</pre>
          </>
        ) : (
          <Empty description="请选择节点" />
        )}
      </div>
    </div>
  );
}

interface NodeStep {
  key: string;
  step?: number;
  node: string;
  result: Record<string, unknown>;
  fieldCount: number;
  next: string[];
  createdAt?: string;
  error?: unknown;
}

function flattenHistory(history: Array<Record<string, unknown>>): NodeStep[] {
  return history.flatMap((item, historyIndex) => {
    const writes = Array.isArray(item.writes) ? item.writes : [];
    return writes.map((write, writeIndex) => {
      const record = asRecord(write);
      const result = asRecord(record.result);
      const node = typeof record.node === 'string' ? record.node : `node_${writeIndex + 1}`;
      const step = typeof item.step === 'number' ? item.step : undefined;
      const createdAt = typeof item.created_at === 'string' ? item.created_at : undefined;
      return {
        key: `${historyIndex}-${writeIndex}-${node}`,
        step,
        node,
        result,
        fieldCount: Object.keys(result).length,
        next: asStringArray(item.next),
        createdAt,
        error: record.error,
      };
    });
  });
}

function buildSampleColumns(rows: Array<Record<string, unknown>>): TableColumnsType<Record<string, unknown>> {
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

function parseJson<T>(text: string | undefined, fallback: T): T {
  if (!text || text === 'null') {
    return fallback;
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    return fallback;
  }
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

function asRows(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object' && !Array.isArray(item))
    : [];
}

function normalizeNestedJson(value: unknown): unknown {
  const parsed = parseNestedJson(value);
  if (Array.isArray(parsed)) {
    return parsed.map((item) => normalizeNestedJson(item));
  }
  if (parsed && typeof parsed === 'object') {
    return Object.fromEntries(
      Object.entries(parsed as Record<string, unknown>).map(([key, item]) => [key, normalizeNestedJson(item)]),
    );
  }
  return parsed;
}

function parseNestedJson(value: unknown): unknown {
  if (typeof value !== 'string') {
    return value;
  }
  const text = value.trim();
  if (!text) {
    return value;
  }
  if (!((text.startsWith('{') && text.endsWith('}')) || (text.startsWith('[') && text.endsWith(']')))) {
    return value;
  }
  try {
    return JSON.parse(text);
  } catch {
    return value;
  }
}

function cleanParams(params: TextToSqlRunPageParams): TextToSqlRunPageParams {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== ''),
  ) as unknown as TextToSqlRunPageParams;
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

function formatDuration(value?: number) {
  if (value === undefined || value === null) {
    return '-';
  }
  if (value < 1000) {
    return `${value} ms`;
  }
  return `${(value / 1000).toFixed(1)} s`;
}

function formatTime(value?: string) {
  if (!value) {
    return '-';
  }
  return value.replace('T', ' ').slice(0, 19);
}
