import React from 'react'

export function LogField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-neutral-500 font-medium">{label}: </span>
      <span className="font-medium font-mono">{children}</span>
    </div>
  )
}
