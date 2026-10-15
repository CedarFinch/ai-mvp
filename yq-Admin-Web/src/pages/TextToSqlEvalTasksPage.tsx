import { Button, Descriptions, Drawer, Empty, Form, Input, Modal, Progress, Select, Space, Table, Tag, Typography, message } from 'antd';
import type { TableColumnsType } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { textToSqlEvalQuestionApi, textToSqlEvalTaskApi } from '../api/system';
import type {
  PageResult,
  TextToSqlEvalAssertionResultItem,
  TextToSqlEvalQuestionItem,
  TextToSqlEvalResultItem,
  TextToSqlEvalResultPageParams,
  TextToSqlEvalTaskItem,
  TextToSqlEvalTaskPageParams,
  TextToSqlEvalTaskValues,
} from '../types/system';

const { Paragraph, Text } = Typography;

const businessOptions = [
  { label: '订单', value: 'order' },
  { label: '学员', value: 'student' },
  { label: '教学', value: 'teaching' },
];

const evalTargetOptions = [
  { label: '端到端', value: 'END_TO_END', color: 'blue' },
  { label: '意图识别', value: 'INTENT_RECOGNITION', color: 'purple' },
  { label: '选表', value: 'TABLE_SELECTION', color: 'cyan' },
  { label: 'SQL生成', value: 'SQL_GENERATION', color: 'green' },
  { label: '澄清', value: 'CLARIFICATION', color: 'gold' },
  { label: '结果总结', value: 'RESULT_SUMMARY', color: 'magenta' },
];

const sampleCategoryOptions = [
  { label: '正常问题', value: 'NORMAL', color: 'green' },
  { label: '边界问题', value: 'BOUNDARY', color: 'orange' },
  { label: '回归问题', value: 'REGRESSION', color: 'red' },
  { label: '歧义澄清', value: 'AMBIGUOUS', color: 'gold' },
  { label: '负向问题', value: 'NEGATIVE', color: 'default' },
];

const taskStatusMeta: Record<string, { text: string; color: string }> = {
  PENDING: { text: '等待中', color: 'default' },
  RUNNING: { text: '运行中', color: 'processing' },
  COMPLETED: { text: '已完成', color: 'green' },
  FAILED: { text: '失败', color: 'red' },
};

const resultStatusMeta: Record<string, { text: string; color: string }> = {
  PASSED: { text: '通过', color: 'green' },
  FAILED: { text: '失败', color: 'red' },
  INTERRUPTED: { text: '中断', color: 'gold' },
};

const optionLabel = (options: Array<{ label: string; value: string }>, value?: string) =>
  options.find((item) => item.value === value)?.label || value || '-';

const optionColor = (options: Array<{ color?: string; value: string }>, value?: string) =>
  options.find((item) => item.value === value)?.color || 'default';

