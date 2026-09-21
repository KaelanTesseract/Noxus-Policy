"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState } from "react";
import qrcode from "qrcode-generator";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { api } from "@/lib/api";
import { ShieldCheck } from "lucide-react";

interface Props {
  enabled: boolean;
  onChanged: () => void;
}

type Step = "idle" | "confirm-password" | "scan" | "codes" | "disable";

// The QR code is drawn in the browser from the otpauth link - the secret never
// goes to an external QR service. Rendered as JSX (no injected markup).
function QrCode({ text }: { text: string }) {
  const qr = qrcode(0, "M");
  qr.addData(text);
  qr.make();
  const count = qr.getModuleCount();
  const quiet = 2;
  const cells: React.ReactNode[] = [];
  for (let row = 0; row < count; row++) {
    for (let col = 0; col < count; col++) {
      if (qr.isDark(row, col)) {
        cells.push(<rect key={`${row}-${col}`} x={col + quiet} y={row + quiet} width={1} height={1} />);
      }
    }
  }
  const size = count + quiet * 2;
  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full h-full" shapeRendering="crispEdges" role="img" aria-label="QR-Code für die Authenticator-App">
      <rect width={size} height={size} fill="#fff" />
      <g fill="#000">{cells}</g>
    </svg>
  );
}

