import http, { streamPost, type StreamHandlers } from './http';
import type {
  CampusItem,
  CampusPageParams,
  CampusValues,
  ClazzItem,
  ClazzPageParams,
  ClassScheduleGenerateResult,
  ClassScheduleGenerateValues,
  ClassScheduleDateDetail,
  ClassScheduleItem,
  ClassScheduleAddCourseValues,
  ClassStageInfoItem,
  ClassScheduleTeacherAssignResult,
  ClassScheduleTeacherAssignValues,
  ClassDutyItem,
  ClassDutyDateResult,
  ClassDutyDateSaveValues,
  ClassDutyPageParams,
  ClassDutyValues,
  TeacherScheduleItem,
  TeacherScheduleQuery,
  IdResult,
  TextToSqlAnalyzeResult,
  TextToSqlAnalyzeValues,
  TextToSqlEvalQuestionItem,
  TextToSqlEvalQuestionPageParams,
  TextToSqlEvalQuestionValues,
  TextToSqlEvalResultItem,
  TextToSqlEvalResultPageParams,
  TextToSqlEvalTaskDetail,
  TextToSqlEvalTaskItem,
  TextToSqlEvalTaskPageParams,
  TextToSqlEvalTaskValues,
  TextToSqlFeedbackValues,
  TextToSqlRunItem,
  TextToSqlRunPageParams,
  TextToSqlRolePermissionDetail,
  TextToSqlRolePermissionSaveValues,
  TextToSqlSchemaDomain,
  ClazzValues,
  CourseItem,
  CourseHomeworkTemplateItem,
  CourseHomeworkTemplateValues,
  CourseDetailItem,
  CourseDetailValues,
  CoursePageParams,
  CourseValues,
  ExamQuestionItem,
  ExamQuestionPageParams,
  ExamQuestionStatus,
  ExamQuestionValues,
  ExamPaperDetailItem,
  ExamPaperItem,
  ExamPaperPageParams,
  ExamPaperValues,
  ExamItem,
  ExamPageParams,
  ExamSubmissionDetailItem,
  ExamSubmissionGradeValues,
  ExamSubmissionItem,
  ExamSubmissionPageParams,
  ExamValues,
  HomeworkItem,
  HomeworkAnswerValues,
  HomeworkPageParams,
  HomeworkPrepareResult,
  HomeworkSubmissionItem,
  HomeworkSubmissionGradeValues,
  HomeworkSubmissionPageParams,
  HomeworkValues,
  KnowledgeBaseCreateValues,
  KnowledgeDocumentChunkDetail,
  KnowledgeDocumentChunkItem,
  KnowledgeDocumentChunkPageParams,
  KnowledgeDocumentCreateResult,
  KnowledgeDocumentCreateValues,
  KnowledgeDocumentItem,
  KnowledgeDocumentPageParams,
  KnowledgeDocumentPresignValues,
  KnowledgeBaseItem,
  KnowledgeBasePageParams,
  KnowledgeBaseUpdateValues,
  KnowledgeRecallResult,
  KnowledgeRecallValues,
  KnowledgeQaValues,
  MediaAudioPreviewResult,
  MediaTranscriptResult,
  MediaTranscriptUtteranceItem,
  MediaProcessTaskCreateResult,
  MediaVideoCreateResult,
  MediaVideoCreateValues,
  MediaVideoItem,
  MediaVideoClipItem,
  MediaMaterialPageParams,
  MediaVideoPageParams,
  MediaVideoPresignValues,
  DouyinCollectRunResult,
  DouyinVideoItem,
  DouyinVideoPageParams,
  ContentCreationValues,
  ContentGenerationResumeValues,
  ContentGenerationStartValues,
  ContentGenerationWorkflowResult,
  ContentMaterialTaskCreateResult,
  ContentMaterialTaskResult,
  ContentReviewTaskResult,
  ContentPreviewTaskResult,
  LoginResult,
  LoginValues,
  PageResult,
  PaymentOrderItem,
  PaymentOrderPageParams,
  PermissionItem,
  PermissionPageParams,
  PermissionValues,
  PromptTemplateCreateValues,
  PromptTemplateItem,
  PromptTemplatePageParams,
  PromptTemplateType,
  PromptTestValues,
  PromptTemplateUpdateValues,
  PromptTemplateVersionCreateValues,
  PromptTemplateVersionItem,
  PrepayOrderItem,
  PrepayOrderPageParams,
  PrepayOrderValues,
  ProductItem,
  ProductPageParams,
  ProductValues,
  RefundOrderApplyResult,
  RefundOrderApplyValues,
  RefundOrderCreateResult,
  RefundOrderItem,
  RefundOrderPageParams,
  RoleItem,
  RolePageParams,
  RoleValues,
  StudentItem,
  StudentFollowupRecordCancelValues,
  StudentFollowupRecordCompleteValues,
  StudentFollowupRecordItem,
  StudentFollowupRecordPageParams,
  StudentFollowupRecordStats,
  StudentFollowupTagItem,
  StudentFollowupTagPageParams,
  StudentFollowupTagValues,
  StudentPageParams,
  StudentSopAssignValues,
  StudentSopCompleteValues,
  StudentSopItem,
  StudentSopPageParams,
  StudentLearningCalendarItem,
  StudentLearningPlanCreateValues,
  StudentLearningPlanDetail,
  StudentLearningPlanItem,
  StudentLearningPlanPageParams,
  StudentTagUpdateValues,
  SysConfigItem,
  SysConfigPageParams,
  SysConfigValues,
  DownloadPresignResult,
  UploadPresignResult,
  UserCreateValues,
  UserItem,
  UserPageParams,
  UserUpdateValues,
} from '../types/system';