export default function TextToSqlEvalTasksPage() {
  const [filterForm] = Form.useForm<TextToSqlEvalTaskPageParams>();
  const [createForm] = Form.useForm<TextToSqlEvalTaskValues>();
  const [page, setPage] = useState<PageResult<TextToSqlEvalTaskItem>>({
    total: 0,
    pageNum: 1,
    pageSize: 10,
    records: [],
  });
  const [results, setResults] = useState<PageResult<TextToSqlEvalResultItem>>({
    total: 0,
    pageNum: 1,
    pageSize: 10,
    records: [],
  });
  const [loading, setLoading] = useState(false);
  const [resultLoading, setResultLoading] = useState(false);
  const [sampleLoading, setSampleLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [continuing, setContinuing] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [detail, setDetail] = useState<TextToSqlEvalTaskItem>();
  const [activeResult, setActiveResult] = useState<TextToSqlEvalResultItem>();
  const [resultStatus, setResultStatus] = useState<string>();
  const [selectableSamples, setSelectableSamples] = useState<TextToSqlEvalQuestionItem[]>([]);
  const [selectedSampleIds, setSelectedSampleIds] = useState<number[]>([]);

  const stats = useMemo(() => {
    const records = page.records;
    return [
      { label: '任务总数', value: page.total },
      { label: '运行中', value: records.filter((item) => item.status === 'RUNNING').length },
      { label: '本页通过', value: records.reduce((sum, item) => sum + (item.passCount || 0), 0) },
      { label: '本页失败', value: records.reduce((sum, item) => sum + (item.failCount || 0), 0) },
      { label: '本页中断', value: records.reduce((sum, item) => sum + (item.interruptedCount || 0), 0) },
    ];
  }, [page]);

  useEffect(() => {
    load({ pageNum: 1, pageSize: 10 });
  }, []);

  async function load(next?: Partial<TextToSqlEvalTaskPageParams>) {
    setLoading(true);
    try {
      const values = filterForm.getFieldsValue();
      const params: TextToSqlEvalTaskPageParams = {
        ...values,
        ...next,
        pageNum: next?.pageNum || page.pageNum || 1,
        pageSize: next?.pageSize || page.pageSize || 10,
      };
      setPage(await textToSqlEvalTaskApi.page(cleanTaskParams(params)));
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    filterForm.resetFields();
    load({ pageNum: 1 });
  }

  function openCreate() {
    createForm.resetFields();
    createForm.setFieldsValue({ name: `Text-to-SQL评测 ${new Date().toLocaleString()}` });
    setCreateOpen(true);
    loadSelectableSamples({});
  }

  async function createTask() {
    const values = await createForm.validateFields();
    if (!selectedSampleIds.length) {
      message.warning('请至少选择一条评测样本');
      return;
    }
    setCreating(true);
    try {
      const data = await textToSqlEvalTaskApi.create({ ...values, evalQuestionIds: selectedSampleIds });
      message.success('评测任务已创建，正在后台执行');
      setCreateOpen(false);
      await load({ pageNum: 1 });
      await openDetail(data.id);
    } finally {
      setCreating(false);
    }
  }

  async function loadSelectableSamples(values: Partial<TextToSqlEvalTaskValues>) {
    setSampleLoading(true);
    try {
      const data = await textToSqlEvalQuestionApi.page({
        businessDomain: values.businessDomain,
        evalTarget: values.evalTarget,
        sampleCategory: values.sampleCategory,
        status: 'ACTIVE',
        pageNum: 1,
        pageSize: 1000,
      });
      setSelectableSamples(data.records);
      setSelectedSampleIds(data.records.map((item) => item.id));
    } finally {
      setSampleLoading(false);
    }
  }

  function handleCreateValuesChange(changed: Partial<TextToSqlEvalTaskValues>, values: TextToSqlEvalTaskValues) {
    if ('businessDomain' in changed || 'evalTarget' in changed || 'sampleCategory' in changed) {
      loadSelectableSamples(values);
    }
  }

  async function openDetail(id: number, resultParams?: Partial<TextToSqlEvalResultPageParams>) {
    setResultLoading(true);
    try {
      const detailData = await textToSqlEvalTaskApi.detail(id);
      setDetail(detailData.task);
      const params: TextToSqlEvalResultPageParams = {
        resultStatus: resultParams?.resultStatus === undefined ? resultStatus : resultParams.resultStatus,
        ...resultParams,
        pageNum: resultParams?.pageNum || 1,
        pageSize: resultParams?.pageSize || 10,
      };
      setResults(await textToSqlEvalTaskApi.results(id, params));
    } finally {
      setResultLoading(false);
    }
  }

  async function continueResult(record: TextToSqlEvalResultItem, clarificationAnswer: string) {
    setContinuing(true);
    try {
      const updated = await textToSqlEvalTaskApi.continueResult(record.id, clarificationAnswer);
      message.success('已继续执行评测样本');
      setActiveResult(updated);
      if (detail) {
        await openDetail(detail.id, { resultStatus, pageNum: results.pageNum, pageSize: results.pageSize });
      }
    } finally {
      setContinuing(false);
    }
  }

  const columns: TableColumnsType<TextToSqlEvalTaskItem> = [
    {
      title: '任务',
      dataIndex: 'name',
      width: 300,
      render: (value?: string, record?: TextToSqlEvalTaskItem) => (
        <div className="eval-task-name-cell">
          <strong>{value || '-'}</strong>
          <span>{formatTime(record?.createdAt)}</span>
        </div>
      ),
    },
    {
      title: '范围',
      width: 260,
      render: (_, record) => (
        <Space size={6} wrap>
          <Tag>{optionLabel(businessOptions, record.businessDomain)}</Tag>
          <Tag color={optionColor(evalTargetOptions, record.evalTarget)}>{optionLabel(evalTargetOptions, record.evalTarget)}</Tag>
          <Tag color={optionColor(sampleCategoryOptions, record.sampleCategory)}>{optionLabel(sampleCategoryOptions, record.sampleCategory)}</Tag>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (value?: string) => <TaskStatusTag status={value} />,
    },
    {
      title: '通过率',
      dataIndex: 'passRate',
      width: 170,
      render: (value?: number, record?: TextToSqlEvalTaskItem) => (
        <Progress percent={Number(value || 0)} size="small" status={record?.failCount ? 'exception' : 'success'} />
      ),
    },
    { title: '样本数', dataIndex: 'totalCount', width: 90 },
    { title: '通过', dataIndex: 'passCount', width: 80 },
    { title: '失败', dataIndex: 'failCount', width: 80 },
    { title: '中断', dataIndex: 'interruptedCount', width: 80 },
    {
      title: '耗时',
      dataIndex: 'durationMs',
      width: 100,
      render: (value?: number) => formatDuration(value),
    },
    {
      title: '操作',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Button size="small" type="primary" ghost onClick={() => openDetail(record.id)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <div className="text-sql-eval-task-page">
      <section className="eval-task-hero">
        <div>
          <div className="eval-task-kicker">Text-to-SQL Eval Tasks</div>
          <h2>评测任务</h2>
          <p>批量重跑正式样本，并用 State 断言判断每条样本是否通过。</p>
        </div>
        <div className="eval-task-hero-actions">
          {stats.map((item) => (
            <div className="eval-task-stat" key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
          <Button type="primary" onClick={openCreate}>
            创建任务
          </Button>
        </div>
      </section>

      <section className="eval-task-filter">
        <Form form={filterForm} layout="inline">
          <Form.Item name="keyword">
            <Input.Search className="eval-task-search" placeholder="搜索任务名称" allowClear onSearch={() => load({ pageNum: 1 })} />
          </Form.Item>
          <Form.Item name="businessDomain">
            <Select placeholder="业务环境" allowClear options={businessOptions} style={{ width: 130 }} />
          </Form.Item>
          <Form.Item name="evalTarget">
            <Select placeholder="评测目标" allowClear options={evalTargetOptions} style={{ width: 140 }} />
          </Form.Item>
          <Form.Item name="sampleCategory">
            <Select placeholder="样本场景" allowClear options={sampleCategoryOptions} style={{ width: 130 }} />
          </Form.Item>
          <Form.Item name="status">
            <Select placeholder="状态" allowClear options={Object.entries(taskStatusMeta).map(([value, meta]) => ({ label: meta.text, value }))} style={{ width: 120 }} />
          </Form.Item>
          <Space>
            <Button type="primary" onClick={() => load({ pageNum: 1 })}>
              查询
            </Button>
            <Button onClick={reset}>重置</Button>
          </Space>
        </Form>
      </section>

      <section className="eval-task-table">
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={page.records}
          scroll={{ x: 1200 }}
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

      <Modal
        title="创建评测任务"
        open={createOpen}
        width={980}
        confirmLoading={creating}
        okText="创建并执行"
        cancelText="取消"
        onOk={createTask}
        onCancel={() => setCreateOpen(false)}
        destroyOnClose
      >
        <Form
          form={createForm}
          layout="vertical"
          className="eval-task-create-form"
          onValuesChange={handleCreateValuesChange}
        >
          <div className="eval-task-create-grid">
            <Form.Item name="name" label="任务名称" rules={[{ required: true, whitespace: true, message: '请输入任务名称' }]}>
              <Input maxLength={128} />
            </Form.Item>
            <Form.Item name="businessDomain" label="业务环境">
              <Select allowClear options={businessOptions} placeholder="全部业务环境" />
            </Form.Item>
            <Form.Item name="evalTarget" label="评测目标">
              <Select allowClear options={evalTargetOptions} placeholder="全部评测目标" />
            </Form.Item>
            <Form.Item name="sampleCategory" label="样本场景">
              <Select allowClear options={sampleCategoryOptions} placeholder="全部样本场景" />
            </Form.Item>
          </div>
          <div className="eval-task-sample-picker">
            <div className="eval-task-sample-head">
              <div>
                <strong>选择执行样本</strong>
                <span>只展示正式样本，默认全选；可以取消不想跑的样本。</span>
              </div>
              <Tag color={selectedSampleIds.length ? 'blue' : 'red'}>已选 {selectedSampleIds.length} 条</Tag>
            </div>
            <Table
              rowKey="id"
              size="small"
              loading={sampleLoading}
              dataSource={selectableSamples}
              rowSelection={{
                selectedRowKeys: selectedSampleIds,
                onChange: (keys) => setSelectedSampleIds(keys.map((key) => Number(key))),
              }}
              columns={[
                {
                  title: '问题',
                  dataIndex: 'question',
                  render: (value?: string) => <Text ellipsis={{ tooltip: value || '-' }}>{value || '-'}</Text>,
                },
                {
                  title: '业务',
                  dataIndex: 'businessDomain',
                  width: 90,
                  render: (value?: string) => optionLabel(businessOptions, value),
                },
                {
                  title: '目标',
                  dataIndex: 'evalTarget',
                  width: 110,
                  render: (value?: string) => optionLabel(evalTargetOptions, value),
                },
                {
                  title: '场景',
                  dataIndex: 'sampleCategory',
                  width: 110,
                  render: (value?: string) => optionLabel(sampleCategoryOptions, value),
                },
                {
                  title: '断言',
                  dataIndex: 'assertionCount',
                  width: 70,
                  render: (value?: number) => value || 0,
                },
              ]}
              pagination={false}
              scroll={{ y: 320 }}
            />
          </div>
        </Form>
      </Modal>

      <EvalTaskDrawer
        task={detail}
        results={results}
        loading={resultLoading}
        activeResult={activeResult}
        onClose={() => setDetail(undefined)}
        onRefresh={() => detail && openDetail(detail.id, { pageNum: results.pageNum, pageSize: results.pageSize })}
        onResultPage={(pageNum, pageSize) => detail && openDetail(detail.id, { pageNum, pageSize })}
        onResultFilter={(passed) => {
          setResultStatus(passed);
          if (detail) {
            openDetail(detail.id, { resultStatus: passed, pageNum: 1, pageSize: results.pageSize });
          }
        }}
        onOpenResult={setActiveResult}
        onCloseResult={() => setActiveResult(undefined)}
        onContinueResult={continueResult}
        continuing={continuing}
      />
    </div>
  );
}

function EvalTaskDrawer({
  task,
  results,
  loading,
  activeResult,
  onClose,
  onRefresh,
  onResultPage,
  onResultFilter,
  onOpenResult,
  onCloseResult,
  onContinueResult,
  continuing,
}: {
  task?: TextToSqlEvalTaskItem;
  results: PageResult<TextToSqlEvalResultItem>;
  loading: boolean;
  activeResult?: TextToSqlEvalResultItem;
  onClose: () => void;
  onRefresh: () => void;
  onResultPage: (pageNum: number, pageSize: number) => void;
  onResultFilter: (resultStatus?: string) => void;
  onOpenResult: (record: TextToSqlEvalResultItem) => void;
  onCloseResult: () => void;
  onContinueResult: (record: TextToSqlEvalResultItem, clarificationAnswer: string) => Promise<void>;
  continuing: boolean;
}) {
  const resultColumns: TableColumnsType<TextToSqlEvalResultItem> = [
    {
      title: '问题',
      dataIndex: 'question',
      render: (value?: string) => <Text ellipsis={{ tooltip: value || '-' }}>{value || '-'}</Text>,
    },
    {
      title: '结果',
      dataIndex: 'resultStatus',
      width: 90,
      render: (value?: string, record?: TextToSqlEvalResultItem) => <ResultStatusTag status={value || (record?.passed ? 'PASSED' : 'FAILED')} />,
    },
    {
      title: '得分',
      dataIndex: 'score',
      width: 80,
      render: (value?: number) => Number(value || 0).toFixed(2),
    },
    {
      title: '运行记录',
      dataIndex: 'runRecordId',
      width: 120,
      render: (value?: number) => (value ? <Link to={`/textToSqlRuns?runId=${value}`}>#{value}</Link> : '-'),
    },
    {
      title: '耗时',
      dataIndex: 'durationMs',
      width: 100,
      render: (value?: number) => formatDuration(value),
    },
    {
      title: '操作',
      width: 90,
      render: (_, record) => (
        <Button size="small" onClick={() => onOpenResult(record)}>
          查看
        </Button>
      ),
    },
  ];

  return (
    <Drawer title={task ? `评测任务 #${task.id}` : '评测任务'} open={Boolean(task)} onClose={onClose} width={1040}>
      {task ? (
        <div className="eval-task-detail">
          <section className="eval-task-detail-head">
            <div>
              <TaskStatusTag status={task.status} />
              <h3>{task.name}</h3>
              {task.errorMessage ? <p>{task.errorMessage}</p> : null}
            </div>
            <Space>
              <Button onClick={onRefresh}>刷新</Button>
            </Space>
          </section>
          <Descriptions column={4} size="small" bordered>
            <Descriptions.Item label="业务环境">{optionLabel(businessOptions, task.businessDomain)}</Descriptions.Item>
            <Descriptions.Item label="评测目标">{optionLabel(evalTargetOptions, task.evalTarget)}</Descriptions.Item>
            <Descriptions.Item label="样本场景">{optionLabel(sampleCategoryOptions, task.sampleCategory)}</Descriptions.Item>
            <Descriptions.Item label="通过率">{Number(task.passRate || 0).toFixed(2)}%</Descriptions.Item>
            <Descriptions.Item label="样本数">{task.totalCount || 0}</Descriptions.Item>
            <Descriptions.Item label="通过">{task.passCount || 0}</Descriptions.Item>
            <Descriptions.Item label="失败">{task.failCount || 0}</Descriptions.Item>
            <Descriptions.Item label="中断">{task.interruptedCount || 0}</Descriptions.Item>
            <Descriptions.Item label="耗时">{formatDuration(task.durationMs)}</Descriptions.Item>
          </Descriptions>
          <section className="eval-task-result-toolbar">
            <Space>
              <Button onClick={() => onResultFilter(undefined)}>全部</Button>
              <Button onClick={() => onResultFilter('PASSED')}>只看通过</Button>
              <Button danger onClick={() => onResultFilter('FAILED')}>只看失败</Button>
              <Button onClick={() => onResultFilter('INTERRUPTED')}>只看中断</Button>
            </Space>
          </section>
          <Table
            rowKey="id"
            loading={loading}
            columns={resultColumns}
            dataSource={results.records}
            pagination={{
              current: results.pageNum,
              pageSize: results.pageSize,
              total: results.total,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条`,
              onChange: onResultPage,
            }}
          />
          <EvalResultDrawer
            result={activeResult}
            onClose={onCloseResult}
            onContinueResult={onContinueResult}
            continuing={continuing}
          />
        </div>
      ) : (
        <Empty description="请选择评测任务" />
      )}
    </Drawer>
  );
}

function EvalResultDrawer({
  result,
  onClose,
  onContinueResult,
  continuing,
}: {
  result?: TextToSqlEvalResultItem;
  onClose: () => void;
  onContinueResult: (record: TextToSqlEvalResultItem, clarificationAnswer: string) => Promise<void>;
  continuing: boolean;
}) {
  const [clarificationAnswer, setClarificationAnswer] = useState('');

  useEffect(() => {
    setClarificationAnswer('');
  }, [result?.id]);

  return (
    <Drawer title={result ? `样本结果 #${result.id}` : '样本结果'} open={Boolean(result)} onClose={onClose} width={920}>
      {result ? (
        <div className="eval-result-detail">
          <section className="eval-result-question">
            <ResultStatusTag status={result.resultStatus || (result.passed ? 'PASSED' : 'FAILED')} />
            <Paragraph>{result.question}</Paragraph>
            {result.errorMessage ? <Text type="danger">{result.errorMessage}</Text> : null}
          </section>
          {result.resultStatus === 'INTERRUPTED' ? (
            <section className="eval-result-continue">
              <div className="eval-result-section-title">继续澄清</div>
              <Input.TextArea
                rows={4}
                maxLength={1000}
                showCount
                value={clarificationAnswer}
                placeholder="输入这次澄清的补充回答，然后继续执行这个评测样本"
                onChange={(event) => setClarificationAnswer(event.target.value)}
              />
              <Button
                type="primary"
                loading={continuing}
                disabled={!clarificationAnswer.trim()}
                onClick={() => onContinueResult(result, clarificationAnswer.trim())}
              >
                继续运行
              </Button>
            </section>
          ) : null}
          <section>
            <div className="eval-result-section-title">断言结果</div>
            <div className="eval-result-assertion-list">
              {result.assertionResults?.length ? (
                result.assertionResults.map((item) => <AssertionResultCard key={item.id} item={item} />)
              ) : (
                <Empty description="没有断言结果" />
              )}
            </div>
          </section>
          <section>
            <div className="eval-result-section-title">State 快照</div>
            <pre className="eval-result-json">{formatJson(result.stateSnapshotJson)}</pre>
          </section>
          <section>
            <div className="eval-result-section-title">节点历史</div>
            <pre className="eval-result-json">{formatJson(result.stateHistoryJson)}</pre>
          </section>
        </div>
      ) : (
        <Empty description="请选择样本结果" />
      )}
    </Drawer>
  );
}

function AssertionResultCard({ item }: { item: TextToSqlEvalAssertionResultItem }) {
  return (
    <div className="eval-result-assertion-card">
      <div>
        <strong>{item.actualKey}</strong>
        <Space size={6} wrap>
          <Tag>{item.operator}</Tag>
          {item.required ? <Tag color="blue">影响最终结果</Tag> : <Tag>仅记录</Tag>}
          {item.passed ? <Tag color="green">通过</Tag> : <Tag color="red">失败</Tag>}
        </Space>
      </div>
      <Descriptions column={2} size="small">
        <Descriptions.Item label="期望值">{item.expectedValue || '-'}</Descriptions.Item>
        <Descriptions.Item label="实际值">{shortText(item.actualValue)}</Descriptions.Item>
        <Descriptions.Item label="得分">{Number(item.score || 0).toFixed(2)}</Descriptions.Item>
        <Descriptions.Item label="原因">{item.reason || '-'}</Descriptions.Item>
      </Descriptions>
    </div>
  );
}

function TaskStatusTag({ status }: { status?: string }) {
  const meta = status ? taskStatusMeta[status] : undefined;
  return <Tag color={meta?.color || 'default'}>{meta?.text || status || '-'}</Tag>;
}

function ResultStatusTag({ status }: { status?: string }) {
  const meta = status ? resultStatusMeta[status] : undefined;
  return <Tag color={meta?.color || 'default'}>{meta?.text || status || '-'}</Tag>;
}

function cleanTaskParams(params: TextToSqlEvalTaskPageParams): TextToSqlEvalTaskPageParams {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== ''),
  ) as unknown as TextToSqlEvalTaskPageParams;
}

function formatTime(value?: string) {
  if (!value) {
    return '-';
  }
  return value.replace('T', ' ').slice(0, 19);
}

function formatDuration(value?: number) {
  if (!value) {
    return '-';
  }
  if (value < 1000) {
    return `${value}ms`;
  }
  return `${(value / 1000).toFixed(1)}s`;
}

function formatJson(value?: string) {
  if (!value) {
    return '暂无数据';
  }
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
}

function shortText(value?: string) {
  if (!value) {
    return '-';
  }
  const text = formatJson(value);
  return text.length > 180 ? `${text.slice(0, 180)}...` : text;
}
