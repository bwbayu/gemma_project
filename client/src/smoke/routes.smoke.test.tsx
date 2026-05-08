import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { AppShell } from '../app/AppShell'
import { DashboardPage } from '../pages/DashboardPage'
import { WorkspacePage } from '../pages/WorkspacePage'
import { SettingsPage } from '../pages/SettingsPage'
import { HelpPage } from '../pages/HelpPage'
import { NotFoundPage } from '../pages/NotFoundPage'

function renderAt(path: string) {
  const router = createMemoryRouter(
    [
      {
        path: '/',
        element: <AppShell />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: 'workspace', element: <WorkspacePage /> },
          { path: 'settings', element: <SettingsPage /> },
          { path: 'help', element: <HelpPage /> },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
    { initialEntries: [path] },
  )

  render(<RouterProvider router={router} />)
}

describe('app shell smoke', () => {
  it('renders shell and dashboard route', () => {
    renderAt('/')
    expect(screen.getByText('PhysicsAnimator Client')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('renders workspace route', async () => {
    renderAt('/workspace')
    expect(await screen.findByRole('heading', { name: 'Workspace' })).toBeInTheDocument()
  })

  it('renders settings route', () => {
    renderAt('/settings')
    expect(screen.getByRole('heading', { name: 'Settings' })).toBeInTheDocument()
  })

  it('renders help route', () => {
    renderAt('/help')
    expect(
      screen.getByRole('heading', { name: 'Help and Tutorial' }),
    ).toBeInTheDocument()
  })

  it('renders not found route fallback', () => {
    renderAt('/not-real-route')
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })
})
