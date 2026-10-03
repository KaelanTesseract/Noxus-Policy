/**
 * Copyright (c) 2026 Dennis Guse
 * SPDX-License-Identifier: MIT
 * See the LICENSE file in the project root.
 */

const DAY_MS = 86_400_000;

/** Midnight of today in the local time zone. */
export function startOfToday(): Date {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}

/** Whole days from today until an ISO date (negative if it has passed). */
export function daysUntil(isoDate: string, from: Date = startOfToday()): number {
  const target = new Date(isoDate);
  target.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - from.getTime()) / DAY_MS);
}

/** "heute", "morgen", "in 12 Tagen", "in 5 Wochen", "in 4 Monaten". */
export function relativeDays(days: number): string {
  if (days < 0) return "abgelaufen";
  if (days === 0) return "heute";
  if (days === 1) return "morgen";
  if (days < 14) return `in ${days} Tagen`;
  if (days < 60) return `in ${Math.round(days / 7)} Wochen`;
  const months = Math.round(days / 30.4);
  return `in ${months} Monaten`;
}

export function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function formatEuro(value: number): string {
  return value.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";
}

/** A deadline is "soon" (worth the signal colour) within this many days. */
export const SOON_DAYS = 30;
