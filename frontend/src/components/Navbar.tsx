"use client"
/**
 * Copyright (c) 2026 Dennis Guse
 * SPDX-License-Identifier: MIT
 * See the LICENSE file in the project root.
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { FileText, Inbox, LogOut, Plus, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { logout } from "@/lib/session";

interface NavbarProps {
  userEmail?: string;
  onUploadClick?: () => void;
  onTaxExportClick?: () => void;
}

export function Navbar({ userEmail, onUploadClick, onTaxExportClick }: NavbarProps) {
  const router = useRouter();
  const [inboxCount, setInboxCount] = useState(0);

  useEffect(() => {
    api.get("/inbox")
      .then((docs: any) => {
        if (Array.isArray(docs)) {
          setInboxCount(docs.length);
        }
      })
      .catch(() => {});
  }, []);

  // Quiet icon buttons: no coloured fills, so the primary action is the only strong element.
  const iconButton =
    "relative size-11 sm:size-9 border-transparent bg-transparent text-zinc-400 hover:bg-zinc-800/70 hover:text-zinc-50";

  return (
    <header className="sticky top-0 z-40 mb-10 w-full border-b border-zinc-800/80 bg-zinc-950/90 backdrop-blur-xl">
      <div className="flex h-16 items-center justify-between px-1 md:px-4">
        <button
          type="button"
          onClick={() => router.push("/")}
          className="flex items-center gap-3 rounded-md text-left"
          aria-label="Zur Übersicht"
        >
          <img src="/logo.png" alt="" className="h-8 w-auto object-contain" />
          <span className="whitespace-nowrap font-display text-lg leading-none text-zinc-50 sm:text-2xl">Zettelfrieden</span>
        </button>

        <nav className="flex items-center gap-1 sm:gap-2" aria-label="Hauptnavigation">
          {userEmail && <span className="hidden pr-2 text-sm text-zinc-400 xl:inline">{userEmail}</span>}

          <Button
            onClick={() => router.push("/inbox")}
            title="Posteingang"
            aria-label={inboxCount > 0 ? `Posteingang, ${inboxCount} ungelesen` : "Posteingang"}
            variant="outline"
            size="icon"
            className={iconButton}
          >
            <Inbox className="size-[18px]" aria-hidden />
            {inboxCount > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-[var(--calm-signal,#e6b24c)] px-1 text-[11px] font-semibold leading-none text-zinc-950">
                {inboxCount > 99 ? "99+" : inboxCount}
              </span>
            )}
          </Button>

          {onTaxExportClick && (
            <Button
              onClick={onTaxExportClick}
              title="Steuererklärungs- und Haushalts-PDF exportieren"
              variant="outline"
              className="hidden border-transparent bg-transparent px-3 text-sm text-zinc-300 hover:bg-zinc-800/70 hover:text-zinc-50 sm:inline-flex"
            >
              <FileText className="size-4" aria-hidden />
              Steuer-Export
            </Button>
          )}

          <Button
            onClick={() => router.push("/settings")}
            variant="outline"
            size="icon"
            title="Einstellungen"
            aria-label="Einstellungen"
            className={iconButton}
          >
            <Settings className="size-[18px]" aria-hidden />
          </Button>

          <Button
            onClick={() => logout()}
            variant="outline"
            size="icon"
            title="Abmelden"
            aria-label="Abmelden"
            className={iconButton}
          >
            <LogOut className="size-[18px]" aria-hidden />
          </Button>

          {onUploadClick && (
            <Button
              onClick={onUploadClick}
              title="Dokument hochladen"
              className="theme-bg-accent ml-1 h-9 px-3 text-sm font-medium sm:px-4"
            >
              <Plus className="size-4" aria-hidden />
              <span className="hidden sm:inline">Dokument hochladen</span>
            </Button>
          )}
        </nav>
      </div>
    </header>
  );
}
