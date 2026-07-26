"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

export default function SessionExpiredPage() {
  const router = useRouter();
  const [countdown, setCountdown] = useState(5);

  useEffect(() => {
    // Clear any leftover auth token
    localStorage.removeItem("token");

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          router.push("/login");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [router]);

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      <div className="max-w-md w-full p-8 rounded-2xl bg-zinc-900/80 border border-zinc-800 shadow-2xl backdrop-blur-xl text-center space-y-6">
        <div className="w-16 h-16 mx-auto rounded-full bg-amber-950/60 border border-amber-800/80 flex items-center justify-center text-3xl shadow-lg">
          🔒
        </div>

        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-white tracking-tight">Sitzung abgelaufen</h1>
          <p className="text-sm text-zinc-400 leading-relaxed">
            Aus Sicherheitsgründen wurdest du automatisch abgemeldet. Bitte melde dich erneut an, um fortzufahren.
          </p>
        </div>

        {/* Countdown Indicator */}
        <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/80 space-y-2">
          <p className="text-xs text-zinc-400 font-mono">
            Automatische Weiterleitung in <span className="text-amber-400 font-bold text-base">{countdown}</span> Sekunden...
          </p>
          <div className="w-full h-1.5 rounded-full bg-zinc-900 overflow-hidden">
            <div
              className="h-full bg-amber-500 transition-all duration-1000 ease-linear"
              style={{ width: `${(countdown / 5) * 100}%` }}
            ></div>
          </div>
        </div>

        <Button
          onClick={() => router.push("/login")}
          className="w-full theme-bg-accent text-white theme-glow font-medium text-sm py-2.5"
        >
          Jetzt anmelden →
        </Button>
      </div>
    </div>
  );
}
