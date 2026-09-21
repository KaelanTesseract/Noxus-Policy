/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { NextResponse } from "next/server";
import { GITHUB_REPO } from "@/lib/version";

// The footer's "new version available" hint used to call the GitHub API straight
// from every visitor's browser, which told GitHub each user's IP address and made
// a strict Content-Security-Policy impossible. The server asks instead - once an
// hour at most - and the browser only ever talks to its own origin.
const SUCCESS_TTL_MS = 60 * 60 * 1000;
const FAILURE_TTL_MS = 10 * 60 * 1000;

let cache: { at: number; ttl: number; tag: string | null } | null = null;

export async function GET() {
  if (cache && Date.now() - cache.at < cache.ttl) {
    return NextResponse.json({ tag_name: cache.tag });
  }

  let tag: string | null = null;
  try {
    const res = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/releases/latest`, {
      headers: { Accept: "application/vnd.github+json" },
      signal: AbortSignal.timeout(5000),
      cache: "no-store",
    });
    if (res.ok) {
      const data = await res.json();
      if (typeof data.tag_name === "string") tag = data.tag_name;
    }
  } catch (_) {
    // Offline installs simply get no update hint.
  }

  cache = { at: Date.now(), ttl: tag ? SUCCESS_TTL_MS : FAILURE_TTL_MS, tag };
  return NextResponse.json({ tag_name: tag });
}
