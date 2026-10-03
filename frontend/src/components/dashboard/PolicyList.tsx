"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useLayoutEffect, useRef } from "react";
import Link from "next/link";
import { gsap } from "gsap";
import { Pause } from "lucide-react";
import { CompanyLogo } from "@/components/CompanyLogo";
import { daysUntil, formatDate, formatEuro, relativeDays, SOON_DAYS } from "@/lib/deadlines";
import { prefersReducedMotion } from "@/lib/motion";

interface PolicyListProps {
  insurances: any[];
  annualCost: (ins: any) => number;
}

const SIGNAL = "var(--calm-signal, #e6b24c)";

function classesLine(ins: any): string {
  const parts: string[] = [];
  if (ins.sf_class) parts.push(`SF ${String(ins.sf_class).replace(/^sf\s*/i, "")}`);
  if (ins.regional_class) parts.push(`Regio ${ins.regional_class}`);
  if (ins.type_class) parts.push(`Typklasse ${ins.type_class}`);
  return parts.join(", ");
}

/**
 * One row per contract instead of a grid of identical cards: the eye can run down
 * the amount and deadline columns and compare. When filter or sort changes, rows
 * glide to their new position (the reaction to the user's own action, not decoration).
 */
export function PolicyList({ insurances, annualCost }: PolicyListProps) {
  const listRef = useRef<HTMLUListElement>(null);
  const previousTops = useRef<Map<string, number>>(new Map());
  const orderKey = insurances.map(i => i.id).join(",");

  useLayoutEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const rows = Array.from(list.children) as HTMLElement[];
    const before = previousTops.current;
    const animate = before.size > 0 && !prefersReducedMotion();

    rows.forEach(row => {
      const id = row.dataset.id as string;
      const top = row.offsetTop;
      if (animate) {
        const was = before.get(id);
        if (was === undefined) {
          gsap.fromTo(row, { opacity: 0 }, { opacity: 1, duration: 0.3, ease: "power2.out", clearProps: "opacity" });
        } else if (was !== top) {
          gsap.fromTo(row, { y: was - top }, { y: 0, duration: 0.45, ease: "power3.out", clearProps: "transform" });
        }
      }
    });

    const next = new Map<string, number>();
    rows.forEach(row => next.set(row.dataset.id as string, row.offsetTop));
    previousTops.current = next;
  }, [orderKey]);

  return (
    <ul ref={listRef} className="divide-y divide-zinc-800 border-y border-zinc-800">
      {insurances.map(ins => {
        const days = ins.cancellation_date && !ins.is_suspended ? daysUntil(ins.cancellation_date) : null;
        const soon = days !== null && days >= 0 && days <= SOON_DAYS;
        const classes = classesLine(ins);
        const change = ins.price_change_pct;

        return (
          <li key={ins.id} data-id={ins.id} className="relative bg-[var(--calm-bg,transparent)]">
            <Link
              href={`/insurance/${ins.id}`}
              className="grid grid-cols-[2.5rem_minmax(0,1fr)] items-center gap-x-4 gap-y-1 px-1 py-4 transition-colors hover:bg-zinc-900/60 md:grid-cols-[2.5rem_minmax(0,1fr)_10rem_12rem] md:px-3"
            >
              <CompanyLogo company={ins.company || ins.name} size="md" />

              <div className="min-w-0">
                <p className="truncate text-base font-medium text-zinc-50">{ins.name}</p>
                <p className="truncate text-sm text-zinc-400">
                  {ins.company || "Gesellschaft unbekannt"}
                  {ins.category ? `, ${ins.category}` : ""}
                  {ins.insurance_number ? `, Nr. ${ins.insurance_number}` : ""}
                </p>
                {classes && <p className="truncate text-xs text-zinc-500">{classes}</p>}
              </div>

              <div className="col-start-2 text-sm md:col-start-auto md:text-right">
                {ins.is_suspended ? (
                  <span className="inline-flex items-center gap-1.5 text-zinc-400">
                    <Pause className="size-3.5" aria-hidden /> Ruht, keine Kosten
                  </span>
                ) : ins.cost ? (
                  <>
                    <span className="font-medium tabular-nums text-zinc-100">{formatEuro(ins.cost)}</span>
                    <span className="text-zinc-400"> {ins.payment_cycle || "jährlich"}</span>
                    {typeof change === "number" && change !== 0 && (
                      <span
                        className="ml-2 text-xs tabular-nums"
                        style={{ color: change > 0 ? "var(--calm-bad, #e0796a)" : "var(--calm-good, #8fbf9a)" }}
                      >
                        {change > 0 ? `+${change} %` : `${String(change).replace("-", "−")} %`}
                      </span>
                    )}
                    {annualCost(ins) !== ins.cost && (
                      <span className="block text-xs tabular-nums text-zinc-500">{formatEuro(annualCost(ins))} im Jahr</span>
                    )}
                  </>
                ) : (
                  <span className="text-zinc-500">Kein Beitrag hinterlegt</span>
                )}
              </div>

              <div className="col-start-2 text-sm md:col-start-auto md:text-right">
                {days === null ? (
                  <span className="text-zinc-500">{ins.is_suspended ? "" : "Keine Frist hinterlegt"}</span>
                ) : (
                  <>
                    <span className="tabular-nums text-zinc-100">{formatDate(ins.cancellation_date)}</span>
                    <span className="block text-xs" style={{ color: soon ? SIGNAL : "var(--calm-muted, #aaa294)" }}>
                      {days >= 0 ? relativeDays(days) : "verstrichen"}
                    </span>
                  </>
                )}
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
