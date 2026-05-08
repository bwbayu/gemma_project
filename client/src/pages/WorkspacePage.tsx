import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Badge } from '../components/ui/Badge'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { mockService } from '../features/mock/service'
import type {
  GenerationJob,
  JobStage,
  QuestionItem,
  ReviewResult,
  Workspace,
} from '../features/mock/types'

const PROGRESS_FLOW: Array<{ stage: JobStage; message: string }> = [
  { stage: 'reading_question', message: 'Reading source question...' },
  { stage: 'generating_animation', message: 'Generating animation plan...' },
  { stage: 'rendering_video', message: 'Rendering mock video output...' },
  { stage: 'validating_output', message: 'Running mock validation checks...' },
  { stage: 'preparing_assets', message: 'Preparing review assets...' },
]

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
}

function getStatusTone(status: QuestionItem['status']): 'neutral' | 'success' | 'warning' {
  if (status === 'added') {
    return 'success'
  }
  if (status === 'failed' || status === 'discarded') {
    return 'warning'
  }
  return 'neutral'
}

function getStageLabel(stage: JobStage): string {
  return stage
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function getReviewSourceText(reviewResult: ReviewResult): string {
  if (reviewResult.source.inputType === 'text') {
    return reviewResult.source.text ?? ''
  }

  if (reviewResult.source.imageUrl) {
    return decodeURIComponent(reviewResult.source.imageUrl.split('/').pop() ?? 'Uploaded image')
  }

  return 'Uploaded image source'
}

export function WorkspacePage() {
  const navigate = useNavigate()
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [questionItems, setQuestionItems] = useState<QuestionItem[]>([])
  const [activeJob, setActiveJob] = useState<GenerationJob | null>(null)
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null)
  const [loading, setLoading] = useState(true)

  const [mode, setMode] = useState<'image' | 'text'>('image')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [textInput, setTextInput] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [decisionLoading, setDecisionLoading] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [submitSuccess, setSubmitSuccess] = useState('')
  const [copyMessage, setCopyMessage] = useState('')

  useEffect(() => {
    let mounted = true

    async function hydrateWorkspace() {
      const [found, list, job] = await Promise.all([
        mockService.getWorkspace(),
        mockService.listQuestionItems(),
        mockService.getActiveJob(),
      ])
      if (mounted) {
        setWorkspace(found)
        setQuestionItems(list)
        setActiveJob(job)
        setLoading(false)
      }
    }

    void hydrateWorkspace()

    return () => {
      mounted = false
    }
  }, [])

  async function refreshQuestions(): Promise<void> {
    const list = await mockService.listQuestionItems()
    setQuestionItems(list)
  }

  async function runProgress(questionItemId: string): Promise<void> {
    for (const step of PROGRESS_FLOW) {
      const updated = await mockService.setActiveJobStage(step.stage, step.message)
      setActiveJob(updated)
    }

    const review = await mockService.finalizeGeneration(questionItemId)
    if (!review) {
      setSubmitError('Generation finished without review payload.')
      return
    }

    const awaitReviewJob = await mockService.setActiveJobStage(
      'awaiting_review',
      review.validation.verdict === 'PASS'
        ? 'Ready for teacher review.'
        : 'Validation flagged issues. Regenerate or discard is recommended.',
    )
    setActiveJob(awaitReviewJob)
    setReviewResult(review)
    await refreshQuestions()
  }

  async function handleStartGeneration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!workspace) {
      setSubmitError('Create or open a workspace before creating questions.')
      return
    }

    setSubmitError('')
    setSubmitSuccess('')
    setCopyMessage('')
    setReviewResult(null)
    setSubmitting(true)

    try {
      if (mode === 'image') {
        if (!selectedFile) {
          setSubmitError('Choose an image file first.')
          return
        }
        const result = await mockService.startQuestionFromImage(
          workspace.workspaceId,
          selectedFile.name,
        )
        setQuestionItems((prev) => [result.question, ...prev])
        setActiveJob(result.job)
        setSelectedFile(null)
        setSubmitSuccess('Image question queued. Running generation flow...')
        await runProgress(result.question.questionItemId)
      } else {
        if (!textInput.trim()) {
          setSubmitError('Paste question text first.')
          return
        }
        const result = await mockService.startQuestionFromText(
          workspace.workspaceId,
          textInput,
        )
        setQuestionItems((prev) => [result.question, ...prev])
        setActiveJob(result.job)
        setTextInput('')
        setSubmitSuccess('Text question queued. Running generation flow...')
        await runProgress(result.question.questionItemId)
      }
    } catch {
      setSubmitError('Could not start mock generation. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleOpenReview(questionItemId: string): Promise<void> {
    setSubmitError('')
    setSubmitSuccess('')
    setCopyMessage('')
    const payload = await mockService.getReviewResult(questionItemId)
    if (!payload) {
      setSubmitError('No review payload yet for this question. Regenerate to create one.')
      return
    }

    setReviewResult(payload)
  }

  async function handleApprove(): Promise<void> {
    if (!reviewResult) {
      return
    }

    setDecisionLoading(true)
    setCopyMessage('')
    const appendJob = await mockService.setActiveJobStage(
      'appending_to_form',
      'Appending question to active form...',
    )
    setActiveJob(appendJob)

    const updated = await mockService.approveQuestion(reviewResult.questionItemId)
    if (!updated) {
      setSubmitError('Could not approve this question.')
      setDecisionLoading(false)
      return
    }

    setReviewResult(updated)
    await refreshQuestions()
    const completedJob = await mockService.setActiveJobStage(
      'completed',
      'Question appended to form in mock mode.',
    )
    setActiveJob(completedJob)
    await mockService.clearActiveJob()
    setActiveJob(null)
    setDecisionLoading(false)
  }

  async function handleDiscard(): Promise<void> {
    if (!reviewResult) {
      return
    }

    setDecisionLoading(true)
    await mockService.discardQuestion(reviewResult.questionItemId)
    await refreshQuestions()
    setReviewResult(null)
    setDecisionLoading(false)
  }

  async function handleRegenerate(): Promise<void> {
    if (!reviewResult || !workspace) {
      return
    }

    setDecisionLoading(true)
    setCopyMessage('')
    const updated = await mockService.regenerateQuestion(reviewResult.questionItemId)
    if (!updated) {
      setSubmitError('Could not regenerate this question.')
      setDecisionLoading(false)
      return
    }

    await refreshQuestions()
    setReviewResult(null)
    const restart = await mockService.startRegenerationJob(
      workspace.workspaceId,
      updated.questionItemId,
    )
    if (!restart) {
      setSubmitError('Could not initialize regeneration job.')
      setDecisionLoading(false)
      return
    }
    setActiveJob(restart)
    await runProgress(updated.questionItemId)
    setDecisionLoading(false)
  }

  async function handleCopyResponderLink(): Promise<void> {
    if (!workspace) {
      return
    }

    try {
      await navigator.clipboard.writeText(workspace.formRef.formResponderUrl)
      setCopyMessage('Responder link copied to clipboard.')
    } catch {
      setCopyMessage('Clipboard unavailable. Copy manually from workspace header.')
    }
  }

  return (
    <section className="space-y-5">
      <header className="space-y-1">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Workspace
        </h1>
        <p className="text-sm text-slate">
          Manage intake, monitor generation progress, and make review decisions
          (approve/regenerate/discard).
        </p>
      </header>

      <Card className="flex items-center justify-between">
        <div>
          {loading ? (
            <>
              <p className="font-medium text-ink">Loading workspace...</p>
              <p className="text-sm text-slate">Checking local mock persistence.</p>
            </>
          ) : workspace ? (
            <>
              <p className="font-medium text-ink">{workspace.formRef.formTitle}</p>
              <p className="text-sm text-slate">{workspace.formRef.formDescription}</p>
              <p className="mt-1 text-xs text-slate">Form ID: {workspace.formRef.formId}</p>
            </>
          ) : (
            <>
              <p className="font-medium text-ink">No Active Workspace</p>
              <p className="text-sm text-slate">
                Return to the dashboard and create or open a workspace first.
              </p>
            </>
          )}
        </div>
        <div className="flex items-center gap-3">
          <Badge tone={workspace ? 'success' : 'warning'}>
            {workspace ? 'Workspace Active' : 'No Active Form'}
          </Badge>
          {!loading && !workspace ? (
            <Button onClick={() => navigate('/')} variant="secondary">
              Go to Dashboard
            </Button>
          ) : null}
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="space-y-3">
          <p className="font-medium text-ink">Question List</p>
          {questionItems.length === 0 ? (
            <p className="text-sm text-slate">
              No questions yet. Create your first image/text question from the
              panel on the right.
            </p>
          ) : (
            <ul className="space-y-2">
              {questionItems.map((item) => (
                <li
                  className="rounded-md border border-line bg-white px-3 py-2"
                  key={item.questionItemId}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-ink">{item.label}</p>
                      <p className="text-xs text-slate">
                        {item.inputType.toUpperCase()} - {formatDate(item.createdAt)}
                      </p>
                    </div>
                    <Badge tone={getStatusTone(item.status)}>{item.status}</Badge>
                  </div>
                  <div className="mt-2">
                    <Button
                      onClick={() => void handleOpenReview(item.questionItemId)}
                      variant="ghost"
                    >
                      Open Review
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="space-y-3">
          <p className="font-medium text-ink">Create New Animation</p>
          <p className="text-sm text-slate">
            Flow: intake to generation progress to review decision actions.
          </p>

          <div className="flex gap-2">
            <Button
              onClick={() => setMode('image')}
              variant={mode === 'image' ? 'primary' : 'secondary'}
            >
              Image Input
            </Button>
            <Button
              onClick={() => setMode('text')}
              variant={mode === 'text' ? 'primary' : 'secondary'}
            >
              Text Input
            </Button>
          </div>

          <form className="space-y-3" onSubmit={(event) => void handleStartGeneration(event)}>
            {mode === 'image' ? (
              <label className="block space-y-1 text-sm text-slate">
                <span>Upload source image</span>
                <input
                  accept="image/*"
                  className="block w-full rounded-md border border-line bg-white p-2 text-sm text-ink file:mr-3 file:rounded-md file:border-0 file:bg-[#edf6f3] file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-accent"
                  onChange={(event) => {
                    setSelectedFile(event.target.files?.[0] ?? null)
                    if (submitError) {
                      setSubmitError('')
                    }
                  }}
                  type="file"
                />
                {selectedFile ? (
                  <p className="text-xs text-slate">Selected: {selectedFile.name}</p>
                ) : null}
              </label>
            ) : (
              <label className="block space-y-1 text-sm text-slate">
                <span>Paste source question</span>
                <textarea
                  className="min-h-[110px] w-full rounded-md border border-line bg-white p-3 text-sm text-ink placeholder:text-slate focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ink/10"
                  onChange={(event) => {
                    setTextInput(event.target.value)
                    if (submitError) {
                      setSubmitError('')
                    }
                  }}
                  placeholder="Type or paste physics question text..."
                  value={textInput}
                />
              </label>
            )}

            {submitError ? <p className="text-sm text-[#b44f2a]">{submitError}</p> : null}
            {submitSuccess ? (
              <p className="text-sm text-[#0f624f]">{submitSuccess}</p>
            ) : null}

            <Button disabled={submitting || !workspace} type="submit" variant="secondary">
              {submitting ? 'Starting...' : 'Start Mock Generation'}
            </Button>
          </form>
        </Card>
      </div>

      {activeJob ? (
        <Card className="space-y-2 border-[#d5e8e3] bg-[#f2faf7]">
          <p className="text-sm font-medium text-accent">Progress</p>
          <div className="grid gap-2 md:grid-cols-2">
            <p className="text-xs text-slate">Job ID: {activeJob.jobId}</p>
            <p className="text-xs text-slate">
              Current stage: {getStageLabel(activeJob.stage)}
            </p>
          </div>
          <p className="text-sm text-slate">{activeJob.message}</p>
        </Card>
      ) : null}

      {reviewResult ? (
        <Card className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="font-medium text-ink">Review Result</p>
            <Badge tone={reviewResult.validation.verdict === 'PASS' ? 'success' : 'warning'}>
              {reviewResult.validation.verdict}
            </Badge>
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            <Card className="space-y-2 p-3 shadow-none">
              <p className="text-sm font-medium text-ink">Source</p>
              {reviewResult.source.inputType === 'text' ? (
                <p className="text-sm text-slate">{getReviewSourceText(reviewResult)}</p>
              ) : (
                <div className="rounded-md border border-dashed border-line bg-[#faf8f4] p-3 text-sm text-slate">
                  Image source placeholder: {getReviewSourceText(reviewResult)}
                </div>
              )}
            </Card>

            <Card className="space-y-2 p-3 shadow-none">
              <p className="text-sm font-medium text-ink">Generated Preview</p>
              <div className="rounded-md border border-dashed border-line bg-[#f7fbfe] p-3 text-sm text-slate">
                Mock media assets prepared.
              </div>
              <p className="text-xs text-slate">Video: {reviewResult.result.videoUrl}</p>
              <p className="text-xs text-slate">GIF: {reviewResult.result.gifUrl}</p>
            </Card>
          </div>

          <Card className="space-y-2 p-3 shadow-none">
            <p className="text-sm font-medium text-ink">Extracted Summary</p>
            <p className="text-sm text-slate">{reviewResult.summary.scenario}</p>
            <ul className="list-disc pl-5 text-sm text-slate">
              {reviewResult.summary.givenInformation.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
            <p className="text-sm text-slate">{reviewResult.summary.studentTask}</p>
            <p className="text-sm text-slate">{reviewResult.validation.summary}</p>
          </Card>

          <div className="flex flex-wrap gap-3">
            <Button disabled={decisionLoading} onClick={() => void handleApprove()}>
              {decisionLoading ? 'Working...' : 'Approve'}
            </Button>
            <Button
              disabled={decisionLoading}
              onClick={() => void handleRegenerate()}
              variant="secondary"
            >
              Regenerate
            </Button>
            <Button
              disabled={decisionLoading}
              onClick={() => void handleDiscard()}
              variant="ghost"
            >
              Discard
            </Button>
          </div>

          {reviewResult.append.status === 'added' ? (
            <div className="flex flex-wrap items-center gap-3">
              <Button
                onClick={() => {
                  if (workspace) {
                    window.open(workspace.formRef.formEditUrl, '_blank', 'noopener,noreferrer')
                  }
                }}
                variant="secondary"
              >
                Open Form
              </Button>
              <Button onClick={() => void handleCopyResponderLink()} variant="secondary">
                Copy Responder Link
              </Button>
              {copyMessage ? <p className="text-sm text-accent">{copyMessage}</p> : null}
            </div>
          ) : null}
        </Card>
      ) : null}
    </section>
  )
}
