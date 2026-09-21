/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { NextRequest, NextResponse } from "next/server";

// Insurer logos used to be loaded by every user's browser straight from Google's
// favicon service, which told Google each user's IP address together with the
// insurers they have contracts with (and forced img-src to allow Google).
// The server fetches them instead - Google only ever sees this server and a
// company domain - and keeps them in a small in-memory cache.
// Set DISABLE_LOGO_LOOKUP=true to make no external request at all (initials only).

const SESSION_COOKIE = "noxus_session";
const DOMAIN_PATTERN = /^(?=.{4,100}$)[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$/;
const ALLOWED_TYPES = ["image/png", "image/jpeg", "image/gif", "image/webp", "image/x-icon", "image/vnd.microsoft.icon"];
const MAX_BYTES = 100 * 1024;
const HIT_TTL_MS = 7 * 24 * 60 * 60 * 1000;
const MISS_TTL_MS = 24 * 60 * 60 * 1000;
const MAX_ENTRIES = 500;

type Entry = { at: number; hit: boolean; type: string; body: Uint8Array | null };
const cache = new Map<string, Entry>();

function remember(domain: string, entry: Entry) {
  if (cache.size >= MAX_ENTRIES) {
    const oldest = cache.keys().next().value;
    if (oldest !== undefined) cache.delete(oldest);
  }
  cache.set(domain, entry);
}

function image(entry: Entry) {
  if (!entry.hit || !entry.body) return new NextResponse(null, { status: 404, headers: { "cache-control": "private, max-age=3600" } });
  return new NextResponse(new Uint8Array(entry.body), {
    status: 200,
    headers: { "content-type": entry.type, "cache-control": "private, max-age=604800" },
  });
}

export async function GET(request: NextRequest) {
  if (!request.cookies.get(SESSION_COOKIE)?.value) {
    return NextResponse.json({ detail: "Nicht angemeldet." }, { status: 401 });
  }
  if (process.env.DISABLE_LOGO_LOOKUP === "true") {
    return new NextResponse(null, { status: 404 });
  }

  const domain = (request.nextUrl.searchParams.get("domain") || "").toLowerCase();
  if (!DOMAIN_PATTERN.test(domain)) {
    return NextResponse.json({ detail: "Ungültige Domain." }, { status: 400 });
  }

  const cached = cache.get(domain);
  if (cached && Date.now() - cached.at < (cached.hit ? HIT_TTL_MS : MISS_TTL_MS)) {
    return image(cached);
  }

  let entry: Entry = { at: Date.now(), hit: false, type: "", body: null };
  try {
    // The host is fixed and the domain is validated above, so this can't be pointed at internal addresses.
    const res = await fetch(`https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=128`, {
      signal: AbortSignal.timeout(5000),
      cache: "no-store",
      redirect: "follow",
    });
    const type = (res.headers.get("content-type") || "").split(";")[0].trim().toLowerCase();
    if (res.ok && ALLOWED_TYPES.includes(type)) {
      const body = new Uint8Array(await res.arrayBuffer());
      if (body.byteLength > 0 && body.byteLength <= MAX_BYTES) {
        entry = { at: Date.now(), hit: true, type, body };
      }
    }
  } catch (_) {
    // Offline or blocked: fall back to initials on the client, retry after the miss TTL.
  }
  remember(domain, entry);
  return image(entry);
}
