import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { mockService } from '../features/mock/service'
import { normalizeGoogleFormRef, isValidGoogleFormRef } from '../features/mock/validation'
import type { Workspace } from '../features/mock/types'

export function DashboardPage() {
  const navigate = useNavigate()
  const [createTitle, setCreateTitle] = useState('')
  const [createDescription, setCreateDescription] = useState('')
  const [formRefInput, setFormRefInput] = useState('')
  const [createError, setCreateError] = useState('')
  const [openError, setOpenError] = useState('')
  const [loadingCreate, setLoadingCreate] = useState(false)
  const [loadingOpen, setLoadingOpen] = useState(false)
  const [hydrating, setHydrating] = useState(true)
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null)
  const [statusMessage, setStatusMessage] = useState('')

  useEffect(() => {
    let mounted = true

    async function hydrateWorkspace() {
      const workspace = await mockService.getWorkspace()
      if (mounted) {
        setActiveWorkspace(workspace)
        setHydrating(false)
      }
    }

    void hydrateWorkspace()

    return () => {
      mounted = false
    }
  }, [])

  async function handleCreateWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setCreateError('')
    setStatusMessage('')

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
      const workspace = await mockService.createWorkspace(title, description)
      setActiveWorkspace(workspace)
      setStatusMessage('Workspace created. Redirecting to workspace page.')
      navigate('/workspace')
    } catch {
      setCreateError('Could not create workspace. Try again.')
    } finally {
      setLoadingCreate(false)
    }
  }

  async function handleOpenWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setOpenError('')
    setStatusMessage('')

    if (!isValidGoogleFormRef(formRefInput)) {
      setOpenError('Enter a valid Google Form URL or Form ID.')
      return
    }

    setLoadingOpen(true)
    try {
      const normalized = normalizeGoogleFormRef(formRefInput)
      const workspace = await mockService.openWorkspaceByRef(normalized)
      setActiveWorkspace(workspace)
      setStatusMessage('Workspace loaded. Redirecting to workspace page.')
      navigate('/workspace')
    } catch {
      setOpenError('Could not open workspace from this reference.')
    } finally {
      setLoadingOpen(false)
    }
  }

  return (
    <section className="space-y-5">
      <header className="space-y-1">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Dashboard
        </h1>
        <p className="max-w-2xl text-sm text-slate">
          Create a new form workspace or open an existing one. This UI currently
          uses mock persistence and no backend integration.
        </p>
      </header>

      {statusMessage ? (
        <Card className="border-[#b9e5da] bg-[#eef9f5] text-sm text-accent">
          {statusMessage}
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="font-medium text-ink">Readiness</p>
            <Badge tone="success">Mocked Ready</Badge>
          </div>
          <ul className="space-y-2 text-sm text-slate">
            <li>Google credentials: available (simulated)</li>
            <li>Token session: available (simulated)</li>
            <li>Backend availability: intentionally disconnected</li>
          </ul>
          <p className="text-xs text-slate">
            {hydrating
              ? 'Checking active workspace...'
              : activeWorkspace
                ? `Active workspace: ${activeWorkspace.formRef.formTitle}`
                : 'No active workspace in local storage.'}
          </p>
        </Card>

        <Card className="space-y-3">
          <p className="font-medium text-ink">Open Existing Form Workspace</p>
          <form className="space-y-3" onSubmit={(event) => void handleOpenWorkspace(event)}>
            <Input
              aria-label="Google form URL or ID"
              onChange={(event) => {
                setFormRefInput(event.target.value)
                if (openError) {
                  setOpenError('')
                }
              }}
              placeholder="Paste Google Form URL or Form ID"
              value={formRefInput}
            />
            {openError ? <p className="text-sm text-[#b44f2a]">{openError}</p> : null}
            <Button disabled={loadingOpen} variant="secondary">
              {loadingOpen ? 'Opening...' : 'Open Workspace'}
            </Button>
          </form>
        </Card>
      </div>

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
              <Button
                disabled={!activeWorkspace || hydrating}
                onClick={() => {
                  if (activeWorkspace) {
                    navigate('/workspace')
                  }
                }}
                type="button"
                variant="secondary"
              >
                Use Active Workspace
              </Button>
              <Button onClick={() => navigate('/help')} type="button" variant="ghost">
                View Tutorial
              </Button>
            </div>
          </div>
        </form>
      </Card>
    </section>
  )
}
