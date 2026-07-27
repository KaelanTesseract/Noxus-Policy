/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import { Footer } from "@/components/Footer";

export const metadata: Metadata = {
  title: "Noxus Policy | AI Versicherungsmanager",
  description: "Dein intelligenter digitaler Versicherungsmanager",
  icons: {
    icon: "/logo.png",
    shortcut: "/logo.png",
    apple: "/logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de" className="dark" data-theme="indigo">
      <head>
        <link rel="icon" href="/logo.png" type="image/png" />
        <link rel="apple-touch-icon" href="/logo.png" />
      </head>
      <body className="font-sans bg-zinc-950 text-zinc-50 antialiased min-h-screen selection:bg-indigo-500/30 flex flex-col justify-between">
        <ThemeProvider>
          {/* Animated background gradient */}
          <div className="fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-zinc-900/40 via-zinc-950 to-zinc-950"></div>
          <main className="container mx-auto px-4 pt-2 pb-6 max-w-6xl flex-1 flex flex-col justify-between">
            {children}
          </main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}
