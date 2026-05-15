import * as RadixSelect from '@radix-ui/react-select'
import { Check, ChevronDown } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

type SelectOption = {
  value: string
  label: ReactNode
  disabled?: boolean
}

type SelectProps = {
  value: string | undefined
  onValueChange: (value: string) => void
  options: SelectOption[]
  placeholder?: string
  disabled?: boolean
  className?: string
  ariaLabel?: string
}

/** Styled select built on Radix Select, matching the house Input look (border-line, ring-ink/10). */
export function Select({
  value,
  onValueChange,
  options,
  placeholder,
  disabled,
  className,
  ariaLabel,
}: SelectProps) {
  return (
    <RadixSelect.Root
      disabled={disabled}
      onValueChange={onValueChange}
      value={value ?? undefined}
    >
      <RadixSelect.Trigger
        aria-label={ariaLabel}
        className={cn(
          'inline-flex w-full items-center justify-between gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm text-ink',
          'focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ink/10',
          'data-[placeholder]:text-slate disabled:cursor-not-allowed disabled:opacity-60',
          className,
        )}
      >
        <RadixSelect.Value placeholder={placeholder} />
        <RadixSelect.Icon className="text-slate">
          <ChevronDown className="h-4 w-4" />
        </RadixSelect.Icon>
      </RadixSelect.Trigger>
      <RadixSelect.Portal>
        <RadixSelect.Content
          className="z-50 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-md border border-line bg-white text-sm text-ink shadow-panel"
          position="popper"
          sideOffset={4}
        >
          <RadixSelect.Viewport className="p-1">
            {options.map((option) => (
              <RadixSelect.Item
                className={cn(
                  'relative flex cursor-pointer select-none items-center rounded-md py-2 pl-8 pr-3 outline-none',
                  'data-[highlighted]:bg-[#edf6f3] data-[highlighted]:text-accent',
                  'data-[state=checked]:font-medium',
                  'data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50',
                )}
                disabled={option.disabled}
                key={option.value}
                value={option.value}
              >
                <RadixSelect.ItemIndicator className="absolute left-2 inline-flex items-center">
                  <Check className="h-4 w-4 text-accent" />
                </RadixSelect.ItemIndicator>
                <RadixSelect.ItemText>{option.label}</RadixSelect.ItemText>
              </RadixSelect.Item>
            ))}
          </RadixSelect.Viewport>
        </RadixSelect.Content>
      </RadixSelect.Portal>
    </RadixSelect.Root>
  )
}
