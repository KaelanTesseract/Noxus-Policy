"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { Check, Calculator, TriangleAlert } from "lucide-react";

// What the backend says about each extracted value (backend/field_checks.py).
export type FieldCheck = {
  status: "gefunden" | "berechnet" | "unsicher";
  seite?: number;
  stelle?: string;
  grund?: string;
  quelle?: string;
};

const FIELD_LABELS: [string, string][] = [
  ["company", "Gesellschaft"],
  ["insurance_number", "Versicherungsnummer"],
  ["cost", "Beitrag"],
  ["start_date", "Beginn"],
  ["end_date", "Ablauf"],
  ["cancellation_date", "Kündigungsfrist"],
  ["sf_class", "SF-Klasse"],
  ["regional_class", "Regionalklasse"],
  ["type_class", "Typklasse"],
];

const STATUS_STYLE = {
  gefunden: { icon: Check, color: "text-[color:var(--calm-good,#34d399)]", label: "im Dokument gefunden" },
  berechnet: { icon: Calculator, color: "text-[color:var(--calm-signal,#fbbf24)]", label: "berechnet" },
  unsicher: { icon: TriangleAlert, color: "text-[color:var(--calm-bad,#f87171)]", label: "bitte prüfen" },
} as const;

export function formatValue(field: string, value: unknown): string {
  if (value === null || value === undefined || value === "") return "";
  if (field === "cost") {
    const n = Number(value);
    return Number.isFinite(n) ? n.toLocaleString("de-DE", { style: "currency", currency: "EUR" }) : String(value);
  }
  if (/^\d{4}-\d{2}-\d{2}/.test(String(value))) {
    const [y, m, d] = String(value).slice(0, 10).split("-");
    return `${d}.${m}.${y}`;
  }
  return String(value);
}

/** Small note under a form field when its value was computed or could not be found in the document. */
export function CheckHint({ check }: { check?: FieldCheck }) {
  if (!check || check.status === "gefunden") return null;
  const style = STATUS_STYLE[check.status];
  const Icon = style.icon;
  return (
    <p className={`flex items-start gap-1.5 text-[11px] leading-snug ${style.color}`}>
      <Icon className="size-3 mt-0.5 shrink-0" aria-hidden />
      <span>{check.grund || style.label}</span>
    </p>
  );
}

/** Which values were read from the document, which were computed, which need a look. */
export function FieldChecks({ data, checks }: { data: Record<string, unknown>; checks?: Record<string, FieldCheck> }) {
  if (!checks) return null;
  const rows = FIELD_LABELS.filter(([field]) => checks[field] && data[field] !== null && data[field] !== undefined && data[field] !== "");
  if (rows.length === 0) return null;

  const count = (status: string) => rows.filter(([field]) => checks[field].status === status).length;
  const found = count("gefunden");
  const computed = count("berechnet");
  const unsure = count("unsicher");

  return (
    <details open={unsure > 0} className="rounded-xl border border-zinc-800 bg-zinc-900/40 text-xs group">
      <summary className="cursor-pointer select-none px-3.5 py-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-zinc-300">
        <span className="font-semibold text-zinc-200">Prüfung der ausgelesenen Werte</span>
        <span className="text-[color:var(--calm-good,#34d399)]">{found} im Dokument gefunden</span>
        {computed > 0 && <span className="text-[color:var(--calm-signal,#fbbf24)]">{computed} berechnet</span>}
        {unsure > 0 && <span className="text-[color:var(--calm-bad,#f87171)]">{unsure} bitte prüfen</span>}
      </summary>
      <ul className="divide-y divide-zinc-800 border-t border-zinc-800">
        {rows.map(([field, label]) => {
          const check = checks[field];
          const style = STATUS_STYLE[check.status];
          const Icon = style.icon;
          return (
            <li key={field} className="px-3.5 py-2 grid grid-cols-1 sm:grid-cols-[9rem_1fr] gap-x-3 gap-y-0.5">
              <span className="text-zinc-500">{label}</span>
              <span className="min-w-0">
                <span className="flex items-center gap-1.5 text-zinc-100">
                  <Icon className={`size-3.5 shrink-0 ${style.color}`} aria-hidden />
                  <span className="font-mono">{formatValue(field, data[field])}</span>
                  {check.quelle === "ki" && (
                    <span className="px-1.5 py-px rounded border border-zinc-700 text-[10px] text-zinc-400">von der KI gelesen</span>
                  )}
                  <span className="sr-only">{style.label}</span>
                </span>
                <span className="block text-zinc-500 break-words">
                  {check.status === "gefunden" && (
                    <>
                      Seite {check.seite ?? 1}
                      {check.stelle ? <>: <span className="font-mono">„{check.stelle}“</span></> : null}
                    </>
                  )}
                  {check.status !== "gefunden" && (check.grund || style.label)}
                </span>
              </span>
            </li>
          );
        })}
      </ul>
    </details>
  );
}