export const authApi = {
  login(data: LoginValues) {
    return http.post<never, LoginResult>('/api/sysUser/login', data);
  },
  logout() {
    return http.post<never, void>('/api/sysUser/logout');
  },
};

export const userApi = {
  page(params: UserPageParams) {
    return http.get<never, PageResult<UserItem>>('/api/sysUser', { params });
  },
  detail(id: number) {
    return http.get<never, UserItem>(`/api/sysUser/${id}`);
  },
  create(data: UserCreateValues) {
    return http.post<never, { id: number }>('/api/sysUser', data);
  },
  update(id: number, data: UserUpdateValues) {
    return http.put<never, { id: number }>(`/api/sysUser/${id}`, data);
  },
  remove(id: number) {
    return http.delete<never, { id: number }>(`/api/sysUser/${id}`);
  },
  assignRoles(id: number, roleIds: number[]) {
    return http.put<never, { userId: number; roleIds: number[] }>(`/api/sysUser/${id}/roles`, { roleIds });
  },
};

export const studentManageApi = {
  page(params: StudentPageParams) {
    return http.get<never, PageResult<StudentItem>>('/api/students', { params });
  },
  assignClass(id: number, classId: number) {
    return http.put<never, { studentId: number; classId: number }>(`/api/students/${id}/class`, { classId });
  },
  tagOptions() {
    return http.get<never, string[]>('/api/students/tag-options');
  },
  updateTag(id: number, data: StudentTagUpdateValues) {
    return http.put<never, { studentId: number; studentTag?: string }>(`/api/students/${id}/tag`, data);
  },
  assignSop(id: number, data: StudentSopAssignValues) {
    return http.post<never, { id: number; studentId: number }>(`/api/students/${id}/sop`, data);
  },
};

export const studentFollowupTagApi = {
  page(params: StudentFollowupTagPageParams) {
    return http.get<never, PageResult<StudentFollowupTagItem>>('/api/studentFollowupTags', { params });
  },
  detail(id: number) {
    return http.get<never, StudentFollowupTagItem>(`/api/studentFollowupTags/${id}`);
  },
  create(data: StudentFollowupTagValues) {
    return http.post<never, { id: number }>('/api/studentFollowupTags', data);
  },
  update(id: number, data: StudentFollowupTagValues) {
    return http.put<never, { id: number }>(`/api/studentFollowupTags/${id}`, data);
  },
  remove(id: number) {
    return http.delete<never, { id: number }>(`/api/studentFollowupTags/${id}`);
  },
};

export const studentFollowupRecordApi = {
  page(params: StudentFollowupRecordPageParams) {
    return http.get<never, PageResult<StudentFollowupRecordItem>>('/api/studentFollowupRecords', { params });
  },
  stats() {
    return http.get<never, StudentFollowupRecordStats>('/api/studentFollowupRecords/stats');
  },
  detail(id: number) {
    return http.get<never, StudentFollowupRecordItem>(`/api/studentFollowupRecords/${id}`);
  },
  generate() {
    return http.post<never, { generatedCount: number }>('/api/studentFollowupRecords/generate');
  },
  complete(id: number, data: StudentFollowupRecordCompleteValues) {
    return http.put<never, { id: number }>(`/api/studentFollowupRecords/${id}/complete`, data);
  },
  cancel(id: number, data: StudentFollowupRecordCancelValues) {
    return http.put<never, { id: number }>(`/api/studentFollowupRecords/${id}/cancel`, data);
  },
};

export const studentSopApi = {
  page(params: StudentSopPageParams) {
    return http.get<never, PageResult<StudentSopItem>>('/api/studentSops', { params });
  },
  complete(id: number, data: StudentSopCompleteValues) {
    return http.put<never, { id: number }>(`/api/studentSops/${id}/complete`, data);
  },
};

