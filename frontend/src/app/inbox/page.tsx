"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";

export default function InboxPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [inboxDocs, setInboxDocs] = useState<any[]>([]);
  const [insurances, setInsurances] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [analyzingId, setAnalyzingId] = useState<number | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Modals & Active selection
  const [previewDoc, setPreviewDoc] = useState<any>(null);
  const [assignDoc, setAssignDoc] = useState<any>(null);
  const [selectedInsuranceId, setSelectedInsuranceId] = useState<string>("");
  const [customName, setCustomName] = useState("");
  const [docType, setDocType] = useState("Police");

  const [createDoc, setCreateDoc] = useState<any>(null);
  const [newInsuranceForm, setNewInsuranceForm] = useState({
    name: "",
    company: "",
    insurance_number: "",
    category: "Sonstige",
    cost: "0",
    payment_cycle: "monatlich",
    start_date: "",
    end_date: "",
    cancellation_date: "",
    notes: ""
  });

  useEffect(() => {
    loadData();

    // Auto-refresh inbox every 4s to catch newly dropped Netzlaufwerk files immediately
    const interval = setInterval(() => {
      api.get("/inbox").then((docs) => {
        if (docs) setInboxDocs(docs);
      }).catch(() => {});
    }, 4000);

    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const user = await api.get("/users/me");
      setCurrentUser(user);

      const docs = await api.get("/inbox");
      setInboxDocs(docs || []);

      const insList = await api.get("/insurances");
      setInsurances(insList || []);
    } catch (err: any) {
      console.error(err);
      if (err?.message?.includes("401")) {
        window.location.href = "/login";
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    setMessage(null);

    try {
      for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append("file", files[i]);
        await api.postForm("/inbox/upload", formData);
      }
      setMessage({ type: "success", text: `${files.length} Datei(en) erfolgreich im Posteingang abgelegt!` });
      await loadData();
    } catch (err: any) {
      setMessage({ type: "error", text: err?.message || "Fehler beim Upload in den Posteingang." });
    } finally {
      setUploading(false);
    }
  };

  const handleAnalyze = async (docId: number) => {
    setAnalyzingId(docId);
    setMessage(null);
    try {
      const res = await api.post(`/inbox/${docId}/analyze`, {});
      setMessage({ type: "success", text: "KI-Analyse erfolgreich abgeschlossen!" });
      await loadData();
    } catch (err: any) {
      setMessage({ type: "error", text: err?.message || "Fehler bei der KI-Analyse." });
    } finally {
      setAnalyzingId(null);
    }
  };

  const handleDelete = async (docId: number) => {
    if (!confirm("Möchtest du dieses Dokument wirklich aus dem Posteingang löschen?")) return;
    try {
      await api.delete(`/inbox/${docId}`);
      setMessage({ type: "success", text: "Dokument gelöscht." });
      await loadData();
    } catch (err: any) {
      setMessage({ type: "error", text: err?.message || "Fehler beim Löschen." });
    }
  };

  const openAssignModal = (doc: any) => {
    setAssignDoc(doc);
    setSelectedInsuranceId(insurances[0]?.id ? String(insurances[0].id) : "");
    let aiData: any = {};
    if (doc.ai_data) {
      try {
        aiData = typeof doc.ai_data === "string" ? JSON.parse(doc.ai_data) : doc.ai_data;
      } catch (_) {}
    }
    const cleanFilename = (doc.original_filename || doc.filename || "").replace(/\.[^/.]+$/, "");
    const suggestedName = aiData.subject || aiData.document_title || doc.custom_name || cleanFilename;
    setCustomName(suggestedName);
    setDocType(aiData.doc_type || "Police");
  };

  const handleAssignSubmit = async () => {
    if (!assignDoc || !selectedInsuranceId) return;
    try {
      await api.post(`/inbox/${assignDoc.id}/assign`, {
        insurance_id: parseInt(selectedInsuranceId, 10),
        custom_name: customName,
        doc_type: docType
      });
      setMessage({ type: "success", text: "Dokument erfolgreich der Versicherung zugeordnet und im Posteingang archiviert!" });
      setAssignDoc(null);
      await loadData();
    } catch (err: any) {
      setMessage({ type: "error", text: err?.message || "Fehler bei der Zuordnung." });
    }
  };

  const openCreateInsuranceModal = (doc: any) => {
    setCreateDoc(doc);

    let aiData: any = {};
    if (doc.ai_data) {
      try {
        aiData = typeof doc.ai_data === "string" ? JSON.parse(doc.ai_data) : doc.ai_data;
      } catch (_) {}
    }

    setNewInsuranceForm({
      name: aiData.name || aiData.company || doc.custom_name || "Neue Versicherung",
      company: aiData.company || "",
      insurance_number: aiData.insurance_number || "",
      category: aiData.category || "Sonstige",
      cost: aiData.cost !== undefined ? String(aiData.cost) : "0",
      payment_cycle: aiData.payment_cycle || "monatlich",
      start_date: aiData.start_date || "",
      end_date: aiData.end_date || "",
      cancellation_date: aiData.cancellation_date || "",
      notes: aiData.notes || (doc.original_filename ? `Erstellt aus Posteingang: ${doc.original_filename}` : "")
    });
  };

  const handleCreateInsuranceSubmit = async () => {
    if (!createDoc) return;
    try {
      await api.post(`/inbox/${createDoc.id}/create-insurance`, {
        ...newInsuranceForm,
        cost: parseFloat(newInsuranceForm.cost) || 0.0
      });
      setMessage({ type: "success", text: "Neue Versicherung erfolgreich erstellt und Dokument zugeordnet!" });
      setCreateDoc(null);
      await loadData();
    } catch (err: any) {
      setMessage({ type: "error", text: err?.message || "Fehler beim Erstellen der Versicherung." });
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return "Unbekannt";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 pb-16">
      <Navbar userEmail={currentUser?.email} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-5">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-zinc-100 to-indigo-200 bg-clip-text text-transparent">
                📬 Posteingang & Netzlaufwerk
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                {inboxDocs.length} Dokumente
              </span>
            </div>
            <p className="text-xs sm:text-sm text-zinc-400 mt-1">
              Hier landen alle per Windows-Netzlaufwerk abgelegten oder hochgeladenen Dokumente zur KI-Analyse & Zuordnung.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              onClick={() => router.push("/settings")}
              variant="outline"
              className="border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300 text-xs sm:text-sm"
            >
              ⚙️ Netzlaufwerk einrichten
            </Button>
          </div>
        </div>

        {/* Status Messages */}
        {message && (
          <div className={`p-4 rounded-xl text-sm font-medium border transition-all ${
            message.type === "success" 
              ? "bg-emerald-950/60 border-emerald-800 text-emerald-300" 
              : "bg-red-950/60 border-red-800 text-red-300"
          }`}>
            {message.text}
          </div>
        )}

        {/* Drag & Drop Upload Dropzone */}
        <Card className="border-dashed border-2 border-indigo-900/50 bg-indigo-950/10 hover:bg-indigo-950/20 transition-all rounded-2xl">
          <CardContent className="p-6 text-center">
            <div className="flex flex-col items-center justify-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 text-xl">
                📂
              </div>
              <div>
                <p className="text-sm font-semibold text-zinc-200">
                  Dateien in den Posteingang hochladen oder per Netzlaufwerk ablegen
                </p>
                <p className="text-xs text-zinc-500 mt-0.5">
                  PDF, PNG, JPG (Dokumente werden automatisch im Hintergrund registriert)
                </p>
              </div>
              <label className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs sm:text-sm transition-all shadow-md">
                <span>{uploading ? "Wird hochgeladen..." : "➕ Datei auswählen"}</span>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.png,.jpg,.jpeg"
                  onChange={handleFileUpload}
                  disabled={uploading}
                  className="hidden"
                />
              </label>
            </div>
          </CardContent>
        </Card>

        {/* Inbox List */}
        {isLoading ? (
          <div className="py-12 text-center text-zinc-500 text-sm">Posteingang wird geladen...</div>
        ) : inboxDocs.length === 0 ? (
          <Card className="border-zinc-800/80 bg-zinc-900/40 rounded-2xl py-12 text-center">
            <CardContent className="space-y-2">
              <span className="text-4xl">📭</span>
              <h3 className="text-base font-semibold text-zinc-300">Dein Posteingang ist leer</h3>
              <p className="text-xs text-zinc-500 max-w-md mx-auto">
                Lege Dokumente über dein Windows-Netzlaufwerk im Ordner ab oder lade Dateien oben hoch.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {inboxDocs.map((doc) => {
              let aiParsed: any = null;
              if (doc.ai_data) {
                try {
                  aiParsed = typeof doc.ai_data === "string" ? JSON.parse(doc.ai_data) : doc.ai_data;
                } catch (_) {}
              }

              return (
                <Card key={doc.id} className="border-zinc-800 bg-zinc-900/60 hover:border-zinc-700 transition-all rounded-2xl overflow-hidden">
                  <CardContent className="p-5 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
                    {/* Left: Info */}
                    <div className="flex items-start gap-4 flex-1">
                      <div className="w-12 h-12 rounded-xl bg-zinc-800 border border-zinc-700/80 flex items-center justify-center text-2xl shrink-0">
                        📄
                      </div>
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="font-bold text-sm sm:text-base text-zinc-100 truncate">
                            {doc.custom_name || doc.original_filename}
                          </h3>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${
                            doc.status === "analyzed"
                              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                              : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                          }`}>
                            {doc.status === "analyzed" ? "⚡ KI-Analysiert" : "⏳ Ausstehend"}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 text-xs text-zinc-400 flex-wrap font-mono">
                          <span>📅 {new Date(doc.upload_date).toLocaleDateString("de-DE")}</span>
                          <span>💾 {formatFileSize(doc.file_size)}</span>
                          <span className="text-zinc-500 truncate max-w-[200px]">{doc.original_filename}</span>
                        </div>

                        {/* AI Extraction Preview Box */}
                        {aiParsed && (
                          <div className="mt-3 p-3 rounded-xl bg-indigo-950/30 border border-indigo-900/40 text-xs text-indigo-200 space-y-1 font-mono">
                            <div className="font-bold text-indigo-400 flex items-center gap-1">
                              <span>🤖 Extrahierter Inhalt:</span>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 pt-1 text-[11px]">
                              <div><span className="text-zinc-500">Versicherung:</span> {aiParsed.name || aiParsed.company || "-"}</div>
                              <div><span className="text-zinc-500">Kategorie:</span> {aiParsed.category || "-"}</div>
                              <div><span className="text-zinc-500">Beitrag:</span> {aiParsed.cost ? `${aiParsed.cost} € (${aiParsed.payment_cycle || 'monatlich'})` : "-"}</div>
                              <div><span className="text-zinc-500">Polizzen-Nr:</span> {aiParsed.insurance_number || "-"}</div>
                              <div><span className="text-zinc-500">Vertragsbeginn:</span> {aiParsed.start_date || "-"}</div>
                              <div><span className="text-zinc-500">Ablaufdatum:</span> {aiParsed.end_date || "-"}</div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Right: Action Buttons */}
                    <div className="flex items-center gap-2 flex-wrap shrink-0 w-full lg:w-auto justify-end border-t lg:border-t-0 border-zinc-800 pt-3 lg:pt-0">
                      <Button
                        onClick={() => setPreviewDoc(doc)}
                        variant="outline"
                        size="sm"
                        className="border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 text-xs"
                      >
                        👁️ Vorschau
                      </Button>

                      <Button
                        onClick={() => handleAnalyze(doc.id)}
                        disabled={analyzingId === doc.id}
                        variant="outline"
                        size="sm"
                        className="border-indigo-800/80 bg-indigo-950/40 hover:bg-indigo-900/60 text-indigo-200 text-xs font-semibold"
                      >
                        {analyzingId === doc.id ? "Analysiere..." : "⚡ KI-Analyse"}
                      </Button>

                      {insurances.length > 0 && (
                        <Button
                          onClick={() => openAssignModal(doc)}
                          variant="outline"
                          size="sm"
                          className="border-emerald-800/80 bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-200 text-xs font-semibold"
                        >
                          📋 Zuordnen
                        </Button>
                      )}

                      <Button
                        onClick={() => openCreateInsuranceModal(doc)}
                        size="sm"
                        className="theme-bg-accent text-white hover:opacity-90 text-xs font-semibold"
                      >
                        ➕ Neue Versicherung
                      </Button>

                      <Button
                        onClick={() => handleDelete(doc.id)}
                        variant="outline"
                        size="sm"
                        className="border-zinc-800 hover:bg-red-950/50 text-zinc-400 hover:text-red-400 text-xs"
                      >
                        🗑️
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Modal: Preview Document */}
        {previewDoc && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
              <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
                <h3 className="font-bold text-sm sm:text-base text-zinc-100">
                  {previewDoc.original_filename}
                </h3>
                <Button variant="ghost" size="sm" onClick={() => setPreviewDoc(null)}>✕</Button>
              </div>
              <div className="p-4 flex-1 overflow-auto bg-zinc-950 flex items-center justify-center">
                <iframe
                  src={`/api/inbox/${previewDoc.id}/file`}
                  className="w-full h-[70vh] rounded-xl border border-zinc-800"
                />
              </div>
            </div>
          </div>
        )}

        {/* Modal: Assign to existing insurance */}
        {assignDoc && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md p-6 space-y-4">
              <h3 className="font-bold text-lg text-zinc-100">📋 Zu bestehender Versicherung zuordnen</h3>
              <p className="text-xs text-zinc-400">
                Wähle die Ziel-Versicherung aus. Das Dokument wird dort eingeordnet und aus dem Posteingang archiviert.
              </p>

              <div className="space-y-3">
                <div>
                  <Label className="text-xs text-zinc-300">Ziel-Versicherung</Label>
                  <select
                    value={selectedInsuranceId}
                    onChange={(e) => setSelectedInsuranceId(e.target.value)}
                    className="w-full mt-1 bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-sm text-zinc-100"
                  >
                    {insurances.map((ins) => (
                      <option key={ins.id} value={ins.id}>
                        {ins.name} ({ins.company || 'Unbekannt'})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <Label className="text-xs text-zinc-300">Dokumentname (optional)</Label>
                  <Input
                    value={customName}
                    onChange={(e) => setCustomName(e.target.value)}
                    className="mt-1 bg-zinc-950 border-zinc-800"
                  />
                </div>

                <div>
                  <Label className="text-xs text-zinc-300">Dokumenttyp</Label>
                  <select
                    value={docType}
                    onChange={(e) => setDocType(e.target.value)}
                    className="w-full mt-1 bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-sm text-zinc-100"
                  >
                    <option value="Police">Police / Versicherungsschein</option>
                    <option value="Rechnung">Rechnung / Beitragsrechnung</option>
                    <option value="Schadenmeldung">Schadenmeldung</option>
                    <option value="Kündigung">Kündigung / Schreiben</option>
                    <option value="Sonstiges">Sonstiges</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3">
                <Button variant="outline" onClick={() => setAssignDoc(null)} className="border-zinc-800 text-xs">
                  Abbrechen
                </Button>
                <Button onClick={handleAssignSubmit} className="theme-bg-accent text-white text-xs font-semibold">
                  Zuordnen & Verschieben
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Modal: Create new insurance */}
        {createDoc && (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-lg p-6 space-y-4 max-h-[90vh] overflow-y-auto">
              <h3 className="font-bold text-lg text-zinc-100">➕ Neue Versicherung aus Dokument erstellen</h3>
              <p className="text-xs text-zinc-400">
                Die Daten wurden per KI vorbereitet. Überprüfe die Werte und erstelle die Versicherung.
              </p>

              <div className="space-y-3 text-xs">
                <div>
                  <Label className="text-xs text-zinc-300">Bezeichnung / Vertrag *</Label>
                  <Input
                    value={newInsuranceForm.name}
                    onChange={(e) => setNewInsuranceForm({ ...newInsuranceForm, name: e.target.value })}
                    className="mt-1 bg-zinc-950 border-zinc-800 text-sm"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs text-zinc-300">Gesellschaft</Label>
                    <Input
                      value={newInsuranceForm.company}
                      onChange={(e) => setNewInsuranceForm({ ...newInsuranceForm, company: e.target.value })}
                      className="mt-1 bg-zinc-950 border-zinc-800"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-zinc-300">Versicherungsnummer</Label>
                    <Input
                      value={newInsuranceForm.insurance_number}
                      onChange={(e) => setNewInsuranceForm({ ...newInsuranceForm, insurance_number: e.target.value })}
                      className="mt-1 bg-zinc-950 border-zinc-800"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <Label className="text-xs text-zinc-300">Kategorie</Label>
                    <Input
                      value={newInsuranceForm.category}
                      onChange={(e) => setNewInsuranceForm({ ...newInsuranceForm, category: e.target.value })}
                      className="mt-1 bg-zinc-950 border-zinc-800"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-zinc-300">Beitrag (€)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={newInsuranceForm.cost}
                      onChange={(e) => setNewInsuranceForm({ ...newInsuranceForm, cost: e.target.value })}
                      className="mt-1 bg-zinc-950 border-zinc-800"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-zinc-300">Zahlweise</Label>
                    <select
                      value={newInsuranceForm.payment_cycle}
                      onChange={(e) => setNewInsuranceForm({ ...newInsuranceForm, payment_cycle: e.target.value })}
                      className="w-full mt-1 bg-zinc-950 border border-zinc-800 rounded-xl px-2 py-2 text-xs text-zinc-100"
                    >
                      <option value="monatlich">monatlich</option>
                      <option value="vierteljährlich">vierteljährlich</option>
                      <option value="halbjährlich">halbjährlich</option>
                      <option value="jährlich">jährlich</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs text-zinc-300">Vertragsbeginn</Label>
                    <Input
                      type="date"
                      value={newInsuranceForm.start_date}
                      onChange={(e) => setNewInsuranceForm({ ...newInsuranceForm, start_date: e.target.value })}
                      className="mt-1 bg-zinc-950 border-zinc-800"
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-zinc-300">Ablaufdatum</Label>
                    <Input
                      type="date"
                      value={newInsuranceForm.end_date}
                      onChange={(e) => setNewInsuranceForm({ ...newInsuranceForm, end_date: e.target.value })}
                      className="mt-1 bg-zinc-950 border-zinc-800"
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-zinc-800">
                <Button variant="outline" onClick={() => setCreateDoc(null)} className="border-zinc-800 text-xs">
                  Abbrechen
                </Button>
                <Button onClick={handleCreateInsuranceSubmit} className="theme-bg-accent text-white text-xs font-semibold">
                  Versicherung Erstellen & Dokument Zuordnen
                </Button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
