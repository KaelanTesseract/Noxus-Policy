"use client"
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/components/ThemeProvider";
import { api } from "@/lib/api";

interface NavbarProps {
  userEmail?: string;
  onUploadClick?: () => void;
}

export function Navbar({ userEmail, onUploadClick }: NavbarProps) {
  const router = useRouter();
  const { theme } = useTheme();
  const [useAi, setUseAi] = useState(true);

  useEffect(() => {
    api.get("/documents/ai-config")
      .then((cfg: any) => setUseAi(!!cfg.use_ai))
      .catch(() => setUseAi(true));
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
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-xl tracking-wide bg-gradient-to-r from-white via-zinc-100 to-zinc-300 bg-clip-text text-transparent">
                NOXUS <span className="theme-text-accent">POLICY</span>
              </span>
              {useAi && (
                <span className="text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold theme-bg-accent text-white uppercase tracking-widest shadow-sm">
                  AI
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-zinc-400 font-mono">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              SYSTEM ONLINE
            </div>
          </div>
        </div>

        {/* Right Navigation & Actions */}
        <div className="flex items-center gap-3">
          {userEmail && (
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-900/80 border border-zinc-800 text-xs text-zinc-300">
              <span className="w-2 h-2 rounded-full theme-bg-accent"></span>
              <span className="font-medium text-zinc-200">{userEmail}</span>
            </div>
          )}

          {onUploadClick && (
            <Button
              onClick={onUploadClick}
              className="theme-bg-accent text-white shadow-lg theme-glow transition-all hover:opacity-90 font-medium"
            >
              <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Dokument hochladen
            </Button>
          )}

          <Button
            onClick={() => router.push("/settings")}
            variant="outline"
            size="icon"
            title="Einstellungen"
            className="border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300 hover:text-white transition-all rounded-xl"
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
            className="border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-400 hover:text-red-400 transition-all rounded-xl"
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
