/**
 * Copyright (c) 2026 Dennis Guse
 * SPDX-License-Identifier: MIT
 * See the LICENSE file in the project root.
 */

/** Which one-off animations already ran in this page load, so that navigating
 *  back to the dashboard does not replay them. */
export const introState = { timelinePlayed: false, countUpPlayed: false };

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
