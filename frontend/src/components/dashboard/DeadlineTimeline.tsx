"use client"
/**
 * Copyright (c) 2026 Dennis Guse
 * SPDX-License-Identifier: MIT
 * See the LICENSE file in the project root.
 */

import { useEffect, useMemo, useRef } from "react";
import Link from "next/link";
import { gsap } from "gsap";
import { daysUntil, formatDate, relativeDays, SOON_DAYS, startOfToday } from "@/lib/deadlines";
import { introState } from "@/lib/motion";

export interface TimelineItem {
  id: number;
  name: string;
  company?: string;
  cancellation_date: string;
}

const WINDOW_DAYS = 365;
const LANE_HEIGHT = 46;
const MIN_GAP_PERCENT = 17; // keeps neighbouring labels in one lane from overlapping
const SIGNAL = "var(--calm-signal, #e6b24c)";

interface Placed extends TimelineItem {
  days: number;
  x: number;
  lane: number;
  soon: boolean;
  alignRight: boolean;
}

function monthTicks(today: Date) {
  const ticks: { x: number; label: string }[] = [];
  for (let m = 1; m <= 12; m++) {
    const d = new Date(today.getFullYear(), today.getMonth() + m, 1);
    const x = ((d.getTime() - today.getTime()) / 86_400_000 / WINDOW_DAYS) * 100;
    if (x > 100) break;
    const label = d.getMonth() === 0
      ? d.toLocaleDateString("de-DE", { month: "short", year: "numeric" })
      : d.toLocaleDateString("de-DE", { month: "short" });
    ticks.push({ x, label: label.replace(".", "") });
  }
  return ticks;
}

/**
 * The deadlines of the next twelve months on one line. This is the dashboard's
 * signature element: it answers "what do I have to do, and when" at a glance.
 * Wide screens get the line; narrow ones get the same information as a list.
 */
export function DeadlineTimeline({ items }: { items: TimelineItem[] }) {
  const root = useRef<HTMLDivElement>(null);
  const today = useMemo(() => startOfToday(), []);

  const { placed, laneCount } = useMemo(() => {
    const inWindow = items
      .map(it => ({ ...it, days: daysUntil(it.cancellation_date, today) }))
      .filter(it => it.days >= 0 && it.days <= WINDOW_DAYS)
      .sort((a, b) => a.days - b.days);
    const lastX: number[] = [];
    const out: Placed[] = inWindow.map(it => {
      const x = (it.days / WINDOW_DAYS) * 100;
      let lane = lastX.findIndex(last => x - last >= MIN_GAP_PERCENT);
      if (lane === -1) lane = lastX.length;
      lastX[lane] = x;
      return { ...it, x, lane, soon: it.days <= SOON_DAYS, alignRight: x > 78 };
    });
    return { placed: out, laneCount: Math.max(1, lastX.length) };
  }, [items, today]);

  const ticks = useMemo(() => monthTicks(today), [today]);

  // The one orchestrated moment of the dashboard: the line is drawn, then the
  // deadlines are set on it from the nearest to the farthest. Plays once per page load.
  useEffect(() => {
    if (!root.current || introState.timelinePlayed || placed.length === 0) return;
    const mm = gsap.matchMedia();
    mm.add("(prefers-reduced-motion: no-preference)", () => {
      const ctx = gsap.context(() => {
        // The flag is set on completion, not on start: React runs effects twice in development.
        const tl = gsap.timeline({ defaults: { ease: "power3.out" }, onComplete: () => { introState.timelinePlayed = true; } });
        tl.from("[data-tl-axis]", { scaleX: 0, transformOrigin: "left center", duration: 0.9 })
          .from("[data-tl-tick]", { opacity: 0, duration: 0.4, stagger: 0.03 }, 0.2)
          .from("[data-tl-stem]", { scaleY: 0, transformOrigin: "bottom center", duration: 0.5, stagger: 0.12 }, 0.45)
          .from("[data-tl-dot]", { scale: 0, duration: 0.45, ease: "back.out(2.4)", stagger: 0.12 }, 0.45)
          .from("[data-tl-label]", { opacity: 0, y: 8, duration: 0.5, stagger: 0.12 }, 0.6);
      }, root);
      return () => ctx.revert();
    });
    return () => mm.revert();
  }, [placed.length]);

  if (placed.length === 0) {
    return (
      <p className="text-sm text-zinc-400">
        In den nächsten zwölf Monaten läuft keine Kündigungsfrist ab.
      </p>
    );
  }

  const height = 70 + laneCount * LANE_HEIGHT;

  return (
    <div ref={root}>
      {/* Wide screens: the line */}
      <div className="relative hidden md:block" style={{ height }} role="list" aria-label="Kündigungsfristen der nächsten zwölf Monate">
        <div data-tl-axis className="absolute left-0 right-0 h-px bg-zinc-600" style={{ bottom: 40 }} />
        {ticks.map(t => (
          <div key={t.label + t.x} data-tl-tick className="absolute" style={{ left: `${t.x}%`, bottom: 32 }} aria-hidden>
            <div className="h-2 w-px bg-zinc-600" />
            <span className="absolute left-1/2 top-3 -translate-x-1/2 text-[11px] text-zinc-500 whitespace-nowrap">{t.label}</span>
          </div>
        ))}
        <span className="absolute left-0 text-[11px] text-zinc-400" style={{ bottom: 12 }} aria-hidden>Heute</span>

        {placed.map(p => {
          const labelBottom = 40 + 12 + p.lane * LANE_HEIGHT;
          const side = p.alignRight
            ? { right: `${100 - p.x}%`, textAlign: "right" as const, paddingRight: 10 }
            : { left: `${p.x}%`, paddingLeft: 10 };
          return (
            <div key={p.id} role="listitem">
              <div
                data-tl-stem
                className="absolute w-px bg-zinc-600"
                style={{ left: `${p.x}%`, bottom: 40, height: labelBottom - 40 + 38 }}
                aria-hidden
              />
              <Link
                href={`/insurance/${p.id}`}
                data-tl-label
                className="group absolute block max-w-[13rem] rounded-sm outline-offset-4"
                style={{ bottom: labelBottom, ...side }}
              >
                <span className="block truncate text-sm font-medium text-zinc-100 underline-offset-4 group-hover:underline">{p.name}</span>
                <span className="block text-xs text-zinc-400" style={p.soon ? { color: SIGNAL } : undefined}>
                  {formatDate(p.cancellation_date)}, {relativeDays(p.days)}
                </span>
              </Link>
              <span
                data-tl-dot
                className="absolute h-3 w-3 -translate-x-1/2 translate-y-1/2 rounded-full border-2 border-zinc-200"
                style={{ left: `${p.x}%`, bottom: 40, background: p.soon ? SIGNAL : "var(--calm-bg, #1a1815)", borderColor: p.soon ? SIGNAL : undefined }}
                aria-hidden
              />
            </div>
          );
        })}
      </div>

      {/* Narrow screens: the same information as a list */}
      <ul className="space-y-3 md:hidden">
        {placed.map(p => (
          <li key={p.id}>
            <Link href={`/insurance/${p.id}`} className="flex items-baseline justify-between gap-4">
              <span className="truncate text-sm font-medium text-zinc-100">{p.name}</span>
              <span className="shrink-0 text-xs text-zinc-400" style={p.soon ? { color: SIGNAL } : undefined}>
                {formatDate(p.cancellation_date)}, {relativeDays(p.days)}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
