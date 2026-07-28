"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const isInformationalDocType = (type: string) => {
  if (!type) return false;
  const t = type.toLowerCase().trim();
  return (
    t.includes("sonstig") ||
    t.includes("verbraucherinformation") ||
    t.includes("kundeninformation") ||
    t.includes("informationsblatt") ||
    t.includes("produktinformation") ||
    t.includes("beratungsprotokoll")
  );
};

export function UploadModal({ isOpen, onClose, onSuccess, insurances = [], preselectedInsuranceId, targetInsuranceId }: any) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractedData, setExtractedData] = useState<any>(null);
  const [extractError, setExtractError] = useState<string>("");
  const [showRawText, setShowRawText] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressText, setProgressText] = useState("Dokument wird vorbereitet...");
  const [useAi, setUseAi] = useState(true);
  const [includeCoverageDetails, setIncludeCoverageDetails] = useState<boolean>(true);
  
  const initialPreId = preselectedInsuranceId || targetInsuranceId;
  const [selectedInsuranceId, setSelectedInsuranceId] = useState<string>(initialPreId ? String(initialPreId) : "new");
  const [insuranceList, setInsuranceList] = useState<any[]>(insurances);

  const [docType, setDocType] = useState<string>("Versicherungsschein / Polizze");
  const [customDocName, setCustomDocName] = useState<string>("");

  useEffect(() => {
    const preId = preselectedInsuranceId || targetInsuranceId;
    if (preId) {
      setSelectedInsuranceId(String(preId));
    }
  }, [preselectedInsuranceId, targetInsuranceId]);

  useEffect(() => {
    if (isOpen) {
      api.get("/documents/ai-config")
        .then((cfg: any) => setUseAi(!!cfg.use_ai))
        .catch(() => setUseAi(true));

      api.get("/insurances")
        .then((data: any[]) => setInsuranceList(data))
        .catch((err) => console.error("Fehler beim Laden der Versicherungsliste:", err));
    }
  }, [isOpen]);

  const [formData, setFormData] = useState({
    name: "",
    company: "",
    insurance_number: "",
    category: "Haftpflicht",
    cost: "",
    payment_cycle: "jährlich",
    start_date: "",
    end_date: "",
    cancellation_date: "",
    is_suspended: false,
    suspension_reason: ""
  });

  const processFile = async (selectedFile: File) => {
    setFile(selectedFile);
    setExtractError("");
    setIsExtracting(true);
    setShowRawText(false);
    setProgress(10);
    setProgressText("Dokument wird hochgeladen...");

    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev < 35) {
          setProgressText(useAi ? "Optische Texterkennung (OCR) verarbeitet Dokument..." : "Texterkennung liest Dokument aus...");
          return prev + 10;
        } else if (prev < 88) {
          setProgressText(useAi ? "Lokale Mini-KI (Qwen2.5 1.5B) analysiert Vertragsdaten & Leistungen..." : "Vertragsdaten werden strukturiert...");
          return prev + 8;
        } else if (prev < 98) {
          setProgressText("Formularfelder werden aufbereitet...");
          return prev + 2;
        }
        return prev;
      });
    }, 250);

    const fd = new FormData();
    fd.append("file", selectedFile);
    try {
      const data = await api.postForm("/documents/extract", fd);
      clearInterval(progressInterval);
      setProgress(100);
      setProgressText("Analyse abgeschlossen!");
      setExtractedData(data);
      
      const suggestedName = data.suggested_title || selectedFile.name.replace(/\.[^/.]+$/, "");
      setCustomDocName(suggestedName);
      setDocType(data.doc_type || "Versicherungsschein / Polizze");

      const categoryMap: Record<string, string> = {
        "Kfz": "Kfz-Versicherung",
        "Haftpflicht": "Haftpflichtversicherung",
        "Hausrat": "Hausratversicherung",
        "Leben": "Lebensversicherung",
        "Gesundheit": "Krankenversicherung",
        "Rechtsschutz": "Rechtsschutzversicherung",
        "Sonstige": "Versicherung"
      };
      const unifiedType = data.doc_type && data.doc_type !== "Versicherung" 
        ? data.doc_type 
        : (categoryMap[data.category] || data.category || "Versicherung");

      const existingIns = selectedInsuranceId !== "new"
        ? insuranceList.find((i: any) => String(i.id) === String(selectedInsuranceId))
        : null;

      const autoTitle = existingIns 
        ? existingIns.name 
        : (data.company ? `${data.company} (${unifiedType})` : selectedFile.name.replace(/\.[^/.]+$/, ""));

      setFormData({
        name: autoTitle,
        company: data.company || (existingIns ? existingIns.company : ""),
        insurance_number: data.insurance_number || (existingIns ? existingIns.insurance_number : ""),
        category: data.category || (existingIns ? existingIns.category : "Haftpflicht"),
        cost: data.cost ? String(data.cost) : (existingIns ? String(existingIns.cost) : ""),
        payment_cycle: data.payment_cycle || (existingIns ? existingIns.payment_cycle : "jährlich"),
        start_date: data.start_date || (existingIns ? existingIns.start_date : ""),
        end_date: data.end_date || (existingIns ? existingIns.end_date : ""),
        cancellation_date: data.cancellation_date || (existingIns ? existingIns.cancellation_date : ""),
        is_suspended: existingIns ? !!existingIns.is_suspended : false,
        suspension_reason: existingIns ? (existingIns.suspension_reason || "") : ""
      });
    } catch (err: any) {
      clearInterval(progressInterval);
      console.error(err);
      if (err.message?.includes("Could not validate credentials") || err.message?.includes("401") || err.message?.includes("Unauthorized")) {
        setExtractError("Sitzung abgelaufen: Bitte melde dich erneut an, um Dokumente zu verarbeiten.");
      } else {
        setExtractError(err.message || "Texterkennung fehlgeschlagen. Du kannst die Daten manuell eintragen.");
      }
    } finally {
      setIsExtracting(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleSave = async () => {
    if (!file) return;
    
    try {
      let insId = selectedInsuranceId;
      const existingTargetIns = insId !== "new" 
        ? insuranceList.find((i: any) => String(i.id) === String(insId))
        : null;
      
      const payload = {
        name: existingTargetIns ? existingTargetIns.name : (formData.name || "Versicherung"),
        company: formData.company || (existingTargetIns ? existingTargetIns.company : null),
        insurance_number: formData.insurance_number || (existingTargetIns ? existingTargetIns.insurance_number : null),
        category: formData.category || (existingTargetIns ? existingTargetIns.category : "Haftpflicht"),
        cost: formData.cost ? parseFloat(formData.cost.replace(',', '.')) : (existingTargetIns ? existingTargetIns.cost : null),
        payment_cycle: formData.payment_cycle || (existingTargetIns ? existingTargetIns.payment_cycle : "jährlich"),
        start_date: formData.start_date || (existingTargetIns ? existingTargetIns.start_date : null),
        end_date: formData.end_date || (existingTargetIns ? existingTargetIns.end_date : null),
        cancellation_date: formData.cancellation_date || (existingTargetIns ? existingTargetIns.cancellation_date : null),
        is_suspended: existingTargetIns ? !!existingTargetIns.is_suspended : (formData.is_suspended || false),
        suspension_reason: existingTargetIns ? (existingTargetIns.suspension_reason || null) : (formData.suspension_reason || null),
        coverage_details: includeCoverageDetails ? (extractedData?.coverage_details || []) : []
      };

      const isInformational = isInformationalDocType(docType);

      if (insId === "new") {
        const newIns = await api.post("/insurances", payload);
        insId = newIns.id;
      } else if (!isInformational) {
        // Do NOT overwrite existing insurance metadata for informational documents (Sonstiges, Verbraucherinformationen, Kundeninformationen)
        await api.put(`/insurances/${insId}`, payload);
      }
      
      const fd = new FormData();
      fd.append("file", file);
      fd.append("custom_name", customDocName || file.name);
      fd.append("doc_type", docType || "Vertragsschreiben");

      await api.postForm(`/documents?insurance_id=${insId}&original_filename=${encodeURIComponent(file.name)}`, fd);
      
      onSuccess();
      onClose();
    } catch (e: any) {
      console.error(e);
      alert("Fehler beim Speichern: " + (e.message || "Unbekannter Fehler"));
    }
  };

  const handleManualEntry = () => {
    setExtractedData({ manual: true });
    if (file) {
      setCustomDocName(file.name.replace(/\.[^/.]+$/, ""));
    }
    setFormData({
      name: file ? file.name.replace(/\.[^/.]+$/, "") : "Neue Versicherung",
      company: "",
      insurance_number: "",
      category: "Haftpflicht",
      cost: "",
      payment_cycle: "jährlich",
      start_date: "",
      end_date: "",
      cancellation_date: "",
      is_suspended: false,
      suspension_reason: ""
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[640px] bg-zinc-950 border-zinc-800 text-zinc-50 shadow-2xl backdrop-blur-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold flex items-center gap-2">
            <span>Dokument hochladen & analysieren</span>
          </DialogTitle>
          <DialogDescription className="text-zinc-400">
            Ziehe deine Versicherungspolizze (PDF oder Bild) per Drag & Drop hinein oder klicke zum Durchsuchen.
          </DialogDescription>
        </DialogHeader>

        {!extractedData ? (
          <div className="space-y-6">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer relative ${
                isDragOver
                  ? "theme-border-accent bg-zinc-900/80 theme-glow scale-[1.01]"
                  : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-700 hover:bg-zinc-900/60"
              }`}
            >
              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={handleFileChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
              />

              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-zinc-800/80 border border-zinc-700 flex items-center justify-center text-3xl shadow-lg">
                📄
              </div>

              {file ? (
                <div>
                  <p className="font-semibold text-zinc-200 text-lg">{file.name}</p>
                  <p className="text-xs text-zinc-500 font-mono mt-1">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
              ) : (
                <div>
                  <p className="font-semibold text-zinc-200 text-base">
                    Datei hierher ziehen <span className="text-zinc-400 font-normal">oder</span> durchsuchen
                  </p>
                  <p className="text-xs text-zinc-500 mt-1 font-mono">Unterstützt PDF, PNG, JPG (max. 15MB)</p>
                </div>
              )}
            </div>

            {isExtracting && (
              <div className="p-5 rounded-2xl bg-zinc-950/80 border border-zinc-800 shadow-2xl space-y-3.5 backdrop-blur-md">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <div className="flex items-center gap-2 text-indigo-300">
                    <span className="w-2.5 h-2.5 rounded-full bg-purple-500 animate-ping"></span>
                    <span className="font-mono">{progressText}</span>
                  </div>
                  <span className="font-mono text-emerald-400 font-bold">{progress}%</span>
                </div>

                {/* Progress Bar Track */}
                <div className="w-full h-3.5 rounded-full bg-zinc-900 overflow-hidden border border-zinc-800 p-0.5 relative">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-indigo-600 via-purple-500 to-emerald-400 transition-all duration-300 ease-out relative overflow-hidden shadow-lg shadow-purple-500/20"
                    style={{ width: `${progress}%` }}
                  >
                    <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
                  </div>
                </div>

                <div className="flex justify-between items-center text-[11px] text-zinc-500 font-mono pt-1">
                  <span>1. Texterkennung (OCR)</span>
                  <span>{useAi ? "2. 🤖 Mini-KI (Qwen2.5 1.5B)" : "2. Daten-Strukturierung"}</span>
                </div>
              </div>
            )}

            {extractError && (
              <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/60 text-amber-300 space-y-3">
                <p className="text-sm">{extractError}</p>
                <div className="flex gap-2">
                  {extractError.includes("Sitzung abgelaufen") ? (
                    <Button size="sm" onClick={() => window.location.href = "/login"} className="theme-bg-accent text-white text-xs">
                      🔑 Zur Anmeldung →
                    </Button>
                  ) : (
                    <Button size="sm" onClick={handleManualEntry} className="theme-bg-accent text-white text-xs">
                      Daten manuell eingeben →
                    </Button>
                  )}
                </div>
              </div>
            )}

            {file && !isExtracting && (
              <div className="flex justify-end gap-3 pt-2">
                <Button variant="outline" onClick={onClose} className="border-zinc-800 hover:bg-zinc-800 text-zinc-300">
                  Abbrechen
                </Button>
                <Button onClick={() => processFile(file)} className="theme-bg-accent text-white theme-glow">
                  Erneut analysieren ⚡
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-800/50 flex items-center justify-between text-xs text-emerald-300 font-mono">
              <div className="flex items-center gap-2">
                <span>✓ Daten verarbeitet</span>
                {useAi && extractedData?.ai_used ? (
                  <span className="px-2 py-0.5 rounded text-[10px] bg-purple-950 text-purple-300 border border-purple-800 font-sans font-semibold flex items-center gap-1">
                    🤖 Mini-KI ({extractedData.ai_model || "Qwen2.5 1.5B"})
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[10px] bg-zinc-800 text-zinc-300 border border-zinc-700 font-sans">
                    Texterkennung (OCR)
                  </span>
                )}
              </div>
              <button
                onClick={() => setShowRawText(!showRawText)}
                className="underline hover:text-white transition-colors"
              >
                {showRawText ? "▲ Rohtext verbergen" : "🔍 Ausgelesenen Rohtext anzeigen (OCR Debug)"}
              </button>
            </div>

            {showRawText && (
              <div className="p-3 rounded-xl bg-zinc-900 border border-zinc-800 text-xs font-mono text-zinc-300 max-h-48 overflow-y-auto space-y-1">
                <p className="text-zinc-500 font-bold border-b border-zinc-800 pb-1">Extrahierter OCR Text aus der Datei:</p>
                <pre className="whitespace-pre-wrap leading-relaxed text-[11px]">
                  {extractedData.extracted_text || "Kein Text ausgelesen."}
                </pre>
              </div>
            )}

            {/* Document Specific Info (Name & Category) */}
            <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-800/50 space-y-3">
              <div className="flex items-center gap-2 text-xs font-mono text-indigo-300 font-semibold uppercase tracking-wider">
                <span>📂 Dokumenten-Informationen</span>
                {extractedData.doc_type && (
                  <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-900/80 border border-indigo-700 text-white font-normal">
                    {useAi ? "KI-Vorschlag:" : "Vorschlag:"} {extractedData.doc_type}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5 col-span-2 sm:col-span-1">
                  <Label className="text-xs font-mono text-zinc-400">Dokumenten-Name (Titel)</Label>
                  <Input
                    value={customDocName}
                    onChange={e => setCustomDocName(e.target.value)}
                    placeholder="z.B. Polizze 2026"
                    className="bg-zinc-950 border-zinc-800 text-zinc-200"
                  />
                </div>

                <div className="space-y-1.5 col-span-2 sm:col-span-1">
                  <Label className="text-xs font-mono text-zinc-400">Dokumenten-Typ (Kategorie)</Label>
                  <Select value={docType} onValueChange={(val) => setDocType(val || "Versicherungsschein / Polizze")}>
                    <SelectTrigger className="bg-zinc-950 border-zinc-800 text-zinc-200">
                      <SelectValue placeholder="Typ wählen" />
                    </SelectTrigger>
                    <SelectContent className="bg-zinc-900 border-zinc-800 text-zinc-50">
                      <SelectItem value="Versicherungsschein / Polizze">Versicherungsschein / Polizze</SelectItem>
                      <SelectItem value="Beitragsrechnung">Beitragsrechnung</SelectItem>
                      <SelectItem value="Beitragsanpassung">Beitragsanpassung</SelectItem>
                      <SelectItem value="Nachtrag / Änderungsschein">Nachtrag / Änderungsschein</SelectItem>
                      <SelectItem value="Verbraucherinformationen">Verbraucherinformationen</SelectItem>
                      <SelectItem value="Kundeninformationen">Kundeninformationen</SelectItem>
                      <SelectItem value="Beratungsprotokoll">Beratungsprotokoll</SelectItem>
                      <SelectItem value="Schadenmeldung">Schadenmeldung</SelectItem>
                      <SelectItem value="Kündigungsbestätigung">Kündigungsbestätigung</SelectItem>
                      <SelectItem value="Sonstiges">Sonstiges</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {selectedInsuranceId !== "new" && isInformationalDocType(docType) && (
                <div className="p-3.5 rounded-xl bg-blue-950/40 border border-blue-800/60 text-xs text-blue-200 flex items-center gap-2">
                  <span className="text-base shrink-0">ℹ️</span>
                  <span>
                    <strong>Informationsschreiben ({docType}):</strong> Es werden keine Vertragsdaten oder Beiträge der bestehenden Versicherung überschrieben. Das Dokument wird lediglich als Datei abgelegt.
                  </span>
                </div>
              )}

            {extractedData?.coverage_details && extractedData.coverage_details.length > 0 && (
              <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-800/50 space-y-3">
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2.5 text-xs font-mono text-emerald-300 font-semibold uppercase tracking-wider cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeCoverageDetails}
                      onChange={(e) => setIncludeCoverageDetails(e.target.checked)}
                      className="rounded accent-emerald-500 w-4 h-4 cursor-pointer"
                    />
                    <span>Erfasste Versicherungsleistungen übernehmen ({extractedData.coverage_details.length} erkannt)</span>
                  </label>
                </div>
                
                {includeCoverageDetails && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {extractedData.coverage_details.map((item: string, idx: number) => (
                      <span key={idx} className="text-xs px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-200 font-medium">
                        ✓ {item}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-mono uppercase text-zinc-400">Zuordnung zur Versicherung</Label>
              <Select value={selectedInsuranceId} onValueChange={(val) => setSelectedInsuranceId(val || "new")}>
                <SelectTrigger className="w-full bg-zinc-900 border-zinc-800 text-zinc-200">
                  <SelectValue placeholder="Wähle eine Versicherung" />
                </SelectTrigger>
                <SelectContent className="bg-zinc-900 border-zinc-800 text-zinc-50 min-w-[380px]">
                  <SelectItem value="new">+ Neue Versicherung anlegen</SelectItem>
                  {insuranceList.map((ins: any) => (
                    <SelectItem key={ins.id} value={String(ins.id)} className="text-sm">
                      {ins.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {selectedInsuranceId === "new" && (
              <div className="grid grid-cols-2 gap-4 border border-zinc-800/80 p-4 rounded-xl bg-zinc-900/40 backdrop-blur-md">
                <div className="space-y-2 col-span-2">
                  <Label className="text-xs font-mono text-zinc-400">Titel der Versicherung</Label>
                  <Input value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="bg-zinc-950 border-zinc-800" />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs font-mono text-zinc-400">Versicherungsart (Kategorie)</Label>
                  <Input value={formData.category} onChange={e => setFormData({...formData, category: e.target.value})} placeholder="z.B. Haftpflicht, Kfz, Hausrat" className="bg-zinc-950 border-zinc-800" />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs font-mono text-zinc-400">Gesellschaft</Label>
                  <Input value={formData.company} onChange={e => setFormData({...formData, company: e.target.value})} className="bg-zinc-950 border-zinc-800" />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs font-mono text-zinc-400">Beitrag / Kosten (€)</Label>
                  <Input type="number" step="0.01" value={formData.cost} onChange={e => setFormData({...formData, cost: e.target.value})} placeholder="148.50" className="bg-zinc-950 border-zinc-800 text-emerald-400 font-mono" />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs font-mono text-zinc-400">Zahlungsrhythmus</Label>
                  <Select value={formData.payment_cycle} onValueChange={(val) => setFormData({...formData, payment_cycle: val || "jährlich"})}>
                    <SelectTrigger className="bg-zinc-950 border-zinc-800">
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
                <div className="space-y-2 col-span-2">
                  <Label className="text-xs font-mono text-zinc-400">Versicherungsnummer</Label>
                  <Input value={formData.insurance_number} onChange={e => setFormData({...formData, insurance_number: e.target.value})} className="bg-zinc-950 border-zinc-800" />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs font-mono text-zinc-400">Versicherungsbeginn</Label>
                  <Input type="date" value={formData.start_date} onChange={e => setFormData({...formData, start_date: e.target.value})} className="bg-zinc-950 border-zinc-800" />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs font-mono text-zinc-400">Vertragsende</Label>
                  <Input type="date" value={formData.end_date} onChange={e => setFormData({...formData, end_date: e.target.value})} className="bg-zinc-950 border-zinc-800" />
                </div>
                <div className="space-y-2 col-span-2">
                  <Label className="text-xs font-mono text-amber-400">Kündigungsfrist (berechnet)</Label>
                  <Input type="date" value={formData.cancellation_date} onChange={e => setFormData({...formData, cancellation_date: e.target.value})} className="bg-zinc-950 border-amber-800/60 text-amber-400 font-mono" />
                </div>

                {/* Ruhendstellung / Beitragsfreistellung Toggle */}
                <div className="col-span-2 p-3.5 rounded-xl bg-amber-950/30 border border-amber-800/50 space-y-2.5">
                  <label className="flex items-center gap-2.5 text-xs font-semibold text-amber-200 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.is_suspended}
                      onChange={e => setFormData({ ...formData, is_suspended: e.target.checked })}
                      className="rounded accent-amber-500 w-4 h-4"
                    />
                    <span>⏸️ Vertrag ruht / ist beitragsfrei gestellt (0 € Jahresbeitrag)</span>
                  </label>
                  {formData.is_suspended && (
                    <Input
                      value={formData.suspension_reason}
                      onChange={e => setFormData({ ...formData, suspension_reason: e.target.value })}
                      placeholder="Grund der Ruhendstellung (z.B. Saisonpause / Elterngeld / Beitragsfreistellung)"
                      className="bg-zinc-950 border-amber-800/60 text-xs text-amber-100"
                    />
                  )}
                </div>
              </div>
            )}
            
            <div className="flex justify-end gap-3 pt-4 border-t border-zinc-800">
              <Button variant="outline" onClick={() => setExtractedData(null)} className="border-zinc-800 text-zinc-300 hover:bg-zinc-800">
                ← Andere Datei wählen
              </Button>
              <Button onClick={handleSave} className="theme-bg-accent text-white theme-glow font-medium px-6">
                Versicherung & Dokument speichern
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
