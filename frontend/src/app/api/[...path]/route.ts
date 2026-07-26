/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 300; // 5 minutes max execution time for AI processing

const BACKEND_URLS = [
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

  for (const baseUrl of BACKEND_URLS) {
    const targetUrl = `${baseUrl}${pathname}${search}`;
    const headers = new Headers(request.headers);
    headers.delete("host");

    try {
      // 3-minute timeout signal per request
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

      // If the backend container responded with a timeout while processing, break loop to prevent duplicate requests
      if (errCode === "UND_ERR_HEADERS_TIMEOUT" || err?.name === "TimeoutError" || err?.name === "AbortError") {
        return NextResponse.json({
          detail: "Die KI-Analyse benötigt noch etwas Zeit zum Verarbeiten oder Herunterladen des Modells. Bitte versuche es in wenigen Sekunden erneut."
        }, { status: 504 });
      }
    }
  }

  return NextResponse.json({ 
    detail: `Backend Verbindung fehlgeschlagen: [${attempted.join(", ")}]. Bitte stelle sicher, dass der Backend-Container läuft.` 
  }, { status: 502 });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const PATCH = proxy;
