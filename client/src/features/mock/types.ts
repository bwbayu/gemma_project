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
  attempt: number
  maxAttempts: number
  message: string
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
  }
}

export interface StageReviewChecklist {
  stageId: string
  stageName: string
  checklist: string[]
}
