/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV === "development";

// Content-Security-Policy without nonces (nonces would force every page to be
// rendered per request). Inline scripts/styles stay allowed because Next.js and
// the print windows need them, so this does not stop an injected inline script
// by itself - what it does do is cap the damage: nothing can be loaded from or
// sent to another origin (connect-src/img-src), no plugins, no framing, no
// <base>/form hijacking. `upgrade-insecure-requests` is deliberately left out:
// it would break plain-HTTP LAN installs.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  // Company logos are fetched server-side (app/api/logo), so no external image host is needed.
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  `connect-src 'self'${isDev ? " ws: wss:" : ""}`,
  // Document previews are shown in iframes fed with blob: URLs.
  "frame-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          // Harmless over plain HTTP; takes effect once a reverse proxy terminates TLS in front of this app.
          { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
        ],
      },
    ];
  },
};

export default nextConfig;
