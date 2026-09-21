/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 300; // 5 minutes max execution time for AI processing

// The login token never reaches page scripts: on login this proxy moves it out of
// the response body into an httpOnly cookie, and on every request it turns that
// cookie back into the Authorization header the backend expects. That way an XSS
// bug can make requests as the user but can no longer copy the token itself.
const SESSION_COOKIE = "noxus_session";

// The backend only listens on loopback (see docker-compose.yml), so it is never
// reachable from the LAN directly - every request has to come through this proxy.
// docker-compose sets BACKEND_URL; the rest are fallbacks for other setups (a
// bridge network where the service is called "backend", or plain local dev).
const BACKEND_URLS = [
  ...(process.env.BACKEND_URL ? [process.env.BACKEND_URL] : []),
  "http://127.0.0.1:8000",
  "http://localhost:8000",
  "http://backend:8000"
];

// Request-body limits, mirroring backend/request_limits.py. The proxy has to buffer
// the body (it may retry against another backend address), so without a cap a single
// oversized request could exhaust this container's memory.
const MB = 1024 * 1024;
const MAX_UPLOAD_BODY = 16 * MB;
const MAX_BACKUP_BODY = 512 * MB;
const MAX_DEFAULT_BODY = 2 * MB;
const UPLOAD_PATHS = ["/api/documents", "/api/documents/extract", "/api/inbox/upload"];
const BACKUP_PATHS = ["/api/backup/import", "/api/backup/import-user"];

function bodyLimitFor(method: string, pathname: string): number {
  if (method === "POST") {
    const path = pathname.replace(/\/+$/, "");
    if (BACKUP_PATHS.includes(path)) return MAX_BACKUP_BODY;
    if (UPLOAD_PATHS.includes(path)) return MAX_UPLOAD_BODY;
  }
  return MAX_DEFAULT_BODY;
}

// Reads the request body but gives up (returns null) as soon as it grows past the
// limit, so a chunked upload without a Content-Length can't slip through either.
async function readBodyLimited(request: NextRequest, limit: number): Promise<ArrayBuffer | null> {
  const declared = Number(request.headers.get("content-length"));
  if (Number.isFinite(declared) && declared > limit) return null;
  if (!request.body) return new ArrayBuffer(0);

  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let received = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    received += value.byteLength;
    if (received > limit) {
      await reader.cancel().catch(() => {});
      return null;
    }
    chunks.push(value);
  }
  const merged = Buffer.concat(chunks);
  return merged.buffer.slice(merged.byteOffset, merged.byteOffset + merged.byteLength) as ArrayBuffer;
}

// Only these request headers are handed to the backend. Everything else a client
// sends (its own Authorization header, hop-by-hop headers, cookies, arbitrary
// X-* headers) stops here: the backend's authentication must only ever see the
// token this proxy derives from the httpOnly session cookie.
const FORWARDED_REQUEST_HEADERS = [
  "accept",
  "accept-language",
  "content-type",
  "user-agent",
  "range",
  "if-range",
  "if-none-match",
  "if-modified-since",
  "x-forwarded-for",
];

function tokenMaxAgeSeconds(token: string): number | undefined {
  try {
    const payload = JSON.parse(Buffer.from(token.split(".")[1], "base64url").toString("utf8"));
    if (typeof payload.exp === "number") {
      return Math.max(1, Math.floor(payload.exp - Date.now() / 1000));
    }
  } catch (_) {}
  return undefined;
}

function isSecureRequest(request: NextRequest): boolean {
  return request.nextUrl.protocol === "https:" || request.headers.get("x-forwarded-proto") === "https";
}

