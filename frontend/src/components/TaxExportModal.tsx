"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface InsuranceItem {
  id: number;
  name: string;
  company?: string;
  insurance_number?: string;
  category?: string;
  cost?: number;
  payment_cycle?: string;
  start_date?: string;
  end_date?: string;
  is_suspended?: boolean;
}

interface TaxExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  insurances: InsuranceItem[];
  userEmail?: string;
}

export function classifyTaxDeductibility(category: string = ""): { deductible: boolean; taxType: "vorsorge" | "werbungskosten" | "sach"; label: string } {
  const c = category.toLowerCase();
  if (c.includes("haftpflicht") || c.includes("kranken") || c.includes("unfall") || c.includes("berufsunfähigkeit") || c.includes("bu") || c.includes("leben") || c.includes("pflege") || c.includes("rente") || c.includes("zahn") || c.includes("risiko")) {
    return { deductible: true, taxType: "vorsorge", label: "Sonderausgaben / Vorsorgeaufwendungen (§ 10 EStG)" };
  }
  if (c.includes("berufsrecht") || c.includes("berufshaft") || c.includes("dienstfehlanzeige") || c.includes("rechtsschutz")) {
    return { deductible: true, taxType: "werbungskosten", label: "Werbungskosten / Berufsbezogen (§ 9 EStG)" };
  }
  return { deductible: false, taxType: "sach", label: "Sachversicherung (Nicht als Vorsorge absetzbar)" };
}

export function calcAnnualCost(cost?: number, cycle?: string): number {
  if (!cost) return 0;
  const c = (cycle || "jährlich").toLowerCase();
  if (c === "monatlich") return cost * 12;
  if (c === "quartalsweise" || c === "vierteljährlich") return cost * 4;
  if (c === "halbjährlich") return cost * 2;
  return cost;
}