export const studentLearningPlanApi = {
  page(params: StudentLearningPlanPageParams) {
    return http.get<never, PageResult<StudentLearningPlanItem>>('/api/studentLearningPlans', { params });
  },
  create(data: StudentLearningPlanCreateValues) {
    return http.post<never, { id: number; calendarCount: number }>('/api/studentLearningPlans', data);
  },
  detail(id: number) {
    return http.get<never, StudentLearningPlanDetail>(`/api/studentLearningPlans/${id}`);
  },
  calendar(id: number) {
    return http.get<never, StudentLearningCalendarItem[]>(`/api/studentLearningPlans/${id}/calendar`);
  },
};

export const roleApi = {
  page(params: RolePageParams) {
    return http.get<never, PageResult<RoleItem>>('/api/sysRole', { params });
  },
  detail(id: number) {
    return http.get<never, RoleItem>(`/api/sysRole/${id}`);
  },
  create(data: RoleValues) {
    return http.post<never, { id: number }>('/api/sysRole', data);
  },
  update(id: number, data: RoleValues) {
    return http.put<never, { id: number }>(`/api/sysRole/${id}`, data);
  },
  remove(id: number) {
    return http.delete<never, { id: number }>(`/api/sysRole/${id}`);
  },
  assignPermissions(id: number, permissionIds: number[]) {
    return http.put<never, { roleId: number; permissionIds: number[] }>(`/api/sysRole/${id}/permissions`, {
      permissionIds,
    });
  },
};

export const textToSqlPermissionApi = {
  schemaTree() {
    return http.get<never, TextToSqlSchemaDomain[]>('/api/ai/text-to-sql/schema-tree');
  },
  rolePermission(roleId: number) {
    return http.get<never, TextToSqlRolePermissionDetail>(`/api/ai/text-to-sql/permissions/roles/${roleId}`);
  },
  saveRolePermission(roleId: number, data: TextToSqlRolePermissionSaveValues) {
    return http.put<never, { roleId: number }>(`/api/ai/text-to-sql/permissions/roles/${roleId}`, data);
  },
};

const TEXT_TO_SQL_ANALYSIS_TIMEOUT_MS = 300000;

export const textToSqlAnalysisApi = {
  analyze(data: TextToSqlAnalyzeValues) {
    return http.post<never, TextToSqlAnalyzeResult>('/api/ai/text-to-sql/analyze', data, {
      timeout: TEXT_TO_SQL_ANALYSIS_TIMEOUT_MS,
    });
  },
  runs(params: TextToSqlRunPageParams) {
    return http.get<never, PageResult<TextToSqlRunItem>>('/api/ai/text-to-sql/runs', { params });
  },
  runDetail(id: number) {
    return http.get<never, TextToSqlRunItem>(`/api/ai/text-to-sql/runs/${id}`);
  },
  feedback(id: number, data: TextToSqlFeedbackValues) {
    return http.post<never, TextToSqlRunItem>(`/api/ai/text-to-sql/runs/${id}/feedback`, data);
  },
};

export const textToSqlEvalQuestionApi = {
  page(params: TextToSqlEvalQuestionPageParams) {
    return http.get<never, PageResult<TextToSqlEvalQuestionItem>>('/api/ai/text-to-sql/eval-questions', { params });
  },
  detail(id: number) {
    return http.get<never, TextToSqlEvalQuestionItem>(`/api/ai/text-to-sql/eval-questions/${id}`);
  },
  create(data: TextToSqlEvalQuestionValues) {
    return http.post<never, IdResult>('/api/ai/text-to-sql/eval-questions', data);
  },
  update(id: number, data: TextToSqlEvalQuestionValues) {
    return http.put<never, void>(`/api/ai/text-to-sql/eval-questions/${id}`, data);
  },
  fromRun(runId: number) {
    return http.post<never, IdResult>(`/api/ai/text-to-sql/eval-questions/from-run/${runId}`);
  },
};

export const textToSqlEvalTaskApi = {
  page(params: TextToSqlEvalTaskPageParams) {
    return http.get<never, PageResult<TextToSqlEvalTaskItem>>('/api/ai/text-to-sql/eval-tasks', { params });
  },
  create(data: TextToSqlEvalTaskValues) {
    return http.post<never, IdResult>('/api/ai/text-to-sql/eval-tasks', data);
  },
  detail(id: number) {
    return http.get<never, TextToSqlEvalTaskDetail>(`/api/ai/text-to-sql/eval-tasks/${id}`);
  },
  results(id: number, params: TextToSqlEvalResultPageParams) {
    return http.get<never, PageResult<TextToSqlEvalResultItem>>(`/api/ai/text-to-sql/eval-tasks/${id}/results`, { params });
  },
  continueResult(resultId: number, clarificationAnswer: string) {
    return http.post<never, TextToSqlEvalResultItem>(`/api/ai/text-to-sql/eval-tasks/results/${resultId}/continue`, {
      clarificationAnswer,
    });
  },
};

