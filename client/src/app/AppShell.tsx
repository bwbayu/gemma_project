import { BookOpen, LayoutDashboard, Settings } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { cn } from '../lib/cn'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/settings', label: 'Settings', icon: Settings, end: false },
  { to: '/help', label: 'Help', icon: BookOpen, end: false },
]

/** Top-level layout shell with a branded header, side navigation, and a main content outlet. */
export function AppShell() {
  return (
    <div className="flex min-h-screen flex-col bg-canvas text-ink">
      <header className="border-b border-line bg-panel/90 backdrop-blur">
        <div className="flex w-full items-center justify-between gap-3 px-4 py-3 sm:px-5 lg:px-6">
          <div>
            <p className="font-display text-lg font-semibold tracking-tight sm:text-xl">
              PhysicsAnimator Client
            </p>
            <p className="text-xs text-slate sm:text-sm">Animated Question Builder for Physics Teachers</p>
          </div>
        </div>
      </header>

      <div className="grid flex-1 grid-cols-1 gap-3 p-3 sm:p-4 lg:grid-cols-[220px_minmax(0,1fr)]">
        <nav className="rounded-xl border border-line bg-panel p-2 shadow-panel sm:p-3 lg:h-full">
          <ul className="flex gap-1 overflow-x-auto lg:block lg:space-y-1">
            {navItems.map(({ to, label, icon: Icon, end }) => (
              <li className="shrink-0 lg:shrink" key={to}>
                <NavLink
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-[#dff3ee] text-accent'
                        : 'text-slate hover:bg-[#e8edf2] hover:text-ink',
                    )
                  }
                  end={end}
                  to={to}
                >
                  <Icon size={16} />
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <main className="h-full min-h-0 rounded-xl border border-line bg-panel p-4 shadow-panel sm:p-5">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
