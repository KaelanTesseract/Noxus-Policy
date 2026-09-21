"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { api } from "@/lib/api";
import { clearSession } from "@/lib/session";
import { Trash2 } from "lucide-react";

// Right to erasure: removes the account together with every contract, claim and
// uploaded document. Administrators can't use this (an instance must keep one) -
// another admin deletes their account instead.
export function DeleteAccountCard() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!window.confirm("Dein Konto und ALLE zugehörigen Verträge, Schadensfälle und Dokumente werden unwiderruflich gelöscht. Fortfahren?")) return;
    setBusy(true);
    setError("");
    try {
      await api.post("/users/me/delete", { password });
      clearSession();
      router.push("/login");
    } catch (err: any) {
      setError(err.message || "Das Konto konnte nicht gelöscht werden.");
      setBusy(false);
    }
  };

  return (
    <Card className="border-red-900/60 bg-zinc-900/50 backdrop-blur-md shadow-xl">
      <CardHeader>
        <CardTitle className="text-xl font-semibold flex items-center gap-2">
          <Trash2 className="w-5 h-5 text-red-400" />
          <span>Konto löschen</span>
        </CardTitle>
        <CardDescription className="mt-1">
          Entfernt dein Konto samt aller Verträge, Schadensfälle und hochgeladenen Dokumente vom Server. Das lässt sich nicht rückgängig machen.
          Bereits erstellte Server-Backups enthalten deine Daten weiterhin, bis der Administrator sie löscht.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!open ? (
          <Button type="button" variant="outline" onClick={() => setOpen(true)} className="border-red-900 bg-red-950/40 text-red-300 hover:bg-red-950/70 text-xs">
            Konto löschen …
          </Button>
        ) : (
          <form onSubmit={submit} className="space-y-3 max-w-sm">
            {error && <div className="p-3 bg-red-950/50 border border-red-800/80 text-red-300 rounded-xl text-xs">{error}</div>}
            <div className="space-y-2">
              <Label htmlFor="delete-password" className="text-xs font-mono text-zinc-400">Zur Bestätigung: dein Passwort</Label>
              <Input id="delete-password" type="password" value={password} onChange={e => setPassword(e.target.value)} required autoComplete="current-password" className="bg-zinc-950/60 border-zinc-800" />
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={busy} variant="destructive" className="bg-red-950/80 hover:bg-red-900 text-red-300 border border-red-800">
                {busy ? "Lösche …" : "Endgültig löschen"}
              </Button>
              <Button type="button" variant="outline" onClick={() => { setOpen(false); setPassword(""); setError(""); }} className="border-zinc-700 bg-zinc-900 text-zinc-300">
                Abbrechen
              </Button>
            </div>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
