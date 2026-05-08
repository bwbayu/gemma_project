import { Card } from '../components/ui/Card'

const quickStart = [
  'Open Dashboard and create or load one active workspace.',
  'Go to Workspace and submit image/text question input.',
  'Follow generation progress until review payload appears.',
  'Decide: approve, regenerate, or discard.',
  'After approve, open form or copy responder link.',
]

const promptTips = [
  'Keep question text concise and include all known values.',
  'For image inputs, use high-contrast screenshots with visible labels.',
  'Avoid including worked solutions in the source prompt.',
]

const samplePrompts = [
  'A 2 kg block rests on a 30-degree incline with friction coefficient 0.2. Determine acceleration when released.',
  'Two masses connected by a rope over a pulley, m1 = 3 kg and m2 = 5 kg. Determine direction of motion and acceleration.',
]

export function HelpPage() {
  return (
    <section className="space-y-5">
      <header className="space-y-1">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Help and Tutorial
        </h1>
        <p className="text-sm text-slate">
          Fast onboarding for teacher workflow in the FE-only mock system.
        </p>
      </header>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="space-y-3">
          <p className="font-medium text-ink">Quick Start</p>
          <ol className="list-decimal space-y-1 pl-5 text-sm text-slate">
            {quickStart.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </Card>

        <Card className="space-y-3">
          <p className="font-medium text-ink">Input Quality Tips</p>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate">
            {promptTips.map((tip) => (
              <li key={tip}>{tip}</li>
            ))}
          </ul>
        </Card>
      </div>

      <Card className="space-y-3">
        <p className="font-medium text-ink">Sample Prompt Ideas</p>
        <ul className="space-y-2 text-sm text-slate">
          {samplePrompts.map((prompt) => (
            <li className="rounded-md border border-line bg-white p-3" key={prompt}>
              {prompt}
            </li>
          ))}
        </ul>
      </Card>

      <Card className="space-y-2 text-sm text-slate">
        <p className="font-medium text-ink">Mock Mode Note</p>
        <p>
          This frontend currently uses local mock data and localStorage persistence.
          The Google Form links and animation assets are placeholders for FE flow validation.
        </p>
      </Card>
    </section>
  )
}
