export type QuestionStatus = 'generated' | 'added' | 'failed' | 'discarded'

export type JobStage =
  | 'reading_question'
  | 'generating_animation'
  | 'rendering_video'
  | 'validating_output'
  | 'preparing_assets'
  | 'awaiting_review'
  | 'appending_to_form'
  | 'completed'
  | 'failed'

export interface WorkspaceFormRef {
  formId: string
  formTitle: string
  formDescription: string
  formEditUrl: string
  formResponderUrl: string
}

export interface Workspace {
  workspaceId: string
  formRef: WorkspaceFormRef
  createdAt: string
  updatedAt: string
}

export interface QuestionItem {
  questionItemId: string
  label: string
  inputType: 'image' | 'text'
  status: QuestionStatus
  createdAt: string
}

export interface GenerationJob {
  jobId: string
  workspaceId: string
  questionItemId: string
  stage: JobStage
  status?: 'queued' | 'running' | 'completed' | 'failed'
  attempt: number
  maxAttempts: number
  message: string
  error?: unknown
  finishedAt?: string | null
}

export interface ReviewResult {
  questionItemId: string
  source: {
    inputType: 'image' | 'text'
    imageUrl: string | null
    text: string | null
  }
  result: {
    videoUrl: string
    gifUrl: string
    gifDriveFileId: string | null
    thumbnailUrl: string
  }
  summary: {
    scenario: string
    givenInformation: string[]
    studentTask: string
  }
  validation: {
    verdict: 'PASS' | 'FAIL'
    summary: string
  }
  append: {
    status: 'not_started' | 'in_progress' | 'added' | 'error'
    formId: string
    errorMessage?: string | null
  }
  gifStatus?: 'pending' | 'done' | 'failed' | null
}

export interface StageReviewChecklist {
  stageId: string
  stageName: string
  checklist: string[]
}
