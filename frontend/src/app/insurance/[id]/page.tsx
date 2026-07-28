"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { UploadModal } from "@/components/UploadModal";
import { CompanyLogo } from "@/components/CompanyLogo";
import { CancellationModal } from "@/components/CancellationModal";
import { api } from "@/lib/api";
import { Eye, RefreshCw, Pencil, Trash2 } from "lucide-react";

interface PremiumHistoryItem {
  id: number;
  cost: number;
  payment_cycle: string;
  annual_cost: number;
  effective_date?: string;
  note?: string;
}

interface Insurance {
  id: number;
  name: string;
  company: string;
  insurance_number: string;
  category: string;
  cost: number;
  payment_cycle: string;
  start_date: string;
  end_date: string;
  cancellation_date: string;
  contact_info: string;
  coverage_details?: string[];
  notes?: string;
  sf_class?: string;
  regional_class?: string;
  type_class?: string;
  is_suspended?: boolean;
  suspension_reason?: string;
  price_change_pct?: number;
  premium_history?: PremiumHistoryItem[];
}

interface DocumentItem {
  id: number;
  original_filename: string;
  filename: string;
  custom_name?: string;
  doc_type?: string;
  upload_date: string;
}

export default function InsuranceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const insuranceId = params.id as string;

  const [currentUser, setCurrentUser] = useState<any>(null);
  const [insurance, setInsurance] = useState<Insurance | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Tab State
  const [activeTab, setActiveTab] = useState<"stammdaten" | "historie" | "dokumente" | "schaden" | "notizen">("stammdaten");

  // Edit form state
  const [formData, setFormData] = useState({
    name: "",
    company: "",
    insurance_number: "",
    category: "",
    cost: "",
    payment_cycle: "jährlich",
    start_date: "",
    end_date: "",
    cancellation_date: "",
    sf_class: "",
    regional_class: "",
    type_class: "",
    is_suspended: false,
    suspension_reason: ""
  });
  const [coverageList, setCoverageList] = useState<string[]>([]);
  const [newCoverageItem, setNewCoverageItem] = useState("");

  const [saveMsg, setSaveMsg] = useState("");
  const [saveErr, setSaveErr] = useState("");
  const [saving, setSaving] = useState(false);

  // Premium History form state
  const [newHCost, setNewHCost] = useState("");
  const [newHCycle, setNewHCycle] = useState("jährlich");
  const [newHDate, setNewHDate] = useState("");
  const [newHNote, setNewHNote] = useState("");
  const [addingHistory, setAddingHistory] = useState(false);

  // Upload modal state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isCancellationModalOpen, setIsCancellationModalOpen] = useState(false);
  const [isCardDragOver, setIsCardDragOver] = useState(false);

  // Document viewer modal state
  const [viewingDoc, setViewingDoc] = useState<DocumentItem | null>(null);

  // Document edit state
  const [editingDoc, setEditingDoc] = useState<DocumentItem | null>(null);
  const [editDocName, setEditDocName] = useState("");
  const [editDocType, setEditDocType] = useState("");

  // Notes state
  const [notesText, setNotesText] = useState("");
  const [notesMsg, setNotesMsg] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);

  // Claims state
  const [claimsList, setClaimsList] = useState<any[]>([]);
  const [isAddClaimOpen, setIsAddClaimOpen] = useState(false);
  const [newClaimNum, setNewClaimNum] = useState("");
  const [newClaimDate, setNewClaimDate] = useState("");
  const [newClaimAmount, setNewClaimAmount] = useState("");
  const [newClaimStatus, setNewClaimStatus] = useState("In Bearbeitung");
  const [newClaimDesc, setNewClaimDesc] = useState("");
  const [addingClaim, setAddingClaim] = useState(false);

  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (insuranceId && insuranceId !== "undefined") {
      loadData();
    }
  }, [insuranceId]);

  const isSuspensionEligible = (cat: string) => {
    const c = (cat || "").toLowerCase();
    return (
      c.includes("kfz") || c.includes("auto") || c.includes("fahrzeug") || c.includes("motorrad") ||
      c.includes("kranken") || c.includes("pkv") || c.includes("zusatz") || c.includes("gesundheit") ||
      c.includes("leben") || c.includes("rente") || c.includes("riester") || c.includes("rürup") || c.includes("vorsorge") ||
      c.includes("berufsunfähigkeit") || c.includes("bu") || c.includes("unfall") || c.includes("rechtsschutz")
    );
  };

  const isKfzCategory = (cat: string) => {
    const c = (cat || "").toLowerCase();
    return c.includes("kfz") || c.includes("auto") || c.includes("fahrzeug") || c.includes("motorrad");
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const u = await api.get("/users/me");
      setCurrentUser(u);

      const insData = await api.get(`/insurances/${insuranceId}`);
      setInsurance(insData);

      setFormData({
        name: insData.name || "",
        company: insData.company || "",
        insurance_number: insData.insurance_number || "",
        category: insData.category || "",
        cost: insData.cost !== null && insData.cost !== undefined ? String(insData.cost) : "",
        payment_cycle: insData.payment_cycle || "jährlich",
        start_date: insData.start_date || "",
        end_date: insData.end_date || "",
        cancellation_date: insData.cancellation_date || "",
        sf_class: insData.sf_class || "",
        regional_class: insData.regional_class || "",
        type_class: insData.type_class || "",
        is_suspended: !!insData.is_suspended,
        suspension_reason: insData.suspension_reason || ""
      });

      setNotesText(insData.notes || "");
      setClaimsList(insData.claims || []);
      setCoverageList(insData.coverage_details || []);

      const docsData = await api.get(`/documents/insurance/${insuranceId}`);
      setDocuments(docsData);
    } catch (err: any) {
      console.error("Error loading insurance details:", err);
      if (err.message?.includes("401") || err.message?.includes("Unauthorized")) {
        router.push("/login");
      } else {
        setErrorMsg(err.message || "Versicherung konnte nicht geladen werden.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSaveDetails = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveMsg("");
    setSaveErr("");
    setSaving(true);

    try {
      const payload = {
        ...formData,
        cost: formData.cost ? parseFloat(formData.cost.replace(',', '.')) : null,
        coverage_details: coverageList
      };
      const updated = await api.put(`/insurances/${insuranceId}`, payload);
      setInsurance(updated);
      setCoverageList(updated.coverage_details || []);
      setSaveMsg("Versicherungsdaten & Leistungen erfolgreich gespeichert!");
    } catch (err: any) {
      setSaveErr(err.message || "Fehler beim Speichern der Änderungen.");
    } finally {
      setSaving(false);
    }
  };

  const handleAddCoverageItem = () => {
    if (!newCoverageItem.trim()) return;
    setCoverageList([...coverageList, newCoverageItem.trim()]);
    setNewCoverageItem("");
  };

  const handleRemoveCoverageItem = (idx: number) => {
    setCoverageList(coverageList.filter((_, i) => i !== idx));
  };

  const handleSaveNotes = async () => {
    setNotesMsg("");
    setSavingNotes(true);
    try {
      await api.put(`/insurances/${insuranceId}/notes`, { notes: notesText });
      setNotesMsg("Speichert...");
      setTimeout(() => setNotesMsg("Gespeichert!"), 600);
      setTimeout(() => setNotesMsg(""), 2500);
    } catch (err: any) {
      alert(err.message || "Fehler beim Speichern der Notiz.");
    } finally {
      setSavingNotes(false);
    }
  };

  const handleAddClaim = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddingClaim(true);
    try {
      const payload = {
        claim_number: newClaimNum || undefined,
        claim_date: newClaimDate || undefined,
        amount: newClaimAmount ? parseFloat(newClaimAmount.replace(',', '.')) : null,
        status: newClaimStatus,
        description: newClaimDesc || undefined
      };
      const added = await api.post(`/insurances/${insuranceId}/claims`, payload);
      setClaimsList([...claimsList, added]);
      setIsAddClaimOpen(false);
      setNewClaimNum("");
      setNewClaimDate("");
      setNewClaimAmount("");
      setNewClaimStatus("In Bearbeitung");
      setNewClaimDesc("");
    } catch (err: any) {
      alert(err.message || "Fehler beim Hinzufügen der Schadensmeldung.");
    } finally {
      setAddingClaim(false);
    }
  };

  const handleDeleteClaim = async (claimId: number) => {
    if (!window.confirm("Möchtest du diese Schadensmeldung wirklich löschen?")) return;
    try {
      await api.delete(`/insurances/${insuranceId}/claims/${claimId}`);
      setClaimsList(claimsList.filter(c => c.id !== claimId));
    } catch (err: any) {
      alert(err.message || "Fehler beim Löschen der Schadensmeldung.");
    }
  };

  const handleAddPremiumHistory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHCost) return;
    setAddingHistory(true);
    try {
      const payload = {
        cost: parseFloat(newHCost.replace(',', '.')),
        payment_cycle: newHCycle,
        effective_date: newHDate || undefined,
        note: newHNote || "Beitragsanpassung"
      };
      await api.post(`/insurances/${insuranceId}/premium-history`, payload);
      setNewHCost("");
      setNewHNote("");
      setNewHDate("");
      loadData();
    } catch (err: any) {
      alert(err.message || "Fehler beim Hinzufügen der Beitragsanpassung.");
    } finally {
      setAddingHistory(false);
    }
  };

  const handleDeletePremiumHistory = async (historyId: number) => {
    if (!window.confirm("Möchtest du diesen historischen Beitrags-Eintrag wirklich löschen?")) return;
    try {
      await api.delete(`/insurances/${insuranceId}/premium-history/${historyId}`);
      loadData();
    } catch (err: any) {
      alert(err.message || "Fehler beim Löschen.");
    }
  };

  const handleDeleteInsurance = async () => {
    if (!window.confirm(`⚠️ ACHTUNG: Möchtest du die Versicherung "${insurance?.name}" wirklich unwiderruflich löschen? Alle verknüpften Dokumente und Notizen werden ebenfalls entfernt.`)) {
      return;
    }
    try {
      await api.delete(`/insurances/${insuranceId}`);
      router.push("/");
    } catch (err: any) {
      alert(err.message || "Fehler beim Löschen der Versicherung.");
    }
  };

  const handleSaveDocEdit = async (docId: number) => {
    try {
      const updated = await api.put(`/documents/${docId}`, {
        custom_name: editDocName,
        doc_type: editDocType
      });
      setDocuments(prev => prev.map(d => d.id === docId ? { ...d, custom_name: updated.custom_name, doc_type: updated.doc_type } : d));
      setEditingDoc(null);
    } catch (err: any) {
      alert(err.message || "Fehler beim Speichern des Dokuments.");
    }
  };

  const [analyzingDocId, setAnalyzingDocId] = useState<number | null>(null);

  const handleReanalyzeDoc = async (docId: number) => {
    setAnalyzingDocId(docId);
    try {
      const res = await api.post(`/documents/${docId}/reanalyze`, {});
      alert(res.message || "Dokument erfolgreich erneut analysiert!");
      loadData();
    } catch (err: any) {
      alert(err.message || "Fehler bei der erneuten Dokumenten-Analyse.");
    } finally {
      setAnalyzingDocId(null);
    }
  };

  const handleDeleteDoc = async (docId: number, name: string) => {
    if (!window.confirm(`Möchtest du das Dokument "${name}" wirklich löschen?`)) return;
    try {
      await api.delete(`/documents/${docId}`);
      setDocuments(prev => prev.filter(d => d.id !== docId));
    } catch (err: any) {
      alert(err.message || "Fehler beim Löschen des Dokuments.");
    }
  };

  const handleCardDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsCardDragOver(true);
  };

  const handleCardDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsCardDragOver(false);
  };

  const handleCardDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsCardDragOver(false);
    setIsUploadModalOpen(true);
  };

  if (loading || !insurance) {
    return null;
  }

  const handleDownloadIcal = () => {
    if (!insurance) return;
    const deadlineStr = insurance.cancellation_date || insurance.end_date;
    if (!deadlineStr) {
      alert("Für diese Versicherung ist keine Kündigungsfrist eingetragen.");
      return;
    }

    const dateObj = new Date(deadlineStr);
    const formattedDate = dateObj.toISOString().replace(/-|:|\.\d+/g, "").substring(0, 8);

    const icsContent = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//Noxus Policy//DE",
      "CALSCALE:GREGORIAN",
      "METHOD:PUBLISH",
      "BEGIN:VEVENT",
      `UID:noxus-policy-single-${insurance.id}-${formattedDate}@noxus-policy`,
      `SUMMARY:⏰ Kündigungsfrist: ${insurance.name} (${insurance.company || "Unbekannt"})`,
      `DESCRIPTION:Kündigungsfrist für ${insurance.name} bei ${insurance.company || "Gesellschaft k.A."}.\\nSchein-Nr: ${insurance.insurance_number || "k.A."}\\nKosten: ${insurance.cost ? insurance.cost.toFixed(2) + " €" : "k.A."}`,
      `DTSTART;VALUE=DATE:${formattedDate}`,
      `DTEND;VALUE=DATE:${formattedDate}`,
      "STATUS:CONFIRMED",
      "BEGIN:VALARM",
      "ACTION:DISPLAY",
      "DESCRIPTION:Erinnerung Kündigungsfrist in 14 Tagen",
      "TRIGGER:-P14D",
      "END:VALARM",
      "BEGIN:VALARM",
      "ACTION:DISPLAY",
      "DESCRIPTION:Eilige Erinnerung Kündigungsfrist in 7 Tagen",
      "TRIGGER:-P7D",
      "END:VALARM",
      "END:VEVENT",
      "END:VCALENDAR"
    ].join("\r\n");

    const blob = new Blob([icsContent], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Kuendigung_${(insurance.name || "Versicherung").replace(/[^a-zA-Z0-9]/g, "_")}.ics`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const historyEntries = insurance.premium_history || [];
  const maxHistoryCost = historyEntries.length > 0 
    ? Math.max(...historyEntries.map(h => h.annual_cost || 0), insurance.cost || 1) 
    : (insurance.cost || 1);

  return (
    <div className="space-y-6 flex-1">
      <Navbar userEmail={currentUser?.email} />

      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-5 border-b border-zinc-800/80 pb-5">
          <div className="flex items-start gap-3 sm:gap-4">
            <CompanyLogo company={insurance.company || insurance.name} size="lg" className="mt-1 shrink-0" />
            <div>
              <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
                <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">{insurance.name}</h1>
                <span className="text-xs font-mono px-2.5 py-1 rounded-md theme-bg-accent text-white font-medium shadow-md">
                  {insurance.category || "Versicherung"}
                </span>

                {insurance.is_suspended && (
                  <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-amber-950/90 border border-amber-700 text-amber-300 font-bold shadow-md">
                    ⏸️ Vertrag ruht
                  </span>
                )}

                <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-indigo-950/80 border border-indigo-800/80 text-indigo-300 font-bold">
                  📋 VSN: {insurance.insurance_number || "Nicht angegeben"}
                </span>

                {insurance.cost && (
                  <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-emerald-950/80 border border-emerald-800 text-emerald-300 font-bold">
                    💰 {insurance.cost.toFixed(2)} € / {insurance.payment_cycle || "Jahr"}
                  </span>
                )}

                {insurance.price_change_pct !== undefined && insurance.price_change_pct !== null && insurance.price_change_pct !== 0 && (
                  <span className={`text-xs font-mono px-2.5 py-1 rounded-md font-bold shadow-md border ${
                    insurance.price_change_pct > 0 
                      ? "bg-rose-950/90 border-rose-800 text-rose-300" 
                      : "bg-emerald-950/90 border-emerald-800 text-emerald-300"
                  }`}>
                    {insurance.price_change_pct > 0 ? `📈 +${insurance.price_change_pct}% Erhöhung` : `📉 ${insurance.price_change_pct}% Senkung`}
                  </span>
                )}
              </div>

              {/* KFZ Badges */}
              {(insurance.sf_class || insurance.regional_class || insurance.type_class) && (
                <div className="flex items-center gap-2 flex-wrap mt-2">
                  {insurance.sf_class && (
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-800 text-cyan-300 font-bold">
                      🚗 {insurance.sf_class}
                    </span>
                  )}
                  {insurance.regional_class && (
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-violet-950/80 border border-violet-800 text-violet-300 font-bold">
                      📍 Regio: {insurance.regional_class}
                    </span>
                  )}
                  {insurance.type_class && (
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-800 text-indigo-300 font-bold">
                      🚘 Typklasse: {insurance.type_class}
                    </span>
                  )}
                </div>
              )}

              <p className="text-xs sm:text-sm text-zinc-400 mt-2">
                Gesellschaft: <span className="text-zinc-200 font-medium">{insurance.company || "Nicht angegeben"}</span>
                {insurance.is_suspended && insurance.suspension_reason && (
                  <span className="text-amber-300 ml-2 font-mono text-xs">({insurance.suspension_reason})</span>
                )}
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full md:w-auto shrink-0 justify-start md:justify-end">
            <Button 
              onClick={() => setIsCancellationModalOpen(true)} 
              variant="outline" 
              className="border-indigo-800/80 bg-indigo-950/40 hover:bg-indigo-900/50 text-indigo-300 font-semibold text-xs transition-all shadow-md flex items-center gap-1.5 w-full sm:w-auto justify-center"
            >
              ✍️ Kündigungsschreiben
            </Button>
            <Button 
              onClick={handleDownloadIcal} 
              variant="outline" 
              className="border-amber-800/80 bg-amber-950/40 hover:bg-amber-900/50 text-amber-300 font-semibold text-xs transition-all shadow-md flex items-center gap-1.5 w-full sm:w-auto justify-center"
            >
              📅 Kalender-Termin (.ics)
            </Button>
            <Button variant="outline" onClick={() => router.push("/")} className="border-zinc-800 bg-zinc-900/50 hover:bg-zinc-800 text-zinc-300 text-xs w-full sm:w-auto justify-center">
              ← Zurück
            </Button>
          </div>
        </div>

        {/* Tab Navigation Bar */}
        <div className="flex items-center gap-1.5 border-b border-zinc-800/80 overflow-x-auto whitespace-nowrap scrollbar-none pb-2 text-sm font-medium">
          <button
            onClick={() => setActiveTab("stammdaten")}
            className={`px-4 py-2.5 rounded-xl transition-all flex items-center gap-2 font-semibold text-xs sm:text-sm ${
              activeTab === "stammdaten"
                ? "theme-bg-accent text-white shadow-lg theme-glow border border-emerald-500/50"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900/60"
            }`}
          >
            <span>📋 Stammdaten & Leistungen</span>
          </button>

          <button
            onClick={() => setActiveTab("historie")}
            className={`px-4 py-2.5 rounded-xl transition-all flex items-center gap-2 font-semibold text-xs sm:text-sm ${
              activeTab === "historie"
                ? "theme-bg-accent text-white shadow-lg theme-glow border border-emerald-500/50"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900/60"
            }`}
          >
            <span>📈 Beitragsentwicklung</span>
            {historyEntries.length > 0 && (
              <span className={`px-2 py-0.5 text-[10px] rounded-full font-mono font-bold ${
                activeTab === "historie" ? "bg-white/20 text-white" : "bg-zinc-800 text-emerald-400"
              }`}>
                {historyEntries.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("dokumente")}
            className={`px-4 py-2.5 rounded-xl transition-all flex items-center gap-2 font-semibold text-xs sm:text-sm ${
              activeTab === "dokumente"
                ? "theme-bg-accent text-white shadow-lg theme-glow border border-emerald-500/50"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900/60"
            }`}
          >
            <span>📄 Dokumente</span>
            <span className={`px-2 py-0.5 text-[10px] rounded-full font-mono font-bold ${
              activeTab === "dokumente" ? "bg-white/20 text-white" : "bg-zinc-800 text-indigo-300"
            }`}>
              {documents.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab("schaden")}
            className={`px-4 py-2.5 rounded-xl transition-all flex items-center gap-2 font-semibold text-xs sm:text-sm ${
              activeTab === "schaden"
                ? "theme-bg-accent text-white shadow-lg theme-glow border border-emerald-500/50"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900/60"
            }`}
          >
            <span>💥 Schadensfälle</span>
            {claimsList.length > 0 && (
              <span className={`px-2 py-0.5 text-[10px] rounded-full font-mono font-bold ${
                activeTab === "schaden" ? "bg-white/20 text-white" : "bg-zinc-800 text-amber-300"
              }`}>
                {claimsList.length}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("notizen")}
            className={`px-4 py-2.5 rounded-xl transition-all flex items-center gap-2 font-semibold text-xs sm:text-sm ${
              activeTab === "notizen"
                ? "theme-bg-accent text-white shadow-lg theme-glow border border-emerald-500/50"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900/60"
            }`}
          >
            <span>📝 Notizen & Memos</span>
          </button>
        </div>

        {/* Tab Content Panels */}
        <div>
          {/* TAB 1: Stammdaten & Leistungen */}
          {activeTab === "stammdaten" && (
            <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md shadow-xl">
              <CardHeader>
                <CardTitle className="text-xl font-semibold">Vertragsdetails & Stammdaten</CardTitle>
                <CardDescription>Passe die ausgelesenen Daten deiner Versicherung an.</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSaveDetails} className="space-y-6">
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="name" className="text-xs font-mono text-zinc-400">Titel der Versicherung</Label>
                      <Input id="name" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} required className="bg-zinc-950/50 border-zinc-800" />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="category" className="text-xs font-mono text-zinc-400">Versicherungsart (Kategorie)</Label>
                        <Input id="category" value={formData.category} onChange={e => setFormData({...formData, category: e.target.value})} placeholder="z.B. Haftpflicht, Kfz, Hausrat" className="bg-zinc-950/50 border-zinc-800" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="company" className="text-xs font-mono text-zinc-400">Gesellschaft</Label>
                        <Input id="company" value={formData.company} onChange={e => setFormData({...formData, company: e.target.value})} className="bg-zinc-950/50 border-zinc-800" />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="cost" className="text-xs font-mono text-emerald-400">Kosten / Beitrag (€)</Label>
                        <Input id="cost" type="number" step="0.01" value={formData.cost} onChange={e => setFormData({...formData, cost: e.target.value})} placeholder="148.50" className="bg-zinc-950/50 border-zinc-800 text-emerald-400 font-mono font-bold" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="payment_cycle" className="text-xs font-mono text-zinc-400">Zahlungsrhythmus</Label>
                        <Select value={formData.payment_cycle} onValueChange={(val) => setFormData({...formData, payment_cycle: val || "jährlich"})}>
                          <SelectTrigger className="bg-zinc-950/50 border-zinc-800">
                            <SelectValue placeholder="Rhythmus" />
                          </SelectTrigger>
                          <SelectContent className="bg-zinc-900 border-zinc-700 text-zinc-50">
                            <SelectItem value="monatlich">Monatlich</SelectItem>
                            <SelectItem value="quartalsweise">Quartalsweise</SelectItem>
                            <SelectItem value="halbjährlich">Halbjährlich</SelectItem>
                            <SelectItem value="jährlich">Jährlich</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    {/* KFZ Specific Attributes Form Row */}
                    {(isKfzCategory(formData.category) || formData.sf_class || formData.regional_class || formData.type_class) && (
                      <div className="p-4 rounded-xl bg-zinc-950/40 border border-cyan-900/40 space-y-3">
                        <h4 className="text-xs font-bold text-cyan-300 uppercase tracking-wider flex items-center gap-2">
                          <span>🚗 KFZ-Tarifmerkmale</span>
                        </h4>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                          <div className="space-y-1">
                            <Label htmlFor="sf_class" className="text-[11px] font-mono text-zinc-400">SF-Klasse</Label>
                            <Input id="sf_class" value={formData.sf_class} onChange={e => setFormData({...formData, sf_class: e.target.value})} placeholder="z.B. SF 15" className="bg-zinc-900 border-zinc-800 text-xs" />
                          </div>
                          <div className="space-y-1">
                            <Label htmlFor="regional_class" className="text-[11px] font-mono text-zinc-400">Regionalklasse</Label>
                            <Input id="regional_class" value={formData.regional_class} onChange={e => setFormData({...formData, regional_class: e.target.value})} placeholder="z.B. R4" className="bg-zinc-900 border-zinc-800 text-xs" />
                          </div>
                          <div className="space-y-1">
                            <Label htmlFor="type_class" className="text-[11px] font-mono text-zinc-400">Typklasse</Label>
                            <Input id="type_class" value={formData.type_class} onChange={e => setFormData({...formData, type_class: e.target.value})} placeholder="z.B. 18" className="bg-zinc-900 border-zinc-800 text-xs" />
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Ruhendstellung / Beitragsfreistellung Switch */}
                    {isSuspensionEligible(formData.category) && (
                      <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/80 space-y-3">
                        <div className="flex items-center justify-between">
                          <div>
                            <Label htmlFor="is_suspended" className="text-sm font-bold text-white flex items-center gap-2 cursor-pointer">
                              <span>⏸️ Vertrag ruht / ist beitragsfrei gestellt</span>
                            </Label>
                            <p className="text-xs text-zinc-400 mt-0.5">
                              Für Fahrzeug-Abmeldungen, Saison, Anwartschaften oder Beitragsfreistellungen.
                            </p>
                          </div>
                          <input
                            type="checkbox"
                            id="is_suspended"
                            checked={formData.is_suspended}
                            onChange={e => setFormData({...formData, is_suspended: e.target.checked})}
                            className="w-5 h-5 accent-amber-500 rounded cursor-pointer shrink-0"
                          />
                        </div>
                        {formData.is_suspended && (
                          <div className="pt-2 border-t border-zinc-800/60">
                            <Label htmlFor="suspension_reason" className="text-xs font-mono text-zinc-400">Grund der Ruhendstellung (optional)</Label>
                            <Input
                              id="suspension_reason"
                              value={formData.suspension_reason}
                              onChange={e => setFormData({...formData, suspension_reason: e.target.value})}
                              placeholder="z.B. Fahrzeug vorübergehend abgemeldet, Elternzeit, Anwartschaft..."
                              className="bg-zinc-900 border-zinc-800 text-xs mt-1"
                            />
                          </div>
                        )}
                      </div>
                    )}

                    <div className="space-y-2">
                      <Label htmlFor="insurance_number" className="text-xs font-mono text-zinc-400">Versicherungsnummer</Label>
                      <Input id="insurance_number" value={formData.insurance_number} onChange={e => setFormData({...formData, insurance_number: e.target.value})} className="bg-zinc-950/50 border-zinc-800" />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="start_date" className="text-xs font-mono text-zinc-400">Versicherungsbeginn</Label>
                        <Input id="start_date" type="date" value={formData.start_date} onChange={e => setFormData({...formData, start_date: e.target.value})} className="bg-zinc-950/50 border-zinc-800" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="end_date" className="text-xs font-mono text-zinc-400">Vertragsende</Label>
                        <Input id="end_date" type="date" value={formData.end_date} onChange={e => setFormData({...formData, end_date: e.target.value})} className="bg-zinc-950/50 border-zinc-800" />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="cancellation_date" className="text-xs font-mono text-amber-400">Kündigungsfrist (spätester Kündigungstermin)</Label>
                      <Input id="cancellation_date" type="date" value={formData.cancellation_date} onChange={e => setFormData({...formData, cancellation_date: e.target.value})} className="bg-zinc-950/50 border-amber-800/60 text-amber-400 font-mono" />
                    </div>
                  </div>

                  {/* Coverage Benefits Section */}
                  <div className="pt-6 border-t border-zinc-800/80 space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-base font-bold text-white flex items-center gap-2">
                          <span>🛡️ Enthaltene Versicherungsleistungen & Abdeckung</span>
                        </h3>
                        <p className="text-xs text-zinc-400 mt-0.5">
                          Automatisch aus deinen hochgeladenen Dokumenten ausgelesen.
                        </p>
                      </div>
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/80">
                        {coverageList.length} Leistungen
                      </span>
                    </div>

                    <div className="space-y-2">
                      {coverageList.map((item, idx) => (
                        <div key={idx} className="p-3 rounded-xl bg-zinc-950/60 border border-zinc-800/80 flex items-center justify-between gap-3 group hover:border-zinc-700 transition-all">
                          <div className="flex items-center gap-2.5 text-sm text-zinc-200">
                            <span className="text-emerald-400 font-bold shrink-0">✓</span>
                            <span>{item}</span>
                          </div>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => handleRemoveCoverageItem(idx)}
                            className="text-zinc-500 hover:text-red-400 h-8 w-8 p-0"
                          >
                            ✕
                          </Button>
                        </div>
                      ))}
                    </div>

                    <div className="flex gap-2 pt-2">
                      <Input
                        value={newCoverageItem}
                        onChange={e => setNewCoverageItem(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && (e.preventDefault(), handleAddCoverageItem())}
                        placeholder="z.B. Schutzbrief, Teilkasko, Schlüsselverlust..."
                        className="bg-zinc-950/50 border-zinc-800 text-xs"
                      />
                      <Button type="button" onClick={handleAddCoverageItem} variant="outline" className="border-zinc-800 bg-zinc-900 text-zinc-300 text-xs shrink-0">
                        + Hinzufügen
                      </Button>
                    </div>
                  </div>

                  {saveMsg && (
                    <div className="p-3 bg-emerald-950/50 border border-emerald-800 text-emerald-300 rounded-lg text-sm">
                      {saveMsg}
                    </div>
                  )}
                  {saveErr && <p className="text-red-400 text-sm">{saveErr}</p>}

                  <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center pt-4 border-t border-zinc-800/80 gap-3 w-full">
                    <Button type="button" variant="destructive" onClick={handleDeleteInsurance} className="bg-red-950/80 hover:bg-red-900 text-red-300 border border-red-800 text-xs w-full sm:w-auto">
                      Versicherung löschen
                    </Button>
                    <Button type="submit" disabled={saving} className="theme-bg-accent text-white theme-glow w-full sm:w-auto">
                      {saving ? "Speichert..." : "Änderungen speichern"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {/* TAB 2: Beitragsentwicklung & Preis-Historie */}
          {activeTab === "historie" && (
            <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md shadow-xl">
              <CardHeader className="pb-3 border-b border-zinc-800/60">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-xl font-semibold flex items-center gap-2">
                      <span>📈 Beitragsentwicklung & Preis-Historie</span>
                    </CardTitle>
                    <CardDescription className="text-xs mt-0.5">
                      Verfolge die Preisentwicklung deiner Beitragsanpassungen über die Jahre.
                    </CardDescription>
                  </div>
                  {insurance.price_change_pct !== undefined && insurance.price_change_pct !== null && (
                    <span className={`text-xs font-mono px-2.5 py-1 rounded-md font-bold border ${
                      insurance.price_change_pct > 0 
                        ? "bg-rose-950/90 border-rose-800 text-rose-300" 
                        : "bg-emerald-950/90 border-emerald-800 text-emerald-300"
                    }`}>
                      {insurance.price_change_pct > 0 ? `📈 +${insurance.price_change_pct}%` : `📉 ${insurance.price_change_pct}%`}
                    </span>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-6 pt-5">
                {/* Visual SVG Bar Chart */}
                {historyEntries.length > 0 ? (
                  <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/80 space-y-4">
                    <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Jahresbeitrag im Zeitverlauf</h4>
                    <div className="flex items-end justify-around h-44 gap-3 pt-6 pb-2 border-b border-zinc-800/80 px-4">
                      {historyEntries.map((h, i) => {
                        const heightPct = maxHistoryCost > 0 ? Math.max(15, Math.round((h.annual_cost / maxHistoryCost) * 100)) : 20;
                        const dateLabel = h.effective_date ? new Date(h.effective_date).getFullYear().toString() : `Eintrag ${i+1}`;
                        return (
                          <div key={h.id || i} className="flex flex-col items-center flex-1 max-w-[80px] group">
                            <span className="text-[11px] font-mono text-emerald-400 font-bold mb-1.5 opacity-90 group-hover:opacity-100">
                              {h.annual_cost.toFixed(0)}€
                            </span>
                            <div className="w-full bg-zinc-800/80 rounded-t-lg relative overflow-hidden flex items-end" style={{ height: `${heightPct}%` }}>
                              <div className="w-full h-full theme-bg-accent opacity-85 group-hover:opacity-100 transition-all rounded-t-lg shadow-md"></div>
                            </div>
                            <span className="text-xs font-mono text-zinc-300 mt-2.5 truncate w-full text-center">
                              {dateLabel}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-zinc-500 italic">Noch keine historischen Beitragsanpassungen erfasst.</p>
                )}

                {/* History Entries List */}
                {historyEntries.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Historische Anpassungen</h4>
                    <div className="divide-y divide-zinc-800/60 border border-zinc-800/80 rounded-xl overflow-hidden bg-zinc-950/40">
                      {historyEntries.map((h) => (
                        <div key={h.id} className="p-4 flex items-center justify-between gap-3 text-xs sm:text-sm">
                          <div>
                            <div className="flex items-center gap-2 font-mono font-bold text-white">
                              <span>💰 {h.cost.toFixed(2)} €</span>
                              <span className="text-xs text-zinc-400 font-normal">({h.payment_cycle})</span>
                              <span className="text-xs text-emerald-400">({h.annual_cost.toFixed(2)} € / Jahr)</span>
                            </div>
                            <div className="text-xs text-zinc-400 mt-1 flex items-center gap-2">
                              {h.effective_date && <span>Gültig ab: {h.effective_date}</span>}
                              {h.note && <span className="italic">• {h.note}</span>}
                            </div>
                          </div>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDeletePremiumHistory(h.id)}
                            className="text-zinc-500 hover:text-red-400 h-8 w-8 p-0 shrink-0"
                          >
                            ✕
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Form to Add New Price Adjustment */}
                <form onSubmit={handleAddPremiumHistory} className="p-5 rounded-xl bg-zinc-950/60 border border-zinc-800 space-y-4">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">+ Neue Beitragsanpassung eintragen</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="space-y-1">
                      <Label htmlFor="h_cost" className="text-xs font-mono text-emerald-400">Neuer Beitrag (€)</Label>
                      <Input
                        id="h_cost"
                        type="number"
                        step="0.01"
                        value={newHCost}
                        onChange={e => setNewHCost(e.target.value)}
                        placeholder="165.00"
                        required
                        className="bg-zinc-900 border-zinc-800 text-xs font-mono"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor="h_cycle" className="text-xs font-mono text-zinc-400">Zahlweise</Label>
                      <Select value={newHCycle} onValueChange={(val) => setNewHCycle(val || "jährlich")}>
                        <SelectTrigger className="bg-zinc-900 border-zinc-800 text-xs h-9">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-zinc-900 border-zinc-700 text-zinc-50">
                          <SelectItem value="monatlich">Monatlich</SelectItem>
                          <SelectItem value="quartalsweise">Quartalsweise</SelectItem>
                          <SelectItem value="halbjährlich">Halbjährlich</SelectItem>
                          <SelectItem value="jährlich">Jährlich</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1 col-span-1 sm:col-span-1">
                      <Label htmlFor="h_date" className="text-xs font-mono text-zinc-400">Gültig ab (Datum)</Label>
                      <Input
                        id="h_date"
                        type="date"
                        value={newHDate}
                        onChange={e => setNewHDate(e.target.value)}
                        className="bg-zinc-900 border-zinc-800 text-xs"
                      />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="h_note" className="text-xs font-mono text-zinc-400">Anlass / Notiz (optional)</Label>
                    <Input
                      id="h_note"
                      value={newHNote}
                      onChange={e => setNewHNote(e.target.value)}
                      placeholder="z.B. Jährliche Beitragsanpassung 2026..."
                      className="bg-zinc-900 border-zinc-800 text-xs"
                    />
                  </div>
                  <Button type="submit" disabled={addingHistory} className="theme-bg-accent text-white text-xs w-full mt-2">
                    {addingHistory ? "Speichert..." : "+ Beitragsanpassung speichern"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          )}

          {/* TAB 3: Dokumente */}
          {activeTab === "dokumente" && (
            <Card 
              onDragOver={handleCardDragOver}
              onDragLeave={handleCardDragLeave}
              onDrop={handleCardDrop}
              className={`border-zinc-800 bg-zinc-900/40 backdrop-blur-md shadow-xl transition-all ${
                isCardDragOver ? "border-indigo-500 bg-indigo-950/20 scale-[1.01]" : ""
              }`}
            >
              <CardHeader className="pb-3 border-b border-zinc-800/60">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xl font-semibold flex items-center gap-2">
                    <span>📄 Hinterlegte Dokumente ({documents.length})</span>
                  </CardTitle>
                  <Button 
                    onClick={() => setIsUploadModalOpen(true)} 
                    size="sm" 
                    className="theme-bg-accent text-white text-xs font-medium"
                  >
                    + Hinzufügen
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="pt-5 space-y-4">
                {documents.length > 0 ? (
                  <div className="space-y-3">
                    {documents.map((doc) => (
                      <div key={doc.id} className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/80 flex items-center justify-between gap-4 group hover:border-zinc-700 transition-all">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="w-10 h-10 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center text-xl shrink-0">
                            📄
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-white truncate">
                              {doc.custom_name || doc.original_filename}
                            </p>
                            <p className="text-xs text-zinc-500 font-mono mt-0.5">
                              {doc.doc_type || "Dokument"} • Hochgeladen: {new Date(doc.upload_date).toLocaleDateString("de-DE")}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-1.5 shrink-0">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setViewingDoc(doc)}
                            className="border-zinc-800 bg-zinc-900/80 hover:bg-zinc-800 text-zinc-300 h-8 w-8 p-0 flex items-center justify-center rounded-lg transition-colors"
                            title="Dokument anzeigen (PDF Vorschau)"
                          >
                            <Eye className="w-4 h-4 text-zinc-300" />
                          </Button>

                          <Button
                            size="sm"
                            variant="outline"
                            disabled={analyzingDocId === doc.id}
                            onClick={() => handleReanalyzeDoc(doc.id)}
                            className="border-zinc-800 bg-zinc-900/80 hover:bg-zinc-800 text-zinc-300 h-8 w-8 p-0 flex items-center justify-center rounded-lg transition-colors"
                            title="Dokument erneut analysieren & Stammdaten aktualisieren"
                          >
                            <RefreshCw className={`w-4 h-4 text-zinc-300 ${analyzingDocId === doc.id ? "animate-spin text-indigo-400" : ""}`} />
                          </Button>

                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setEditingDoc(doc);
                              setEditDocName(doc.custom_name || doc.original_filename);
                              setEditDocType(doc.doc_type || "Dokument");
                            }}
                            className="border-zinc-800 bg-zinc-900/80 hover:bg-zinc-800 text-zinc-300 h-8 w-8 p-0 flex items-center justify-center rounded-lg transition-colors"
                            title="Eigenschaften bearbeiten"
                          >
                            <Pencil className="w-4 h-4 text-zinc-300" />
                          </Button>

                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleDeleteDoc(doc.id, doc.custom_name || doc.original_filename)}
                            className="border-zinc-800 bg-zinc-900/80 hover:bg-red-950/50 hover:border-red-800/80 text-zinc-400 hover:text-red-300 h-8 w-8 p-0 flex items-center justify-center rounded-lg transition-colors"
                            title="Dokument löschen"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-12 text-center border-2 border-dashed border-zinc-800 rounded-xl bg-zinc-950/20">
                    <p className="text-sm text-zinc-400">Keine Dokumente hinterlegt.</p>
                    <p className="text-xs text-zinc-500 mt-1">Ziehe eine PDF hierher oder klicke oben auf Hinzufügen.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* TAB 4: Schadensfälle */}
          {activeTab === "schaden" && (
            <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md shadow-xl">
              <CardHeader className="pb-3 border-b border-zinc-800/60">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xl font-semibold flex items-center gap-2">
                    <span>💥 Schadensfall-Tracker</span>
                  </CardTitle>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setIsAddClaimOpen(!isAddClaimOpen)}
                    className="border-indigo-800 bg-indigo-950/50 text-indigo-300 text-xs hover:bg-indigo-900"
                  >
                    + Schaden melden
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="pt-5 space-y-4">
                {isAddClaimOpen && (
                  <form onSubmit={handleAddClaim} className="p-5 rounded-xl bg-zinc-950/60 border border-zinc-800 space-y-4">
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">Neuen Schadensfall erfassen</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label htmlFor="c_num" className="text-xs font-mono text-zinc-400">Schadennummer</Label>
                        <Input
                          id="c_num"
                          value={newClaimNum}
                          onChange={e => setNewClaimNum(e.target.value)}
                          placeholder="z.B. SCH-2026-001"
                          className="bg-zinc-900 border-zinc-800 text-xs"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor="c_date" className="text-xs font-mono text-zinc-400">Schadendatum</Label>
                        <Input
                          id="c_date"
                          type="date"
                          value={newClaimDate}
                          onChange={e => setNewClaimDate(e.target.value)}
                          className="bg-zinc-900 border-zinc-800 text-xs"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label htmlFor="c_amount" className="text-xs font-mono text-zinc-400">Schadenshöhe (€)</Label>
                        <Input
                          id="c_amount"
                          type="number"
                          step="0.01"
                          value={newClaimAmount}
                          onChange={e => setNewClaimAmount(e.target.value)}
                          placeholder="z.B. 450.00"
                          className="bg-zinc-900 border-zinc-800 text-xs font-mono"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor="c_status" className="text-xs font-mono text-zinc-400">Status</Label>
                        <Select value={newClaimStatus} onValueChange={(val) => setNewClaimStatus(val || "In Bearbeitung")}>
                          <SelectTrigger className="bg-zinc-900 border-zinc-800 text-xs h-9">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-zinc-900 border-zinc-700 text-zinc-50">
                            <SelectItem value="In Bearbeitung">In Bearbeitung</SelectItem>
                            <SelectItem value="Erstattet / Reguliert">Erstattet / Reguliert</SelectItem>
                            <SelectItem value="Abgelehnt">Abgelehnt</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor="c_desc" className="text-xs font-mono text-zinc-400">Beschreibung des Schadens</Label>
                      <Input
                        id="c_desc"
                        value={newClaimDesc}
                        onChange={e => setNewClaimDesc(e.target.value)}
                        placeholder="z.B. Steinschlag Windschutzscheibe, Wildunfall..."
                        className="bg-zinc-900 border-zinc-800 text-xs"
                      />
                    </div>
                    <div className="flex justify-end gap-2 pt-1">
                      <Button type="button" variant="ghost" onClick={() => setIsAddClaimOpen(false)} className="text-xs h-8">Abbrechen</Button>
                      <Button type="submit" disabled={addingClaim} className="theme-bg-accent text-white text-xs h-8">
                        {addingClaim ? "Speichert..." : "Schadensfall speichern"}
                      </Button>
                    </div>
                  </form>
                )}

                {claimsList.length > 0 ? (
                  <div className="space-y-3">
                    {claimsList.map((claim) => (
                      <div key={claim.id} className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/80 flex items-start justify-between gap-3 group hover:border-zinc-700 transition-all">
                        <div className="space-y-1.5 text-xs sm:text-sm">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-white">{claim.claim_number || "Schadensfall"}</span>
                            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                              claim.status === "Erstattet / Reguliert" 
                                ? "bg-emerald-950/80 text-emerald-300 border-emerald-800" 
                                : claim.status === "Abgelehnt"
                                ? "bg-red-950/80 text-red-300 border-red-800"
                                : "bg-amber-950/80 text-amber-300 border-amber-800"
                            }`}>
                              {claim.status}
                            </span>
                          </div>
                          {claim.description && <p className="text-zinc-300">{claim.description}</p>}
                          <div className="flex items-center gap-4 text-xs text-zinc-400 font-mono">
                            {claim.claim_date && <span>Datum: {claim.claim_date}</span>}
                            {claim.amount !== null && claim.amount !== undefined && <span className="text-emerald-400 font-bold">Höhe: {claim.amount.toFixed(2)} €</span>}
                          </div>
                        </div>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDeleteClaim(claim.id)}
                          className="text-zinc-500 hover:text-red-400 h-8 w-8 p-0 shrink-0"
                        >
                          ✕
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-zinc-500 italic">Keine Schadensfälle für diese Versicherung eingetragen.</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* TAB 5: Notizen & Memos */}
          {activeTab === "notizen" && (
            <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md shadow-xl">
              <CardHeader className="pb-3 border-b border-zinc-800/60">
                <CardTitle className="text-xl font-semibold flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <span>📝 Notizen & Persönliche Memos</span>
                  </span>
                  {notesMsg && <span className="text-xs text-emerald-400 font-normal">{notesMsg}</span>}
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-5 space-y-4">
                <textarea
                  rows={8}
                  value={notesText}
                  onChange={e => setNotesText(e.target.value)}
                  placeholder="Hinterlege hier eigene Notizen, z.B. Selbstbeteiligung 150€, Ansprechpartner, Hotline-Nummer für Pannen, Schadens-Protokolle..."
                  className="w-full rounded-xl bg-zinc-950/60 border border-zinc-800/80 p-4 text-xs sm:text-sm text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-700"
                />
                <div className="flex justify-end">
                  <Button
                    type="button"
                    onClick={handleSaveNotes}
                    disabled={savingNotes}
                    className="border-zinc-800 bg-zinc-900 text-zinc-300 text-xs hover:bg-zinc-800 px-4 py-2"
                    variant="outline"
                  >
                    {savingNotes ? "Speichert..." : "Notizen speichern"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Upload Modal */}
      {isUploadModalOpen && (
        <UploadModal 
          isOpen={isUploadModalOpen} 
          onClose={() => setIsUploadModalOpen(false)} 
          targetInsuranceId={Number(insuranceId)}
          onSuccess={() => loadData()}
        />
      )}

      {/* Cancellation Modal */}
      {isCancellationModalOpen && (
        <CancellationModal
          isOpen={isCancellationModalOpen}
          onClose={() => setIsCancellationModalOpen(false)}
          insurance={insurance}
        />
      )}

      {/* Document View Modal */}
      {viewingDoc && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/50">
              <div>
                <h3 className="text-sm font-bold text-white">{viewingDoc.custom_name || viewingDoc.original_filename}</h3>
                <p className="text-xs text-zinc-400 font-mono">{viewingDoc.doc_type || "Dokument"}</p>
              </div>
              <Button variant="ghost" onClick={() => setViewingDoc(null)} className="text-zinc-400 hover:text-white h-8 w-8 p-0">✕</Button>
            </div>
            <div className="flex-1 p-2 bg-zinc-950 overflow-auto min-h-[500px]">
              <iframe
                src={`/api/documents/${viewingDoc.id}/view`}
                className="w-full h-full min-h-[500px] border-0 rounded-lg"
                title="Dokument-Vorschau"
              />
            </div>
          </div>
        </div>
      )}

      {/* Document Edit Modal */}
      {editingDoc && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white">Dokument-Eigenschaften bearbeiten</h3>
            <div className="space-y-3">
              <div className="space-y-1">
                <Label htmlFor="doc_name" className="text-xs text-zinc-400">Anzeigename</Label>
                <Input id="doc_name" value={editDocName} onChange={e => setEditDocName(e.target.value)} className="bg-zinc-950 border-zinc-800 text-xs" />
              </div>
              <div className="space-y-1">
                <Label htmlFor="doc_type_sel" className="text-xs text-zinc-400">Dokumententyp</Label>
                <Input id="doc_type_sel" value={editDocType} onChange={e => setEditDocType(e.target.value)} placeholder="z.B. Polizze, Rechnung, Beitragsanpassung..." className="bg-zinc-950 border-zinc-800 text-xs" />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" onClick={() => setEditingDoc(null)} className="text-xs h-8">Abbrechen</Button>
              <Button onClick={() => handleSaveDocEdit(editingDoc.id)} className="theme-bg-accent text-white text-xs h-8">Speichern</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
