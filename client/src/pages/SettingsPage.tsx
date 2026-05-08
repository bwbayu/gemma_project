import { useEffect, useState } from 'react'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { mockService } from '../features/mock/service'
import type { GenerationJob, Workspace } from '../features/mock/types'

export function SettingsPage() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [activeJob, setActiveJob] = useState<GenerationJob | null>(null)
  const [loading, setLoading] = useState(true)

  async function refreshWorkspaceData(withLoader: boolean) {
    if (withLoader) {
      setLoading(true)
    }
    const [ws, job] = await Promise.all([
      mockService.getWorkspace(),
      mockService.getActiveJob(),
    ])
    setWorkspace(ws)
    setActiveJob(job)
    setLoading(false)
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refreshWorkspaceData(false)
    }, 0)

    return () => {
      window.clearTimeout(timer)
    }
  }, [])

  return (
    <section className="space-y-5">
      <header className="space-y-1">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Settings
        </h1>
        <p className="text-sm text-slate">
          Workspace and activity configuration view for frontend mock mode.
        </p>
      </header>

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
              <p className="text-sm font-medium text-ink">Latest Generation Job</p>
              <Badge tone={activeJob ? 'neutral' : 'success'}>
                {activeJob ? 'Running' : 'Idle'}
              </Badge>
            </div>
            <p className="mt-2 text-xs text-slate">
              {activeJob
                ? `${activeJob.stage} - ${activeJob.message}`
                : 'No active generation job at the moment.'}
            </p>
          </li>
        </ul>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="space-y-2">
          <p className="font-medium text-ink">Environment Summary</p>
          <ul className="space-y-1 text-sm text-slate">
            <li>Mode: FE-only mock</li>
            <li>Persistence: localStorage</li>
            <li>Workspace model: single active workspace</li>
            <li>Question history: persisted per active workspace context</li>
          </ul>
        </Card>
        <Card className="space-y-2">
          <p className="font-medium text-ink">Operator Actions</p>
          <ul className="space-y-1 text-sm text-slate">
            <li>Use Dashboard to create/open active workspace.</li>
            <li>Use Workspace for generation and review decisions.</li>
            <li>Use Help page for onboarding flow and examples.</li>
          </ul>
        </Card>
      </div>
    </section>
  )
}
