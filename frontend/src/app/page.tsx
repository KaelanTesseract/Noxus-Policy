"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { UploadModal } from "@/components/UploadModal";
import { CompanyLogo } from "@/components/CompanyLogo";
import { useTheme } from "@/components/ThemeProvider";

const CATEGORY_COLORS = [
  { bg: "bg-indigo-500", text: "text-indigo-400", border: "border-indigo-500/30", lightBg: "bg-indigo-500/10" },
  { bg: "bg-emerald-500", text: "text-emerald-400", border: "border-emerald-500/30", lightBg: "bg-emerald-500/10" },
  { bg: "bg-violet-500", text: "text-violet-400", border: "border-violet-500/30", lightBg: "bg-violet-500/10" },
  { bg: "bg-cyan-500", text: "text-cyan-400", border: "border-cyan-500/30", lightBg: "bg-cyan-500/10" },
  { bg: "bg-amber-500", text: "text-amber-400", border: "border-amber-500/30", lightBg: "bg-amber-500/10" },
  { bg: "bg-rose-500", text: "text-rose-400", border: "border-rose-500/30", lightBg: "bg-rose-500/10" },
];

export default function Dashboard() {
  const router = useRouter();
  const { showCostChart } = useTheme();
  const [insurances, setInsurances] = useState<any[]>([]);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<any>(null);
  
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Filter & Search States
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [sortBy, setSortBy] = useState("fristen");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("token");
      if (!token) {
        window.location.href = "/login";
        return;
      }
      checkAuthAndLoad(token);
    }
  }, []);

  const checkAuthAndLoad = async (token: string) => {
    try {
      const userRes = await fetch("/api/users/me", {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!userRes.ok) {
        localStorage.removeItem("token");
        window.location.href = "/login";
        return;
      }

      const userData = await userRes.json();
      if (userData.must_change_password) {
        window.location.href = "/admin-setup";
        return;
      }
      setCurrentUser(userData);

      const res = await fetch("/api/insurances", {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (!res.ok) {
        localStorage.removeItem("token");
        window.location.href = "/login";
        return;
      }
      
      const data = await res.json();
      setInsurances(data);
      setIsAuthenticated(true);
    } catch (e) {
      console.error(e);
      localStorage.removeItem("token");
      window.location.href = "/login";
    } finally {
      setIsCheckingAuth(false);
    }
  };

  const totalCostAnnual = insurances.reduce((acc, ins) => acc + (ins.cost || 0), 0);

  // Calculate category statistics & breakdown
  const categoryStats = insurances.reduce((acc: any, ins: any) => {
    const cat = ins.category || "Sonstige";
    if (!acc[cat]) {
      acc[cat] = { count: 0, cost: 0 };
    }
    acc[cat].count += 1;
    acc[cat].cost += ins.cost || 0;
    return acc;
  }, {});

  const categoryList = Object.entries(categoryStats).map(([cat, data]: [string, any], index: number) => ({
    name: cat,
    count: data.count,
    cost: data.cost,
    percentage: totalCostAnnual > 0 ? Math.round((data.cost / totalCostAnnual) * 100) : 0,
    style: CATEGORY_COLORS[index % CATEGORY_COLORS.length]
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
      return (b.cost || 0) - (a.cost || 0);
    }
    if (sortBy === "name") {
      return (a.name || "").localeCompare(b.name || "");
    }
    if (sortBy === "fristen") {
      if (!a.cancellation_deadline) return 1;
      if (!b.cancellation_deadline) return -1;
      return a.cancellation_deadline.localeCompare(b.cancellation_deadline);
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
      />

      <div className="space-y-6 flex-1">
        {/* Metric Quick Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="border-zinc-800/80 bg-zinc-900/40 backdrop-blur-md relative overflow-hidden group hover:border-zinc-700 transition-all">
            <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-indigo-500/10 to-transparent rounded-bl-full pointer-events-none"></div>
            <CardContent className="p-5 flex items-center justify-between">
              <div>
                <p className="text-xs font-mono uppercase tracking-wider text-zinc-400">Aktive Policen</p>
                <h3 className="text-3xl font-bold text-white mt-1">{insurances.length}</h3>
              </div>
              <div className="w-12 h-12 rounded-xl bg-zinc-800/80 border border-zinc-700/50 flex items-center justify-center text-xl text-zinc-200">
                🛡️
              </div>
            </CardContent>
          </Card>

          <Card className="border-zinc-800/80 bg-zinc-900/40 backdrop-blur-md relative overflow-hidden group hover:border-zinc-700 transition-all">
            <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-emerald-500/10 to-transparent rounded-bl-full pointer-events-none"></div>
            <CardContent className="p-5 flex items-center justify-between">
              <div>
                <p className="text-xs font-mono uppercase tracking-wider text-zinc-400">Gesamtkosten / Jahr</p>
                <h3 className="text-2xl font-bold text-emerald-400 mt-1">
                  {totalCostAnnual > 0 ? `${totalCostAnnual.toFixed(2)} €` : "0,00 €"}
                </h3>
              </div>
              <div className="w-12 h-12 rounded-xl bg-emerald-950/40 border border-emerald-800/50 flex items-center justify-center text-xl text-emerald-300">
                💰
              </div>
            </CardContent>
          </Card>

          <Card className="border-zinc-800/80 bg-zinc-900/40 backdrop-blur-md relative overflow-hidden group hover:border-zinc-700 transition-all">
            <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-amber-500/10 to-transparent rounded-bl-full pointer-events-none"></div>
            <CardContent className="p-5 flex items-center justify-between">
              <div>
                <p className="text-xs font-mono uppercase tracking-wider text-zinc-400">Kündigungsfristen</p>
                <h3 className="text-sm font-semibold text-amber-300 mt-2">
                  {insurances.length > 0 ? "Überwachung aktiv" : "Keine Fristen"}
                </h3>
              </div>
              <div className="w-12 h-12 rounded-xl bg-amber-950/40 border border-amber-800/50 flex items-center justify-center text-xl text-amber-300">
                ⏰
              </div>
            </CardContent>
          </Card>

          <Card className="border-zinc-800/80 bg-zinc-900/40 backdrop-blur-md relative overflow-hidden group hover:border-zinc-700 transition-all">
            <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-br from-cyan-500/10 to-transparent rounded-bl-full pointer-events-none"></div>
            <CardContent className="p-5 flex items-center justify-between">
              <div>
                <p className="text-xs font-mono uppercase tracking-wider text-zinc-400">AI OCR Vision Engine</p>
                <div className="flex items-center gap-1.5 mt-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                  <span className="text-xs font-mono font-medium text-emerald-400">BEREIT</span>
                </div>
              </div>
              <div className="w-12 h-12 rounded-xl bg-cyan-950/40 border border-cyan-800/50 flex items-center justify-center text-xl text-cyan-300">
                ⚡
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Visual Category & Cost Distribution Diagram */}
        {showCostChart && categoryList.length > 0 && (
          <Card className="border-zinc-800/80 bg-zinc-900/40 backdrop-blur-md overflow-hidden">
            <CardHeader className="pb-3 border-b border-zinc-800/60">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                    <span>📊 Kosten-Verteilung nach Sparten</span>
                  </CardTitle>
                  <p className="text-xs text-zinc-400 mt-0.5">Übersicht deiner Ausgaben aufgeschlüsselt nach Versicherungskategorie</p>
                </div>
                {selectedCategory !== "all" && (
                  <Button 
                    onClick={() => setSelectedCategory("all")} 
                    variant="ghost" 
                    size="sm" 
                    className="text-xs text-zinc-400 hover:text-white h-8 self-start sm:self-auto"
                  >
                    ✕ Filter zurücksetzen
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              {/* Stacked Percentage Bar */}
              <div className="w-full h-3.5 bg-zinc-800/80 rounded-full overflow-hidden flex gap-0.5 p-0.5 border border-zinc-700/50">
                {categoryList.map((cat) => (
                  <div
                    key={cat.name}
                    style={{ width: `${Math.max(cat.percentage, 4)}%` }}
                    className={`h-full ${cat.style.bg} transition-all duration-500 rounded-sm cursor-pointer hover:opacity-80`}
                    title={`${cat.name}: ${cat.cost.toFixed(2)} € (${cat.percentage}%)`}
                    onClick={() => setSelectedCategory(cat.name)}
                  />
                ))}
              </div>

              {/* Interactive Category Chips Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
                {categoryList.map((cat) => {
                  const isSelected = selectedCategory.toLowerCase() === cat.name.toLowerCase();
                  return (
                    <div
                      key={cat.name}
                      onClick={() => setSelectedCategory(isSelected ? "all" : cat.name)}
                      className={`p-2.5 rounded-xl border text-xs font-mono cursor-pointer transition-all ${
                        isSelected 
                          ? `${cat.style.border} ${cat.style.lightBg} ring-1 ring-white/20 shadow-md` 
                          : "border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800/60"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className={`font-bold ${cat.style.text} truncate`}>{cat.name}</span>
                        <span className="text-[10px] text-zinc-400 px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700">
                          {cat.count}x
                        </span>
                      </div>
                      <div className="flex justify-between items-baseline text-zinc-300">
                        <span className="font-semibold text-white">{cat.cost.toFixed(2)} €</span>
                        <span className="text-[10px] text-zinc-500">{cat.percentage}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Filter & Search Toolbar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800/80 pb-4">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <span>Meine Versicherungs-Policen</span>
              <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
                {filteredInsurances.length} von {insurances.length}
              </span>
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">Durchsuche und verwalte deine aktiv ausgelesenen Verträge</p>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-3">
            {/* Search Input */}
            <div className="relative w-full sm:w-64">
              <Input
                type="text"
                placeholder="🔍 Suche nach Name, Anzieher..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-zinc-900/60 border-zinc-800 text-xs pl-8 placeholder:text-zinc-500 rounded-xl"
              />
              <svg className="w-3.5 h-3.5 absolute left-2.5 top-3 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>

            {/* Sort Select */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-zinc-900/60 border border-zinc-800 text-xs text-zinc-300 px-3 py-2 rounded-xl outline-none cursor-pointer w-full sm:w-auto"
            >
              <option value="fristen">⏳ Sortieren: Fristen demnächst</option>
              <option value="cost">💰 Sortieren: Kosten (höchste)</option>
              <option value="name">🔤 Sortieren: Name (A - Z)</option>
            </select>
          </div>
        </div>

        {/* Insurance Cards Grid */}
        {filteredInsurances.length === 0 ? (
          <div className="text-center py-12 bg-zinc-900/20 border border-zinc-800/60 rounded-2xl p-8 space-y-3">
            <span className="text-3xl">🔎</span>
            <h3 className="text-base font-bold text-white">Keine Versicherungen gefunden</h3>
            <p className="text-xs text-zinc-400 max-w-md mx-auto">
              {searchQuery || selectedCategory !== "all" 
                ? "Keine Ergebnisse für deine aktuellen Filtereinstellungen. Ändere die Suche oder wähle eine andere Sparte."
                : "Du hast noch keine Versicherungspolicen hochgeladen."}
            </p>
            {(searchQuery || selectedCategory !== "all") && (
              <Button 
                onClick={() => { setSearchQuery(""); setSelectedCategory("all"); }}
                variant="outline"
                size="sm"
                className="border-zinc-700 bg-zinc-800 text-xs text-zinc-200 mt-2"
              >
                Filter zurücksetzen
              </Button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredInsurances.map((ins: any) => (
              <Card 
                key={ins.id} 
                onClick={() => router.push(`/insurance/${ins.id}`)}
                className="group cursor-pointer border-zinc-800/80 bg-zinc-900/40 hover:bg-zinc-900/80 backdrop-blur-md transition-all duration-300 hover:border-zinc-600 hover:shadow-xl hover:-translate-y-1 relative overflow-hidden flex flex-col justify-between"
              >
                <div className="absolute top-0 left-0 w-full h-[2px] theme-bg-accent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <CardHeader className="pb-2">
                  <div className="flex items-start gap-3">
                    <CompanyLogo company={ins.company || ins.name} size="md" className="mt-1" />
                    <div className="flex-1 min-w-0 space-y-1.5">
                      <CardTitle className="text-base sm:text-lg font-bold text-white group-hover:theme-text-accent transition-colors leading-snug break-words">
                        {ins.name}
                      </CardTitle>
                      <div>
                        <span className="inline-block text-[11px] px-2 py-0.5 rounded bg-zinc-800/90 text-zinc-300 font-mono border border-zinc-700/80 font-medium shadow-sm">
                          {ins.category || "Versicherung"}
                        </span>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 flex-1 flex flex-col justify-between">
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-sm text-zinc-300">
                      <span className="text-zinc-500">Gesellschaft:</span>
                      <span className="font-medium text-zinc-200">{ins.company || "Nicht angegeben"}</span>
                    </div>
                    
                    <div className="flex items-center justify-between text-xs font-mono text-zinc-400">
                      <span className="text-zinc-500">Versicherungsschein-Nr:</span>
                      <span className="bg-zinc-800/80 px-2 py-0.5 rounded text-indigo-300 border border-zinc-700/50">
                        {ins.insurance_number || "k.A."}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs font-mono text-zinc-400">
                      <span className="text-zinc-500">Beitrag / Kosten:</span>
                      <span className="font-bold text-emerald-400">
                        {ins.cost ? `${ins.cost.toFixed(2)} € / ${ins.payment_cycle || "jährlich"}` : "k.A."}
                      </span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-zinc-800/60 flex items-center justify-between text-xs font-mono">
                    <span className="text-zinc-400">Kündigungsfrist:</span>
                    <span className="text-amber-400 font-bold px-2 py-0.5 bg-amber-950/30 rounded border border-amber-800/40">
                      {ins.cancellation_deadline || "Keine Angabe"}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <UploadModal 
        isOpen={isUploadModalOpen} 
        onClose={() => setIsUploadModalOpen(false)} 
        onSuccess={() => {
          if (typeof window !== "undefined") {
            const token = localStorage.getItem("token");
            if (token) checkAuthAndLoad(token);
          }
        }}
      />
    </div>
  );
}
