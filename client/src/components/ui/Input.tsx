import type { InputHTMLAttributes } from 'react'
import { cn } from '../../lib/cn'

type InputProps = InputHTMLAttributes<HTMLInputElement>

/** Styled text input that forwards all native input attributes and merges className. */
export function Input({ className, ...props }: InputProps) {
  return (
    <input
      className={cn(
        'w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink placeholder:text-slate',
        'focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ink/10',
        className,
      )}
      {...props}
    />
  )
}