export const permissionApi = {
  page(params: PermissionPageParams) {
    return http.get<never, PageResult<PermissionItem>>('/api/sysPermission', { params });
  },
  detail(id: number) {
    return http.get<never, PermissionItem>(`/api/sysPermission/${id}`);
  },
  create(data: PermissionValues) {
    return http.post<never, { id: number }>('/api/sysPermission', data);
  },
  update(id: number, data: PermissionValues) {
    return http.put<never, { id: number }>(`/api/sysPermission/${id}`, data);
  },
  remove(id: number) {
    return http.delete<never, { id: number }>(`/api/sysPermission/${id}`);
  },
};

export const sysConfigApi = {
  page(params: SysConfigPageParams) {
    return http.get<never, PageResult<SysConfigItem>>('/api/sysConfig', { params });
  },
  detail(id: number) {
    return http.get<never, SysConfigItem>(`/api/sysConfig/${id}`);
  },
  create(data: SysConfigValues) {
    return http.post<never, { id: number }>('/api/sysConfig', data);
  },
  update(id: number, data: SysConfigValues) {
    return http.put<never, { id: number }>(`/api/sysConfig/${id}`, data);
  },
  remove(id: number) {
    return http.delete<never, { id: number }>(`/api/sysConfig/${id}`);
  },
};

export const knowledgeBaseApi = {
  page(params: KnowledgeBasePageParams) {
    return http.get<never, PageResult<KnowledgeBaseItem>>('/api/ai/knowledge-bases', { params });
  },
  detail(id: number) {
    return http.get<never, KnowledgeBaseItem>(`/api/ai/knowledge-bases/${id}`);
  },
  create(data: KnowledgeBaseCreateValues) {
    return http.post<never, { id: number }>('/api/ai/knowledge-bases', data);
  },
  update(id: number, data: KnowledgeBaseUpdateValues) {
    return http.put<never, { id: number }>(`/api/ai/knowledge-bases/${id}`, data);
  },
  updateStatus(id: number, status: KnowledgeBaseItem['status']) {
    return http.put<never, { id: number; status: KnowledgeBaseItem['status'] }>(
      `/api/ai/knowledge-bases/${id}/status`,
      { status },
    );
  },
  recall(id: number, data: KnowledgeRecallValues) {
    return http.post<never, KnowledgeRecallResult>(`/api/ai/knowledge-bases/${id}/recall`, data);
  },
  streamQa(id: number, data: KnowledgeQaValues, handlers: StreamHandlers, signal?: AbortSignal) {
    return streamPost(`/api/ai/knowledge-bases/${id}/qa/stream`, data, handlers, signal);
  },
  remove(id: number) {
    return http.delete<never, { id: number }>(`/api/ai/knowledge-bases/${id}`);
  },
};

export const promptTemplateApi = {
  page(params: PromptTemplatePageParams) {
    return http.get<never, PageResult<PromptTemplateItem>>('/api/ai/prompt-templates', { params });
  },
  options(promptType: PromptTemplateType) {
    return http.get<never, PromptTemplateItem[]>('/api/ai/prompt-templates/options', { params: { promptType } });
  },
  detail(id: number) {
    return http.get<never, PromptTemplateItem>(`/api/ai/prompt-templates/${id}`);
  },
  create(data: PromptTemplateCreateValues) {
    return http.post<never, void>('/api/ai/prompt-templates', data);
  },
  update(id: number, data: PromptTemplateUpdateValues) {
    return http.put<never, void>(`/api/ai/prompt-templates/${id}`, data);
  },
  updateStatus(id: number, status: PromptTemplateItem['status']) {
    return http.put<never, void>(
      `/api/ai/prompt-templates/${id}/status`,
      { status },
    );
  },
  remove(id: number) {
    return http.delete<never, void>(`/api/ai/prompt-templates/${id}`);
  },
};

export const promptTemplateVersionApi = {
  list(templateId: number) {
    return http.get<never, PromptTemplateVersionItem[]>(`/api/ai/prompt-templates/${templateId}/versions`);
  },
  detail(templateId: number, versionId: number) {
    return http.get<never, PromptTemplateVersionItem>(`/api/ai/prompt-templates/${templateId}/versions/${versionId}`);
  },
  create(templateId: number, data: PromptTemplateVersionCreateValues) {
    return http.post<never, void>(`/api/ai/prompt-templates/${templateId}/versions`, data);
  },
  publish(templateId: number, versionId: number) {
    return http.put<never, void>(`/api/ai/prompt-templates/${templateId}/versions/${versionId}/publish`);
  },
  rollback(templateId: number, versionId: number) {
    return http.put<never, void>(`/api/ai/prompt-templates/${templateId}/versions/${versionId}/rollback`);
  },
};

