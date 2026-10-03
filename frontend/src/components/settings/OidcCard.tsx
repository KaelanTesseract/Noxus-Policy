"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { api } from "@/lib/api";
import { KeyRound } from "lucide-react";

interface OidcSettings {
  enabled: boolean;
  issuer: string;
  client_id: string;
  client_secret_set: boolean;
  button_label: string;
  auto_create: boolean;
  password_login_enabled: boolean;
  app_url: string;
  redirect_uri: string;
  own_account_linked: boolean;
}

function looksLikeLocalAddress(url: string): boolean {
  try {
    const host = new URL(url).hostname;
    return host === "localhost" || /^\d{1,3}(\.\d{1,3}){3}$/.test(host);
  } catch {
    return false;
  }
}

export function OidcCard() {
  const [cfg, setCfg] = useState<OidcSettings | null>(null);
  const [secret, setSecret] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    try {
      setCfg(await api.get("/users/oidc-config"));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Die SSO-Einstellungen konnten nicht geladen werden.");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async (changes: Partial<OidcSettings> & { client_secret?: string }) => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      setCfg(await api.put("/users/oidc-config", changes));
      setSecret("");
      setMessage("Gespeichert.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Speichern fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!cfg) return;
    save({
      app_url: cfg.app_url,
      enabled: cfg.enabled,
      issuer: cfg.issuer,
      client_id: cfg.client_id,
      client_secret: secret,
      button_label: cfg.button_label,
      auto_create: cfg.auto_create,
    });
  };

  const redirectUri = cfg ? `${cfg.app_url.trim().replace(/\/+$/, "")}/api/auth/oidc/callback` : "";

  if (!cfg) {
    return error ? <div className="rounded-xl border border-red-800/80 bg-red-950/50 p-3 text-xs text-red-300">{error}</div> : null;
  }

  return (
    <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-md shadow-xl">
      <CardHeader>
        <CardTitle className="text-xl font-semibold flex items-center gap-2">
          <KeyRound className="w-5 h-5 text-zinc-400" />
          <span>Single Sign-On (OpenID Connect)</span>
        </CardTitle>
        <CardDescription className="mt-1">
          Nutzer melden sich mit einem Identity-Provider an, zum Beispiel Pocket ID, statt mit einem Passwort. Neue Konten sind normale Benutzer; wer Administrator ist, legst du weiterhin hier in der App fest.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {message && <div className="rounded-xl border border-emerald-800/80 bg-emerald-950/40 p-3 text-xs text-emerald-300">{message}</div>}
        {error && <div className="rounded-xl border border-red-800/80 bg-red-950/50 p-3 text-xs text-red-300">{error}</div>}

        <div className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="oidcAppUrl" className="text-xs font-mono text-zinc-400">Adresse dieser App (so rufen Nutzer sie auf)</Label>
            <Input
              id="oidcAppUrl"
              value={cfg.app_url}
              onChange={e => setCfg({ ...cfg, app_url: e.target.value })}
              placeholder="https://nexus.beispiel.de"
              className="bg-zinc-950/60 border-zinc-800"
            />
          </div>
          {looksLikeLocalAddress(cfg.app_url) && (
            <p className="rounded-lg border border-amber-800/60 bg-amber-950/30 p-3 text-xs text-amber-200">
              Das ist eine IP-Adresse oder „localhost“. Pocket ID kennt deine App vermutlich unter ihrer Domain; trage hier dieselbe Adresse ein, die du im Browser benutzt, z. B. https://nexus.beispiel.de.
            </p>
          )}
          <div className="space-y-1">
            <Label className="text-xs font-mono text-zinc-400">Rückkehr-Adresse (genau so im Provider eintragen)</Label>
            <p className="break-all font-mono text-sm text-zinc-100 select-all">{redirectUri}</p>
            <p className="text-xs text-zinc-500">Wird beim Speichern übernommen. Dieselbe Adresse verwenden auch die Links in Passwort-Reset-Mails.</p>
          </div>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div className="flex items-center gap-2">
            <input id="oidcEnabled" type="checkbox" checked={cfg.enabled} onChange={e => setCfg({ ...cfg, enabled: e.target.checked })} className="size-4 accent-zinc-200" />
            <Label htmlFor="oidcEnabled" className="text-sm text-zinc-200 cursor-pointer">Anmeldung per SSO anbieten</Label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="oidcIssuer" className="text-xs font-mono text-zinc-400">Aussteller-URL (Issuer)</Label>
              <Input id="oidcIssuer" value={cfg.issuer} onChange={e => setCfg({ ...cfg, issuer: e.target.value })} placeholder="https://id.beispiel.de" className="bg-zinc-950/60 border-zinc-800" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="oidcClientId" className="text-xs font-mono text-zinc-400">Client-ID</Label>
              <Input id="oidcClientId" value={cfg.client_id} onChange={e => setCfg({ ...cfg, client_id: e.target.value })} className="bg-zinc-950/60 border-zinc-800" autoComplete="off" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="oidcClientSecret" className="text-xs font-mono text-zinc-400">Client-Secret</Label>
              <Input
                id="oidcClientSecret"
                type="password"
                value={secret}
                onChange={e => setSecret(e.target.value)}
                placeholder={cfg.client_secret_set ? "gespeichert – leer lassen zum Beibehalten" : ""}
                autoComplete="new-password"
                className="bg-zinc-950/60 border-zinc-800"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="oidcLabel" className="text-xs font-mono text-zinc-400">Text auf dem Anmelde-Knopf</Label>
              <Input id="oidcLabel" value={cfg.button_label} onChange={e => setCfg({ ...cfg, button_label: e.target.value })} placeholder="Mit Pocket ID anmelden" maxLength={60} className="bg-zinc-950/60 border-zinc-800" />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input id="oidcAutoCreate" type="checkbox" checked={cfg.auto_create} onChange={e => setCfg({ ...cfg, auto_create: e.target.checked })} className="size-4 accent-zinc-200" />
            <Label htmlFor="oidcAutoCreate" className="text-sm text-zinc-200 cursor-pointer">Beim ersten Login automatisch ein Konto anlegen</Label>
          </div>
          <p className="-mt-2 text-xs text-zinc-500">Gilt unabhängig von der Registrierungs-Sperre. Ein bestehendes Konto mit gleicher, vom Provider bestätigter E-Mail-Adresse wird immer verknüpft.</p>

          <Button type="submit" disabled={busy} className="theme-bg-accent">{busy ? "Speichert …" : "SSO-Einstellungen speichern"}</Button>
        </form>

        <div className="space-y-3 border-t border-zinc-800 pt-5">
          <h3 className="text-sm font-medium text-zinc-100">Passwort-Anmeldung</h3>
          {cfg.password_login_enabled ? (
            <>
              <p className="text-sm text-zinc-400">
                Zurzeit können sich alle mit Passwort anmelden. Du kannst das ausschalten, sobald SSO läuft und dein eigenes Konto verknüpft ist. Das Notfall-Skript <code className="text-zinc-200">reset_admin.py --enable-password-login</code> schaltet es auf dem Server wieder ein.
              </p>
              {!cfg.own_account_linked && (
                <p className="text-sm text-zinc-400">
                  Dein Konto ist noch nicht verknüpft. Speichere zuerst die Einstellungen oben, dann melde dich einmal beim Provider an; welche E-Mail-Adresse du dort hast, spielt dabei keine Rolle.{" "}
                  {cfg.enabled && <a href="/api/auth/oidc/link" className="text-zinc-100 underline underline-offset-4">Mein Konto jetzt verknüpfen</a>}
                </p>
              )}
              <Button
                type="button"
                variant="outline"
                disabled={busy || !cfg.enabled || !cfg.own_account_linked}
                onClick={() => {
                  if (window.confirm("Die Anmeldung mit Passwort für alle Konten ausschalten? Danach geht es nur noch über SSO.")) save({ password_login_enabled: false });
                }}
                className="border-zinc-700 bg-transparent text-zinc-200 hover:bg-zinc-800/70"
              >
                Passwort-Anmeldung ausschalten
              </Button>
            </>
          ) : (
            <>
              <p className="text-sm text-zinc-400">Die Anmeldung mit Passwort ist ausgeschaltet. Bestehende Sitzungen laufen weiter.</p>
              <Button type="button" variant="outline" disabled={busy} onClick={() => save({ password_login_enabled: true })} className="border-zinc-700 bg-transparent text-zinc-200 hover:bg-zinc-800/70">
                Passwort-Anmeldung wieder einschalten
              </Button>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
