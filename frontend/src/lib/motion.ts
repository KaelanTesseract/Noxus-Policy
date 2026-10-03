/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

/** Which one-off animations already ran in this page load, so that navigating
 *  back to the dashboard does not replay them. */
export const introState = { timelinePlayed: false, countUpPlayed: false };

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