export const promptTestApi = {
  stream(data: PromptTestValues, handlers: StreamHandlers, signal?: AbortSignal) {
    return streamPost('/api/ai/prompt-tests/stream', data, handlers, signal);
  },
};

export const knowledgeDocumentApi = {
  page(knowledgeBaseId: number, params: KnowledgeDocumentPageParams) {
    return http.get<never, PageResult<KnowledgeDocumentItem>>(
      `/api/ai/knowledge-bases/${knowledgeBaseId}/documents`,
      { params },
    );
  },
  presignUpload(knowledgeBaseId: number, data: KnowledgeDocumentPresignValues) {
    return http.post<never, UploadPresignResult>(
      `/api/ai/knowledge-bases/${knowledgeBaseId}/documents/presign-upload`,
      data,
    );
  },
  create(knowledgeBaseId: number, data: KnowledgeDocumentCreateValues) {
    return http.post<never, KnowledgeDocumentCreateResult>(
      `/api/ai/knowledge-bases/${knowledgeBaseId}/documents`,
      data,
    );
  },
  rebuild(knowledgeBaseId: number, documentId: number) {
    return http.post<never, void>(`/api/ai/knowledge-bases/${knowledgeBaseId}/documents/${documentId}/rebuild`);
  },
  chunks(knowledgeBaseId: number, documentId: number, params: KnowledgeDocumentChunkPageParams) {
    return http.get<never, PageResult<KnowledgeDocumentChunkItem>>(
      `/api/ai/knowledge-bases/${knowledgeBaseId}/documents/${documentId}/chunks`,
      { params },
    );
  },
  chunkDetail(knowledgeBaseId: number, documentId: number, chunkIndex: number) {
    return http.get<never, KnowledgeDocumentChunkDetail>(
      `/api/ai/knowledge-bases/${knowledgeBaseId}/documents/${documentId}/chunks/${chunkIndex}`,
    );
  },
  remove(knowledgeBaseId: number, documentId: number) {
    return http.delete<never, void>(`/api/ai/knowledge-bases/${knowledgeBaseId}/documents/${documentId}`);
  },
};

export const mediaVideoApi = {
  page(params: MediaVideoPageParams) {
    return http.get<never, PageResult<MediaVideoItem>>('/api/ai/media-videos', { params });
  },
  presignUpload(data: MediaVideoPresignValues) {
    return http.post<never, UploadPresignResult>('/api/ai/media-videos/presign-upload', data);
  },
  create(data: MediaVideoCreateValues) {
    return http.post<never, MediaVideoCreateResult>('/api/ai/media-videos', data);
  },
  previewUrl(id: number) {
    return http.get<never, DownloadPresignResult>(`/api/ai/media-videos/${id}/preview-url`);
  },
  createProcessTask(videoId: number) {
    return http.post<never, MediaProcessTaskCreateResult>(`/api/ai/media-process-tasks/videos/${videoId}`);
  },
  retryProcessTask(videoId: number) {
    return http.post<never, MediaProcessTaskCreateResult>(`/api/ai/media-process-tasks/videos/${videoId}/retry`);
  },
  audioPreview(videoId: number) {
    return http.get<never, MediaAudioPreviewResult>(`/api/ai/media-videos/${videoId}/audio`);
  },
  transcript(videoId: number) {
    return http.get<never, MediaTranscriptResult>(`/api/ai/media-videos/${videoId}/transcript`);
  },
  transcriptUtterances(videoId: number, pageNum: number, pageSize: number) {
    return http.get<never, PageResult<MediaTranscriptUtteranceItem>>(
      `/api/ai/media-videos/${videoId}/transcript/utterances`,
      { params: { pageNum, pageSize } },
    );
  },
  clips(videoId: number) {
    return http.get<never, MediaVideoClipItem[]>(`/api/ai/media-videos/${videoId}/clips`);
  },
};

/** 跨原视频的素材库接口。 */
export const mediaMaterialApi = {
  page(params: MediaMaterialPageParams) {
    return http.get<never, PageResult<MediaVideoClipItem>>('/api/ai/media-materials', { params });
  },
  previewUrl(id: number) {
    return http.get<never, DownloadPresignResult>(`/api/ai/media-materials/${id}/preview-url`);
  },
};

/** 抖音热点视频查询与手动采集接口。 */
export const douyinHotspotApi = {
  page(params: DouyinVideoPageParams) {
    return http.get<never, PageResult<DouyinVideoItem>>('/api/ai/douyin-videos', { params });
  },
  run() {
    return http.post<never, DouyinCollectRunResult>('/api/ai/douyin-collection/run');
  },
};

