export type ActiveStatus = 'ACTIVE' | 'INACTIVE';

export interface PageResult<T> {
  total: number;
  pageNum: number;
  pageSize: number;
  records: T[];
}

export interface LoginValues {
  username: string;
  password: string;
}

export interface LoginResult {
  token: string;
  signSecret: string;
  userDetailRes?: UserItem;
  permissionDetailResList?: PermissionItem[];
  roleDetailResList?: RoleItem[];
}

export interface UserItem {
  id: number;
  username: string;
  nickname: string;
  realName?: string;
  phone?: string;
  email?: string;
  unionId?: string;
  status: ActiveStatus;
  statusDesc?: string;
  createdAt?: string;
  updatedAt?: string;
  roleIds?: number[];
}

export interface UserCreateValues {
  username: string;
  password: string;
  nickname: string;
  realName?: string;
  phone?: string;
  email?: string;
  status: ActiveStatus;
}

export interface UserUpdateValues {
  nickname: string;
  realName?: string;
  phone?: string;
  email?: string;
  unionId?: string;
  status: ActiveStatus;
}

export interface UserPageParams {
  keyword?: string;
  status?: ActiveStatus;
  roleCode?: string;
  pageNum: number;
  pageSize: number;
}

export interface StudentItem {
  id: number;
  studentNo: string;
  studentName: string;
  studentPhone: string;
  education: string;
  gradeYear: number;
  school: string;
  major?: string;
  teachingMode: ProductTeachingMode;
  classId?: number;
  classPeriod?: string;
  productContent?: string;
  studentTag?: string;
  status: ActiveStatus;
  sopAssigned?: boolean;
  sopId?: number;
  sopMentorId?: number;
  sopMentorName?: string;
  sopVideoObjectKey?: string;
  sopVideoFileName?: string;
  sopTime?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface StudentPageParams {
  studentName?: string;
  studentPhone?: string;
  education?: string;
  school?: string;
  teachingMode?: ProductTeachingMode;
  studentTag?: string;
  status?: ActiveStatus;
  pageNum: number;
  pageSize: number;
}

export interface StudentTagUpdateValues {
  studentTag?: string;
}

export interface StudentFollowupTagItem {
  id: number;
  studentTag: string;
  followupIntervalDays: number;
  status: ActiveStatus;
  remark?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface StudentFollowupTagValues {
  studentTag: string;
  followupIntervalDays: number;
  status?: ActiveStatus;
  remark?: string;
}

export interface StudentFollowupTagPageParams {
  studentTag?: string;
  status?: ActiveStatus;
  pageNum: number;
  pageSize: number;
}

export type StudentFollowupRecordStatus = 'NEED_FOLLOWUP' | 'FOLLOWED' | 'CANCELED';

export interface StudentFollowupRecordItem {
  id: number;
  studentId: number;
  studentName?: string;
  studentPhone?: string;
  learningPlanId?: number;
  studentTag: string;
  enrollDate: string;
  lastFollowupTime?: string;
  dueDate: string;
  followupIntervalDays: number;
  status: StudentFollowupRecordStatus;
  followupUserId?: number;
  followupUserName?: string;
  followupTime?: string;
  followupContent?: string;
  followupVideoObjectKey?: string;
  followupVideoFileName?: string;
  remark?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface StudentFollowupRecordPageParams {
  studentName?: string;
  studentPhone?: string;
  studentTag?: string;
  status?: StudentFollowupRecordStatus;
  followupUserId?: number;
  startDate?: string;
  endDate?: string;
  pageNum: number;
  pageSize: number;
}

export interface StudentFollowupRecordStats {
  totalCount: number;
  todayNeedFollowupCount: number;
  todayFollowedCount: number;
  completedCount: number;
  completionRate: number;
}

export interface StudentFollowupRecordCompleteValues {
  followupContent: string;
  followupVideoObjectKey: string;
  followupVideoFileName: string;
  remark?: string;
}

export interface StudentFollowupRecordCancelValues {
  remark?: string;
}

export interface StudentSopAssignValues {
  mentorId: number;
}

export interface StudentSopItem {
  id: number;
  studentId: number;
  studentName?: string;
  studentPhone?: string;
  teachingMode?: ProductTeachingMode;
  mentorId: number;
  mentorName?: string;
  sopVideoObjectKey?: string;
  sopVideoFileName?: string;
  sopTime?: string;
  status: string;
  learningPlanCreated?: boolean;
  remark?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface StudentSopCompleteValues {
  sopVideoObjectKey: string;
  sopVideoFileName?: string;
  sopTime: string;
}

export interface StudentSopPageParams {
  studentName?: string;
  studentPhone?: string;
  mentorId?: number;
  status?: string;
  pageNum: number;
  pageSize: number;
}

export interface StudentLearningPlanStageValues {
  stageName: string;
  stageDays: number;
}

export interface StudentLearningPlanCreateValues {
  sopId: number;
  courseId: number;
  startDate: string;
  stages: StudentLearningPlanStageValues[];
}

export interface StudentLearningPlanItem {
  id: number;
  studentId: number;
  studentName?: string;
  studentPhone?: string;
  courseId: number;
  courseName?: string;
  sopId: number;
  startDate: string;
  status: string;
  createdAt?: string;
}

export interface StudentLearningPlanPageParams {
  studentName?: string;
  studentPhone?: string;
  courseId?: number;
  status?: string;
  pageNum: number;
  pageSize: number;
}

export interface StudentLearningPlanStageItem {
  id: number;
  planId: number;
  stageName: string;
  stageDays: number;
  sortOrder: number;
}

export interface StudentLearningPlanDetail {
  id: number;
  studentId: number;
  studentName?: string;
  studentPhone?: string;
  courseId: number;
  courseName?: string;
  sopId: number;
  startDate: string;
  status: string;
  stages: StudentLearningPlanStageItem[];
}

export interface StudentLearningCalendarItem {
  id: number;
  planId: number;
  studentId: number;
  studyDate: string;
  stageName: string;
  dayIndex: number;
  stageDayIndex: number;
  status: string;
}

export interface RoleItem {
  id: number;
  roleCode: string;
  roleName: string;
  description?: string;
  status: ActiveStatus;
  permissionIds?: number[];
  createdAt?: string;
  updatedAt?: string;
}

export interface RoleValues {
  roleCode: string;
  roleName: string;
  description?: string;
  status: ActiveStatus;
  permissionIds?: number[];
}

export interface RolePageParams {
  keyword?: string;
  status?: ActiveStatus;
  pageNum: number;
  pageSize: number;
}

export interface TextToSqlColumnNode {
  id: number;
  tableId: number;
  businessDomain: string;
  tableName: string;
  columnName: string;
  columnComment?: string;
  status: ActiveStatus;
}

export interface TextToSqlTableNode {
  id: number;
  businessDomain: string;
  tableName: string;
  tableComment?: string;
  status: ActiveStatus;
  columns: TextToSqlColumnNode[];
}

export interface TextToSqlSchemaDomain {
  businessDomain: string;
  businessDomainName: string;
  tables: TextToSqlTableNode[];
}

export interface TextToSqlColumnGrant {
  businessDomain: string;
  tableName: string;
  columnName: string;
  granted: boolean;
}

export interface TextToSqlRolePermissionDetail {
  roleId: number;
  grants: TextToSqlColumnGrant[];
}

export interface TextToSqlRolePermissionSaveValues {
  grants: TextToSqlColumnGrant[];
}

export interface TextToSqlAnalyzeValues {
  question: string;
  maxRows?: number;
  conversationId?: string;
  clarificationAnswer?: string;
}

export interface TextToSqlChartData {
  chartType: string;
  chart_type?: string;
  xField?: string;
  x_field?: string;
  yFields?: string[];
  y_fields?: string[];
  categories?: unknown[];
  series?: Array<Record<string, unknown>>;
  rows?: Array<Record<string, unknown>>;
}

export interface TextToSqlResultSummary {
  conclusion: string;
  dataDescription?: string;
  data_description?: string;
  keyFindings?: string[];
  key_findings?: string[];
  cautions?: string[];
  chartType?: string;
  chart_type?: string;
  chartTitle?: string;
  chart_title?: string;
  chartReason?: string;
  chart_reason?: string;
  chartData?: TextToSqlChartData;
  chart_data?: TextToSqlChartData;
  echartsOption?: Record<string, unknown>;
  echarts_option?: Record<string, unknown>;
  basis?: string[];
  sql?: string;
  rowCount?: number;
  row_count?: number;
}

export interface TextToSqlQueryTrace {
  originalQuestion?: string;
  original_question?: string;
  normalizedQuestion?: string;
  normalized_question?: string;
  businessDomain?: string;
  business_domain?: string;
  selectedTables?: string[];
  selected_tables?: string[];
  tableSelectionReason?: string;
  table_selection_reason?: string;
  generatedSql?: string;
  generated_sql?: string;
  sqlGenerationReason?: string;
  sql_generation_reason?: string;
  executedSql?: string;
  executed_sql?: string;
  rowCount?: number;
  row_count?: number;
  validation?: Record<string, unknown>;
  permission?: Record<string, unknown>;
  explain?: Record<string, unknown>;
  metricContext?: string;
  metric_context?: string;
  businessContext?: string;
  business_context?: string;
  tableDdlContext?: string;
  table_ddl_context?: string;
  clarificationAnswer?: string;
  clarification_answer?: string;
}

export interface TextToSqlAnalyzeResult {
  question: string;
  intent: string;
  action: string;
  businessDomain?: string;
  business_domain?: string;
  message: string;
  conversationId?: string;
  conversation_id?: string;
  needClarification?: boolean;
  need_clarification?: boolean;
  clarificationQuestion?: string;
  clarification_question?: string;
  clarificationReason?: string;
  clarification_reason?: string;
  clarificationAnswer?: string;
  clarification_answer?: string;
  errorMessage?: string;
  error_message?: string;
  answer?: string;
  sql?: string;
  executedSql?: string;
  executed_sql?: string;
  rows: Array<Record<string, unknown>>;
  chartType?: string;
  chart_type?: string;
  chartData?: TextToSqlChartData;
  chart_data?: TextToSqlChartData;
  echartsOption?: Record<string, unknown>;
  echarts_option?: Record<string, unknown>;
  resultSummaryDetail?: TextToSqlResultSummary;
  result_summary_detail?: TextToSqlResultSummary;
  queryTrace?: TextToSqlQueryTrace;
  query_trace?: TextToSqlQueryTrace;
  sqlExecutionDetail?: Record<string, unknown>;
  sql_execution_detail?: Record<string, unknown>;
  runRecordId?: number;
  run_record_id?: number;
}

export interface TextToSqlRunPageParams {
  keyword?: string;
  conversationId?: string;
  sourceType?: string;
  status?: string;
  feedbackResult?: string;
  pageNum: number;
  pageSize: number;
}

export interface TextToSqlFeedbackValues {
  feedbackResult: 'GOOD' | 'BAD';
  feedbackComment?: string;
}

export interface IdResult {
  id: number;
}

export interface TextToSqlRunItem {
  id: number;
  conversationId: string;
  sourceType: string;
  originalQuestion: string;
  status: string;
  errorMessage?: string;
  stateSnapshotJson?: string;
  stateHistoryJson?: string;
  durationMs?: number;
  feedbackResult?: 'GOOD' | 'BAD';
  feedbackComment?: string;
  feedbackAt?: string;
  createdBy?: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface TextToSqlEvalQuestionPageParams {
  keyword?: string;
  businessDomain?: string;
  evalTarget?: string;
  sampleCategory?: string;
  sourceType?: string;
  status?: string;
  pageNum: number;
  pageSize: number;
}

export interface TextToSqlEvalAssertionItem {
  id?: number;
  evalQuestionId?: number;
  actualKey?: string;
  operator?: string;
  expectedValue?: string;
  required?: boolean;
  weight?: number;
  failureType?: string;
  referenceAnswer?: string;
  keyPoints?: string;
  forbiddenPoints?: string;
  minScore?: number;
  sortOrder?: number;
  remark?: string;
}

export interface TextToSqlEvalQuestionValues {
  question: string;
  businessDomain?: string;
  evalTarget?: string;
  sampleCategory?: string;
  judgeNote?: string;
  remark?: string;
  status?: string;
  assertions?: TextToSqlEvalAssertionItem[];
}

export interface TextToSqlEvalQuestionItem extends TextToSqlEvalQuestionValues {
  id: number;
  sourceType: string;
  sourceRunId?: number;
  createdBy?: number;
  createdAt?: string;
  updatedAt?: string;
  assertionCount?: number;
}

export interface TextToSqlEvalTaskPageParams {
  keyword?: string;
  businessDomain?: string;
  evalTarget?: string;
  sampleCategory?: string;
  status?: string;
  pageNum: number;
  pageSize: number;
}

export interface TextToSqlEvalTaskValues {
  name: string;
  businessDomain?: string;
  evalTarget?: string;
  sampleCategory?: string;
  evalQuestionIds?: number[];
}

export interface TextToSqlEvalTaskItem extends TextToSqlEvalTaskValues {
  id: number;
  status: string;
  totalCount: number;
  passCount: number;
  failCount: number;
  interruptedCount: number;
  passRate: number;
  startedAt?: string;
  finishedAt?: string;
  durationMs?: number;
  errorMessage?: string;
  createdBy?: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface TextToSqlEvalTaskDetail {
  task: TextToSqlEvalTaskItem;
  resultCount: number;
}

export interface TextToSqlEvalResultPageParams {
  passed?: boolean;
  resultStatus?: string;
  pageNum: number;
  pageSize: number;
}

export interface TextToSqlEvalAssertionResultItem {
  id: number;
  evalResultId: number;
  evalAssertionId?: number;
  actualKey: string;
  operator: string;
  expectedValue?: string;
  actualValue?: string;
  required: boolean;
  passed: boolean;
  score: number;
  failureType?: string;
  reason?: string;
  createdAt?: string;
}

export interface TextToSqlEvalResultItem {
  id: number;
  evalTaskId: number;
  evalQuestionId: number;
  runRecordId?: number;
  question: string;
  resultStatus: string;
  passed: boolean;
  score: number;
  stateSnapshotJson?: string;
  stateHistoryJson?: string;
  errorMessage?: string;
  durationMs?: number;
  createdAt?: string;
  assertionResults: TextToSqlEvalAssertionResultItem[];
}

export interface PermissionItem {
  id: number;
  parentId: number;
  permissionCode: string;
  permissionName: string;
  permissionType: string;
  apiPath?: string;
  sortNum?: number;
  description?: string;
  status: ActiveStatus;
  createdAt?: string;
  updatedAt?: string;
}

export interface PermissionValues {
  parentId?: number;
  permissionCode: string;
  permissionName: string;
  permissionType: string;
  apiPath?: string;
  sortNum?: number;
  description?: string;
  status: ActiveStatus;
}

export interface PermissionPageParams {
  keyword?: string;
  parentId?: number;
  permissionType?: string;
  status?: ActiveStatus;
  pageNum: number;
  pageSize: number;
}

export interface SysConfigItem {
  id: number;
  k: string;
  v: string;
}

export interface SysConfigValues {
  k: string;
  v: string;
}

export interface SysConfigPageParams {
  keyword?: string;
  pageNum: number;
  pageSize: number;
}

export interface KnowledgeBaseItem {
  id: number;
  name: string;
  code: string;
  description?: string;
  documentCount: number;
  chunkCount: number;
  status: ActiveStatus;
  statusText?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface KnowledgeBaseCreateValues {
  name: string;
  code: string;
  description?: string;
}

export interface KnowledgeBaseUpdateValues {
  name: string;
  description?: string;
}

export interface KnowledgeBasePageParams {
  keyword?: string;
  status?: ActiveStatus;
  pageNum: number;
  pageSize: number;
}

export type PromptTemplateType = 'SYSTEM' | 'USER';

export type PromptTemplateScene =
  | 'CHAT'
  | 'RAG'
  | 'SUMMARY'
  | 'JUDGE'
  | 'STRUCTURED_EXTRACT'
  | 'CONTENT_TOPIC_DISCOVERY'
  | 'CONTENT_RESEARCH'
  | 'CONTENT_WRITING'
  | 'CONTENT_MATERIAL_MATCHING';

export interface PromptTemplateItem {
  id: number;
  code: string;
  name: string;
  agentCode: string;
  promptType: PromptTemplateType;
  sceneCode?: PromptTemplateScene;
  status: ActiveStatus;
  statusText?: string;
  activeVersionId?: number;
  activeVersionNo?: number;
  description?: string;
  createTime?: string;
  updateTime?: string;
}

export interface PromptTemplateCreateValues {
  name: string;
  code: string;
  agentCode: string;
  promptType: PromptTemplateType;
  sceneCode?: PromptTemplateScene;
  status?: ActiveStatus;
  description?: string;
}

export interface PromptTemplateUpdateValues {
  name: string;
  agentCode: string;
  promptType: PromptTemplateType;
  sceneCode?: PromptTemplateScene;
  description?: string;
}

export interface PromptTemplatePageParams {
  keyword?: string;
  agentCode?: string;
  status?: ActiveStatus;
  pageNum: number;
  pageSize: number;
}

export interface PromptTemplateVersionItem {
  id: number;
  templateId: number;
  versionNo: number;
  content: string;
  variables?: string;
  changeNote?: string;
  createBy?: number;
  createByName?: string;
  current: boolean;
  status: 'CURRENT' | 'UNPUBLISHED' | 'HISTORY';
  statusText?: string;
  createTime?: string;
  updateTime?: string;
}

export interface PromptTemplateVersionCreateValues {
  content: string;
  variables?: string;
  changeNote?: string;
}

export interface PromptTestValues {
  systemTemplateId: number;
  systemVersionId: number;
  userTemplateId: number;
  userVersionId: number;
  variables: Record<string, string>;
  model: string;
}

export type KnowledgeRecallMode = 'SEMANTIC' | 'KEYWORD' | 'HYBRID';

export interface KnowledgeRecallValues {
  query: string;
  mode: KnowledgeRecallMode;
  topK: number;
}

export interface KnowledgeRecallItem {
  rank: number;
  score: number;
  documentCode: string;
  documentVersion: number;
  chunkIndex: number;
  content: string;
  contentPreview: string;
  wordCount: number;
}

export interface KnowledgeRecallResult {
  query: string;
  mode: KnowledgeRecallMode;
  topK: number;
  records: KnowledgeRecallItem[];
}

export interface KnowledgeQaValues {
  question: string;
  recallMode: KnowledgeRecallMode;
  topK: number;
}

export interface KnowledgeQaCitation {
  rank: number;
  score: number;
  documentCode: string;
  documentVersion: number;
  chunkIndex: number;
  content: string;
  contentPreview: string;
  wordCount: number;
}

export interface KnowledgeQaDone {
  model?: string;
  finishReason?: string;
  truncated?: boolean;
  usage?: unknown;
}

export type KnowledgeDocumentStatus = 'INDEXING' | 'READY' | 'FAILED';
export type KnowledgeChunkStrategy = 'MARKDOWN' | 'NONE' | 'BY_ITEM';

export interface KnowledgeDocumentItem {
  id: number;
  knowledgeBaseId: number;
  knowledgeBaseCode: string;
  name: string;
  code: string;
  objectKey: string;
  fileType: string;
  chunkStrategy: KnowledgeChunkStrategy;
  fileSize?: number;
  fileSizeText?: string;
  status: KnowledgeDocumentStatus;
  statusText?: string;
  chunkCount: number;
  version: number;
  lastErrorMessage?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface KnowledgeDocumentPageParams {
  keyword?: string;
  status?: KnowledgeDocumentStatus;
  pageNum: number;
  pageSize: number;
}

export interface KnowledgeDocumentCreateValues {
  name: string;
  code: string;
  objectKey: string;
  chunkStrategy?: KnowledgeChunkStrategy;
  fileSize?: number;
}

export interface KnowledgeDocumentPresignValues {
  fileName: string;
}

export interface KnowledgeDocumentCreateResult {
  id: number;
  status: KnowledgeDocumentStatus;
}

export interface KnowledgeDocumentChunkItem {
  chunkIndex: number;
  contentPreview: string;
  wordCount: number;
  charCount: number;
}

export interface KnowledgeDocumentChunkDetail {
  chunkIndex: number;
  content: string;
  wordCount: number;
  charCount: number;
}

export interface KnowledgeDocumentChunkPageParams {
  pageNum: number;
  pageSize: number;
}

export interface CampusItem {
  id: number;
  campusLocation: string;
  managerName: string;
  managerPhone: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface CampusValues {
  campusLocation: string;
  managerName: string;
  managerPhone: string;
}

export interface CampusPageParams {
  keyword?: string;
  pageNum: number;
  pageSize: number;
}

export interface CourseItem {
  id: number;
  courseName: string;
  courseDays: number;
  teachingMode: ProductTeachingMode;
  materialPath: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface CourseValues {
  courseName: string;
  courseDays: number;
  teachingMode: ProductTeachingMode;
  materialPath: string;
}

export interface CoursePageParams {
  keyword?: string;
  pageNum: number;
  pageSize: number;
}

export interface CourseDetailItem {
  id: number;
  courseId: number;
  stageName: string;
  dayNumber: number;
  classContent: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface CourseDetailValues {
  stageName: string;
  dayNumber: number;
  classContent: string;
}

export interface CourseHomeworkTemplateItem {
  id: number;
  courseId: number;
  teachingMode: ProductTeachingMode;
  stageName?: string;
  dayNumber?: number;
  contentObjectKey: string;
  contentFileName: string;
  status: ActiveStatus;
  remark?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface CourseHomeworkTemplateValues {
  stageName?: string;
  dayNumber?: number;
  contentObjectKey: string;
  contentFileName: string;
  status: ActiveStatus;
  remark?: string;
}

export interface ProductItem {
  id: number;
  courseContent: string;
  teachingMode: ProductTeachingMode;
  price: number;
  createdAt?: string;
  updatedAt?: string;
}

export type ProductTeachingMode = 'ONLINE' | 'OFFLINE';

export interface ProductValues {
  courseContent: string;
  teachingMode: ProductTeachingMode;
  price: number;
}

export interface ProductPageParams {
  keyword?: string;
  pageNum: number;
  pageSize: number;
}

export type ExamQuestionType = 'SINGLE' | 'MULTIPLE' | 'JUDGE' | 'FILL' | 'SHORT' | 'PROGRAMMING';

export type ExamQuestionDifficulty = 'EASY' | 'NORMAL' | 'HARD';

export type ExamQuestionStatus = 'ENABLED' | 'DISABLED';

export interface ExamQuestionOptionItem {
  id?: number;
  questionId?: number;
  optionKey: string;
  optionContent: string;
}

export interface ExamQuestionItem {
  id: number;
  questionType: ExamQuestionType;
  questionContent: string;
  answerContent?: string;
  analysisContent?: string;
  difficulty: ExamQuestionDifficulty;
  courseIds?: number[];
  courseNames?: string;
  courseStageKeys?: string[];
  courseStageNames?: string;
  status: ExamQuestionStatus;
  options?: ExamQuestionOptionItem[];
  createdAt?: string;
  updatedAt?: string;
}

export interface ExamQuestionValues {
  questionType: ExamQuestionType;
  questionContent: string;
  answerContent: string | string[];
  analysisContent?: string;
  difficulty: ExamQuestionDifficulty;
  courseIds?: number[];
  courseStages?: ExamQuestionCourseStageValues[];
  status: ExamQuestionStatus;
  options?: ExamQuestionOptionItem[];
}

export interface ExamQuestionCourseStageValues {
  courseId: number;
  stageName: string;
}

export interface ExamQuestionPageParams {
  questionType?: ExamQuestionType;
  courseId?: number;
  stageName?: string;
  difficulty?: ExamQuestionDifficulty;
  status?: ExamQuestionStatus;
  keyword?: string;
  pageNum: number;
  pageSize: number;
}

export interface ExamPaperQuestionValue {
  questionId: number;
  questionScore: number;
}

export interface ExamPaperValues {
  paperName: string;
  courseId: number;
  stageName?: string;
  totalScore: number;
  questions: ExamPaperQuestionValue[];
}

export interface ExamPaperItem {
  id: number;
  paperName: string;
  courseId: number;
  courseName?: string;
  stageName?: string;
  totalScore: number;
  questionCount?: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface ExamPaperQuestionItem {
  id?: number;
  paperId?: number;
  questionId: number;
  questionContent?: string;
  questionType?: ExamQuestionType;
  difficulty?: ExamQuestionDifficulty;
  questionScore: number;
}

export interface ExamPaperDetailItem extends ExamPaperItem {
  questions: ExamPaperQuestionItem[];
}

export interface ExamPaperPageParams {
  courseId?: number;
  stageName?: string;
  paperName?: string;
  pageNum: number;
  pageSize: number;
}

export interface ExamItem {
  id: number;
  paperId: number;
  paperName?: string;
  classId: number;
  classPeriod?: string;
  startTime: string;
  endTime: string;
  durationMinutes: number;
  invigilatorUserId: number;
  invigilatorName?: string;
  answerVisible: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface ExamValues {
  paperId: number;
  classId: number;
  startTime: string;
  endTime: string;
  durationMinutes: number;
  invigilatorUserId: number;
}

export interface ExamPageParams {
  paperId?: number;
  classId?: number;
  invigilatorUserId?: number;
  pageNum: number;
  pageSize: number;
}

export interface ExamSubmissionPageParams {
  pageNum: number;
  pageSize: number;
}

export interface ExamSubmissionItem {
  recordId?: number;
  examId: number;
  studentId: number;
  studentName?: string;
  studentPhone?: string;
  recordStatus: string;
  recordStatusText?: string;
  gradingStatus?: 'PENDING' | 'GRADING' | 'COMPLETED';
  score?: number;
  startTime?: string;
  deadlineTime?: string;
  submitTime?: string;
}

export interface ExamSubmissionOptionItem {
  id: number;
  questionId: number;
  optionKey: string;
  optionContent: string;
}

export interface ExamSubmissionQuestionItem {
  answerId?: number;
  questionId: number;
  questionContent?: string;
  questionType?: ExamQuestionType;
  questionScore: number;
  answerContent?: string;
  correctAnswer?: string;
  analysisContent?: string;
  correct?: boolean;
  score?: number;
  options: ExamSubmissionOptionItem[];
}

export interface ExamSubmissionDetailItem {
  recordId: number;
  examId: number;
  paperId: number;
  paperName: string;
  classPeriod?: string;
  stageName?: string;
  studentId: number;
  studentName?: string;
  studentPhone?: string;
  totalScore: number;
  score?: number;
  recordStatus: string;
  gradingStatus?: 'PENDING' | 'GRADING' | 'COMPLETED';
  startTime?: string;
  deadlineTime?: string;
  submitTime?: string;
  questions: ExamSubmissionQuestionItem[];
}

export interface ExamSubmissionGradeValues {
  answers: Array<{
    answerId: number;
    score: number;
  }>;
}

export type PrepayOrderStatus = 'PENDING_PAYMENT' | 'PAID' | 'CANCELED';

export interface PrepayOrderItem {
  id: number;
  orderNo: string;
  studentName: string;
  studentPhone: string;
  productId: number;
  productAmount: number;
  discountAmount: number;
  orderStatus: PrepayOrderStatus;
  createdAt?: string;
  updatedAt?: string;
}

export interface PrepayOrderValues {
  studentName: string;
  studentPhone: string;
  productId: number;
  productAmount: number;
  discountAmount: number;
  orderStatus: PrepayOrderStatus;
}

export interface PrepayOrderPageParams {
  keyword?: string;
  orderStatus?: PrepayOrderStatus;
  pageNum: number;
  pageSize: number;
}

export type PaymentOrderStatus = 'INIT' | 'FAIL' | 'PROCESSING' | 'SUCCESS' | 'TIMEOUT';

export interface PaymentOrderItem {
  id: number;
  orderNo: string;
  studentPhone: string;
  studentName: string;
  productId: string;
  productContent?: string;
  orderAmount: number;
  refundedAmount?: number;
  prepayOrderNo: string;
  status: PaymentOrderStatus;
  uniqueOrderNo?: string;
  paySuccessTime?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface PaymentOrderPageParams {
  orderNo?: string;
  studentName?: string;
  studentPhone?: string;
  prepayOrderNo?: string;
  status?: PaymentOrderStatus;
  pageNum: number;
  pageSize: number;
}

export interface RefundOrderCreateResult {
  refundOrderNo: string;
}

export interface RefundOrderApplyValues {
  paymentOrderNo: string;
  refundAmount: number;
  reason?: string;
}

export interface RefundOrderApplyResult {
  refundOrderNo: string;
  paymentOrderNo: string;
  refundAmount: number;
  status: string;
  uniqueRefundNo?: string;
}

export type RefundOrderStatus = 'INIT' | 'PROCESSING' | 'SUCCESS' | 'FAIL' | 'CLOSED';

export interface RefundOrderItem {
  id: number;
  refundOrderNo: string;
  paymentOrderNo: string;
  paymentAmount: number;
  refundAmount?: number;
  status: RefundOrderStatus;
  reason?: string;
  uniqueRefundNo?: string;
  failReason?: string;
  refundSuccessTime?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface RefundOrderPageParams {
  refundOrderNo?: string;
  paymentOrderNo?: string;
  status?: RefundOrderStatus;
  pageNum: number;
  pageSize: number;
}

export interface ClazzItem {
  id: number;
  classPeriod: string;
  headTeacherId: number;
  headTeacherName?: string;
  campusId: number;
  campusName?: string;
  courseId: number;
  courseName?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface ClazzValues {
  classPeriod: string;
  headTeacherId: number;
  campusId: number;
  courseId: number;
}

export interface ClazzPageParams {
  keyword?: string;
  headTeacherId?: number;
  campusId?: number;
  courseId?: number;
  pageNum: number;
  pageSize: number;
}

export interface HomeworkItem {
  id: number;
  title: string;
  contentObjectKey: string;
  contentFileName: string;
  answerObjectKey?: string;
  answerFileName?: string;
  answerStudentVisible: boolean;
  classId: number;
  classPeriod?: string;
  homeworkDate: string;
  classContent: string;
  startTime?: string;
  deadline?: string;
  remark?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface HomeworkPageParams {
  title?: string;
  classId?: number;
  homeworkDate?: string;
  pageNum: number;
  pageSize: number;
}

export interface HomeworkValues {
  title: string;
  contentObjectKey: string;
  contentFileName: string;
  classId: number;
  homeworkDate: string;
  classContent: string;
  startTime: string;
  deadline: string;
  remark?: string;
}

export interface HomeworkAnswerValues {
  answerObjectKey: string;
  answerFileName: string;
  answerStudentVisible: boolean;
}

export interface HomeworkSubmissionItem {
  id: number;
  homeworkId: number;
  studentId: number;
  studentName?: string;
  studentPhone?: string;
  contentObjectKey: string;
  contentFileName: string;
  submitTime: string;
  lateSubmitted: boolean;
  teacherRemark?: string;
  score?: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface HomeworkSubmissionPageParams {
  pageNum: number;
  pageSize: number;
}

export interface HomeworkSubmissionGradeValues {
  score: number;
  teacherRemark?: string;
}

export interface HomeworkUploadSignResult {
  uploadUrl: string;
  contentObjectKey: string;
  contentFileName: string;
  expires: number;
  headers?: Record<string, string>;
}

export interface HomeworkContentResult {
  contentFileName: string;
  previewUrl: string;
  expires: number;
}

export interface UploadPresignResult {
  uploadUrl: string;
  objectKey: string;
  expires: number;
  headers?: Record<string, string>;
}

export interface DownloadPresignResult {
  downloadUrl: string;
  objectKey: string;
  expires: number;
}

export type MediaVideoUploadStatus = 'UPLOADING' | 'UPLOADED' | 'UPLOAD_FAILED';
export type MediaProcessStatus = 'PENDING' | 'PROCESSING' | 'SUCCESS' | 'FAILED';

export interface MediaVideoItem {
  id: number;
  title: string;
  description?: string;
  originalFileName: string;
  objectKey: string;
  fileType: string;
  contentType?: string;
  fileSize: number;
  durationMs?: number;
  width?: number;
  height?: number;
  /** 原始视频上传状态。 */
  uploadStatus: MediaVideoUploadStatus;
  /** 最新离线处理任务状态；为空表示尚未开始处理。 */
  processStatus?: MediaProcessStatus;
  failureStep?: string;
  failureMessage?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface MediaVideoPageParams {
  keyword?: string;
  processStatus?: MediaProcessStatus | 'NOT_STARTED';
  pageNum: number;
  pageSize: number;
}

export interface MediaVideoPresignValues {
  fileName: string;
  fileSize: number;
  contentType?: string;
}

export interface MediaVideoCreateValues {
  title: string;
  description?: string;
  originalFileName: string;
  objectKey: string;
  fileSize: number;
  contentType?: string;
  durationMs?: number;
  width?: number;
  height?: number;
}

export interface MediaVideoCreateResult {
  id: number;
  uploadStatus: MediaVideoUploadStatus;
}

export interface MediaProcessTaskCreateResult {
  taskId: number;
  status: 'PENDING' | 'PROCESSING' | 'SUCCESS' | 'FAILED';
}

export interface MediaAudioPreviewResult {
  id: number;
  videoId: number;
  fileFormat: string;
  fileSize: number;
  durationMs?: number;
  sampleRate?: number;
  channels?: number;
  previewUrl: string;
}

export interface MediaTranscriptResult {
  id: number;
  videoId: number;
  language?: string;
  fullText?: string;
  durationMs?: number;
  updatedAt?: string;
}

export interface MediaTranscriptUtteranceItem {
  segmentNo: number;
  startTime: number;
  endTime: number;
  text: string;
  speaker?: string;
}

export interface MediaVideoClipItem {
  id: number;
  videoId: number;
  taskId: number;
  segmentNo: number;
  startMs: number;
  endMs: number;
  durationMs: number;
  title: string;
  summary: string;
  coreViewpoint: string;
  clipType: 'Q_AND_A' | 'VIEWPOINT' | 'KNOWLEDGE' | 'STORY' | 'CASE' | 'TUTORIAL';
  valueReason: string;
  tags: string[];
  speakers: string[];
  transcriptText: string;
  objectKey?: string;
  fileSize?: number;
  sourceVideoTitle?: string;
  sourceVideoFileName?: string;
  createdAt?: string;
}

export interface MediaMaterialPageParams {
  keyword?: string;
  clipType?: MediaVideoClipItem['clipType'];
  speaker?: string;
  pageNum: number;
  pageSize: number;
}

/** 抖音热点视频及其最新点赞快照。 */
export interface DouyinVideoItem {
  id: number;
  douyinVideoId: string;
  videoUrl: string;
  title?: string;
  description?: string;
  authorSecUserId?: string;
  authorName?: string;
  authorUrl?: string;
  coverUrl?: string;
  durationMs?: number;
  publishTime?: string;
  matchedKeywords: string[];
  firstSeenAt?: string;
  lastSeenAt?: string;
  likeCount?: number;
  likeIncrease?: number;
  metricsCollectedAt?: string;
}

/** 热点发现分页筛选条件。 */
export interface DouyinVideoPageParams {
  keyword?: string;
  pageNum: number;
  pageSize: number;
}

/** 一轮抖音热点采集的执行摘要。 */
export interface DouyinCollectRunResult {
  collectWindow: string;
  targetCount: number;
  returnedVideoCount: number;
  newVideoCount: number;
  updatedVideoCount: number;
  snapshotCount: number;
  errors: string[];
}

/** 启动内容生成工作流时的配置。 */
export interface ContentGenerationStartValues {
  candidateCount: number;
  sourceMode: 'COLLECTED_HOTSPOTS' | 'REALTIME_KEYWORD';
  keyword?: string;
}

/** 候选选题引用的一条真实热点视频。 */
export interface ContentTopicSourceVideo {
  video_id: string;
  title?: string;
  video_url?: string;
  like_count?: number;
  like_increase?: number;
}

/** 内容生成工作流当前产出的候选选题。 */
export interface ContentTopicCandidate {
  topic_id: string;
  title: string;
  core_event: string;
  creation_angle: string;
  target_audience: string;
  reason: string;
  source_videos: ContentTopicSourceVideo[];
}

/** 资料包中的已核验事实。 */
export interface ContentResearchFact {
  statement: string;
  source_ids: string[];
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
}

/** 资料检索 Agent 实际读取成功的来源。 */
export interface ContentResearchSource {
  source_id: string;
  title: string;
  url: string;
  site: string;
  published_at?: string | null;
  source_type: 'OFFICIAL' | 'GITHUB' | 'MEDIA' | 'OTHER';
}

/** 供后续文案 Agent 使用的结构化资料包。 */
export interface ContentResearchBrief {
  topic_id: string;
  event_summary: string;
  verified_facts: ContentResearchFact[];
  key_points: string[];
  teaching_angles: string[];
  controversies: string[];
  uncertain_claims: string[];
  sources: ContentResearchSource[];
}

/** 文字内容创作 Agent 生成的文章。 */
export interface ContentArticle {
  title: string;
  body: string;
  tags: string[];
  /** 仅供后端追溯和后续审核，内容创作页面不展示。 */
  used_source_ids: string[];
}

export interface ContentCreationValues {
  feedback?: string;
}

/** 素材匹配子图为一处文章片段选择的视频，或待生成图片方案。 */
export interface ContentMaterialMatch {
  need_id: string;
  article_excerpt: string;
  asset_type: 'VIDEO_CLIP' | 'GENERATED_IMAGE' | 'IMAGE_PENDING';
  material_id?: number | null;
  video_id?: number | null;
  clip_type?: string | null;
  duration_ms?: number | null;
  rerank_score?: number | null;
  image_prompt?: string | null;
  provider_task_id?: string | null;
  image_object_key?: string | null;
  image_file_size?: number | null;
  image_width?: number | null;
  image_height?: number | null;
  image_error?: string | null;
  match_reason: string;
}

export type ContentMaterialTaskStatus =
  | 'PENDING'
  | 'PROCESSING'
  | 'SUCCESS'
  | 'PARTIAL_FAILED'
  | 'FAILED';

export interface ContentMaterialTaskCreateResult {
  taskId: number;
  status: ContentMaterialTaskStatus;
}

/** Java 持久化后返回给页面的素材结果（字段使用 Java JSON 命名）。 */
export interface ContentMaterialTaskItem {
  needId: string;
  articleExcerpt: string;
  assetType: 'VIDEO_CLIP' | 'GENERATED_IMAGE' | 'IMAGE_PENDING';
  materialId?: number | null;
  videoId?: number | null;
  clipType?: string | null;
  durationMs?: number | null;
  rerankScore?: number | null;
  renderEngine?: 'PROGRAMMATIC' | 'QWEN_IMAGE' | null;
  visualType?: 'FLOW_DIAGRAM' | 'ARCHITECTURE_DIAGRAM' | 'COMPARISON' | 'CONCEPT_MAP' | 'TIMELINE' | 'SCENE_ILLUSTRATION' | null;
  visualSpec?: Record<string, unknown> | null;
  imagePrompt?: string | null;
  matchReason: string;
  providerTaskId?: string | null;
  imageObjectKey?: string | null;
  imageFileSize?: number | null;
  imageWidth?: number | null;
  imageHeight?: number | null;
  imageError?: string | null;
  imageUrl?: string | null;
  visualReviewScore?: number | null;
  visualReviewSummary?: string | null;
  generationAttempt?: number | null;
  regenerateFeedback?: string | null;
}

export interface ContentMaterialTaskResult {
  taskId: number;
  conversationId: string;
  contentRevision: number;
  status: ContentMaterialTaskStatus;
  errorMessage?: string | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  reviewTaskId?: number | null;
  reviewStatus?: ContentReviewTaskStatus | null;
  materialMatches: ContentMaterialTaskItem[];
}

export type ContentReviewTaskStatus =
  /** 已创建，等待后台线程抢占。 */
  | 'PENDING'
  /** Python 正在执行组装、规则检查或模型审核。 */
  | 'PROCESSING'
  /** 自动审核通过，但仍需人工确认。 */
  | 'AWAITING_APPROVAL'
  /** 内容本身未通过；可修改重做，也可由人工明确批准。 */
  | 'REJECTED'
  /** 人工已经确认通过。 */
  | 'APPROVED'
  /** 调用异常或超时，可以原地重试审核。 */
  | 'FAILED';

export interface ContentReviewIssue {
  /** 稳定问题编码，便于后端统计同类问题。 */
  issueCode: string;
  category: 'FACTUAL' | 'INFERENCE' | 'TITLE' | 'STYLE' | 'STRUCTURE' | 'MATERIAL' | 'COMPLIANCE';
  severity: 'ERROR' | 'WARNING';
  location: string;
  description: string;
  suggestion: string;
  /** RULE 来自代码硬规则，MODEL 来自审核 Agent。 */
  source: 'RULE' | 'MODEL';
}

export interface ContentReviewTaskResult {
  taskId: number;
  conversationId: string;
  contentRevision: number;
  materialTaskId: number;
  status: ContentReviewTaskStatus;
  score?: number | null;
  summary?: string | null;
  previewFormat?: 'VIDEO' | 'IMAGE_CAROUSEL' | null;
  previewPlan?: ContentPublishPreviewPlan | null;
  previewTaskId?: number | null;
  previewStatus?: ContentPreviewTaskStatus | null;
  errorMessage?: string | null;
  approvedBy?: number | null;
  approvedAt?: string | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  issues: ContentReviewIssue[];
}

export interface ContentPublishPreviewItem {
  need_id: string;
  headline: string;
  body: string;
  duration_ms?: number | null;
}

export interface ContentPublishPreviewPlan {
  format: 'VIDEO' | 'IMAGE_CAROUSEL';
  cover_title: string;
  publish_caption: string;
  tags: string[];
  items: ContentPublishPreviewItem[];
}

export type ContentPreviewTaskStatus = 'PENDING' | 'PROCESSING' | 'SUCCESS' | 'FAILED';

export interface ContentPreviewItemResult {
  sequenceNo: number;
  needId: string;
  objectKey: string;
  imageUrl: string;
  fileSize: number;
  width: number;
  height: number;
}

export interface ContentPreviewTaskResult {
  taskId: number;
  reviewTaskId: number;
  conversationId: string;
  contentRevision: number;
  format: 'VIDEO' | 'IMAGE_CAROUSEL';
  status: ContentPreviewTaskStatus;
  previewPlan: ContentPublishPreviewPlan;
  coverObjectKey?: string | null;
  coverUrl?: string | null;
  videoObjectKey?: string | null;
  videoUrl?: string | null;
  durationMs?: number | null;
  errorMessage?: string | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  items: ContentPreviewItemResult[];
}

/** 内容生成工作流启动或恢复后的状态。 */
export interface ContentGenerationWorkflowResult {
  conversation_id: string;
  status:
    | 'WAITING_SELECTION'
    | 'COMPLETED'
    | 'RESEARCH_COMPLETED'
    | 'RESEARCH_FAILED'
    | 'CONTENT_COMPLETED'
    | 'CONTENT_FAILED'
    | 'MATERIAL_MATCHING_COMPLETED'
    | 'MATERIAL_MATCHING_PARTIAL_FAILED'
    | 'MATERIAL_MATCHING_FAILED'
    | 'REVIEW_AWAITING_APPROVAL'
    | 'REVIEW_REJECTED'
    | 'REVIEW_FAILED';
  generation_round: number;
  candidate_topics: ContentTopicCandidate[];
  selected_topic?: ContentTopicCandidate | null;
  research_brief?: ContentResearchBrief | null;
  content_article?: ContentArticle | null;
  content_revision: number;
  material_matches: ContentMaterialMatch[];
  review_status?: string;
  message: string;
}

/** 人工确认节点的恢复参数。 */
export interface ContentGenerationResumeValues {
  action: 'SELECT' | 'REGENERATE';
  topicId?: string;
  feedback?: string;
}

export interface HomeworkPrepareResult {
  classId: number;
  classPeriod?: string;
  homeworkDate: string;
  classContent: string;
  defaultTitle: string;
  startTime: string;
  deadline: string;
}

export type ClassScheduleType = 'CLASS' | 'SELF_STUDY' | 'HOLIDAY' | 'REST';

export interface ClassScheduleItem {
  id: number;
  classId: number;
  teacherId?: number;
  scheduleDate: string;
  courseDetailId?: number;
  courseContent: string;
  classType: ClassScheduleType;
}

export interface ClassScheduleDateDetail {
  id: number;
  classId: number;
  teacherId?: number;
  teacherName?: string;
  scheduleDate: string;
  courseDetailId?: number;
  stageName?: string;
  dayNumber?: number;
  courseContent: string;
  classType: ClassScheduleType;
}

export interface ClassStageInfoItem {
  stageName: string;
  stageNumber: number;
  freeTeacherName: Record<string, string>;
}

export interface ClassScheduleTeacherAssignValues {
  stages: Array<{
    stageName: string;
    teacherId: number;
  }>;
}

export interface ClassScheduleTeacherAssignResult {
  classId: number;
  updateCount: number;
}

export interface ClassScheduleAddCourseValues {
  courseContent: string;
  scheduleDate: string;
  teacherId: number;
}

export interface TeacherScheduleQuery {
  startTime: string;
  endTime: string;
}

export interface TeacherScheduleDetail {
  teacheringDate: string;
  classId: number;
  classPeriod: string;
}

export interface TeacherScheduleItem {
  teacherId: number;
  teacherName: string;
  teacherDetailList: TeacherScheduleDetail[];
}

export interface ClassScheduleGenerateValues {
  classId: number;
  firstClassDate: string;
}

export interface ClassScheduleGenerateResult {
  classId: number;
  scheduleCount: number;
}

export type ClassDutyType = 'EVENING_STUDY_CLASS' | 'EVENING_STUDY_CAMPUS' | 'SELF_STUDY_CLASS';

export interface ClassDutyItem {
  id: number;
  classId?: number;
  classPeriod?: string;
  campusId: number;
  campusName?: string;
  teacherId: number;
  teacherName?: string;
  dutyDate: string;
  dutyType: ClassDutyType;
  dutyTypeDesc?: string;
  startTime: string;
  endTime: string;
  remark?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface ClassDutyValues {
  classId?: number;
  campusId?: number;
  teacherId: number;
  dutyDate: string;
  dutyType: ClassDutyType;
  remark?: string;
}

export interface ClassDutyPageParams {
  classId?: number;
  campusId?: number;
  teacherId?: number;
  dutyType?: ClassDutyType;
  startDate?: string;
  endDate?: string;
  pageNum: number;
  pageSize: number;
}

export interface ClassDutyDateClassItem {
  scheduleId: number;
  classId: number;
  classPeriod?: string;
  campusId: number;
  campusName?: string;
  classType: ClassScheduleType;
  classTypeDesc?: string;
  courseContent?: string;
  dutyType: ClassDutyType;
  dutyTypeDesc?: string;
  startTime: string;
  endTime: string;
  teacherId?: number;
  teacherName?: string;
}

export interface ClassDutyDateCampusItem {
  campusId: number;
  campusName?: string;
  dutyType: ClassDutyType;
  dutyTypeDesc?: string;
  startTime: string;
  endTime: string;
  teacherId?: number;
  teacherName?: string;
}

export interface ClassDutyDateResult {
  dutyDate: string;
  classDutyList: ClassDutyDateClassItem[];
  campusDutyList: ClassDutyDateCampusItem[];
}

export interface ClassDutyDateSaveValues {
  dutyDate: string;
  classDutyList: Array<{
    classId: number;
    teacherId: number;
    dutyType: ClassDutyType;
  }>;
  campusDutyList: Array<{
    campusId: number;
    teacherId: number;
    dutyType: ClassDutyType;
  }>;
}
