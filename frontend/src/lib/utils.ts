/**
 * Copyright (c) 2026 Dennis Guse
 * SPDX-License-Identifier: MIT
 * See the LICENSE file in the project root.
 */

import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