/** 内容生成 LangGraph 工作流接口。 */
export const contentGenerationApi = {
  start(data: ContentGenerationStartValues) {
    return http.post<never, ContentGenerationWorkflowResult>('/api/ai/content-generation/start', data, {
      timeout: 300_000,
    });
  },
  resume(conversationId: string, data: ContentGenerationResumeValues) {
    return http.post<never, ContentGenerationWorkflowResult>(
      `/api/ai/content-generation/${conversationId}/resume`,
      data,
      { timeout: 300_000 },
    );
  },
  retryResearch(conversationId: string) {
    return http.post<never, ContentGenerationWorkflowResult>(
      `/api/ai/content-generation/${conversationId}/research/retry`,
      undefined,
      { timeout: 300_000 },
    );
  },
  generateContent(conversationId: string, data: ContentCreationValues) {
    return http.post<never, ContentGenerationWorkflowResult>(
      `/api/ai/content-generation/${conversationId}/content/generate`,
      data,
      { timeout: 300_000 },
    );
  },
  createMaterialTask(conversationId: string, contentRevision: number) {
    return http.post<never, ContentMaterialTaskCreateResult>(
      `/api/ai/content-generation/${conversationId}/materials/tasks`,
      { contentRevision },
    );
  },
  getMaterialTask(taskId: number) {
    return http.get<never, ContentMaterialTaskResult>(
      `/api/ai/content-generation/materials/tasks/${taskId}`,
    );
  },
  retryMaterialTask(taskId: number) {
    return http.post<never, ContentMaterialTaskCreateResult>(
      `/api/ai/content-generation/materials/tasks/${taskId}/retry`,
    );
  },
  regenerateMaterialImage(taskId: number, needId: string, feedback: string) {
    return http.post<never, ContentMaterialTaskResult>(
      `/api/ai/content-generation/materials/tasks/${taskId}/items/${needId}/regenerate`,
      { feedback },
      { timeout: 720_000 },
    );
  },
  getReviewTask(taskId: number) {
    return http.get<never, ContentReviewTaskResult>(
      `/api/ai/content-generation/reviews/tasks/${taskId}`,
    );
  },
  retryReviewTask(taskId: number) {
    return http.post<never, ContentReviewTaskResult>(
      `/api/ai/content-generation/reviews/tasks/${taskId}/retry`,
    );
  },
  approveReviewTask(taskId: number) {
    return http.post<never, ContentReviewTaskResult>(
      `/api/ai/content-generation/reviews/tasks/${taskId}/approve`,
    );
  },
  getPreviewTask(taskId: number) {
    return http.get<never, ContentPreviewTaskResult>(
      `/api/ai/content-generation/previews/tasks/${taskId}`,
    );
  },
  retryPreviewTask(taskId: number) {
    return http.post<never, ContentPreviewTaskResult>(
      `/api/ai/content-generation/previews/tasks/${taskId}/retry`,
    );
  },
};

export const campusApi = {
  page(params: CampusPageParams) {
    return http.get<never, PageResult<CampusItem>>('/api/campus', { params });
  },
  detail(id: number) {
    return http.get<never, CampusItem>(`/api/campus/${id}`);
  },
  create(data: CampusValues) {
    return http.post<never, { id: number }>('/api/campus', data);
  },
  update(id: number, data: CampusValues) {
    return http.put<never, { id: number }>(`/api/campus/${id}`, data);
  },
  remove(id: number) {
    return http.delete<never, { id: number }>(`/api/campus/${id}`);
  },
};

export const courseApi = {
  page(params: CoursePageParams) {
    return http.get<never, PageResult<CourseItem>>('/api/course', { params });
  },
  detail(id: number) {
    return http.get<never, CourseItem>(`/api/course/${id}`);
  },
  create(data: CourseValues) {
    return http.post<never, { id: number }>('/api/course', data);
  },
  update(id: number, data: CourseValues) {
    return http.put<never, { id: number }>(`/api/course/${id}`, data);
  },
  remove(id: number) {
    return http.delete<never, { id: number }>(`/api/course/${id}`);
  },
  listDetails(courseId: number) {
    return http.get<never, CourseDetailItem[]>(`/api/course/${courseId}/details`);
  },
  listStages(courseId: number) {
    return http.get<never, string[]>(`/api/course/${courseId}/stages`);
  },
  detailItem(id: number) {
    return http.get<never, CourseDetailItem>(`/api/course/details/${id}`);
  },
  createDetail(courseId: number, data: CourseDetailValues) {
    return http.post<never, { id: number }>(`/api/course/${courseId}/details`, data);
  },
  updateDetail(id: number, data: CourseDetailValues) {
    return http.put<never, { id: number }>(`/api/course/details/${id}`, data);
  },
  removeDetail(id: number) {
    return http.delete<never, { id: number }>(`/api/course/details/${id}`);
  },
  importDetails(courseId: number, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return http.post<never, void>(`/api/course/${courseId}/details/import`, formData);
  },
  listHomeworkTemplates(courseId: number) {
    return http.get<never, CourseHomeworkTemplateItem[]>(`/api/course/${courseId}/homeworkTemplates`);
  },
  homeworkTemplateDetail(id: number) {
    return http.get<never, CourseHomeworkTemplateItem>(`/api/course/homeworkTemplates/${id}`);
  },
  createHomeworkTemplate(courseId: number, data: CourseHomeworkTemplateValues) {
    return http.post<never, { id: number }>(`/api/course/${courseId}/homeworkTemplates`, data);
  },
  updateHomeworkTemplate(id: number, data: CourseHomeworkTemplateValues) {
    return http.put<never, { id: number }>(`/api/course/homeworkTemplates/${id}`, data);
  },
  removeHomeworkTemplate(id: number) {
    return http.delete<never, { id: number }>(`/api/course/homeworkTemplates/${id}`);
  },
};

