"use client"
/**
 * Copyright (c) 2026 Dennis Guse
 * SPDX-License-Identifier: MIT
 * See the LICENSE file in the project root.
 */

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { KeyRound } from "lucide-react";

const NOTICES: Record<string, { text: string; ok: boolean }> = {
  linked: { text: "Dein Konto ist jetzt verknüpft. Ab sofort kannst du dich mit Single Sign-On anmelden.", ok: true },
  already: { text: "Dein Konto ist bereits verknüpft.", ok: true },
  error: { text: "Die Verknüpfung hat nicht geklappt. Möglicherweise gehört diese Identität schon zu einem anderen Konto. Frage sonst deinen Administrator.", ok: false },
};

// Lets any signed-in user bind their own account to their identity at the provider,
// whatever email address the provider has for them.
export function SsoLinkCard({ linked }: { linked: boolean }) {
  const [enabled, setEnabled] = useState(false);
  const [notice, setNotice] = useState<{ text: string; ok: boolean } | null>(null);

  useEffect(() => {
    fetch("/api/users/auth-config")
      .then(res => (res.ok ? res.json() : null))
      .then(cfg => setEnabled(!!cfg?.oidc_enabled))
      .catch(() => {});
    const outcome = new URLSearchParams(window.location.search).get("sso");
    if (outcome && NOTICES[outcome]) setNotice(NOTICES[outcome]);
  }, []);

  if (!enabled && !linked && !notice) return null;

  return (
    <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-md shadow-xl">
      <CardHeader>
        <CardTitle className="text-xl font-semibold flex items-center gap-2">
          <KeyRound className="w-5 h-5 text-zinc-400" />
          <span>Single Sign-On</span>
          {linked && (
            <span className="ml-2 rounded border border-emerald-800 bg-emerald-950 px-2 py-0.5 font-mono text-[10px] text-emerald-300">VERKNÜPFT</span>
          )}
        </CardTitle>
        <CardDescription className="mt-1">
          {linked
            ? "Dein Konto ist mit deiner Identität beim Anmelde-Dienst verknüpft. Du kannst dich damit ohne Passwort anmelden."
            : "Verknüpfe dein Konto, um dich künftig ohne Passwort anzumelden. Du meldest dich dafür einmal beim Anmelde-Dienst an; die E-Mail-Adresse dort muss nicht mit der hier übereinstimmen."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {notice && (
          <div className={`rounded-xl border p-3 text-xs ${notice.ok ? "border-emerald-800/80 bg-emerald-950/40 text-emerald-300" : "border-red-800/80 bg-red-950/50 text-red-300"}`} role="status">
            {notice.text}
          </div>
        )}
        {!linked && enabled && (
          <a href="/api/auth/oidc/link" className="theme-bg-accent inline-flex h-9 items-center rounded-lg px-4 text-sm font-medium">
            Konto jetzt verknüpfen
          </a>
        )}
      </CardContent>
    </Card>
  );
}
