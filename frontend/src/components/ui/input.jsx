import { cn } from "@/lib/utils"

function Input({ className, ...props }) {
  return (
    <input
      data-slot="input"
      className={cn(
        "h-9 w-full min-w-0 rounded-md border border-input bg-sheet px-3 text-sm text-ink placeholder:text-slate/70",
        "outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}

function NativeSelect({ className, children, ...props }) {
  return (
    <select
      data-slot="select"
      className={cn(
        "h-9 rounded-md border border-input bg-sheet pl-3 pr-8 text-sm font-medium text-ink",
        "outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40 disabled:opacity-50",
        className
      )}
      {...props}
    >
      {children}
    </select>
  )
}

export { Input, NativeSelect }