export const productApi = {
  page(params: ProductPageParams) {
    return http.get<never, PageResult<ProductItem>>('/api/products', { params });
  },
  detail(id: number) {
    return http.get<never, ProductItem>(`/api/products/${id}`);
  },
  create(data: ProductValues) {
    return http.post<never, { id: number }>('/api/products', data);
  },
  update(id: number, data: ProductValues) {
    return http.put<never, { id: number }>(`/api/products/${id}`, data);
  },
  remove(id: number) {
    return http.delete<never, { id: number }>(`/api/products/${id}`);
  },
};

export const examQuestionApi = {
  page(params: ExamQuestionPageParams) {
    return http.get<never, PageResult<ExamQuestionItem>>('/api/examQuestions', { params });
  },
  detail(id: number) {
    return http.get<never, ExamQuestionItem>(`/api/examQuestions/${id}`);
  },
  create(data: ExamQuestionValues) {
    return http.post<never, { id: number }>('/api/examQuestions', data);
  },
  update(id: number, data: ExamQuestionValues) {
    return http.put<never, { id: number }>(`/api/examQuestions/${id}`, data);
  },
  remove(id: number) {
    return http.delete<never, { id: number }>(`/api/examQuestions/${id}`);
  },
  updateStatus(id: number, status: ExamQuestionStatus) {
    return http.put<never, { id: number; status: ExamQuestionStatus }>(`/api/examQuestions/${id}/status`, { status });
  },
};

export const examPaperApi = {
  page(params: ExamPaperPageParams) {
    return http.get<never, PageResult<ExamPaperItem>>('/api/examPapers', { params });
  },
  detail(id: number) {
    return http.get<never, ExamPaperDetailItem>(`/api/examPapers/${id}`);
  },
  create(data: ExamPaperValues) {
    return http.post<never, { id: number }>('/api/examPapers', data);
  },
  remove(id: number) {
    return http.delete<never, { id: number }>(`/api/examPapers/${id}`);
  },
};

export const examApi = {
  page(params: ExamPageParams) {
    return http.get<never, PageResult<ExamItem>>('/api/exams', { params });
  },
  detail(id: number) {
    return http.get<never, ExamItem>(`/api/exams/${id}`);
  },
  create(data: ExamValues) {
    return http.post<never, { id: number }>('/api/exams', data);
  },
  update(id: number, data: ExamValues) {
    return http.put<never, { id: number }>(`/api/exams/${id}`, data);
  },
  updateAnswerVisible(id: number, answerVisible: boolean) {
    return http.put<never, { id: number }>(`/api/exams/${id}/answer-visible`, { answerVisible });
  },
  remove(id: number) {
    return http.delete<never, { id: number }>(`/api/exams/${id}`);
  },
  submissions(id: number, params: ExamSubmissionPageParams) {
    return http.get<never, PageResult<ExamSubmissionItem>>(`/api/exams/${id}/submissions`, { params });
  },
  submissionDetail(recordId: number) {
    return http.get<never, ExamSubmissionDetailItem>(`/api/exams/submissions/${recordId}`);
  },
  gradeSubmission(recordId: number, data: ExamSubmissionGradeValues) {
    return http.put<never, { recordId: number; score: number; gradingStatus: string }>(`/api/exams/submissions/${recordId}/grade`, data);
  },
};

export const prepayOrderApi = {
  page(params: PrepayOrderPageParams) {
    return http.get<never, PageResult<PrepayOrderItem>>('/api/prepayOrders', { params });
  },
  detail(id: number) {
    return http.get<never, PrepayOrderItem>(`/api/prepayOrders/${id}`);
  },
  create(data: PrepayOrderValues) {
    return http.post<never, { id: number }>('/api/prepayOrders', data);
  },
  update(id: number, data: PrepayOrderValues) {
    return http.put<never, { id: number }>(`/api/prepayOrders/${id}`, data);
  },
  remove(id: number) {
    return http.delete<never, { id: number }>(`/api/prepayOrders/${id}`);
  },
};

export const paymentOrderApi = {
  page(params: PaymentOrderPageParams) {
    return http.get<never, PageResult<PaymentOrderItem>>('/api/orders', { params });
  },
};

