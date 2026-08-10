/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 300; // 5 minutes max execution time for AI processing

const BACKEND_URLS = [
  ...(process.env.BACKEND_URL ? [process.env.BACKEND_URL] : []),
  "http://backend:8000",
  "http://192.168.1.251:8000",
  "http://172.17.0.1:8000",
  "http://127.0.0.1:8000",
  "http://localhost:8000"
];

async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const search = request.nextUrl.search;
  const body = request.method !== "GET" && request.method !== "HEAD"
    ? await request.arrayBuffer()
    : undefined;

  let attempted: string[] = [];

  // Retry loop: Try up to 3 cycles with 1-second pause if backend is still booting
  for (let attempt = 0; attempt < 3; attempt++) {
    for (const baseUrl of BACKEND_URLS) {
      const targetUrl = `${baseUrl}${pathname}${search}`;
      const headers = new Headers(request.headers);
      headers.delete("host");

      try {
        const res = await fetch(targetUrl, {
          method: request.method,
          headers: headers,
          body: body,
          redirect: "manual",
          signal: AbortSignal.timeout(180000)
        });

        const resHeaders = new Headers(res.headers);
        return new NextResponse(res.body, {
          status: res.status,
          statusText: res.statusText,
          headers: resHeaders,
        });
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

  return NextResponse.json({ 
    detail: `Backend Verbindung fehlgeschlagen: [${attempted.slice(0, 5).join(", ")}]. Bitte stelle sicher, dass der Backend-Container läuft.` 
  }, { status: 502 });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const PATCH = proxy;
