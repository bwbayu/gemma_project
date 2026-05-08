import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from './AppShell'
import { DashboardPage } from '../pages/DashboardPage'
import { WorkspacePage } from '../pages/WorkspacePage'
import { SettingsPage } from '../pages/SettingsPage'
import { HelpPage } from '../pages/HelpPage'
import { NotFoundPage } from '../pages/NotFoundPage'

export const appRouter = createBrowserRouter([
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
])
