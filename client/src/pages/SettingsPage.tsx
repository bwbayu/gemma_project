import { useEffect, useState } from 'react'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { mockService } from '../features/mock/service'
import type { GenerationJob, Workspace } from '../features/mock/types'

type ReadinessItem = {
  label: string
  value: string
  tone: 'neutral' | 'success' | 'warning'
  guidance: string
}

function buildReadiness(
  workspace: Workspace | null,
  job: GenerationJob | null,
): ReadinessItem[] {
  return [
    {
      label: 'Google Credentials',
      value: 'Available (mock)',
      tone: 'success',
      guidance: 'In production this comes from secure runtime configuration.',
    },
    {
      label: 'Token Session',
      value: 'Available (mock)',
      tone: 'success',
      guidance: 'In production this must be refreshed and validated at startup.',
    },
    {
      label: 'Workspace State',
      value: workspace ? 'Active workspace loaded' : 'No active workspace',
      tone: workspace ? 'success' : 'warning',
      guidance: workspace
        ? 'You can continue generating in the active workspace.'
        : 'Go to Dashboard and create/open a workspace first.',
    },
    {
      label: 'Generation Pipeline',
      value: job ? `Running step: ${job.stage}` : 'Idle',
      tone: job ? 'neutral' : 'success',
      guidance: job
        ? 'Wait until review is ready, then decide approve/regenerate/discard.'
        : 'No active generation job.',
    },
  ]
}

export function SettingsPage() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [activeJob, setActiveJob] = useState<GenerationJob | null>(null)
  const [loading, setLoading] = useState(true)

  async function refreshReadiness(withLoader: boolean) {
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
      void refreshReadiness(false)
    }, 0)

    return () => {
      window.clearTimeout(timer)
    }
  }, [])

  const readiness = buildReadiness(workspace, activeJob)

  return (
    <section className="space-y-5">
      <header className="space-y-1">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Settings
        </h1>
        <p className="text-sm text-slate">
          Operational readiness panel for the FE-only mock environment.
        </p>
      </header>

      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="font-medium text-ink">Readiness Diagnostics</p>
          <Button
            disabled={loading}
            onClick={() => void refreshReadiness(true)}
            variant="secondary"
          >
            {loading ? 'Refreshing...' : 'Refresh Status'}
          </Button>
        </div>
        <ul className="space-y-3">
          {readiness.map((item) => (
            <li className="rounded-md border border-line bg-white p-3" key={item.label}>
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-ink">{item.label}</p>
                <Badge tone={item.tone}>{item.value}</Badge>
              </div>
              <p className="mt-2 text-xs text-slate">{item.guidance}</p>
            </li>
          ))}
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
