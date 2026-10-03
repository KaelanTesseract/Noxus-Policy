/**
 * Copyright (c) 2026 Dennis Guse
 * SPDX-License-Identifier: MIT
 * See the LICENSE file in the project root.
 */

import type { Metadata } from "next";
import "@fontsource-variable/fraunces/opsz.css";
import "@fontsource-variable/instrument-sans/index.css";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import { Footer } from "@/components/Footer";

export const metadata: Metadata = {
  title: "Zettelfrieden | Versicherungsmanager",
  description: "Dein intelligenter digitaler Versicherungsmanager",
  icons: {
    icon: [{ url: "/favicon.png", type: "image/png" }, { url: "/logo.svg", type: "image/svg+xml" }],
    shortcut: "/favicon.png",
    apple: "/apple-touch-icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de" className="dark" data-theme="indigo" data-style="dark-calm">
      <head>
        <link rel="icon" href="/logo.svg" type="image/svg+xml" />
        <link rel="icon" href="/favicon.png" type="image/png" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
      </head>
      <body className="font-sans bg-zinc-950 text-zinc-50 antialiased min-h-screen selection:bg-indigo-500/30 flex flex-col justify-between">
        <ThemeProvider>
          {/* Animated ambient background: aurora glow + fine grid, adapts per design style */}
          <div className="fixed inset-0 -z-10 app-ambient-bg"></div>
          <main className="container mx-auto px-4 pt-2 pb-6 max-w-6xl flex-1 flex flex-col justify-between">
            {children}
          </main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}
