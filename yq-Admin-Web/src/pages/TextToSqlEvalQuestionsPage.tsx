import { AutoComplete, Button, Drawer, Empty, Form, Input, InputNumber, Modal, Select, Space, Switch, Table, Tag, Typography, message } from 'antd';
import type { TableColumnsType } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { textToSqlAnalysisApi, textToSqlEvalQuestionApi } from '../api/system';
import type {
  PageResult,
  TextToSqlEvalAssertionItem,
  TextToSqlEvalQuestionItem,
  TextToSqlEvalQuestionPageParams,
  TextToSqlEvalQuestionValues,
  TextToSqlRunItem,
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

const sourceOptions = [
  { label: '手动录入', value: 'MANUAL', color: 'default' },
  { label: '运行记录', value: 'RUN_HISTORY', color: 'blue' },
  { label: '反馈沉淀', value: 'FEEDBACK', color: 'volcano' },
];

const statusOptions = [
  { label: '草稿', value: 'DRAFT', color: 'default' },
  { label: '正式', value: 'ACTIVE', color: 'green' },
  { label: '停用', value: 'DISABLED', color: 'red' },
];

const operatorOptions = [
  { label: '等于', value: 'EQ' },
  { label: '包含', value: 'CONTAINS' },
  { label: '不包含', value: 'NOT_CONTAINS' },
  { label: '存在', value: 'EXISTS' },
  { label: '非空', value: 'NOT_EMPTY' },
  { label: '正则', value: 'REGEX' },
  { label: '语义判断', value: 'SEMANTIC' },
];

const failureTypeOptions = [
  { label: '意图错误', value: 'INTENT_ERROR' },
  { label: '选表错误', value: 'TABLE_SELECTION_ERROR' },
  { label: 'SQL生成错误', value: 'SQL_GENERATION_ERROR' },
  { label: '澄清错误', value: 'CLARIFICATION_ERROR' },
  { label: '回答质量错误', value: 'ANSWER_QUALITY_ERROR' },
  { label: 'State断言错误', value: 'STATE_ASSERT_ERROR' },
];

const stateKeyOptions = [
  'request.question',
  'intent_result.intent',
  'intent_result.business_domain',
  'action',
  'selected_tables',
  'table_selection_result.action',
  'table_selection_result.selected_tables',
  'sql_generation_result.action',
  'sql_generation_result.sql',
  'sql',
  'executed_sql',
  'rows',
  'answer',
  'result_summary.conclusion',
].map((value) => ({ value, label: value }));

const optionLabel = (options: Array<{ label: string; value: string }>, value?: string) =>
  options.find((item) => item.value === value)?.label || value || '-';

const optionColor = (options: Array<{ color?: string; value: string }>, value?: string) =>
  options.find((item) => item.value === value)?.color || 'default';

interface StateCandidate {
  key: string;
  source: string;
  path: string;
  value: unknown;
}

export default function TextToSqlEvalQuestionsPage() {
  const [filterForm] = Form.useForm<TextToSqlEvalQuestionPageParams>();
  const [editForm] = Form.useForm<TextToSqlEvalQuestionValues>();
  const [searchParams] = useSearchParams();
  const [page, setPage] = useState<PageResult<TextToSqlEvalQuestionItem>>({
    total: 0,
    pageNum: 1,
    pageSize: 10,
    records: [],
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<TextToSqlEvalQuestionItem>();
  const [sourceRun, setSourceRun] = useState<TextToSqlRunItem>();
  const [sourceLoading, setSourceLoading] = useState(false);
  const [detail, setDetail] = useState<TextToSqlEvalQuestionItem>();
  const stats = useMemo(() => {
    const records = page.records;
    return [
      { label: '样本总数', value: page.total },
      { label: '本页正式', value: records.filter((item) => item.status === 'ACTIVE').length },
      { label: '本页草稿', value: records.filter((item) => item.status === 'DRAFT').length },
      { label: '反馈沉淀', value: records.filter((item) => item.sourceType === 'FEEDBACK').length },
    ];
  }, [page]);

  useEffect(() => {
    load({ pageNum: 1, pageSize: 10 });
    const id = Number(searchParams.get('id'));
    if (id > 0) {
      openDetail(id);
    }
  }, []);

  async function load(next?: Partial<TextToSqlEvalQuestionPageParams>) {
    setLoading(true);
    try {
      const values = filterForm.getFieldsValue();
      const params: TextToSqlEvalQuestionPageParams = {
        ...values,
        ...next,
        pageNum: next?.pageNum || page.pageNum || 1,
        pageSize: next?.pageSize || page.pageSize || 10,
      };
      const data = await textToSqlEvalQuestionApi.page(cleanParams(params));
      setPage(data);
    } finally {
      setLoading(false);
    }
  }

  async function openDetail(id: number) {
    try {
      setDetail(await textToSqlEvalQuestionApi.detail(id));
    } catch {
      message.error('评测样本详情加载失败');
    }
  }

  function openCreate() {
    setEditing(undefined);
    setSourceRun(undefined);
    editForm.resetFields();
    editForm.setFieldsValue({
      evalTarget: 'END_TO_END',
      sampleCategory: 'NORMAL',
      status: 'DRAFT',
      assertions: [],
    });
    setEditOpen(true);
  }

  async function openEdit(record: TextToSqlEvalQuestionItem) {
    const data = record.assertions?.length ? record : await textToSqlEvalQuestionApi.detail(record.id);
    setEditing(data);
    setSourceRun(undefined);
    editForm.setFieldsValue({
      question: data.question,
      businessDomain: data.businessDomain,
      evalTarget: data.evalTarget,
      sampleCategory: data.sampleCategory,
      judgeNote: data.judgeNote,
      remark: data.remark,
      status: data.status,
      assertions: data.assertions || [],
    });
    setEditOpen(true);
    if (data.sourceRunId) {
      setSourceLoading(true);
      try {
        setSourceRun(await textToSqlAnalysisApi.runDetail(data.sourceRunId));
      } catch {
        message.warning('来源运行记录加载失败，暂时只能手动整理断言');
      } finally {
        setSourceLoading(false);
      }
    }
  }

  async function save() {
    const values = await editForm.validateFields();
    setSaving(true);
    try {
      const payload = normalizePayload(values);
      if (editing) {
        await textToSqlEvalQuestionApi.update(editing.id, payload);
        message.success('样本已保存');
      } else {
        await textToSqlEvalQuestionApi.create(payload);
        message.success('样本已新增');
      }
      setEditOpen(false);
      await load({ pageNum: editing ? page.pageNum : 1 });
    } finally {
      setSaving(false);
    }
  }

  function reset() {
    filterForm.resetFields();
    load({ pageNum: 1 });
  }

  const columns: TableColumnsType<TextToSqlEvalQuestionItem> = [
    { title: 'ID', dataIndex: 'id', width: 72 },
    {
      title: '问题',
      dataIndex: 'question',
      width: 360,
      render: (value?: string, record?: TextToSqlEvalQuestionItem) => (
        <div className="eval-question-cell">
          <strong>{value || '-'}</strong>
          <span>{record?.judgeNote || record?.remark || '暂无判断说明'}</span>
        </div>
      ),
    },
    {
      title: '业务环境',
      dataIndex: 'businessDomain',
      width: 110,
      render: (value?: string) => <Tag>{optionLabel(businessOptions, value)}</Tag>,
    },
    {
      title: '评测目标',
      dataIndex: 'evalTarget',
      width: 120,
      render: (value?: string) => <Tag color={optionColor(evalTargetOptions, value)}>{optionLabel(evalTargetOptions, value)}</Tag>,
    },
    {
      title: '场景',
      dataIndex: 'sampleCategory',
      width: 110,
      render: (value?: string) => <Tag color={optionColor(sampleCategoryOptions, value)}>{optionLabel(sampleCategoryOptions, value)}</Tag>,
    },
    {
      title: '来源',
      dataIndex: 'sourceType',
      width: 100,
      render: (value?: string) => <Tag color={optionColor(sourceOptions, value)}>{optionLabel(sourceOptions, value)}</Tag>,
    },
    {
      title: '断言数',
      dataIndex: 'assertionCount',
      width: 90,
      render: (value?: number) => <span className="eval-assertion-count">{value || 0}</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (value?: string) => <Tag color={optionColor(statusOptions, value)}>{optionLabel(statusOptions, value)}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      width: 170,
      render: (value?: string) => formatTime(value),
    },
    {
      title: '操作',
      width: 130,
      fixed: 'right',
      render: (_, record) => (
        <Space size={6}>
          <Button size="small" onClick={() => openDetail(record.id)}>
            详情
          </Button>
          <Button size="small" type="primary" ghost onClick={() => openEdit(record)}>
            整理
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="text-sql-eval-page">
      <section className="eval-question-hero">
        <div>
          <div className="eval-question-kicker">Text-to-SQL Eval Samples</div>
          <h2>评测样本库</h2>
          <p>保存用户问题、业务环境和 State 断言，后续评测直接按这些规则回归。</p>
        </div>
        <div className="eval-question-hero-actions">
          {stats.map((item) => (
            <div className="eval-question-stat" key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
          <Button type="primary" onClick={openCreate}>
            录入样本
          </Button>
          <Button>
            <Link to="/textToSqlEvalTasks">查看评测任务</Link>
          </Button>
        </div>
      </section>

      <section className="eval-question-filter">
        <Form form={filterForm} layout="inline">
          <Form.Item name="keyword">
            <Input.Search className="eval-question-search" placeholder="搜索问题、判断说明或备注" allowClear onSearch={() => load({ pageNum: 1 })} />
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
          <Form.Item name="sourceType">
            <Select placeholder="来源" allowClear options={sourceOptions} style={{ width: 130 }} />
          </Form.Item>
          <Form.Item name="status">
            <Select placeholder="状态" allowClear options={statusOptions} style={{ width: 110 }} />
          </Form.Item>
          <Space>
            <Button type="primary" onClick={() => load({ pageNum: 1 })}>
              查询
            </Button>
            <Button onClick={reset}>重置</Button>
          </Space>
        </Form>
      </section>

      <section className="eval-question-table">
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={page.records}
          scroll={{ x: 1100 }}
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
        title={editing ? '整理评测样本' : '录入评测样本'}
        open={editOpen}
        width={1080}
        className="eval-question-modal"
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
        onOk={save}
        onCancel={() => setEditOpen(false)}
        destroyOnClose
      >
        <EvalQuestionForm form={editForm} sourceRun={sourceRun} sourceLoading={sourceLoading} />
      </Modal>

      <EvalQuestionDrawer
        record={detail}
        onClose={() => setDetail(undefined)}
        onEdit={(record) => openEdit(record)}
      />
    </div>
  );
}

function EvalQuestionForm({
  form,
  sourceRun,
  sourceLoading,
}: {
  form: ReturnType<typeof Form.useForm<TextToSqlEvalQuestionValues>>[0];
  sourceRun?: TextToSqlRunItem;
  sourceLoading: boolean;
}) {
  return (
    <Form form={form} className="eval-question-form" layout="vertical">
      <div className="eval-question-form-top">
        <div className="eval-question-primary-panel">
          <div className="eval-question-section-head">
            <span>Question</span>
            <strong>问题内容</strong>
          </div>
          <Form.Item name="question" label="用户问题" rules={[{ required: true, whitespace: true, message: '请输入用户问题' }]}>
            <Input.TextArea rows={5} maxLength={1000} showCount placeholder="输入这条评测样本要复测的原始问题" />
          </Form.Item>
          <div className="eval-question-note-grid">
            <Form.Item name="judgeNote" label="人工判断说明">
              <Input.TextArea rows={3} maxLength={1000} showCount placeholder="这条样本重点判断什么" />
            </Form.Item>
            <Form.Item name="remark" label="备注">
              <Input.TextArea rows={3} maxLength={1000} showCount placeholder="补充说明，可不填" />
            </Form.Item>
          </div>
        </div>

        <div className="eval-question-side-panel">
          <div className="eval-question-section-head">
            <span>Meta</span>
            <strong>样本定位</strong>
          </div>
          <Form.Item name="businessDomain" label="业务环境">
            <Select allowClear options={businessOptions} placeholder="选择业务环境" />
          </Form.Item>
          <Form.Item name="evalTarget" label="评测目标" rules={[{ required: true, message: '请选择评测目标' }]}>
            <Select options={evalTargetOptions} />
          </Form.Item>
          <Form.Item name="sampleCategory" label="样本场景" rules={[{ required: true, message: '请选择样本场景' }]}>
            <Select options={sampleCategoryOptions} />
          </Form.Item>
          <Form.Item name="status" label="状态" rules={[{ required: true, message: '请选择状态' }]}>
            <Select options={statusOptions} />
          </Form.Item>
        </div>
      </div>

      <div className="eval-question-form-section eval-question-assertion-panel">
        <div className="eval-question-section-head">
          <span>Assertions</span>
          <strong>State 判断标准</strong>
          <p>客观字段直接比对 State；最终回答这类自然语言字段用语义判断。</p>
        </div>
        <Form.List name="assertions">
          {(fields, { add, remove }) => (
            <div className="eval-assertion-list">
              <AssertionPicker form={form} sourceRun={sourceRun} sourceLoading={sourceLoading} />
              {fields.length ? (
                fields.map((field) => (
                  <div className="eval-assertion-row" key={field.key}>
                    <div className="eval-assertion-main">
                      <Form.Item name={[field.name, 'actualKey']} label="State 路径" rules={[{ required: true, message: '请输入State路径' }]}>
                        <AutoComplete options={stateKeyOptions} placeholder="选择或输入 State 路径" />
                      </Form.Item>
                      <Form.Item name={[field.name, 'operator']} label="判断方式" initialValue="EQ">
                        <Select options={operatorOptions} />
                      </Form.Item>
                      <Form.Item shouldUpdate noStyle>
                        {({ getFieldValue }) => {
                          const operator = getFieldValue(['assertions', field.name, 'operator']);
                          if (operator === 'SEMANTIC' || operator === 'EXISTS' || operator === 'NOT_EMPTY') {
                            return (
                              <Form.Item label="期望值">
                                <Input disabled placeholder="当前判断方式不需要填写" />
                              </Form.Item>
                            );
                          }
                          return (
                            <Form.Item name={[field.name, 'expectedValue']} label="期望值">
                              <Input placeholder="期望值" />
                            </Form.Item>
                          );
                        }}
                      </Form.Item>
                      <Form.Item name={[field.name, 'required']} label="影响最终结果" valuePropName="checked" initialValue>
                        <Switch />
                      </Form.Item>
                      <Button className="eval-assertion-remove" danger onClick={() => remove(field.name)}>
                        删除
                      </Button>
                    </div>
                    <details className="eval-assertion-advanced">
                      <summary>高级设置</summary>
                      <Form.Item name={[field.name, 'failureType']} label="失败归因">
                        <Select allowClear options={failureTypeOptions} placeholder="可不填，后续用于研发统计失败原因" />
                      </Form.Item>
                    </details>
                    <Form.Item shouldUpdate noStyle>
                      {({ getFieldValue }) => {
                        const operator = getFieldValue(['assertions', field.name, 'operator']);
                        if (operator !== 'SEMANTIC') {
                          return null;
                        }
                        return (
                          <div className="eval-semantic-grid">
                            <Form.Item name={[field.name, 'referenceAnswer']} label="参考答案">
                              <Input.TextArea rows={2} />
                            </Form.Item>
                            <Form.Item name={[field.name, 'keyPoints']} label="关键要点">
                              <Input.TextArea rows={2} placeholder="每行一个要点" />
                            </Form.Item>
                            <Form.Item name={[field.name, 'forbiddenPoints']} label="禁止内容">
                              <Input.TextArea rows={2} placeholder="每行一个禁止点" />
                            </Form.Item>
                            <Form.Item name={[field.name, 'minScore']} label="最低分">
                              <InputNumber min={0} max={100} placeholder="80" style={{ width: '100%' }} />
                            </Form.Item>
                          </div>
                        );
                      }}
                    </Form.Item>
                  </div>
                ))
              ) : (
                <Empty className="eval-assertion-empty" description="还没有判断标准" />
              )}
              <Button className="eval-assertion-add" type="dashed" onClick={() => add({ operator: 'EQ', required: true })}>添加判断标准</Button>
            </div>
          )}
        </Form.List>
      </div>
    </Form>
  );
}

function AssertionPicker({
  form,
  sourceRun,
  sourceLoading,
}: {
  form: ReturnType<typeof Form.useForm<TextToSqlEvalQuestionValues>>[0];
  sourceRun?: TextToSqlRunItem;
  sourceLoading: boolean;
}) {
  const candidates = useMemo(() => buildStateCandidates(sourceRun), [sourceRun]);

  function appendAssertion(candidate: StateCandidate, operator: string) {
    const assertions = form.getFieldValue('assertions') || [];
    const nextAssertion: TextToSqlEvalAssertionItem = {
      actualKey: candidate.path,
      operator,
      expectedValue: buildExpectedValue(operator, candidate.value),
      required: true,
      weight: 1,
      failureType: guessFailureType(candidate.path),
      referenceAnswer: operator === 'SEMANTIC' ? stringifyValue(candidate.value) : undefined,
      minScore: operator === 'SEMANTIC' ? 80 : undefined,
    };
    form.setFieldsValue({ assertions: [...assertions, nextAssertion] });
    message.success(`已添加断言：${candidate.path}`);
  }

  const columns: TableColumnsType<StateCandidate> = [
    {
      title: '来源',
      dataIndex: 'source',
      width: 150,
      render: (value: string) => <Tag color={value === 'State 快照' ? 'blue' : 'cyan'}>{value}</Tag>,
    },
    {
      title: 'State 路径',
      dataIndex: 'path',
      width: 260,
      render: (value: string) => <Text code>{value}</Text>,
    },
    {
      title: '当前值',
      dataIndex: 'value',
      render: (value: unknown) => <span className="eval-source-value">{stringifyValue(value)}</span>,
    },
    {
      title: '生成断言',
      width: 250,
      render: (_, record) => (
        <Space size={6} wrap>
          <Button size="small" onClick={() => appendAssertion(record, 'NOT_EMPTY')}>
            非空
          </Button>
          <Button size="small" onClick={() => appendAssertion(record, 'EQ')} disabled={!canUseExpectedValue(record.value)}>
            等于
          </Button>
          <Button size="small" onClick={() => appendAssertion(record, 'CONTAINS')} disabled={!canUseExpectedValue(record.value)}>
            包含
          </Button>
          <Button size="small" onClick={() => appendAssertion(record, 'SEMANTIC')} disabled={!isTextLike(record.value)}>
            语义
          </Button>
        </Space>
      ),
    },
  ];

  if (!sourceRun && !sourceLoading) {
    return null;
  }

  return (
    <div className="eval-assertion-picker">
      <div className="eval-assertion-picker-head">
        <div>
          <span>From Run</span>
          <strong>从来源运行记录生成断言</strong>
          <p>点选 State 快照或节点写入字段，自动追加到下面的判断标准里。</p>
        </div>
        {sourceRun ? <Link to={`/textToSqlRuns?runId=${sourceRun.id}`}>运行记录 #{sourceRun.id}</Link> : null}
      </div>
      <Table
        size="small"
        rowKey="key"
        loading={sourceLoading}
        columns={columns}
        dataSource={candidates}
        pagination={{ pageSize: 8, showSizeChanger: false }}
        locale={{ emptyText: sourceLoading ? '加载来源运行记录中' : '来源运行记录里暂时没有可生成断言的字段' }}
      />
    </div>
  );
}

function EvalQuestionDrawer({
  record,
  onClose,
  onEdit,
}: {
  record?: TextToSqlEvalQuestionItem;
  onClose: () => void;
  onEdit: (record: TextToSqlEvalQuestionItem) => void;
}) {
  return (
    <Drawer title={record ? `评测样本 #${record.id}` : '评测样本'} open={Boolean(record)} onClose={onClose} width={920}>
      {record ? (
        <div className="eval-question-detail">
          <section className="eval-question-detail-head">
            <div>
              <Text type="secondary">用户问题</Text>
              <Paragraph>{record.question}</Paragraph>
            </div>
            <Button type="primary" onClick={() => onEdit(record)}>
              整理
            </Button>
          </section>
          <div className="eval-question-tags">
            <Tag>{optionLabel(businessOptions, record.businessDomain)}</Tag>
            <Tag color={optionColor(evalTargetOptions, record.evalTarget)}>{optionLabel(evalTargetOptions, record.evalTarget)}</Tag>
            <Tag color={optionColor(sampleCategoryOptions, record.sampleCategory)}>{optionLabel(sampleCategoryOptions, record.sampleCategory)}</Tag>
            <Tag>{optionLabel(sourceOptions, record.sourceType)}</Tag>
            <Tag color={optionColor(statusOptions, record.status)}>{optionLabel(statusOptions, record.status)}</Tag>
            {record.sourceRunId ? <Link to={`/textToSqlRuns?runId=${record.sourceRunId}`}>来源运行记录 #{record.sourceRunId}</Link> : null}
          </div>
          {record.judgeNote ? <InfoBlock title="人工判断说明" text={record.judgeNote} /> : null}
          {record.remark ? <InfoBlock title="备注" text={record.remark} /> : null}
          <section className="eval-question-assertions">
            <div className="eval-question-section-title">判断标准</div>
            {record.assertions?.length ? (
              record.assertions.map((item) => <AssertionCard key={item.id || `${item.actualKey}-${item.sortOrder}`} item={item} />)
            ) : (
              <Empty description="没有判断标准" />
            )}
          </section>
        </div>
      ) : (
        <Empty description="请选择样本" />
      )}
    </Drawer>
  );
}

function AssertionCard({ item }: { item: TextToSqlEvalAssertionItem }) {
  return (
    <div className="eval-assertion-card">
      <div>
        <strong>{item.actualKey}</strong>
        <span>{optionLabel(operatorOptions, item.operator)}</span>
      </div>
      <pre>{item.operator === 'SEMANTIC' ? semanticText(item) : item.expectedValue || '-'}</pre>
      <Space wrap size={6}>
        {item.required ? <Tag color="red">必过</Tag> : <Tag>可选</Tag>}
        {item.failureType ? <Tag>{item.failureType}</Tag> : null}
        {item.minScore ? <Tag color="blue">最低 {item.minScore}</Tag> : null}
      </Space>
    </div>
  );
}

function InfoBlock({ title, text }: { title: string; text: string }) {
  return (
    <section className="eval-info-block">
      <Text strong>{title}</Text>
      <Paragraph>{text}</Paragraph>
    </section>
  );
}

function normalizePayload(values: TextToSqlEvalQuestionValues): TextToSqlEvalQuestionValues {
  return {
    ...values,
    assertions: (values.assertions || []).map((item) => ({
      ...item,
      expectedValue: ['SEMANTIC', 'EXISTS', 'NOT_EMPTY'].includes(item.operator || '') ? undefined : item.expectedValue,
    })),
  };
}

function semanticText(item: TextToSqlEvalAssertionItem) {
  return [
    item.referenceAnswer ? `参考答案：${item.referenceAnswer}` : '',
    item.keyPoints ? `关键要点：\n${item.keyPoints}` : '',
    item.forbiddenPoints ? `禁止内容：\n${item.forbiddenPoints}` : '',
  ].filter(Boolean).join('\n\n') || '语义判断标准待补充';
}

function cleanParams(params: TextToSqlEvalQuestionPageParams): TextToSqlEvalQuestionPageParams {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== ''),
  ) as unknown as TextToSqlEvalQuestionPageParams;
}

function formatTime(value?: string) {
  if (!value) {
    return '-';
  }
  return value.replace('T', ' ').slice(0, 19);
}

function buildStateCandidates(sourceRun?: TextToSqlRunItem): StateCandidate[] {
  if (!sourceRun) {
    return [];
  }
  const candidates: StateCandidate[] = [];
  const snapshot = parseJsonValue(sourceRun.stateSnapshotJson);
  candidates.push(...flattenValue(snapshot, 'State 快照', ''));

  const history = parseJsonValue(sourceRun.stateHistoryJson);
  if (Array.isArray(history)) {
    history.forEach((item, index) => {
      const step = readObject(item);
      const stepName = `Step ${step?.step || index + 1}`;
      const writes = Array.isArray(step?.writes) ? step.writes : [];
      writes.forEach((writeItem, writeIndex) => {
        const write = readObject(writeItem);
        const nodeName = String(write?.node || write?.name || step?.source || stepName);
        candidates.push(...flattenValue(write?.result, `节点 ${nodeName}`, '', `write-${index}-${writeIndex}`));
      });
      const tasks = Array.isArray(step?.tasks) ? step.tasks : [];
      tasks.forEach((taskItem, taskIndex) => {
        const task = readObject(taskItem);
        if (task?.result) {
          const nodeName = String(task.name || stepName);
          candidates.push(...flattenValue(task.result, `节点 ${nodeName}`, '', `task-${index}-${taskIndex}`));
        }
      });
    });
  }

  const seen = new Set<string>();
  return candidates
    .filter((item) => item.path)
    .filter((item) => {
      const uniqueKey = `${item.source}:${item.path}:${stringifyValue(item.value).slice(0, 80)}`;
      if (seen.has(uniqueKey)) {
        return false;
      }
      seen.add(uniqueKey);
      return true;
    })
    .slice(0, 160);
}

function flattenValue(value: unknown, source: string, prefix: string, keyPrefix = source): StateCandidate[] {
  if (value === undefined || value === null) {
    return [];
  }
  if (Array.isArray(value)) {
    return prefix ? [{ key: `${keyPrefix}:${prefix}`, source, path: prefix, value }] : [];
  }
  if (typeof value !== 'object') {
    return prefix ? [{ key: `${keyPrefix}:${prefix}`, source, path: prefix, value }] : [];
  }

  const objectValue = value as Record<string, unknown>;
  return Object.entries(objectValue).flatMap(([key, child]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (Array.isArray(child) || child === null || typeof child !== 'object') {
      return [{ key: `${keyPrefix}:${path}`, source, path, value: child }];
    }
    return flattenValue(child, source, path, keyPrefix);
  });
}

function parseJsonValue(value?: string): unknown {
  if (!value) {
    return undefined;
  }
  try {
    const parsed = JSON.parse(value);
    if (typeof parsed === 'string' && /^[\[{]/.test(parsed.trim())) {
      return JSON.parse(parsed);
    }
    return parsed;
  } catch {
    return undefined;
  }
}

function readObject(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === 'object' ? value as Record<string, unknown> : undefined;
}

function buildExpectedValue(operator: string, value: unknown) {
  if (['EXISTS', 'NOT_EMPTY', 'SEMANTIC'].includes(operator)) {
    return undefined;
  }
  if (Array.isArray(value)) {
    const first = value.find((item) => item !== undefined && item !== null);
    return stringifyValue(first ?? value);
  }
  return stringifyValue(value);
}

function stringifyValue(value: unknown) {
  if (value === undefined || value === null) {
    return '';
  }
  if (typeof value === 'string') {
    return value;
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function canUseExpectedValue(value: unknown) {
  return value !== undefined && value !== null && stringifyValue(value) !== '';
}

function isTextLike(value: unknown) {
  return typeof value === 'string' && value.trim().length > 0;
}

function guessFailureType(path: string) {
  if (path.includes('intent')) {
    return 'INTENT_ERROR';
  }
  if (path.includes('table') || path.includes('selected_tables')) {
    return 'TABLE_SELECTION_ERROR';
  }
  if (path.includes('sql')) {
    return 'SQL_GENERATION_ERROR';
  }
  if (path.includes('answer') || path.includes('summary') || path.includes('conclusion')) {
    return 'ANSWER_QUALITY_ERROR';
  }
  return 'STATE_ASSERT_ERROR';
}
