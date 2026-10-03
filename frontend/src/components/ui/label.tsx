"use client"

/**
 * Based on shadcn/ui (https://ui.shadcn.com), MIT License, Copyright (c) 2023 shadcn.
 * SPDX-License-Identifier: MIT
 * Full notice: THIRD_PARTY_NOTICES.md in the project root.
 */

import * as React from "react"

import { cn } from "@/lib/utils"

function Label({ className, ...props }: React.ComponentProps<"label">) {
  return (
    <label
      data-slot="label"
      className={cn(
        "flex items-center gap-2 text-sm leading-none font-medium select-none group-data-[disabled=true]:pointer-events-none group-data-[disabled=true]:opacity-50 peer-disabled:cursor-not-allowed peer-disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}

export { Label }
