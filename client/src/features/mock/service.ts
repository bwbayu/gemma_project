import { readStorage, writeStorage } from './storage'
import type {
  GenerationJob,
  JobStage,
  QuestionItem,
  ReviewResult,
  Workspace,
} from './types'

const WORKSPACE_RESOURCE = 'workspace'
const QUESTION_LIST_RESOURCE = 'question-list'
const ACTIVE_JOB_RESOURCE = 'active-job'
const REVIEW_RESULT_RESOURCE = 'review-result-map'
const QUESTION_SOURCE_RESOURCE = 'question-source-map'
const MOCK_STAGE_DELAY_MS = 5000

function nowIso(): string {
  return new Date().toISOString()
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

function buildMockWorkspace(title: string, description: string): Workspace {
  const suffix = `${Date.now()}`

  return {
    workspaceId: `ws_${suffix}`,
    formRef: {
      formId: `form_${suffix}`,
      formTitle: title,
      formDescription: description,
      formEditUrl: 'https://docs.google.com/forms/d/mock-edit',
      formResponderUrl: 'https://docs.google.com/forms/d/mock-response',
    },
    createdAt: nowIso(),
    updatedAt: nowIso(),
  }
}

function buildQuestionItem(
  label: string,
  inputType: 'image' | 'text',
  status: QuestionItem['status'] = 'generated',
): QuestionItem {
  return {
    questionItemId: `q_${Date.now()}`,
    label,
    inputType,
    status,
    createdAt: nowIso(),
  }
}

function buildGenerationJob(workspaceId: string, questionItemId: string): GenerationJob {
  return {
    jobId: `job_${Date.now()}`,
    workspaceId,
    questionItemId,
    stage: 'generating_animation',
    attempt: 1,
    maxAttempts: 3,
    message: 'Mock generation started.',
  }
}

function saveQuestionList(items: QuestionItem[]): void {
  writeStorage(QUESTION_LIST_RESOURCE, items)
}

function getReviewMap(): Record<string, ReviewResult> {
  return readStorage<Record<string, ReviewResult>>(REVIEW_RESULT_RESOURCE, {})
}

function saveReviewMap(map: Record<string, ReviewResult>): void {
  writeStorage(REVIEW_RESULT_RESOURCE, map)
}

type QuestionSource =
  | { inputType: 'image'; fileName: string }
  | { inputType: 'text'; rawText: string }

function getSourceMap(): Record<string, QuestionSource> {
  return readStorage<Record<string, QuestionSource>>(QUESTION_SOURCE_RESOURCE, {})
}

function saveSourceMap(map: Record<string, QuestionSource>): void {
  writeStorage(QUESTION_SOURCE_RESOURCE, map)
}

function updateQuestionStatusInList(
  questionItemId: string,
  status: QuestionItem['status'],
): QuestionItem[] {
  const list = readStorage<QuestionItem[]>(QUESTION_LIST_RESOURCE, [])
  const updated = list.map((item) =>
    item.questionItemId === questionItemId ? { ...item, status } : item,
  )
  saveQuestionList(updated)
  return updated
}

function deriveValidationVerdict(questionItemId: string): 'PASS' | 'FAIL' {
  const numeric = Number(questionItemId.replace(/\D/g, '').slice(-2) || '0')
  return numeric % 3 === 0 ? 'FAIL' : 'PASS'
}

function buildReviewResult(
  workspace: Workspace,
  question: QuestionItem,
  source: QuestionSource | undefined,
): ReviewResult {
  const verdict = deriveValidationVerdict(question.questionItemId)
  const isText = source?.inputType === 'text'
  const givenInformation = isText
    ? ['Given values extracted from text prompt', 'Force/object relationships identified']
    : ['Given values inferred from uploaded image label', 'Diagram assumptions preserved']

  return {
    questionItemId: question.questionItemId,
    source: {
      inputType: question.inputType,
      imageUrl:
        source?.inputType === 'image'
          ? `mock://uploaded-image/${encodeURIComponent(source.fileName)}`
          : null,
      text: source?.inputType === 'text' ? source.rawText : null,
    },
    result: {
      videoUrl: `mock://video/${question.questionItemId}.mp4`,
      gifUrl: `mock://gif/${question.questionItemId}.gif`,
      thumbnailUrl: `mock://thumb/${question.questionItemId}.jpg`,
    },
    summary: {
      scenario: question.inputType === 'text' ? 'Text-derived physics scenario' : 'Image-derived physics scenario',
      givenInformation,
      studentTask: 'Observe the animation and determine the unknown quantity without direct answer leakage.',
    },
    validation: {
      verdict,
      summary:
        verdict === 'PASS'
          ? 'Validation passed in mock mode. Ready for teacher review.'
          : 'Validation flagged issues in mock mode. Regenerate or discard is recommended.',
    },
    append: {
      status: 'not_started',
      formId: workspace.formRef.formId,
    },
  }
}

export const mockService = {
  async getWorkspace(): Promise<Workspace | null> {
    await wait(200)
    return readStorage<Workspace | null>(WORKSPACE_RESOURCE, null)
  },

  async createWorkspace(title: string, description: string): Promise<Workspace> {
    await wait(500)
    const workspace = buildMockWorkspace(title, description)
    writeStorage(WORKSPACE_RESOURCE, workspace)
    return workspace
  },

  async openWorkspaceByRef(formRef: string): Promise<Workspace> {
    await wait(500)
    const workspace = buildMockWorkspace('Imported Form Workspace', `Ref: ${formRef}`)
    writeStorage(WORKSPACE_RESOURCE, workspace)
    return workspace
  },

  async listQuestionItems(): Promise<QuestionItem[]> {
    await wait(180)
    return readStorage<QuestionItem[]>(QUESTION_LIST_RESOURCE, [])
  },

  async getActiveJob(): Promise<GenerationJob | null> {
    await wait(120)
    return readStorage<GenerationJob | null>(ACTIVE_JOB_RESOURCE, null)
  },

  async setActiveJobStage(
    stage: JobStage,
    message: string,
  ): Promise<GenerationJob | null> {
    await wait(MOCK_STAGE_DELAY_MS)
    const current = readStorage<GenerationJob | null>(ACTIVE_JOB_RESOURCE, null)
    if (!current) {
      return null
    }
    const next: GenerationJob = { ...current, stage, message }
    writeStorage(ACTIVE_JOB_RESOURCE, next)
    return next
  },

  async clearActiveJob(): Promise<void> {
    await wait(40)
    writeStorage<GenerationJob | null>(ACTIVE_JOB_RESOURCE, null)
  },

  async getReviewResult(questionItemId: string): Promise<ReviewResult | null> {
    await wait(120)
    const map = getReviewMap()
    return map[questionItemId] ?? null
  },

  async finalizeGeneration(questionItemId: string): Promise<ReviewResult | null> {
    await wait(240)
    const workspace = readStorage<Workspace | null>(WORKSPACE_RESOURCE, null)
    if (!workspace) {
      return null
    }

    const list = readStorage<QuestionItem[]>(QUESTION_LIST_RESOURCE, [])
    const question = list.find((item) => item.questionItemId === questionItemId)
    if (!question) {
      return null
    }

    const sourceMap = getSourceMap()
    const source = sourceMap[questionItemId]
    const review = buildReviewResult(workspace, question, source)

    const reviewMap = getReviewMap()
    reviewMap[questionItemId] = review
    saveReviewMap(reviewMap)

    const status = review.validation.verdict === 'PASS' ? 'generated' : 'failed'
    updateQuestionStatusInList(questionItemId, status)

    return review
  },

  async approveQuestion(questionItemId: string): Promise<ReviewResult | null> {
    await wait(260)
    const reviewMap = getReviewMap()
    const current = reviewMap[questionItemId]
    if (!current) {
      return null
    }

    const updated: ReviewResult = {
      ...current,
      append: { ...current.append, status: 'added' },
    }
    reviewMap[questionItemId] = updated
    saveReviewMap(reviewMap)
    updateQuestionStatusInList(questionItemId, 'added')
    return updated
  },

  async discardQuestion(questionItemId: string): Promise<void> {
    await wait(140)
    updateQuestionStatusInList(questionItemId, 'discarded')
  },

  async regenerateQuestion(questionItemId: string): Promise<QuestionItem | null> {
    await wait(280)
    const list = readStorage<QuestionItem[]>(QUESTION_LIST_RESOURCE, [])
    const current = list.find((item) => item.questionItemId === questionItemId)
    if (!current) {
      return null
    }
    const updated: QuestionItem[] = list.map((item) =>
      item.questionItemId === questionItemId
        ? { ...item, status: 'generated' as const }
        : item,
    )
    saveQuestionList(updated)
    return updated.find((item) => item.questionItemId === questionItemId) ?? null
  },

  async startRegenerationJob(
    workspaceId: string,
    questionItemId: string,
  ): Promise<GenerationJob | null> {
    await wait(160)
    const list = readStorage<QuestionItem[]>(QUESTION_LIST_RESOURCE, [])
    const target = list.find((item) => item.questionItemId === questionItemId)
    if (!target) {
      return null
    }

    const job = buildGenerationJob(workspaceId, questionItemId)
    writeStorage(ACTIVE_JOB_RESOURCE, job)
    return job
  },

  async startQuestionFromImage(workspaceId: string, fileName: string): Promise<{
    question: QuestionItem
    job: GenerationJob
  }> {
    await wait(350)
    const label = fileName.trim() || 'Uploaded image question'
    const question = buildQuestionItem(label, 'image', 'generated')
    const job = buildGenerationJob(workspaceId, question.questionItemId)

    const list = readStorage<QuestionItem[]>(QUESTION_LIST_RESOURCE, [])
    saveQuestionList([question, ...list])
    writeStorage(ACTIVE_JOB_RESOURCE, job)
    const sourceMap = getSourceMap()
    sourceMap[question.questionItemId] = { inputType: 'image', fileName }
    saveSourceMap(sourceMap)

    return { question, job }
  },

  async startQuestionFromText(workspaceId: string, text: string): Promise<{
    question: QuestionItem
    job: GenerationJob
  }> {
    await wait(350)
    const compact = text.trim().replace(/\s+/g, ' ')
    const label = compact.length > 64 ? `${compact.slice(0, 64)}...` : compact
    const question = buildQuestionItem(label || 'Text question', 'text', 'generated')
    const job = buildGenerationJob(workspaceId, question.questionItemId)

    const list = readStorage<QuestionItem[]>(QUESTION_LIST_RESOURCE, [])
    saveQuestionList([question, ...list])
    writeStorage(ACTIVE_JOB_RESOURCE, job)
    const sourceMap = getSourceMap()
    sourceMap[question.questionItemId] = { inputType: 'text', rawText: text.trim() }
    saveSourceMap(sourceMap)

    return { question, job }
  },

}
