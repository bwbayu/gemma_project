import type { PropsWithChildren } from 'react'
import { cn } from '../../lib/cn'

type CardProps = PropsWithChildren<{
  className?: string
}>

/** Rounded panel with a border and shadow, used as the primary content container. */
export function Card({ children, className }: CardProps) {
  return (
    <section
      className={cn(
        'rounded-xl border border-line bg-panel p-5 shadow-panel',
        className,
      )}
    >
      {children}
    </section>
  )
}
