import type { ButtonHTMLAttributes, PropsWithChildren } from 'react'
import { cn } from '../../lib/cn'

type ButtonVariant = 'primary' | 'secondary' | 'ghost'

type ButtonProps = PropsWithChildren<
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: ButtonVariant
  }
>

const styles: Record<ButtonVariant, string> = {
  primary:
    'bg-accent text-white hover:bg-[#0f564a] focus-visible:ring-accent/35',
  secondary:
    'bg-panel text-ink border border-line hover:bg-[#f4f6f8] focus-visible:ring-ink/15',
  ghost:
    'bg-transparent text-slate hover:bg-[#e9eff4] focus-visible:ring-ink/15',
}

/** Themed button supporting primary (filled), secondary (outlined), and ghost (transparent) variants. */
export function Button({
  children,
  className,
  variant = 'primary',
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-4 disabled:cursor-not-allowed disabled:opacity-60',
        styles[variant],
        className,
      )}
      type={type}
      {...props}
    >
      {children}
    </button>
  )
}