async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const search = request.nextUrl.search;
  const method = request.method;
  const isStateChanging = method !== "GET" && method !== "HEAD";

  // Defence in depth on top of the SameSite=Strict cookie: browsers label every
  // request with where it came from, so refuse state-changing calls that another
  // site (or a sibling subdomain) triggered.
  if (isStateChanging) {
    const site = request.headers.get("sec-fetch-site");
    if (site && site !== "same-origin" && site !== "none") {
      return NextResponse.json({ detail: "Anfrage von fremder Herkunft abgelehnt." }, { status: 403 });
    }
  }

  let body: ArrayBuffer | undefined;
  if (isStateChanging) {
    const limited = await readBodyLimited(request, bodyLimitFor(method, pathname));
    if (limited === null) {
      return NextResponse.json({ detail: "Die Anfrage ist zu groß." }, { status: 413 });
    }
    body = limited;
  }
  const sessionToken = request.cookies.get(SESSION_COOKIE)?.value;
  const secure = isSecureRequest(request);
  const isLogin = method === "POST" && pathname === "/api/users/login";
  const isLogout = method === "POST" && pathname === "/api/users/logout";

  const attempted: string[] = [];

  // Retry loop: Try up to 3 cycles with 1-second pause if backend is still booting
  for (let attempt = 0; attempt < 3; attempt++) {
    for (const baseUrl of BACKEND_URLS) {
      const targetUrl = `${baseUrl}${pathname}${search}`;
      const headers = new Headers();
      for (const name of FORWARDED_REQUEST_HEADERS) {
        const value = request.headers.get(name);
        if (value !== null) headers.set(name, value);
      }
      if (sessionToken) {
        headers.set("authorization", `Bearer ${sessionToken}`);
      }

      try {
        const res = await fetch(targetUrl, {
          method,
          headers: headers,
          body: body,
          redirect: "manual",
          signal: AbortSignal.timeout(180000)
        });

        const resHeaders = new Headers(res.headers);
        resHeaders.delete("server");
        // Set by the backend when it just invalidated the caller's token (password or
        // email change) and issued a replacement - stays server-side, never sent on.
        const refreshedToken = resHeaders.get("x-refreshed-token");
        resHeaders.delete("x-refreshed-token");

        let newToken: string | undefined = refreshedToken || undefined;
        let response: NextResponse;

        if (isLogin && res.ok) {
          const data = await res.json();
          newToken = data.access_token;
          delete data.access_token;
          resHeaders.delete("content-length");
          resHeaders.delete("content-encoding");
          resHeaders.set("content-type", "application/json");
          response = new NextResponse(JSON.stringify(data), {
            status: res.status,
            statusText: res.statusText,
            headers: resHeaders,
          });
        } else {
          response = new NextResponse(res.body, {
            status: res.status,
            statusText: res.statusText,
            headers: resHeaders,
          });
        }

        const cookieOptions = { httpOnly: true, sameSite: "strict" as const, secure, path: "/" };
        if (isLogout || (!newToken && res.status === 401 && sessionToken)) {
          response.cookies.set(SESSION_COOKIE, "", { ...cookieOptions, maxAge: 0 });
        } else if (newToken) {
          response.cookies.set(SESSION_COOKIE, newToken, { ...cookieOptions, maxAge: tokenMaxAgeSeconds(newToken) });
        }

        if (!resHeaders.has("cache-control")) {
          response.headers.set("cache-control", "no-store");
        }
        return response;
      } catch (err: any) {
        const errCode = err?.cause?.code || err?.name || err?.message;
        attempted.push(`${targetUrl} (${errCode})`);

        if (errCode === "UND_ERR_HEADERS_TIMEOUT" || err?.name === "TimeoutError" || err?.name === "AbortError") {
          return NextResponse.json({
            detail: "Die KI-Analyse benötigt noch etwas Zeit zum Verarbeiten oder Herunterladen des Modells. Bitte versuche es in wenigen Sekunden erneut."
          }, { status: 504 });
        }
      }
    }

    // Pause 1s if backend was just starting up
    if (attempt < 2) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }

  // Which internal addresses were tried is useful in the server log, not for the client.
  console.error(`Backend nicht erreichbar: ${attempted.slice(0, 8).join(", ")}`);
  return NextResponse.json({
    detail: "Backend Verbindung fehlgeschlagen. Bitte stelle sicher, dass der Backend-Container läuft."
  }, { status: 502 });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const PATCH = proxy;
