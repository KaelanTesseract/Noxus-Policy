/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 *
 * Client-side session bookkeeping. The login token itself is NOT stored here:
 * the Next.js proxy (app/api/[...path]/route.ts) keeps it in an httpOnly cookie
 * that page scripts cannot read, so an XSS bug can no longer just copy it out
 * of localStorage. All that lives in the browser is a harmless "was signed in"
 * hint (to tell "never logged in" from "session expired") and the personal-data
 * caches used for instant page rendering, which must be wiped on sign-out.
 */

const SESSION_HINT_KEY = "noxus_signed_in";
const CACHE_PREFIX = "cache_";

export function markSignedIn() {
  try {
    localStorage.setItem(SESSION_HINT_KEY, "1");
  } catch (_) {}
}

export function hasSessionHint(): boolean {
  try {
    return typeof window !== "undefined" && localStorage.getItem(SESSION_HINT_KEY) === "1";
  } catch (_) {
    return false;
  }
}

/** Removes everything session-related from this browser (hint, legacy token, cached personal data). */
export function clearSession() {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(SESSION_HINT_KEY);
    // Tokens used to be kept here before they moved into an httpOnly cookie.
    localStorage.removeItem("token");
  } catch (_) {}
  try {
    const stale: string[] = [];
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i);
      if (key && key.startsWith(CACHE_PREFIX)) stale.push(key);
    }
    stale.forEach((key) => sessionStorage.removeItem(key));
  } catch (_) {}
}

/** Ends the session on the server (revokes every token of this account), then wipes local state. */
export async function logout() {
  try {
    await fetch("/api/users/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
  } catch (_) {}
  clearSession();
  window.location.href = "/login";
}
