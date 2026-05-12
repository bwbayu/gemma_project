import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Badge } from '../components/ui/Badge'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { ApiError } from '../features/api/http'
import { getJob, isTerminalJob } from '../features/api/jobs'
import {
  createQuestionFromImage,
  createQuestionFromText,
  listWorkspaceQuestions,
} from '../features/api/questions'
import {
  approveQuestion,
  discardQuestion,
  getQuestionReview,
  regenerateQuestion,
} from '../features/api/review'
import type { FormLinks } from '../features/api/review'
import {
  createWorkspace as createWorkspaceApi,
  getActiveWorkspace,
} from '../features/api/workspace'
import type { GenerationJob, JobStage, QuestionItem, ReviewResult, Workspace } from '../features/mock/types'

/** Format an ISO timestamp into a locale-aware date/time string. */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
}

/** Map a question status to the corresponding Badge tone. */
function getStatusTone(status: QuestionItem['status']): 'neutral' | 'success' | 'warning' {
  if (status === 'added') {
    return 'success'
  }
  if (status === 'failed' || status === 'discarded') {
    return 'warning'
  }
  return 'neutral'
}

/** Convert a snake_case job stage identifier to a title-cased display label. */
function getStageLabel(stage: JobStage): string {
  return stage
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

/** Return a human-readable description of the question source (text excerpt or image filename). */
function getReviewSourceText(reviewResult: ReviewResult): string {
  if (reviewResult.source.inputType === 'text') {
    return reviewResult.source.text ?? ''
  }

  if (reviewResult.source.imageUrl) {
    return decodeURIComponent(reviewResult.source.imageUrl.split('/').pop() ?? 'Uploaded image')
  }

  return 'Uploaded image source'
}

/** Resolve a promise after the given number of milliseconds, used for polling delays. */
function wait(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

const POLL_INTERVAL_MS = 2000

/** Main teacher dashboard: workspace setup, question intake, job progress, and review/decision flow. */
export function DashboardPage() {
  const navigate = useNavigate()
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [questionItems, setQuestionItems] = useState<QuestionItem[]>([])
  const [activeJob, setActiveJob] = useState<GenerationJob | null>(null)
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null)
  const [approvedFormLinks, setApprovedFormLinks] = useState<FormLinks | null>(null)
  const [loading, setLoading] = useState(true)

  const [mode, setMode] = useState<'image' | 'text'>('image')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [textInput, setTextInput] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [decisionLoading, setDecisionLoading] = useState(false)

  const [createTitle, setCreateTitle] = useState('')
  const [createDescription, setCreateDescription] = useState('')
  const [createError, setCreateError] = useState('')
  const [submitError, setSubmitError] = useState('')
  const [submitSuccess, setSubmitSuccess] = useState('')
  const [loadError, setLoadError] = useState('')
  const [copyMessage, setCopyMessage] = useState('')
  const [loadingCreate, setLoadingCreate] = useState(false)

  const pollTokenRef = useRef(0)

  useEffect(() => {
    let mounted = true

    /** Load the active workspace and its questions on mount, setting load error on failure. */
    async function hydrateWorkspace() {
      try {
        const found = await getActiveWorkspace()
        if (!mounted) {
          return
        }
        setWorkspace(found)
        if (found) {
          const questions = await listWorkspaceQuestions(found.workspaceId)
          if (mounted) {
            setQuestionItems(questions)
          }
        } else {
          setQuestionItems([])
        }
      } catch (error) {
        if (!mounted) {
          return
        }
        if (error instanceof ApiError) {
          setLoadError(error.message)
        } else {
          setLoadError('Could not load workspace data from backend.')
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    void hydrateWorkspace()

    return () => {
      mounted = false
      pollTokenRef.current = 0
    }
  }, [])

  /** Re-fetch the question list for a workspace and update local state. */
  async function refreshQuestions(targetWorkspaceId: string): Promise<void> {
    const list = await listWorkspaceQuestions(targetWorkspaceId)
    setQuestionItems(list)
  }

  /** Poll the job endpoint until it reaches a terminal state, then refresh the question list. */
  async function trackJob(jobId: string, workspaceId: string): Promise<void> {
    const token = Date.now()
    pollTokenRef.current = token

    while (pollTokenRef.current === token) {
      const latest = await getJob(jobId)
      setActiveJob(latest)

      if (isTerminalJob(latest)) {
        await refreshQuestions(workspaceId)
        if (latest.status === 'failed' || latest.stage === 'failed') {
          setSubmitError(latest.message || 'Generation failed.')
        } else {
          setSubmitSuccess('Generation completed. Open review to inspect result.')
          window.location.reload()
        }
        return
      }

      await wait(POLL_INTERVAL_MS)
    }
  }

  /** Handle the create-workspace form submission, validating inputs before calling the API. */
  async function handleCreateWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setCreateError('')
    setLoadError('')

    const title = createTitle.trim()
    const description = createDescription.trim()

    if (!title) {
      setCreateError('Workspace title is required.')
      return
    }

    if (!description) {
      setCreateError('Workspace description is required.')
      return
    }

    setLoadingCreate(true)
    try {
      const workspace = await createWorkspaceApi(title, description)
      setWorkspace(workspace)
      await refreshQuestions(workspace.workspaceId)
      setCreateTitle('')
      setCreateDescription('')
      setSubmitSuccess('Workspace created and set as active.')
    } catch (error) {
      if (error instanceof ApiError) {
        setCreateError(error.message)
      } else {
        setCreateError('Could not create workspace. Try again.')
      }
    } finally {
      setLoadingCreate(false)
    }
  }

  /** Submit an image or text question and start tracking the resulting generation job. */
  async function handleStartGeneration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!workspace) {
      setSubmitError('Create a workspace before creating questions.')
      return
    }

    setSubmitError('')
    setSubmitSuccess('')
    setLoadError('')
    setCopyMessage('')
    setReviewResult(null)
    setApprovedFormLinks(null)
    setSubmitting(true)

    try {
      if (mode === 'image') {
        if (!selectedFile) {
          setSubmitError('Choose an image file first.')
          return
        }
        const result = await createQuestionFromImage(workspace.workspaceId, selectedFile)
        setQuestionItems((prev) => [result.question, ...prev])
        setActiveJob(result.job)
        setSelectedFile(null)
        setSubmitSuccess('Image question submitted. Tracking backend job...')
        await trackJob(result.job.jobId, workspace.workspaceId)
      } else {
        if (!textInput.trim()) {
          setSubmitError('Paste question text first.')
          return
        }
        const result = await createQuestionFromText(workspace.workspaceId, textInput.trim())
        setQuestionItems((prev) => [result.question, ...prev])
        setActiveJob(result.job)
        setTextInput('')
        setSubmitSuccess('Text question submitted. Tracking backend job...')
        await trackJob(result.job.jobId, workspace.workspaceId)
      }
    } catch (error) {
      if (error instanceof ApiError) {
        setSubmitError(error.message)
      } else {
        setSubmitError('Could not start generation. Try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  /** Load the review result for a specific question and display it in the review panel. */
  async function handleOpenReview(questionItemId: string): Promise<void> {
    setSubmitError('')
    setCopyMessage('')
    setApprovedFormLinks(null)
    try {
      const review = await getQuestionReview(questionItemId)
      setReviewResult(review)
      setSubmitSuccess('Review payload loaded.')
    } catch (error) {
      if (error instanceof ApiError && error.code === 'REVIEW_NOT_READY') {
        setSubmitSuccess('Review is still generating. Please check again shortly.')
      } else if (error instanceof ApiError) {
        setSubmitError(error.message)
      } else {
        setSubmitError('Could not fetch review payload.')
      }
    }
  }

  /** Approve the current review result, appending the animation to the Google Form. */
  async function handleApprove(): Promise<void> {
    if (!reviewResult || !workspace) {
      return
    }
    setDecisionLoading(true)
    setSubmitError('')
    setSubmitSuccess('')
    setCopyMessage('')
    try {
      const response = await approveQuestion(reviewResult.questionItemId)
      setReviewResult(response.review)
      setApprovedFormLinks(response.formLinks)
      await refreshQuestions(workspace.workspaceId)
      if (response.review.append.status === 'added') {
        setSubmitSuccess('Question approved and appended to form.')
      } else {
        setSubmitError(response.review.append.errorMessage || 'Approve completed with append error.')
      }
    } catch (error) {
      if (error instanceof ApiError) {
        setSubmitError(error.message)
      } else {
        setSubmitError('Could not approve question.')
      }
    } finally {
      setDecisionLoading(false)
    }
  }

  /** Trigger a new generation job for the current question and begin tracking it. */
  async function handleRegenerate(): Promise<void> {
    if (!reviewResult || !workspace) {
      return
    }
    setDecisionLoading(true)
    setSubmitError('')
    setSubmitSuccess('')
    setCopyMessage('')
    setApprovedFormLinks(null)
    try {
      const response = await regenerateQuestion(reviewResult.questionItemId)
      await refreshQuestions(workspace.workspaceId)
      setReviewResult(null)
      if (response.job) {
        setActiveJob(response.job)
        setSubmitSuccess('Regeneration started. Tracking backend job...')
        await trackJob(response.job.jobId, workspace.workspaceId)
      } else {
        setSubmitSuccess('Regeneration requested.')
      }
    } catch (error) {
      if (error instanceof ApiError) {
        setSubmitError(error.message)
      } else {
        setSubmitError('Could not regenerate question.')
      }
    } finally {
      setDecisionLoading(false)
    }
  }

  /** Discard the current review result and remove the question from the active list. */
  async function handleDiscard(): Promise<void> {
    if (!reviewResult || !workspace) {
      return
    }
    setDecisionLoading(true)
    setSubmitError('')
    setSubmitSuccess('')
    setCopyMessage('')
    setApprovedFormLinks(null)
    try {
      await discardQuestion(reviewResult.questionItemId)
      await refreshQuestions(workspace.workspaceId)
      setReviewResult(null)
      setSubmitSuccess('Question discarded.')
    } catch (error) {
      if (error instanceof ApiError) {
        setSubmitError(error.message)
      } else {
        setSubmitError('Could not discard question.')
      }
    } finally {
      setDecisionLoading(false)
    }
  }

  /** Copy the form responder URL to the clipboard, preferring the latest approved link. */
  async function handleCopyResponderLink(): Promise<void> {
    const responderUrl = approvedFormLinks?.formResponderUrl || workspace?.formRef.formResponderUrl
    if (!responderUrl) {
      return
    }

    try {
      await navigator.clipboard.writeText(responderUrl)
      setCopyMessage('Responder link copied to clipboard.')
    } catch {
      setCopyMessage('Clipboard unavailable. Copy manually from form link.')
    }
  }

  /** Open the Google Form editor in a new tab, preferring the latest approved link. */
  function openFormLink(): void {
    const editUrl = approvedFormLinks?.formEditUrl || workspace?.formRef.formEditUrl
    if (!editUrl) {
      return
    }
    window.open(editUrl, '_blank', 'noopener,noreferrer')
  }

  const editFormUrl = approvedFormLinks?.formEditUrl || workspace?.formRef.formEditUrl || ''
  const responderFormUrl =
    approvedFormLinks?.formResponderUrl || workspace?.formRef.formResponderUrl || ''

  return (
    <section className="space-y-5">
      <header className="space-y-1">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Dashboard
        </h1>
        <p className="text-sm text-slate">
          Backend-integrated workspace, intake, progress tracking, review, and decision flow.
        </p>
      </header>

      {loadError ? (
        <Card className="border-[#f2d5c8] bg-[#fff4ee] text-sm text-[#b44f2a]">
          {loadError}
        </Card>
      ) : null}

      {submitSuccess ? (
        <Card className="border-[#b9e5da] bg-[#eef9f5] text-sm text-accent">
          {submitSuccess}
        </Card>
      ) : null}

      <Card className="space-y-3">
        <p className="font-medium text-ink">Create New Form Workspace</p>
        <form className="grid gap-3 md:grid-cols-2" onSubmit={(event) => void handleCreateWorkspace(event)}>
          <label className="space-y-1 text-sm">
            <span className="text-slate">Form title</span>
            <Input
              onChange={(event) => {
                setCreateTitle(event.target.value)
                if (createError) {
                  setCreateError('')
                }
              }}
              placeholder="e.g. Newton Law Quiz"
              value={createTitle}
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-slate">Form description</span>
            <Input
              onChange={(event) => {
                setCreateDescription(event.target.value)
                if (createError) {
                  setCreateError('')
                }
              }}
              placeholder="e.g. Grade 10 motion topics"
              value={createDescription}
            />
          </label>
          <div className="md:col-span-2">
            {createError ? <p className="mb-2 text-sm text-[#b44f2a]">{createError}</p> : null}
            <div className="flex flex-wrap gap-3">
              <Button disabled={loadingCreate} type="submit">
                {loadingCreate ? 'Creating...' : 'Create New Form Workspace'}
              </Button>
              <Button onClick={() => navigate('/help')} type="button" variant="ghost">
                View Tutorial
              </Button>
            </div>
          </div>
        </form>
      </Card>

      <Card className="flex items-center justify-between">
        <div>
          {loading ? (
            <>
              <p className="font-medium text-ink">Loading workspace...</p>
              <p className="text-sm text-slate">Checking backend active workspace.</p>
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
                Create a new workspace from the panel above before submitting questions.
              </p>
            </>
          )}
        </div>
        <Badge tone={workspace ? 'success' : 'warning'}>
          {workspace ? 'Workspace Active' : 'No Active Form'}
        </Badge>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="space-y-3">
          <p className="font-medium text-ink">Question List</p>
          {questionItems.length === 0 ? (
            <p className="text-sm text-slate">
              No questions yet. Submit your first image/text question from the right panel.
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
            Generation typically takes around 4-5 minutes per question.
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

            <Button disabled={submitting || !workspace} type="submit" variant="secondary">
              {submitting ? 'Submitting...' : 'Start Generation'}
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
          {activeJob.status ? (
            <p className="text-xs text-slate">Status: {activeJob.status}</p>
          ) : null}
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
                reviewResult.source.imageUrl ? (
                  <img
                    alt="Question source"
                    className="max-h-80 w-full rounded-md border border-line bg-white object-contain"
                    src={reviewResult.source.imageUrl}
                  />
                ) : (
                  <div className="rounded-md border border-dashed border-line bg-[#faf8f4] p-3 text-sm text-slate">
                    Source image unavailable.
                  </div>
                )
              )}
            </Card>

            <Card className="space-y-2 p-3 shadow-none">
              <p className="text-sm font-medium text-ink">Generated Preview</p>
              {reviewResult.result.videoUrl ? (
                <video
                  className="max-h-80 w-full rounded-md border border-line bg-black object-contain"
                  controls
                  playsInline
                  preload="metadata"
                  src={reviewResult.result.videoUrl}
                />
              ) : reviewResult.result.gifUrl ? (
                <img
                  alt="Generated animation preview"
                  className="max-h-80 w-full rounded-md border border-line bg-white object-contain"
                  src={reviewResult.result.gifUrl}
                />
              ) : (
                <div className="rounded-md border border-dashed border-line bg-[#f7fbfe] p-3 text-sm text-slate">
                  No preview media URL available.
                </div>
              )}
              {reviewResult.result.videoUrl ? (
                <a
                  className="text-xs text-accent underline"
                  href={reviewResult.result.videoUrl}
                  rel="noreferrer"
                  target="_blank"
                >
                  Open video in new tab
                </a>
              ) : null}
            </Card>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3">
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

            <div className="flex flex-wrap items-center gap-3">
              <Button
                disabled={decisionLoading || !editFormUrl}
                onClick={openFormLink}
                variant="secondary"
              >
                Open Form
              </Button>
              <Button
                disabled={decisionLoading || !responderFormUrl}
                onClick={() => void handleCopyResponderLink()}
                variant="secondary"
              >
                Copy Responder Link
              </Button>
            </div>
          </div>

          {/* <p className="text-sm text-slate">{reviewResult.validation.summary}</p> */}
          {reviewResult.append.status === 'error' && reviewResult.append.errorMessage ? (
            <p className="text-sm text-[#b44f2a]">Append error: {reviewResult.append.errorMessage}</p>
          ) : null}
          {copyMessage ? <p className="text-sm text-accent">{copyMessage}</p> : null}
        </Card>
      ) : null}
    </section>
  )
}
