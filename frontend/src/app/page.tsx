"use client"
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { UploadModal } from "@/components/UploadModal";
import { CompanyLogo } from "@/components/CompanyLogo";

export default function Dashboard() {
  const router = useRouter();
  const [insurances, setInsurances] = useState<any[]>([]);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<any>(null);
  
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

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

  if (isCheckingAuth || !isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen pb-16">
      <Navbar 
        userEmail={currentUser?.email} 
        onUploadClick={() => setIsUploadModalOpen(true)} 
      />

      <div className="space-y-8">
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

        {/* Title & Filter Bar */}
        <div className="flex justify-between items-end border-b border-zinc-800/80 pb-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <span>Meine Versicherungs-Policen</span>
              <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
                {insurances.length}
              </span>
            </h2>
            <p className="text-sm text-zinc-400 mt-1">Automatisch aus deinen hochgeladenen Dokumenten ausgelesen</p>
          </div>
        </div>

        {/* Insurance Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {insurances.map((ins: any) => (
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
                    <span className="text-indigo-300 font-bold bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800/60">
                      {ins.insurance_number || "Nicht angegeben"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-xs font-mono text-zinc-400 pt-1">
                    <span className="text-zinc-500">Beitrag / Kosten:</span>
                    <span className="text-emerald-400 font-bold">
                      {ins.cost ? `${ins.cost.toFixed(2)} € / ${ins.payment_cycle || 'Jahr'}` : "Nicht angegeben"}
                    </span>
                  </div>
                </div>

                <div className="pt-2 border-t border-zinc-800/60 flex justify-between items-center text-xs">
                  <span className="text-zinc-500">Kündigungsfrist:</span>
                  <span className="font-mono font-medium text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-800/50">
                    {ins.cancellation_date || "Nicht hinterlegt"}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}

          {/* Futuristic Empty State */}
          {insurances.length === 0 && (
            <div className="col-span-full text-center py-20 px-4 bg-zinc-900/30 backdrop-blur-md rounded-2xl border border-dashed border-zinc-800 relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-b from-indigo-500/5 via-transparent to-transparent pointer-events-none"></div>
              
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-zinc-800/80 border border-zinc-700 flex items-center justify-center text-3xl shadow-xl theme-glow">
                📂
              </div>

              <h3 className="text-xl font-bold text-zinc-200">Noch keine Versicherungen hinterlegt</h3>
              <p className="text-sm text-zinc-400 mt-2 max-w-md mx-auto">
                Lade jetzt deine erste Versicherungspolizze als PDF oder Bild hoch. Unsere AI analysiert das Dokument automatisch in Sekunden.
              </p>

              <div className="mt-6">
                <Button 
                  onClick={() => setIsUploadModalOpen(true)} 
                  className="theme-bg-accent text-white shadow-xl theme-glow transition-all hover:scale-105 font-medium px-6 py-5 rounded-xl text-base"
                >
                  <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                  </svg>
                  Erstes Dokument hochladen
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {isUploadModalOpen && (
        <UploadModal 
          isOpen={isUploadModalOpen} 
          onClose={() => setIsUploadModalOpen(false)} 
          onSuccess={() => checkAuthAndLoad(localStorage.getItem("token") || "")}
          insurances={insurances} 
        />
      )}
    </div>
  );
}
