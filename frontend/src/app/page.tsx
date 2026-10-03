"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { UploadModal } from "@/components/UploadModal";
import { TaxExportModal } from "@/components/TaxExportModal";
import { DeadlineTimeline } from "@/components/dashboard/DeadlineTimeline";
import { PolicyList } from "@/components/dashboard/PolicyList";
import { CountUp } from "@/components/dashboard/CountUp";
import { daysUntil, formatDate, formatEuro, relativeDays, startOfToday } from "@/lib/deadlines";
import { useTheme } from "@/components/ThemeProvider";
import { clearSession, hasSessionHint } from "@/lib/session";
import { Search, X } from "lucide-react";

// One hue in descending strength instead of six colours: a category is told apart by
// its label, so colour is free to keep its meaning (saffron = deadline).
const CATEGORY_TONES = [1, 2, 3, 4, 5, 6].map(n => `var(--tone-${n})`);

export default function Dashboard() {
  const router = useRouter();
  const { showCostChart } = useTheme();
  const [insurances, setInsurances] = useState<any[]>([]);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isTaxModalOpen, setIsTaxModalOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<any>(null);
  
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [inboxCount, setInboxCount] = useState(0);

  // Filter & Search States
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [sortBy, setSortBy] = useState("fristen");

  useEffect(() => {
    if (typeof window !== "undefined") {
      // The token itself is in an httpOnly cookie scripts can't see; this hint only
      // avoids a pointless failing request for someone who never signed in.
      if (!hasSessionHint()) {
        window.location.href = "/login";
        return;
      }
      checkAuthAndLoad();
    }
  }, []);

  const checkAuthAndLoad = async () => {
    // Instant cache rendering
    if (typeof window !== "undefined") {
      const cachedUser = sessionStorage.getItem("cache_user");
      const cachedInsurances = sessionStorage.getItem("cache_insurances");
      const cachedInboxCount = sessionStorage.getItem("cache_inbox_count");
      if (cachedUser && cachedInsurances) {
        try {
          setCurrentUser(JSON.parse(cachedUser));
          setInsurances(JSON.parse(cachedInsurances));
          if (cachedInboxCount !== null) setInboxCount(parseInt(cachedInboxCount, 10) || 0);
          setIsAuthenticated(true);
          setIsCheckingAuth(false);
        } catch (_) {}
      }
    }

    // Parallel network fetch (zero waterfall)
    try {
      const [userRes, insRes, inboxRes] = await Promise.all([
        fetch("/api/users/me"),
        fetch("/api/insurances"),
        fetch("/api/inbox")
      ]);

      if (!userRes.ok || !insRes.ok) {
        clearSession();
        window.location.href = "/login";
        return;
      }

      const [userData, insData] = await Promise.all([userRes.json(), insRes.json()]);

      if (userData.must_change_password) {
        window.location.href = "/admin-setup";
        return;
      }

      setCurrentUser(userData);
      setInsurances(insData);
      setIsAuthenticated(true);

      if (inboxRes.ok) {
        const inboxData = await inboxRes.json();
        const count = Array.isArray(inboxData) ? inboxData.length : 0;
        setInboxCount(count);
        if (typeof window !== "undefined") {
          sessionStorage.setItem("cache_inbox_count", String(count));
        }
      }

      if (typeof window !== "undefined") {
        sessionStorage.setItem("cache_user", JSON.stringify(userData));
        sessionStorage.setItem("cache_insurances", JSON.stringify(insData));
      }
    } catch (e) {
      console.error(e);
      clearSession();
      window.location.href = "/login";
    } finally {
      setIsCheckingAuth(false);
    }
  };

  const getAnnualCost = (ins: any) => {
    if (!ins || ins.is_suspended || !ins.cost) return 0;
    const cycle = String(ins.payment_cycle || "jährlich").toLowerCase();
    if (cycle === "monatlich") return ins.cost * 12;
    if (cycle === "vierteljährlich") return ins.cost * 4;
    if (cycle === "halbjährlich") return ins.cost * 2;
    return ins.cost;
  };

  const totalCostAnnual = insurances.reduce((acc, ins) => acc + getAnnualCost(ins), 0);

  // Cancellation deadlines still ahead (suspended policies are excluded). The timeline
  // shows the next twelve months; the headline names the nearest one.
  const today = startOfToday();
  const upcomingDeadlines = insurances
    .filter((ins: any) => ins.cancellation_date && !ins.is_suspended && daysUntil(ins.cancellation_date, today) >= 0)
    .sort((a: any, b: any) => a.cancellation_date.localeCompare(b.cancellation_date));
  const nextDeadline = upcomingDeadlines[0];
  const nextDeadlineDays = nextDeadline ? daysUntil(nextDeadline.cancellation_date, today) : null;

  // Calculate category statistics & breakdown
  const categoryStats = insurances.reduce((acc: any, ins: any) => {
    const cat = ins.category || "Sonstige";
    if (!acc[cat]) {
      acc[cat] = { count: 0, cost: 0 };
    }
    acc[cat].count += 1;
    acc[cat].cost += getAnnualCost(ins);
    return acc;
  }, {});

  const categoryList = Object.entries(categoryStats).map(([cat, data]: [string, any], index: number) => ({
    name: cat,
    count: data.count,
    cost: data.cost,
    percentage: totalCostAnnual > 0 ? Math.round((data.cost / totalCostAnnual) * 100) : 0,
    tone: CATEGORY_TONES[index % CATEGORY_TONES.length]
  })).sort((a, b) => b.cost - a.cost);

  // Filter and Sort Logic
  const filteredInsurances = insurances.filter((ins: any) => {
    const matchesSearch = 
      !searchQuery ||
      (ins.name || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (ins.company || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (ins.category || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (ins.insurance_number || "").toLowerCase().includes(searchQuery.toLowerCase());

    const matchesCategory = 
      selectedCategory === "all" || (ins.category || "Sonstige").toLowerCase() === selectedCategory.toLowerCase();

    return matchesSearch && matchesCategory;
  }).sort((a: any, b: any) => {
    if (sortBy === "cost") {
      return getAnnualCost(b) - getAnnualCost(a);
    }
    if (sortBy === "name") {
      return (a.name || "").localeCompare(b.name || "");
    }
    if (sortBy === "fristen") {
      if (!a.cancellation_date) return 1;
      if (!b.cancellation_date) return -1;
      return a.cancellation_date.localeCompare(b.cancellation_date);
    }
    return 0;
  });

  if (isCheckingAuth || !isAuthenticated) {
    return null;
  }

  return (
    <div className="space-y-6 flex-1 flex flex-col justify-between">
      <Navbar
        userEmail={currentUser?.email}
        onUploadClick={() => setIsUploadModalOpen(true)}
        onTaxExportClick={() => setIsTaxModalOpen(true)}
      />

      <div className="flex-1 space-y-16 px-1 md:px-4">
        {/* The one thing that matters most: what has to be done next, and what it all costs */}
        <section className="grid gap-8 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
          <div className="space-y-5">
            {nextDeadline && nextDeadlineDays !== null ? (
              <>
                <h1 className="font-display text-balance text-4xl leading-[1.08] text-zinc-50 md:text-5xl">
                  Kündigungsfrist für {nextDeadline.name} endet {relativeDays(nextDeadlineDays)}.
                </h1>
                <p className="text-base text-zinc-400">
                  {nextDeadline.company ? `${nextDeadline.company}, ` : ""}Frist am {formatDate(nextDeadline.cancellation_date)}.{" "}
                  <Link href={`/insurance/${nextDeadline.id}`} className="text-zinc-100 underline underline-offset-4 hover:text-white">
                    Vertrag öffnen
                  </Link>
                </p>
              </>
            ) : (
              <h1 className="font-display text-balance text-4xl leading-[1.08] text-zinc-50 md:text-5xl">
                {insurances.length === 0 ? "Noch keine Verträge." : "Keine Kündigungsfrist steht an."}
              </h1>
            )}
            {inboxCount > 0 && (
              <p className="text-sm text-zinc-400">
                <Link href="/inbox" className="text-zinc-100 underline underline-offset-4 hover:text-white">
                  {inboxCount === 1 ? "1 Dokument wartet" : `${inboxCount} Dokumente warten`} im Posteingang
                </Link>{" "}
                auf die Zuordnung.
              </p>
            )}
          </div>

          <div className="md:text-right">
            <p className="font-display text-4xl tabular-nums text-zinc-50 md:text-5xl">
              <CountUp value={totalCostAnnual} format={formatEuro} />
            </p>
            <p className="mt-1 text-sm text-zinc-400">
              pro Jahr, verteilt auf {insurances.length === 1 ? "einen Vertrag" : `${insurances.length} Verträge`}
            </p>
          </div>
        </section>

        <section aria-labelledby="timeline-heading">
          <h2 id="timeline-heading" className="sr-only">Kündigungsfristen der nächsten zwölf Monate</h2>
          <DeadlineTimeline items={insurances.filter((i: any) => i.cancellation_date && !i.is_suspended)} />
        </section>

        {showCostChart && categoryList.length > 0 && (
          <section className="space-y-5" aria-labelledby="costs-heading">
            <div className="flex items-baseline justify-between gap-4">
              <h2 id="costs-heading" className="font-display text-2xl text-zinc-50">Kosten nach Sparte</h2>
              {selectedCategory !== "all" && (
                <Button onClick={() => setSelectedCategory("all")} variant="ghost" size="sm" className="text-zinc-400 hover:text-zinc-50">
                  <X className="size-3.5" aria-hidden /> Auswahl aufheben
                </Button>
              )}
            </div>

            <div className="flex h-2 w-full gap-0.5 overflow-hidden rounded-full" role="img"
              aria-label={categoryList.map(c => `${c.name} ${c.percentage} Prozent`).join(", ")}>
              {categoryList.map(cat => {
                const dimmed = selectedCategory !== "all" && selectedCategory.toLowerCase() !== cat.name.toLowerCase();
                return (
                  <div
                    key={cat.name}
                    style={{ width: `${Math.max(cat.percentage, 3)}%`, background: cat.tone, opacity: dimmed ? 0.25 : 1 }}
                    className="h-full transition-opacity duration-300"
                  />
                );
              })}
            </div>

            <ul className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3 lg:grid-cols-6">
              {categoryList.map(cat => {
                const isSelected = selectedCategory.toLowerCase() === cat.name.toLowerCase();
                return (
                  <li key={cat.name}>
                    <button
                      type="button"
                      aria-pressed={isSelected}
                      onClick={() => setSelectedCategory(isSelected ? "all" : cat.name)}
                      className="group block w-full text-left"
                    >
                      <span className="flex items-center gap-2 text-sm text-zinc-300 group-hover:text-zinc-50">
                        <span className="size-2 shrink-0 rounded-full" style={{ background: cat.tone }} aria-hidden />
                        <span className={`truncate ${isSelected ? "underline underline-offset-4" : ""}`}>{cat.name}</span>
                      </span>
                      <span className="mt-0.5 block text-sm tabular-nums text-zinc-100">{formatEuro(cat.cost)}</span>
                      <span className="block text-xs text-zinc-500">{cat.percentage} %, {cat.count} {cat.count === 1 ? "Vertrag" : "Verträge"}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
        )}

        <section className="space-y-5" aria-labelledby="policies-heading">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <h2 id="policies-heading" className="font-display text-2xl text-zinc-50">
              Verträge
              <span className="ml-3 font-sans text-sm font-normal text-zinc-400">
                {filteredInsurances.length === insurances.length ? insurances.length : `${filteredInsurances.length} von ${insurances.length}`}
              </span>
            </h2>

            <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
              <div className="relative sm:w-72">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-500" aria-hidden />
                <Input
                  type="search"
                  aria-label="Verträge durchsuchen"
                  placeholder="Name, Anbieter oder Nummer"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="h-10 border-zinc-800 bg-transparent pl-9 text-sm placeholder:text-zinc-500"
                />
              </div>
              <select
                aria-label="Sortierung"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="h-10 cursor-pointer rounded-lg border border-zinc-800 bg-transparent px-3 text-sm text-zinc-200 outline-none"
              >
                <option value="fristen">Nächste Frist zuerst</option>
                <option value="cost">Höchste Kosten zuerst</option>
                <option value="name">Name von A bis Z</option>
              </select>
            </div>
          </div>

          {filteredInsurances.length === 0 ? (
            <div className="space-y-3 border-y border-zinc-800 py-12">
              <h3 className="font-display text-xl text-zinc-50">
                {insurances.length === 0 ? "Noch keine Verträge" : "Keine Verträge gefunden"}
              </h3>
              <p className="max-w-md text-sm text-zinc-400">
                {insurances.length === 0
                  ? "Lade eine Police als PDF oder Foto hoch. Gesellschaft, Beitrag und Fristen werden automatisch ausgelesen."
                  : "Zu deiner Suche oder Sparte passt kein Vertrag. Ändere die Suche oder hebe die Auswahl auf."}
              </p>
              {insurances.length === 0 ? (
                <Button onClick={() => setIsUploadModalOpen(true)} className="theme-bg-accent">Police hochladen</Button>
              ) : (
                <Button onClick={() => { setSearchQuery(""); setSelectedCategory("all"); }} variant="outline">Suche zurücksetzen</Button>
              )}
            </div>
          ) : (
            <div>
              <div className="hidden grid-cols-[2.5rem_minmax(0,1fr)_10rem_12rem] gap-x-4 px-3 pb-2 text-xs text-zinc-500 md:grid">
                <span />
                <span>Vertrag</span>
                <span className="text-right">Beitrag</span>
                <span className="text-right">Kündigungsfrist</span>
              </div>
              <PolicyList insurances={filteredInsurances} annualCost={getAnnualCost} />
            </div>
          )}
        </section>
      </div>

      <UploadModal 
        isOpen={isUploadModalOpen} 
        onClose={() => setIsUploadModalOpen(false)} 
        onSuccess={() => {
          if (typeof window !== "undefined" && hasSessionHint()) {
            checkAuthAndLoad();
          }
        }}
      />

      <TaxExportModal
        isOpen={isTaxModalOpen}
        onClose={() => setIsTaxModalOpen(false)}
        insurances={insurances}
        userEmail={currentUser?.email}
      />
    </div>
  );
}
