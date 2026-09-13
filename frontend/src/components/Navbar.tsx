"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/components/ThemeProvider";
import { api } from "@/lib/api";

interface NavbarProps {
  userEmail?: string;
  onUploadClick?: () => void;
  onTaxExportClick?: () => void;
}

export function Navbar({ userEmail, onUploadClick, onTaxExportClick }: NavbarProps) {
  const router = useRouter();
  const { theme } = useTheme();
  const [useAi, setUseAi] = useState(true);
  const [inboxCount, setInboxCount] = useState(0);

  useEffect(() => {
    api.get("/documents/ai-config")
      .then((cfg: any) => setUseAi(!!cfg.use_ai))
      .catch(() => setUseAi(true));

    api.get("/inbox")
      .then((docs: any) => {
        if (Array.isArray(docs)) {
          setInboxCount(docs.length);
        }
      })
      .catch(() => {});
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("token");
    window.location.href = "/login";
  };

  return (
    <header className="sticky top-0 z-40 mb-8 w-full border-b border-zinc-800/80 bg-zinc-950/70 backdrop-blur-xl transition-all">
      <div className="flex h-16 items-center justify-between px-4 md:px-8">
        {/* Brand Logo & Status */}
        <div 
          onClick={() => router.push("/")} 
          className="flex items-center gap-3 cursor-pointer group"
        >
          <div className="relative flex items-center justify-center h-10 w-auto transition-transform group-hover:scale-105">
            <img src="/logo.png" alt="Noxus Policy Logo" className="h-9 w-auto object-contain rounded-lg drop-shadow-md" />
          </div>
          <div>
            <div className="flex items-center gap-1.5 sm:gap-2">
              <span className="font-extrabold text-sm sm:text-base md:text-xl tracking-wide bg-gradient-to-r from-white via-zinc-100 to-zinc-300 bg-clip-text text-transparent">
                NOXUS <span className="theme-text-accent">POLICY</span>
              </span>
              {useAi && (
                <span className="text-[8px] sm:text-[10px] px-1 sm:px-1.5 py-0.5 rounded font-mono font-semibold theme-bg-accent text-white uppercase tracking-widest shadow-sm">
                  AI
                </span>
              )}
            </div>
            <div className="hidden sm:flex items-center gap-1.5 text-[10px] sm:text-[11px] text-zinc-400 font-mono">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              SYSTEM ONLINE
            </div>
          </div>
        </div>

        {/* Right Navigation & Actions */}
        <div className="flex items-center gap-1.5 sm:gap-3">
          {userEmail && (
            <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-900/80 border border-zinc-800 text-xs text-zinc-300">
              <span className="w-2 h-2 rounded-full theme-bg-accent"></span>
              <span className="font-medium text-zinc-200">{userEmail}</span>
            </div>
          )}

          <Button
            onClick={() => router.push("/inbox")}
            title="Posteingang"
            aria-label={inboxCount > 0 ? `Posteingang, ${inboxCount} ungelesen` : "Posteingang"}
            variant="outline"
            size="icon"
            className="relative size-11 sm:size-8 border-indigo-800/80 bg-indigo-950/40 hover:bg-indigo-900/60 text-indigo-200 transition-all rounded-xl"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 12h4.5l1.5 3h6l1.5-3H21" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M5.5 12l1.72-6.45A2 2 0 019.15 4h5.7a2 2 0 011.93 1.55L18.5 12v6a2 2 0 01-2 2h-9a2 2 0 01-2-2v-6z" />
            </svg>
            {inboxCount > 0 && (
              <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center shadow-sm">
                {inboxCount > 99 ? "99+" : inboxCount}
              </span>
            )}
          </Button>

          {onTaxExportClick && (
            <Button
              onClick={onTaxExportClick}
              title="Steuererklärungs- & Haushalts-PDF-Export"
              variant="outline"
              className="border-sky-800/80 bg-sky-950/40 hover:bg-sky-900/60 text-sky-200 transition-all font-semibold text-xs sm:text-sm px-2.5 sm:px-3.5 py-1.5 flex items-center gap-1.5"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8l-5-5z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M14 3v5h5" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 13h6M9 17h6" />
              </svg>
              <span>Steuer-Export</span>
            </Button>
          )}

          {onUploadClick && (
            <Button
              onClick={onUploadClick}
              title="Dokument hochladen"
              className="theme-bg-accent text-white shadow-lg theme-glow transition-all hover:opacity-90 font-medium text-xs sm:text-sm px-2.5 sm:px-4 py-1.5"
            >
              <svg className="w-4 h-4 sm:mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              <span className="hidden sm:inline">Dokument hochladen</span>
            </Button>
          )}

          <Button
            onClick={() => router.push("/settings")}
            variant="outline"
            size="icon"
            title="Einstellungen"
            aria-label="Einstellungen"
            className="size-11 sm:size-8 border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300 hover:text-white transition-all rounded-xl"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </Button>

          <Button
            onClick={handleLogout}
            variant="outline"
            size="icon"
            title="Abmelden"
            aria-label="Abmelden"
            className="size-11 sm:size-8 border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-400 hover:text-red-400 transition-all rounded-xl"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </Button>
        </div>
      </div>
    </header>
  );
}