export const refundOrderApi = {
  page(params: RefundOrderPageParams) {
    return http.get<never, PageResult<RefundOrderItem>>('/api/refundOrders', { params });
  },
  create() {
    return http.post<never, RefundOrderCreateResult>('/api/refundOrders/create');
  },
  apply(refundOrderNo: string, data: RefundOrderApplyValues) {
    return http.post<never, RefundOrderApplyResult>(`/api/refundOrders/${refundOrderNo}/apply`, data);
  },
};

export const clazzApi = {
  page(params: ClazzPageParams) {
    return http.get<never, PageResult<ClazzItem>>('/api/classes', { params });
  },
  detail(id: number) {
    return http.get<never, ClazzItem>(`/api/classes/${id}`);
  },
  create(data: ClazzValues) {
    return http.post<never, { id: number }>('/api/classes', data);
  },
  update(id: number, data: ClazzValues) {
    return http.put<never, { id: number }>(`/api/classes/${id}`, data);
  },
  remove(id: number) {
    return http.delete<never, { id: number }>(`/api/classes/${id}`);
  },
  generateSchedule(data: ClassScheduleGenerateValues) {
    return http.post<never, ClassScheduleGenerateResult>('/api/classes/schedules/generate', data);
  },
  listSchedules(classId: number, params?: { startDate: string; endDate: string }) {
    return http.get<never, ClassScheduleItem[]>(`/api/classes/schedules/${classId}`, { params });
  },
  classStageInfo(classId: number) {
    return http.get<never, ClassStageInfoItem[]>(`/api/classes/schedules/${classId}/classStageInfo`);
  },
  dateDetail(classId: number, scheduleDate: string) {
    return http.get<never, ClassScheduleDateDetail>(`/api/classes/schedules/${classId}/date-detail`, {
      params: { scheduleDate },
    });
  },
  assignScheduleTeachers(classId: number, data: ClassScheduleTeacherAssignValues) {
    return http.put<never, ClassScheduleTeacherAssignResult>(`/api/classes/schedules/${classId}/teachers`, data);
  },
  addScheduleCourse(classId: number, data: ClassScheduleAddCourseValues) {
    return http.put<never, void>(`/api/classes/schedules/${classId}/addClassSchule`, data);
  },
  teacherDetail(data: TeacherScheduleQuery) {
    return http.post<never, TeacherScheduleItem[]>('/api/classes/schedules/teacher-detail', data);
  },
};

export const homeworkApi = {
  page(params: HomeworkPageParams) {
    return http.get<never, PageResult<HomeworkItem>>('/api/homeworks', { params });
  },
  create(data: HomeworkValues) {
    return http.post<never, { id: number }>('/api/homeworks', data);
  },
  prepare(classId: number, homeworkDate: string) {
    return http.get<never, HomeworkPrepareResult>('/api/homeworks/prepare', { params: { classId, homeworkDate } });
  },
  publishAnswer(id: number, data: HomeworkAnswerValues) {
    return http.put<never, { id: number }>(`/api/homeworks/${id}/answer`, data);
  },
  submissions(id: number, params: HomeworkSubmissionPageParams) {
    return http.get<never, PageResult<HomeworkSubmissionItem>>(`/api/homeworks/${id}/submissions`, { params });
  },
  gradeSubmission(submissionId: number, data: HomeworkSubmissionGradeValues) {
    return http.put<never, { id: number; score: number; teacherRemark?: string }>(`/api/homeworks/submissions/${submissionId}/grade`, data);
  },
};

export const uploadApi = {
  presignUpload(objectKey: string) {
    return http.post<never, UploadPresignResult>('/api/upload/presign-upload', { objectKey });
  },
  presignDownload(objectKey: string) {
    return http.get<never, DownloadPresignResult>('/api/upload/presign-download', { params: { objectKey } });
  },
};

export const classDutyApi = {
  page(params: ClassDutyPageParams) {
    return http.get<never, PageResult<ClassDutyItem>>('/api/classDuties', { params });
  },
  detail(id: number) {
    return http.get<never, ClassDutyItem>(`/api/classDuties/${id}`);
  },
  create(data: ClassDutyValues) {
    return http.post<never, { id: number }>('/api/classDuties', data);
  },
  update(id: number, data: ClassDutyValues) {
    return http.put<never, { id: number }>(`/api/classDuties/${id}`, data);
  },
  remove(id: number) {
    return http.delete<never, { id: number }>(`/api/classDuties/${id}`);
  },
  date(dutyDate: string) {
    return http.get<never, ClassDutyDateResult>('/api/classDuties/date', { params: { dutyDate } });
  },
  saveDate(data: ClassDutyDateSaveValues) {
    return http.put<never, { saveCount: number }>('/api/classDuties/date', data);
  },
};
