import { useEffect, useState } from 'react'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { ApiError } from '../features/api/http'
import { listWorkspaceQuestions } from '../features/api/questions'
import { getActiveWorkspace } from '../features/api/workspace'
import type { QuestionItem, Workspace } from '../features/types/types'

/** Settings page showing the active workspace and question activity stats, with a manual refresh button. */
export function SettingsPage() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [questions, setQuestions] = useState<QuestionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  /** Reload the active workspace and its questions; pass withLoader=true to show the loading state. */
  async function refreshWorkspaceData(withLoader: boolean) {
    if (withLoader) {
      setLoading(true)
    }
    setError('')
    try {
      const ws = await getActiveWorkspace()
      setWorkspace(ws)
      if (ws) {
        const list = await listWorkspaceQuestions(ws.workspaceId)
        setQuestions(list)
      } else {
        setQuestions([])
      }
    } catch (fetchError) {
      if (fetchError instanceof ApiError) {
        setError(fetchError.message)
      } else {
        setError('Could not load settings data from backend.')
      }
      setQuestions([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refreshWorkspaceData(false)
    }, 0)

    return () => {
      window.clearTimeout(timer)
    }
  }, [])

  const addedCount = questions.filter((item) => item.status === 'added').length
  const failedCount = questions.filter((item) => item.status === 'failed').length

  return (
    <section className="space-y-5">
      <header className="space-y-1">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Settings
        </h1>
        <p className="text-sm text-slate">
          Workspace and activity configuration view backed by server state.
        </p>
      </header>

      {error ? (
        <Card className="border-[#f2d5c8] bg-[#fff4ee] text-sm text-[#b44f2a]">
          {error}
        </Card>
      ) : null}

      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="font-medium text-ink">Current Session</p>
          <Button
            disabled={loading}
            onClick={() => void refreshWorkspaceData(true)}
            variant="secondary"
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>
        <ul className="space-y-3">
          <li className="rounded-md border border-line bg-white p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium text-ink">Active Workspace</p>
              <Badge tone={workspace ? 'success' : 'warning'}>
                {workspace ? 'Loaded' : 'None'}
              </Badge>
            </div>
            <p className="mt-2 text-xs text-slate">
              {workspace
                ? `${workspace.formRef.formTitle} (${workspace.formRef.formId})`
                : 'No active workspace. Open or create one from Dashboard.'}
            </p>
          </li>
          <li className="rounded-md border border-line bg-white p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium text-ink">Question Activity</p>
              <Badge tone={questions.length > 0 ? 'neutral' : 'success'}>
                {questions.length > 0 ? `${questions.length} items` : 'No items'}
              </Badge>
            </div>
            <p className="mt-2 text-xs text-slate">
              Added: {addedCount} | Failed: {failedCount}
            </p>
          </li>
        </ul>
      </Card>

      <Card className="space-y-2">
        <p className="font-medium text-ink">Operator Actions</p>
        <ul className="space-y-1 text-sm text-slate">
          <li>Use Dashboard to manage workspace and question flow.</li>
          <li>Use Help page for onboarding flow and examples.</li>
        </ul>
      </Card>
    </section>
  )
}