export function TaxExportModal({ isOpen, onClose, insurances = [], userEmail }: TaxExportModalProps) {
  const currentYear = new Date().getFullYear();
  const [selectedYear, setSelectedYear] = useState<number>(currentYear);
  const [taxPayerName, setTaxPayerName] = useState<string>(
    userEmail ? userEmail.split("@")[0].replace(/\./g, " ").replace(/\b\w/g, l => l.toUpperCase()) : "Steuerpflichtige/r"
  );
  
  // Custom overrides for deductibility (insurance.id -> boolean)
  const [customDeductible, setCustomDeductible] = useState<Record<number, boolean>>({});

  if (!isOpen) return null;

  const getDeductibility = (ins: InsuranceItem) => {
    if (customDeductible[ins.id] !== undefined) {
      return customDeductible[ins.id];
    }
    return classifyTaxDeductibility(ins.category).deductible;
  };

  const toggleDeductibility = (id: number) => {
    setCustomDeductible(prev => ({
      ...prev,
      [id]: !getDeductibility(insurances.find(i => i.id === id)!)
    }));
  };

  // Group insurances
  const processedList = insurances.map(ins => {
    const isDeductible = getDeductibility(ins);
    const classification = classifyTaxDeductibility(ins.category);
    const annual = ins.is_suspended ? 0 : calcAnnualCost(ins.cost, ins.payment_cycle);
    return {
      ...ins,
      isDeductible,
      taxLabel: isDeductible ? classification.label : "Sachversicherung (Nicht absetzbar)",
      annualCost: annual
    };
  });

  const deductibleList = processedList.filter(i => i.isDeductible);
  const nonDeductibleList = processedList.filter(i => !i.isDeductible);

  const totalDeductibleSum = deductibleList.reduce((sum, i) => sum + i.annualCost, 0);
  const totalAllSum = processedList.reduce((sum, i) => sum + i.annualCost, 0);

  const todayStr = new Date().toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  });

  const handlePrintPDF = () => {
    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      alert("Druckfenster konnte nicht geöffnet werden. Bitte erlaube Popups.");
      return;
    }

    const rowsDeductible = deductibleList.map(ins => `
      <tr>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">${ins.name}</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0;">${ins.company || "-"}</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; font-family: monospace;">${ins.insurance_number || "k.A."}</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0;">${ins.category || "Vorsorge"}</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; font-size: 9pt; color: #475569;">${ins.taxLabel}</td>
        <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; text-align: right; font-weight: bold; font-family: monospace;">${ins.annualCost.toFixed(2)} €</td>
      </tr>
    `).join("");

    const rowsNonDeductible = nonDeductibleList.map(ins => `
      <tr style="color: #64748b;">
        <td style="padding: 6px 10px; border-bottom: 1px solid #f1f5f9;">${ins.name}</td>
        <td style="padding: 6px 10px; border-bottom: 1px solid #f1f5f9;">${ins.company || "-"}</td>
        <td style="padding: 6px 10px; border-bottom: 1px solid #f1f5f9; font-family: monospace;">${ins.insurance_number || "k.A."}</td>
        <td style="padding: 6px 10px; border-bottom: 1px solid #f1f5f9;">${ins.category || "Sachversicherung"}</td>
        <td style="padding: 6px 10px; border-bottom: 1px solid #f1f5f9; text-align: right; font-family: monospace;">${ins.annualCost.toFixed(2)} €</td>
      </tr>
    `).join("");

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Steuer-Bescheinigung & Jahresübersicht Versicherungen ${selectedYear} - ${taxPayerName}</title>
          <style>
            @page {
              size: A4 portrait;
              margin: 15mm 15mm 15mm 15mm;
            }
            @media print {
              html, body {
                margin: 0 !important;
                padding: 0 !important;
                background: #ffffff !important;
                color: #000000 !important;
                -webkit-print-color-adjust: exact;
              }
            }
            body {
              font-family: Arial, sans-serif;
              font-size: 10pt;
              line-height: 1.4;
              color: #0f172a;
            }
            .header {
              display: flex;
              justify-content: space-between;
              align-items: flex-start;
              border-bottom: 2px solid #0284c7;
              padding-bottom: 12px;
              margin-bottom: 20px;
            }
            .title {
              font-size: 16pt;
              font-weight: bold;
              color: #0369a1;
              margin: 0;
            }
            .subtitle {
              font-size: 9pt;
              color: #64748b;
              margin-top: 3px;
            }
            .summary-card {
              background: #f0f9ff;
              border: 1px solid #bae6fd;
              border-radius: 8px;
              padding: 14px;
              margin-bottom: 25px;
              display: flex;
              justify-content: space-between;
              align-items: center;
            }
            .summary-amount {
              font-size: 18pt;
              font-weight: bold;
              color: #0369a1;
              font-family: monospace;
            }
            table {
              width: 100%;
              border-collapse: collapse;
              margin-bottom: 25px;
              font-size: 9.5pt;
            }
            th {
              background: #f8fafc;
              color: #334155;
              text-align: left;
              padding: 8px 10px;
              font-size: 8.5pt;
              text-transform: uppercase;
              letter-spacing: 0.5px;
              border-bottom: 2px solid #cbd5e1;
            }
            .section-heading {
              font-size: 11pt;
              font-weight: bold;
              color: #1e293b;
              margin-top: 20px;
              margin-bottom: 8px;
            }
            .footer-note {
              font-size: 8pt;
              color: #94a3b8;
              border-top: 1px solid #e2e8f0;
              padding-top: 10px;
              margin-top: 30px;
            }
          </style>
        </head>
        <body>
          <div class="header">
            <div>
              <h1 class="title">📄 STEUER- & HAUSHALTSÜBERSICHT ${selectedYear}</h1>
              <p class="subtitle">Zusammenstellung der Vorsorgeaufwendungen & Versicherungsbeiträge für das Finanzamt</p>
            </div>
            <div style="text-align: right; font-size: 9pt; color: #475569;">
              <div><strong>Steuerpflichtige/r:</strong> ${taxPayerName}</div>
              <div>Erstellt am: ${todayStr}</div>
            </div>
          </div>

          <div class="summary-card">
            <div>
              <div style="font-size: 9pt; text-transform: uppercase; letter-spacing: 0.5px; color: #0369a1; font-weight: bold;">
                Gesamtsumme steuerlich absetzbarer Vorsorgeaufwendungen (${selectedYear}):
              </div>
              <div style="font-size: 8.5pt; color: #475569; margin-top: 2px;">
                Gemäß § 10 EStG (Vorsorgeaufwendungen / Sonderausgaben / Werbungskosten)
              </div>
            </div>
            <div class="summary-amount">${totalDeductibleSum.toFixed(2)} €</div>
          </div>

          <div class="section-heading">🛡️ Steuerlich absetzbare Versicherungen (${deductibleList.length})</div>
          <table>
            <thead>
              <tr>
                <th>Versicherung</th>
                <th>Gesellschaft</th>
                <th>Schein-Nr.</th>
                <th>Kategorie</th>
                <th>Steuer-Zuordnung</th>
                <th style="text-align: right;">Jahresbeitrag</th>
              </tr>
            </thead>
            <tbody>
              ${rowsDeductible || '<tr><td colspan="6" style="padding: 10px; text-align: center; color: #94a3b8;">Keine absetzbaren Versicherungen vorhanden.</td></tr>'}
            </tbody>
            <tfoot>
              <tr style="background: #f8fafc; font-weight: bold;">
                <td colspan="5" style="padding: 10px; text-align: right; border-top: 2px solid #cbd5e1;">Gesamtsumme Absetzbar:</td>
                <td style="padding: 10px; text-align: right; border-top: 2px solid #cbd5e1; font-family: monospace; color: #0369a1; font-size: 11pt;">${totalDeductibleSum.toFixed(2)} €</td>
              </tr>
            </tfoot>
          </table>

          ${nonDeductibleList.length > 0 ? `
            <div class="section-heading" style="margin-top: 30px; color: #64748b;">🏡 Weitere Sach- & Vermögensversicherungen (${nonDeductibleList.length})</div>
            <table>
              <thead>
                <tr>
                  <th>Versicherung</th>
                  <th>Gesellschaft</th>
                  <th>Schein-Nr.</th>
                  <th>Kategorie</th>
                  <th style="text-align: right;">Jahresbeitrag</th>
                </tr>
              </thead>
              <tbody>
                ${rowsNonDeductible}
              </tbody>
            </table>
          ` : ""}

          <div class="footer-note">
            Diese Zusammenstellung wurde automatisch von <strong>Noxus Policy</strong> generiert. Alle Beiträge basieren auf den ausgelesenen Versicherungspolicen.
          </div>

          <script>
            window.onload = function() {
              window.print();
              window.close();
            };
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  const handleDownloadCSV = () => {
    const csvRows = [
      ["Versicherung", "Gesellschaft", "Schein-Nr", "Kategorie", "Steuerlich Absetzbar", "Zuordnung", "Jahresbeitrag EUR"]
    ];

    processedList.forEach(ins => {
      csvRows.push([
        `"${ins.name.replace(/"/g, '""')}"`,
        `"${(ins.company || "").replace(/"/g, '""')}"`,
        `"${(ins.insurance_number || "").replace(/"/g, '""')}"`,
        `"${(ins.category || "").replace(/"/g, '""')}"`,
        ins.isDeductible ? "JA" : "NEIN",
        `"${ins.taxLabel}"`,
        ins.annualCost.toFixed(2)
      ]);
    });

    const csvContent = "\uFEFF" + csvRows.map(e => e.join(";")).join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `Steuer_Uebersicht_Versicherungen_${selectedYear}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 overflow-y-auto">
      <div className="bg-zinc-950 border border-zinc-800 rounded-2xl w-full max-w-4xl overflow-hidden shadow-2xl my-8">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-zinc-800 flex justify-between items-center bg-zinc-900/60">
          <div className="flex items-center gap-2">
            <span className="text-xl">📑</span>
            <div>
              <h2 className="text-lg font-bold text-white">Steuererklärungs- & Haushalts-Export</h2>
              <p className="text-xs text-zinc-400">Erstelle eine fertige Jahresübersicht deiner absetzbaren Vorsorgeaufwendungen</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-zinc-400 hover:text-white text-xl font-bold px-2 py-1 rounded-lg hover:bg-zinc-800"
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">

          {/* Settings / Controls */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-zinc-900/40 p-4 rounded-xl border border-zinc-800/80">
            <div className="space-y-1.5">
              <Label className="text-xs font-mono text-zinc-400">Steuerjahr wählen</Label>
              <select
                value={selectedYear}
                onChange={e => setSelectedYear(Number(e.target.value))}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2 text-xs text-white font-bold"
              >
                {[currentYear, currentYear - 1, currentYear - 2].map(y => (
                  <option key={y} value={y}>Steuerjahr {y}</option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5 sm:col-span-2">
              <Label className="text-xs font-mono text-zinc-400">Name des Steuerpflichtigen (für Dokument)</Label>
              <Input
                value={taxPayerName}
                onChange={e => setTaxPayerName(e.target.value)}
                placeholder="z.B. Max Mustermann"
                className="bg-zinc-950 border-zinc-800 text-xs text-white"
              />
            </div>
          </div>

          {/* Tax Summary Metric Box */}
          <div className="p-5 rounded-2xl bg-gradient-to-r from-sky-950/60 via-indigo-950/40 to-emerald-950/40 border border-sky-800/60 shadow-xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <p className="text-xs font-mono text-sky-300 font-bold uppercase tracking-wider">
                🛡️ Steuerlich absetzbare Vorsorgeaufwendungen ({selectedYear})
              </p>
              <p className="text-xs text-zinc-400 mt-1">
                {deductibleList.length} absetzbare Verträge gemäß § 10 EStG (Sonderausgaben / Vorsorgeaufwendungen)
              </p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold font-mono text-sky-300">
                {totalDeductibleSum.toFixed(2)} €
              </p>
              <p className="text-[11px] text-zinc-500 font-mono">
                Gesamtbeiträge aller Verträge: {totalAllSum.toFixed(2)} €
              </p>
            </div>
          </div>

          {/* Deductible Insurances Table */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-zinc-300 uppercase tracking-wider flex items-center justify-between">
              <span>🛡️ Steuerlich relevante Versicherungen ({deductibleList.length})</span>
              <span className="text-[10px] text-zinc-500 font-normal font-mono">Klicke auf den Status, um die Absetzbarkeit anzupassen</span>
            </h3>

            <div className="border border-zinc-800 rounded-xl overflow-hidden bg-zinc-950">
              <table className="w-full text-left text-xs">
                <thead className="bg-zinc-900 text-zinc-400 font-mono text-[11px] uppercase border-b border-zinc-800">
                  <tr>
                    <th className="p-3">Versicherung</th>
                    <th className="p-3">Kategorie</th>
                    <th className="p-3">Steuer-Klassifizierung</th>
                    <th className="p-3 text-right">Jahresbeitrag</th>
                    <th className="p-3 text-center">Absetzbar?</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60 text-zinc-200">
                  {processedList.map(ins => (
                    <tr key={ins.id} className={ins.isDeductible ? "hover:bg-zinc-900/40" : "opacity-60 hover:opacity-100 hover:bg-zinc-900/40"}>
                      <td className="p-3 font-medium text-white">
                        {ins.name}
                        <div className="text-[10px] text-zinc-500 font-mono">{ins.company || "Gesellschaft k.A."} • {ins.insurance_number || "keine Nr."}</div>
                      </td>
                      <td className="p-3 text-zinc-400">{ins.category || "Sonstige"}</td>
                      <td className="p-3 text-[11px] text-zinc-400">{ins.taxLabel}</td>
                      <td className="p-3 text-right font-mono font-bold text-sky-300">
                        {ins.annualCost.toFixed(2)} €
                      </td>
                      <td className="p-3 text-center">
                        <button
                          type="button"
                          onClick={() => toggleDeductibility(ins.id)}
                          className={`px-2.5 py-1 rounded text-[10px] font-bold font-mono transition-colors border ${
                            ins.isDeductible
                              ? "bg-emerald-950 text-emerald-300 border-emerald-800 hover:bg-emerald-900"
                              : "bg-zinc-900 text-zinc-500 border-zinc-800 hover:text-zinc-300"
                          }`}
                        >
                          {ins.isDeductible ? "✓ JA (Absetzbar)" : "✕ NEIN"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-zinc-800 bg-zinc-900/60 flex flex-col sm:flex-row justify-between items-center gap-3">
          <Button variant="outline" onClick={onClose} className="border-zinc-800 text-zinc-400 text-xs w-full sm:w-auto">
            Schließen
          </Button>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <Button
              type="button"
              variant="outline"
              onClick={handleDownloadCSV}
              className="border-zinc-700 bg-zinc-900 text-zinc-200 text-xs hover:bg-zinc-800 w-full sm:w-auto flex items-center gap-1.5"
            >
              📊 Tabelle als CSV herunterladen
            </Button>

            <Button
              type="button"
              onClick={handlePrintPDF}
              className="theme-bg-accent text-white text-xs font-semibold theme-glow w-full sm:w-auto flex items-center gap-1.5"
            >
              🖨️ PDF für Finanzamt drucken / speichern
            </Button>
          </div>
        </div>

      </div>
    </div>
  );
}