export function TwoFactorCard({ enabled, onChanged }: Props) {
  const [step, setStep] = useState<Step>("idle");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [secret, setSecret] = useState("");
  const [uri, setUri] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const reset = () => {
    setPassword("");
    setCode("");
    setSecret("");
    setUri("");
    setError("");
  };

  const startSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await api.post("/users/2fa/setup", { password });
      setSecret(res.secret);
      setUri(res.otpauth_uri);
      setPassword("");
      setStep("scan");
    } catch (err: any) {
      setError(err.message || "Einrichtung fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  };

  const confirmSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await api.post("/users/2fa/enable", { code: code.trim() });
      setRecoveryCodes(res.recovery_codes || []);
      reset();
      setStep("codes");
      setMessage("");
      onChanged();
    } catch (err: any) {
      setError(err.message || "Der Code wurde nicht akzeptiert.");
    } finally {
      setBusy(false);
    }
  };

  const disable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!window.confirm("Die 2-Faktor-Authentifizierung wirklich ausschalten? Dein Konto ist danach nur noch durch das Passwort geschützt.")) return;
    setBusy(true);
    setError("");
    try {
      const res = await api.post("/users/2fa/disable", { password, code: code.trim() });
      reset();
      setStep("idle");
      setMessage(res.msg || "Die 2-Faktor-Authentifizierung wurde deaktiviert.");
      onChanged();
    } catch (err: any) {
      setError(err.message || "Deaktivieren fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-md shadow-xl">
      <CardHeader>
        <CardTitle className="text-xl font-semibold flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-zinc-400" />
          <span>2-Faktor-Authentifizierung</span>
          {enabled && (
            <span className="ml-2 text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono">
              AKTIV
            </span>
          )}
        </CardTitle>
        <CardDescription className="mt-1">
          Zusätzlich zum Passwort wird beim Anmelden ein Code aus einer Authenticator-App abgefragt (z. B. Aegis, 2FAS, Google Authenticator).
          So reicht ein gestohlenes oder erratenes Passwort allein nicht mehr aus.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {message && (
          <div className="p-3 bg-emerald-950/40 border border-emerald-800/80 text-emerald-300 rounded-xl text-xs">{message}</div>
        )}
        {error && (
          <div className="p-3 bg-red-950/50 border border-red-800/80 text-red-300 rounded-xl text-xs">{error}</div>
        )}

        {step === "idle" && !enabled && (
          <Button type="button" onClick={() => { setMessage(""); setStep("confirm-password"); }} className="theme-bg-accent text-white theme-glow">
            2-Faktor-Authentifizierung einrichten
          </Button>
        )}
        {step === "idle" && enabled && (
          <Button type="button" variant="outline" onClick={() => { setMessage(""); setStep("disable"); }} className="border-zinc-700 bg-zinc-900 text-zinc-300 text-xs hover:bg-zinc-800">
            Ausschalten …
          </Button>
        )}

        {step === "confirm-password" && (
          <form onSubmit={startSetup} className="space-y-3 max-w-sm">
            <div className="space-y-2">
              <Label htmlFor="tfa-password" className="text-xs font-mono text-zinc-400">Zur Sicherheit: dein aktuelles Passwort</Label>
              <Input id="tfa-password" type="password" value={password} onChange={e => setPassword(e.target.value)} required autoComplete="current-password" className="bg-zinc-950/60 border-zinc-800" />
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={busy} className="theme-bg-accent text-white">{busy ? "Prüfe …" : "Weiter"}</Button>
              <Button type="button" variant="outline" onClick={() => { reset(); setStep("idle"); }} className="border-zinc-700 bg-zinc-900 text-zinc-300">Abbrechen</Button>
            </div>
          </form>
        )}

        {step === "scan" && (
          <form onSubmit={confirmSetup} className="space-y-4">
            <ol className="text-xs text-zinc-300 space-y-1 list-decimal list-inside">
              <li>Scanne den QR-Code mit deiner Authenticator-App (oder gib den Schlüssel von Hand ein).</li>
              <li>Gib unten den 6-stelligen Code aus der App ein, um die Einrichtung zu bestätigen.</li>
            </ol>
            <div className="flex flex-col sm:flex-row gap-4 items-start">
              <div className="w-44 h-44 bg-white rounded-lg overflow-hidden shrink-0">
                <QrCode text={uri} />
              </div>
              <div className="space-y-3 min-w-0">
                <div>
                  <p className="text-[11px] text-zinc-400 font-mono">Schlüssel für die manuelle Eingabe</p>
                  <p className="font-mono text-sm text-zinc-100 break-all select-all">{secret}</p>
                </div>
                <div className="space-y-2 max-w-xs">
                  <Label htmlFor="tfa-code" className="text-xs font-mono text-zinc-400">Code aus der App</Label>
                  <Input id="tfa-code" value={code} onChange={e => setCode(e.target.value)} required inputMode="numeric" autoComplete="one-time-code" maxLength={8} placeholder="123456" className="bg-zinc-950/60 border-zinc-800 font-mono tracking-widest" />
                </div>
                <div className="flex gap-2">
                  <Button type="submit" disabled={busy} className="theme-bg-accent text-white">{busy ? "Prüfe …" : "Aktivieren"}</Button>
                  <Button type="button" variant="outline" onClick={() => { reset(); setStep("idle"); }} className="border-zinc-700 bg-zinc-900 text-zinc-300">Abbrechen</Button>
                </div>
              </div>
            </div>
          </form>
        )}

        {step === "codes" && (
          <div className="space-y-3">
            <div className="p-3 bg-amber-950/40 border border-amber-800/80 text-amber-200 rounded-xl text-xs">
              <strong>Wiederherstellungscodes – jetzt sichern!</strong> Jeder Code funktioniert einmal, falls du keinen Zugriff auf die App hast.
              Sie werden nur dieses eine Mal angezeigt. Bewahre sie getrennt vom Passwort auf (z. B. ausgedruckt oder im Passwortmanager).
            </div>
            <div className="grid grid-cols-2 gap-2 max-w-sm font-mono text-sm text-zinc-100 select-all">
              {recoveryCodes.map(c => (
                <span key={c} className="px-2 py-1 rounded bg-zinc-950/70 border border-zinc-800">{c}</span>
              ))}
            </div>
            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={() => navigator.clipboard?.writeText(recoveryCodes.join("\n")).catch(() => {})} className="border-zinc-700 bg-zinc-900 text-zinc-300 text-xs">
                Kopieren
              </Button>
              <Button type="button" onClick={() => { setRecoveryCodes([]); setStep("idle"); setMessage("Die 2-Faktor-Authentifizierung ist jetzt aktiv."); }} className="theme-bg-accent text-white">
                Ich habe die Codes gesichert
              </Button>
            </div>
          </div>
        )}

        {step === "disable" && (
          <form onSubmit={disable} className="space-y-3 max-w-sm">
            <div className="space-y-2">
              <Label htmlFor="tfa-off-password" className="text-xs font-mono text-zinc-400">Passwort</Label>
              <Input id="tfa-off-password" type="password" value={password} onChange={e => setPassword(e.target.value)} required autoComplete="current-password" className="bg-zinc-950/60 border-zinc-800" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tfa-off-code" className="text-xs font-mono text-zinc-400">Code aus der App oder Wiederherstellungscode</Label>
              <Input id="tfa-off-code" value={code} onChange={e => setCode(e.target.value)} required autoComplete="one-time-code" className="bg-zinc-950/60 border-zinc-800 font-mono" />
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={busy} variant="destructive" className="bg-red-950/80 hover:bg-red-900 text-red-300 border border-red-800">{busy ? "Deaktiviere …" : "Ausschalten"}</Button>
              <Button type="button" variant="outline" onClick={() => { reset(); setStep("idle"); }} className="border-zinc-700 bg-zinc-900 text-zinc-300">Abbrechen</Button>
            </div>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
