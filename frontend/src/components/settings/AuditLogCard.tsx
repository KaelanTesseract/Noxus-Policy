"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { api } from "@/lib/api";
import { ScrollText, RefreshCw } from "lucide-react";

interface AuditEntry {
  id: number;
  created_at: string;
  action: string;
  action_label: string;
  actor: string | null;
  ip: string | null;
  detail: string | null;
}

const WARNING_ACTIONS = new Set(["login_failed", "login_locked", "backup_password_revealed", "twofa_reset", "recovery_code_used"]);

export function AuditLogCard() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [onlyWarnings, setOnlyWarnings] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setEntries(await api.get("/users/audit-log?limit=200"));
    } catch (err: any) {
      setError(err.message || "Protokoll konnte nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const shown = onlyWarnings ? entries.filter(e => WARNING_ACTIONS.has(e.action)) : entries;

  return (
    <Card className="border-zinc-800 bg-zinc-900/50 backdrop-blur-md shadow-xl">
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <CardTitle className="text-xl font-semibold flex items-center gap-2">
              <ScrollText className="w-5 h-5 text-zinc-400" />
              <span>Sicherheitsprotokoll</span>
            </CardTitle>
            <CardDescription className="mt-1">
              Anmeldungen, Fehlversuche und Änderungen an Konten und Systemeinstellungen (die letzten 200 Einträge, Aufbewahrung 1 Jahr).
              Viele Fehlversuche von derselben Adresse deuten auf einen Angriff hin.
            </CardDescription>
          </div>
          <div className="flex gap-2 shrink-0">
            <Button type="button" size="sm" variant="outline" onClick={() => setOnlyWarnings(v => !v)} className={`text-xs border-zinc-700 ${onlyWarnings ? "bg-amber-950/50 text-amber-300 border-amber-800" : "bg-zinc-900 text-zinc-300"}`}>
              Nur Auffälliges
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={load} disabled={loading} className="border-zinc-700 bg-zinc-900 text-zinc-300 text-xs">
              <RefreshCw className={`w-3.5 h-3.5 mr-1 ${loading ? "animate-spin" : ""}`} /> Aktualisieren
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {error && <div className="p-3 bg-red-950/50 border border-red-800/80 text-red-300 rounded-xl text-xs mb-3">{error}</div>}
        <div className="overflow-x-auto rounded-xl border border-zinc-800 max-h-96 overflow-y-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-zinc-950/70 text-zinc-400 uppercase tracking-wider text-[10px] sticky top-0">
              <tr>
                <th className="px-3 py-2">Zeitpunkt</th>
                <th className="px-3 py-2">Ereignis</th>
                <th className="px-3 py-2">Konto</th>
                <th className="px-3 py-2">Adresse</th>
                <th className="px-3 py-2">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {shown.length === 0 && !loading && (
                <tr><td colSpan={5} className="px-3 py-4 text-center text-zinc-500">Keine Einträge.</td></tr>
              )}
              {shown.map(e => (
                <tr key={e.id} className="hover:bg-zinc-800/30">
                  {/* All values are rendered as plain text by React - never as HTML. */}
                  <td className="px-3 py-2 font-mono text-zinc-400 whitespace-nowrap">{new Date(e.created_at + "Z").toLocaleString("de-DE")}</td>
                  <td className={`px-3 py-2 ${WARNING_ACTIONS.has(e.action) ? "text-amber-300" : "text-zinc-200"}`}>{e.action_label}</td>
                  <td className="px-3 py-2 text-zinc-300 break-all">{e.actor || "–"}</td>
                  <td className="px-3 py-2 font-mono text-zinc-400">{e.ip || "–"}</td>
                  <td className="px-3 py-2 text-zinc-400 break-words">{e.detail || ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
