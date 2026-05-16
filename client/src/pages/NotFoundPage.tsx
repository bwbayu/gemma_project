import { Link } from 'react-router-dom'
import { Button } from '../components/ui/Button'

/** Fallback page displayed when a route does not match any defined path. */
export function NotFoundPage() {
  return (
    <section className="space-y-4">
      <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
        Page not found
      </h1>
      <p className="text-sm text-slate">
        The route does not exist in this app.
      </p>
      <Link to="/">
        <Button variant="secondary">Return to Dashboard</Button>
      </Link>
    </section>
  )
}
