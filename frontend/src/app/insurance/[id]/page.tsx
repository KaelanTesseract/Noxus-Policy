"use client"
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
import { api } from "@/lib/api";

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
    cancellation_date: ""
  });
  const [coverageList, setCoverageList] = useState<string[]>([]);
  const [newCoverageItem, setNewCoverageItem] = useState("");

  const [saveMsg, setSaveMsg] = useState("");
  const [saveErr, setSaveErr] = useState("");
  const [saving, setSaving] = useState(false);

  // Upload modal state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isCardDragOver, setIsCardDragOver] = useState(false);

  // Document viewer modal state
  const [viewingDoc, setViewingDoc] = useState<DocumentItem | null>(null);

  // Document edit state
  const [editingDoc, setEditingDoc] = useState<DocumentItem | null>(null);
  const [editDocName, setEditDocName] = useState("");
  const [editDocType, setEditDocType] = useState("");

  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (insuranceId && insuranceId !== "undefined") {
      loadData();
    }
  }, [insuranceId]);

  const loadData = async () => {
    if (!insuranceId || insuranceId === "undefined") return;
    try {
      const user = await api.get("/users/me");
      if (user.must_change_password) {
        router.push("/admin-setup");
        return;
      }
      setCurrentUser(user);

      const insData = await api.get(`/insurances/${insuranceId}`);
      setInsurance(insData);
      setFormData({
        name: insData.name || "",
        company: insData.company || "",
        insurance_number: insData.insurance_number || "",
        category: insData.category || "Haftpflicht",
        cost: insData.cost ? String(insData.cost) : "",
        payment_cycle: insData.payment_cycle || "jährlich",
        start_date: insData.start_date || "",
        end_date: insData.end_date || "",
        cancellation_date: insData.cancellation_date || ""
      });

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

  const handleRemoveCoverageItem = (index: number) => {
    setCoverageList(coverageList.filter((_, idx) => idx !== index));
  };

  const handleDeleteInsurance = async () => {
    if (!window.confirm(`Möchtest du die Versicherung "${insurance?.name}" wirklich unwiderruflich löschen?`)) {
      return;
    }

    try {
      await api.delete(`/insurances/${insuranceId}`);
      router.push("/");
    } catch (err: any) {
      alert("Fehler beim Löschen: " + err.message);
    }
  };

  const [reanalyzingId, setReanalyzingId] = useState<number | null>(null);

  const handleReanalyzeDocument = async (docId: number) => {
    setReanalyzingId(docId);
    try {
      const res = await api.post(`/documents/${docId}/reanalyze`, {});
      alert(res.message || "Dokument erfolgreich erneut analysiert!");
      await loadData();
    } catch (err: any) {
      alert("Fehler beim Re-Analysieren: " + (err.message || "Unbekannter Fehler"));
    } finally {
      setReanalyzingId(null);
    }
  };

  const handleDeleteDocument = async (docId: number, docName: string) => {
    if (!window.confirm(`Möchtest du das Dokument "${docName}" wirklich unwiderruflich löschen?`)) {
      return;
    }

    try {
      await api.delete(`/documents/${docId}`);
      const docsData = await api.get(`/documents/insurance/${insuranceId}`);
      setDocuments(docsData);
    } catch (err: any) {
      alert("Fehler beim Löschen des Dokuments: " + err.message);
    }
  };

  const openEditDocModal = (doc: DocumentItem) => {
    setEditingDoc(doc);
    setEditDocName(doc.custom_name || doc.original_filename);
    setEditDocType(doc.doc_type || "Versicherungsschein / Polizze");
  };

  const handleUpdateDocument = async () => {
    if (!editingDoc) return;
    try {
      await api.put(`/documents/${editingDoc.id}`, {
        custom_name: editDocName,
        doc_type: editDocType
      });
      setEditingDoc(null);
      const docsData = await api.get(`/documents/insurance/${insuranceId}`);
      setDocuments(docsData);
    } catch (err: any) {
      alert("Fehler beim Aktualisieren des Dokuments: " + err.message);
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

  return (
    <div className="min-h-screen pb-16">
      <Navbar userEmail={currentUser?.email} />

      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex justify-between items-start border-b border-zinc-800/80 pb-5">
          <div className="flex items-start gap-4">
            <CompanyLogo company={insurance.company || insurance.name} size="lg" className="mt-1" />
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-3xl font-bold tracking-tight text-white">{insurance.name}</h1>
                <span className="text-xs font-mono px-2.5 py-1 rounded-md theme-bg-accent text-white font-medium shadow-md">
                  {insurance.category || "Versicherung"}
                </span>
                <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-indigo-950/80 border border-indigo-800/80 text-indigo-300 font-bold">
                  📋 VSN: {insurance.insurance_number || "Nicht angegeben"}
                </span>
                {insurance.cost && (
                  <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-emerald-950/80 border border-emerald-800 text-emerald-300 font-bold">
                    💰 {insurance.cost.toFixed(2)} € / {insurance.payment_cycle || "Jahr"}
                  </span>
                )}
              </div>
              <p className="text-sm text-zinc-400 mt-2">
                Gesellschaft: <span className="text-zinc-200 font-medium">{insurance.company || "Nicht angegeben"}</span>
              </p>
            </div>
          </div>
          <Button variant="outline" onClick={() => router.push("/")} className="border-zinc-800 bg-zinc-900/50 hover:bg-zinc-800 text-zinc-300">
            ← Zurück zur Übersicht
          </Button>
        </div>

        {/* Content Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Insurance Form & Coverage Details */}
          <div className="lg:col-span-7 space-y-6">
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

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="category" className="text-xs font-mono text-zinc-400">Versicherungsart (Kategorie)</Label>
                        <Input id="category" value={formData.category} onChange={e => setFormData({...formData, category: e.target.value})} placeholder="z.B. Haftpflicht, Kfz, Hausrat" className="bg-zinc-950/50 border-zinc-800" />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="company" className="text-xs font-mono text-zinc-400">Gesellschaft</Label>
                        <Input id="company" value={formData.company} onChange={e => setFormData({...formData, company: e.target.value})} className="bg-zinc-950/50 border-zinc-800" />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
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

                    <div className="space-y-2">
                      <Label htmlFor="insurance_number" className="text-xs font-mono text-zinc-400">Versicherungsnummer</Label>
                      <Input id="insurance_number" value={formData.insurance_number} onChange={e => setFormData({...formData, insurance_number: e.target.value})} className="bg-zinc-950/50 border-zinc-800" />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
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
                            className="text-zinc-500 hover:text-red-400 h-7 w-7 p-0 rounded-lg hover:bg-zinc-900"
                          >
                            ✕
                          </Button>
                        </div>
                      ))}

                      {coverageList.length === 0 && (
                        <p className="text-xs text-zinc-500 italic py-2">
                          Noch keine einzelnen Leistungen hinterlegt. Lade ein Dokument hoch oder füge manuell Leistungen hinzu.
                        </p>
                      )}
                    </div>

                    <div className="flex gap-2 pt-1">
                      <Input
                        value={newCoverageItem}
                        onChange={e => setNewCoverageItem(e.target.value)}
                        placeholder="z.B. Schutzbrief, Teilkasko, Schlüsselverlust"
                        onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); handleAddCoverageItem(); } }}
                        className="bg-zinc-950/50 border-zinc-800 text-xs"
                      />
                      <Button
                        type="button"
                        onClick={handleAddCoverageItem}
                        className="bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs shrink-0"
                      >
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

                  <div className="flex justify-between items-center pt-4 border-t border-zinc-800/80">
                    <Button type="button" variant="destructive" onClick={handleDeleteInsurance} className="bg-red-950/80 hover:bg-red-900 text-red-300 border border-red-800 text-xs">
                      Versicherung löschen
                    </Button>
                    <Button type="submit" disabled={saving} className="theme-bg-accent text-white theme-glow">
                      {saving ? "Speichert..." : "Änderungen speichern"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>

          {/* Right Column: Uploaded Documents & Viewer */}
          <div className="lg:col-span-5 space-y-6">
            <Card
              onDragOver={handleCardDragOver}
              onDragLeave={handleCardDragLeave}
              onDrop={handleCardDrop}
              className={`border-zinc-800 bg-zinc-900/40 backdrop-blur-md shadow-xl transition-all ${
                isCardDragOver ? "theme-border-accent bg-zinc-900/80 theme-glow scale-[1.01]" : ""
              }`}
            >
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-xl font-semibold">Unterlagen & Dokumente</CardTitle>
                  <CardDescription className="text-xs mt-0.5">Drag & Drop oder Durchsuchen</CardDescription>
                </div>
                <Button size="sm" onClick={() => setIsUploadModalOpen(true)} className="theme-bg-accent text-white text-xs theme-glow">
                  + Datei hochladen
                </Button>
              </CardHeader>
              <CardContent className="space-y-4">
                {documents.map(doc => {
                  const isPdf = doc.original_filename.toLowerCase().endsWith(".pdf");
                  const displayName = doc.custom_name || doc.original_filename;
                  const docCategory = doc.doc_type || "Vertragsschreiben";

                  return (
                    <div key={doc.id} className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800/80 space-y-3 group hover:border-zinc-700 transition-all shadow-md">
                      {/* Top Section: Icon + Full Document Title */}
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-xl shrink-0 shadow-inner mt-0.5">
                          {isPdf ? "📄" : "🖼️"}
                        </div>
                        <div className="flex-1 min-w-0 space-y-1.5">
                          <h4 className="text-sm font-bold text-zinc-100 break-words leading-snug">
                            {displayName}
                          </h4>
                          
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-800/80 font-medium">
                              {docCategory}
                            </span>
                            <span className="text-[11px] text-zinc-400 font-mono truncate max-w-[200px]" title={doc.original_filename}>
                              {doc.original_filename}
                            </span>
                            <span className="text-[11px] text-zinc-500 font-mono">
                              • {doc.upload_date ? new Date(doc.upload_date).toLocaleDateString("de-DE") : ""}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Bottom Action Toolbar */}
                      <div className="flex items-center justify-between pt-2.5 border-t border-zinc-900/80 gap-2">
                        <div className="text-[11px] text-zinc-500 font-mono">
                          Aktionen
                        </div>

                        <div className="flex items-center gap-1.5">
                          {/* 1. Re-analyze button */}
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={reanalyzingId === doc.id}
                            onClick={() => handleReanalyzeDocument(doc.id)}
                            title="Erneut mit KI analysieren & Daten aktualisieren"
                            className="border-indigo-800/80 bg-indigo-950/60 hover:bg-indigo-900 text-indigo-300 hover:text-white h-8 w-8 p-0 rounded-lg flex items-center justify-center transition-all"
                          >
                            {reanalyzingId === doc.id ? (
                              <div className="w-3.5 h-3.5 border-2 border-t-transparent border-indigo-300 rounded-full animate-spin" />
                            ) : (
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                              </svg>
                            )}
                          </Button>

                          {/* 2. Edit Name & Type */}
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openEditDocModal(doc)}
                            title="Name & Dokumenten-Typ bearbeiten"
                            className="border-zinc-800 bg-zinc-900/80 hover:bg-zinc-800 text-zinc-300 hover:text-white h-8 w-8 p-0 rounded-lg flex items-center justify-center transition-all"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                            </svg>
                          </Button>

                          {/* 3. Preview */}
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setViewingDoc(doc)}
                            title="Vorschau im Browser ansehen"
                            className="border-zinc-800 bg-zinc-900/80 hover:bg-zinc-800 text-zinc-300 hover:text-white h-8 w-8 p-0 rounded-lg flex items-center justify-center transition-all"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                          </Button>

                          {/* 4. Download */}
                          <a
                            href={`/api/documents/${doc.id}/download`}
                            download={doc.original_filename}
                            title="Dokument herunterladen"
                            className="inline-flex items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900/80 hover:bg-zinc-800 text-zinc-300 hover:text-white h-8 w-8 transition-all"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                          </a>

                          {/* 5. Delete */}
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => handleDeleteDocument(doc.id, displayName)}
                            title="Dokument löschen"
                            className="bg-red-950/80 hover:bg-red-900 border border-red-800 text-red-300 hover:text-white h-8 w-8 p-0 rounded-lg flex items-center justify-center transition-all"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })}

                {documents.length === 0 && (
                  <div className="text-center py-10 text-zinc-500 bg-zinc-950/30 rounded-xl border border-dashed border-zinc-800/80">
                    <p className="text-sm">Keine Dokumente für diese Polizze hinterlegt.</p>
                    <p className="text-xs text-zinc-600 mt-1">Ziehe eine Datei hierher oder klicke oben auf "+ Datei hochladen"</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Upload Modal with preselected insurance */}
      {isUploadModalOpen && (
        <UploadModal
          isOpen={isUploadModalOpen}
          onClose={() => setIsUploadModalOpen(false)}
          onSuccess={() => loadData()}
          insurances={insurance ? [insurance] : []}
          preselectedInsuranceId={String(insurance.id)}
        />
      )}

      {/* Edit Document Modal */}
      {editingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="relative w-full max-w-md bg-zinc-950 border border-zinc-800 rounded-2xl p-6 space-y-4 shadow-2xl">
            <h3 className="text-xl font-bold text-white">Dokument-Details bearbeiten</h3>
            
            <div className="space-y-2">
              <Label className="text-xs font-mono text-zinc-400">Dokumenten-Name (Titel)</Label>
              <Input
                value={editDocName}
                onChange={e => setEditDocName(e.target.value)}
                className="bg-zinc-900 border-zinc-800 text-zinc-200"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-mono text-zinc-400">Dokumenten-Typ (Kategorie)</Label>
              <Select value={editDocType} onValueChange={(val) => setEditDocType(val || "Versicherungsschein / Polizze")}>
                <SelectTrigger className="bg-zinc-900 border-zinc-800 text-zinc-200">
                  <SelectValue placeholder="Typ wählen" />
                </SelectTrigger>
                <SelectContent className="bg-zinc-900 border-zinc-800 text-zinc-50">
                  <SelectItem value="Versicherungsschein / Polizze">Versicherungsschein / Polizze</SelectItem>
                  <SelectItem value="Informationsblatt / Kundeninformation">Informationsblatt / Kundeninformation</SelectItem>
                  <SelectItem value="SEPA-Lastschriftmandat">SEPA-Lastschriftmandat</SelectItem>
                  <SelectItem value="Versicherungsbedingungen (AKB)">Versicherungsbedingungen (AKB)</SelectItem>
                  <SelectItem value="Beitragsrechnung">Beitragsrechnung</SelectItem>
                  <SelectItem value="Beratungsprotokoll">Beratungsprotokoll</SelectItem>
                  <SelectItem value="Schadenmeldung">Schadenmeldung</SelectItem>
                  <SelectItem value="Kündigungsbestätigung">Kündigungsbestätigung</SelectItem>
                  <SelectItem value="Nachtrag / Änderungsschein">Nachtrag / Änderungsschein</SelectItem>
                  <SelectItem value="Sonstiges Schreiben">Sonstiges Schreiben</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-zinc-800">
              <Button variant="outline" onClick={() => setEditingDoc(null)} className="border-zinc-800 text-zinc-300">
                Abbrechen
              </Button>
              <Button onClick={handleUpdateDocument} className="theme-bg-accent text-white theme-glow">
                Speichern
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Embedded Document Viewer Modal */}
      {viewingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="relative w-full max-w-5xl h-[85vh] bg-zinc-950 border border-zinc-800 rounded-2xl flex flex-col shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-900/60">
              <div className="flex items-center gap-3">
                <span className="text-xl">📄</span>
                <div>
                  <h3 className="text-base font-bold text-white">{viewingDoc.custom_name || viewingDoc.original_filename}</h3>
                  <p className="text-xs text-zinc-400 font-mono">{viewingDoc.doc_type || "Dokument-Vorschau"}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <a
                  href={`/api/documents/${viewingDoc.id}/view`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs px-3 py-1.5 rounded-lg bg-zinc-900 border border-zinc-700 text-zinc-300 hover:bg-zinc-800 transition-colors"
                >
                  ↗ In neuem Tab öffnen
                </a>
                <a
                  href={`/api/documents/${viewingDoc.id}/download`}
                  download={viewingDoc.original_filename}
                  className="text-xs px-3 py-1.5 rounded-lg theme-bg-accent text-white transition-colors"
                >
                  ⬇️ Herunterladen
                </a>
                <button
                  onClick={() => setViewingDoc(null)}
                  className="w-8 h-8 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-white flex items-center justify-center text-lg transition-colors ml-2"
                >
                  ✕
                </button>
              </div>
            </div>

            <div className="flex-1 bg-zinc-900/30 p-2 overflow-hidden flex items-center justify-center">
              <iframe
                src={`/api/documents/${viewingDoc.id}/view`}
                className="w-full h-full rounded-xl border border-zinc-800/60 bg-white"
                title={viewingDoc.original_filename}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
