import type { PropsWithChildren } from 'react'
import { cn } from '../../lib/cn'

type BadgeTone = 'neutral' | 'success' | 'warning'

type BadgeProps = PropsWithChildren<{
  tone?: BadgeTone
  className?: string
}>

const toneStyles: Record<BadgeTone, string> = {
  neutral: 'bg-[#e8edf2] text-[#35516f]',
  success: 'bg-[#dcf3ee] text-[#0f624f]',
  warning: 'bg-[#fcead8] text-[#875020]',
}

export function Badge({ children, className, tone = 'neutral' }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium',
        toneStyles[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}
