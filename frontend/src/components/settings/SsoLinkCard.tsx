"use client"
/**
 * Copyright (c) 2026 Dennis Guse
 * SPDX-License-Identifier: MIT
 * See the LICENSE file in the project root.
 */

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { KeyRound } from "lucide-react";
import { api } from "@/lib/api";

const NOTICES: Record<string, { text: string; ok: boolean }> = {
  linked: { text: "Dein Konto ist jetzt verknüpft. Ab sofort kannst du dich mit Single Sign-On anmelden.", ok: true },
  already: { text: "Dein Konto ist bereits verknüpft.", ok: true },
  unlinked: { text: "Die Verknüpfung wurde gelöst. Du meldest dich jetzt mit deinem Passwort an. Meldest du dich später wieder per SSO an und der Anbieter bestätigt deine E-Mail-Adresse, wird das Konto automatisch erneut verknüpft.", ok: true },
  error: { text: "Die Verknüpfung hat nicht geklappt. Möglicherweise gehört diese Identität schon zu einem anderen Konto. Frage sonst deinen Administrator.", ok: false },
};

// Lets any signed-in user bind their own account to their identity at the provider,
// whatever email address the provider has for them.
export function SsoLinkCard({ linked }: { linked: boolean }) {
  const [enabled, setEnabled] = useState(false);
  const [notice, setNotice] = useState<{ text: string; ok: boolean } | null>(null);
  const [unlinking, setUnlinking] = useState(false);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch("/api/users/auth-config")
      .then(res => (res.ok ? res.json() : null))
      .then(cfg => setEnabled(!!cfg?.oidc_enabled))
      .catch(() => {});
    const outcome = new URLSearchParams(window.location.search).get("sso");
    if (outcome && NOTICES[outcome]) setNotice(NOTICES[outcome]);
  }, []);

  const unlink = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/auth/oidc/unlink", { password });
      window.location.href = "/settings?sso=unlinked";
    } catch (err) {
      setNotice({ text: err instanceof Error ? err.message : "Die Verknüpfung konnte nicht gelöst werden.", ok: false });
      setBusy(false);
    }
  };

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
        {linked && !unlinking && (
          <button type="button" onClick={() => setUnlinking(true)} className="inline-flex h-9 items-center rounded-lg border border-zinc-700 px-4 text-sm text-zinc-200 hover:bg-zinc-800">
            Verknüpfung lösen
          </button>
        )}
        {linked && unlinking && (
          <form onSubmit={unlink} className="space-y-3">
            <p className="text-xs text-zinc-400">Zur Bestätigung dein Passwort eingeben. Danach meldest du dich wieder mit Passwort an.</p>
            <input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} aria-label="Passwort" className="h-9 w-full max-w-xs rounded-lg border border-zinc-700 bg-zinc-950 px-3 text-sm" />
            <div className="flex gap-2">
              <button type="submit" disabled={busy} className="theme-bg-accent inline-flex h-9 items-center rounded-lg px-4 text-sm font-medium">{busy ? "Löst …" : "Verknüpfung lösen"}</button>
              <button type="button" onClick={() => { setUnlinking(false); setPassword(""); }} className="inline-flex h-9 items-center rounded-lg border border-zinc-700 px-4 text-sm text-zinc-200">Abbrechen</button>
            </div>
          </form>
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
