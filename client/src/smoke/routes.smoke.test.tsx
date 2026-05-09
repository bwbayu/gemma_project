import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Navigate, RouterProvider, createMemoryRouter } from 'react-router-dom'
import { AppShell } from '../app/AppShell'
import { DashboardPage } from '../pages/DashboardPage'
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
          { path: 'workspace', element: <Navigate replace to="/" /> },
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

  it('renders workspace alias route', async () => {
    renderAt('/workspace')
    const headings = await screen.findAllByRole('heading', { name: 'Dashboard' })
    expect(headings.length).toBeGreaterThan(0)
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
