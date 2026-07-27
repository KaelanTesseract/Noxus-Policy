"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ClaimItem {
  id?: number;
  claim_number?: string;
  claim_date?: string;
  amount?: number;
  status?: string;
  description?: string;
}

interface CancellationModalProps {
  isOpen: boolean;
  onClose: () => void;
  insurance: {
    id?: number;
    name: string;
    company?: string;
    insurance_number?: string;
    cancellation_date?: string;
    contact_info?: string;
    cost?: number;
    payment_cycle?: string;
    claims?: ClaimItem[];
  } | null;
  userEmail?: string;
}

const KNOWN_COMPANY_ADDRESSES: Record<string, string> = {
  "huk-coburg": "Bahnhofsplatz\n96444 Coburg",
  "huk24": "Willi-Hussong-Straße 2\n96444 Coburg",
  "allianz": "Königinstraße 28\n80802 München",
  "axa": "Colonia-Allee 10-20\n51067 Köln",
  "ergo": "Victoriaplatz 2\n40477 Düsseldorf",
  "generali": "Adenauerring 7\n81737 München",
  "signal iduna": "Joseph-Scherer-Straße 3\n44139 Dortmund",
  "devk": "Riehler Straße 190\n50735 Köln",
  "lvm": "Kolde-Ring 21\n48151 Münster",
  "debeka": "Ferdinand-Sauerbruch-Straße 18\n56073 Koblenz",
  "r+v": "Raiffeisenplatz 1\n65189 Wiesbaden",
  "gothaer": "Gothaer Allee 1\n50969 Köln",
  "barmenia": "Barmenia-Allee 1\n42119 Wuppertal",
  "cosmosdirekt": "Halbergstraße 50\n66121 Saarbrücken",
  "hansemerkur": "Siegfried-Wedells-Platz 1\n20354 Hamburg",
  "vhv": "VHV-Platz 1\n30177 Hannover",
  "nürnberger": "Ostendstraße 100\n90334 Nürnberg",
  "zurich": "Platz der Zürcher Versicherung 1\n50674 Köln",
  "hdi": "HDI-Platz 1\n30659 Hannover",
  "adac": "Hansastraße 19\n80686 München",
  "arag": "ARAG-Platz 1\n40472 Düsseldorf",
  "wgv": "Tübinger Straße 55\n70178 Stuttgart",
  "provinzial": "Provinzialallee 1\n48159 Münster",
  "sv sparkassenversicherung": "Löwentorstraße 65\n70376 Stuttgart",
  "haftpflichtkasse": "Darmstädter Straße 103\n64372 Ober-Ramstadt",
  "die haftpflichtkasse": "Darmstädter Straße 103\n64372 Ober-Ramstadt",
  "helvetia": "Berliner Straße 56-58\n60311 Frankfurt am Main",
  "wwk": "Marsstraße 37\n80335 München",
  "vgh": "Schiffgraben 4\n30159 Hannover",
  "concordia": "Karl-Wiechert-Allee 55\n30625 Hannover",
  "volkswohl bund": "Südwall 37-41\n44137 Dortmund",
  "alte leipziger": "Alte Leipziger-Platz 1\n61440 Oberursel",
  "hallesche": "Reinsburgstraße 10\n70178 Stuttgart",
  "continentale": "Ruhrallee 92\n44139 Dortmund",
  "janitos": "Im Breitspiel 2-4\n69126 Heidelberg",
  "baloise": "Ludwig-Erhard-Straße 22\n20459 Hamburg",
  "techniker krankenkasse": "Bramfelder Straße 140\n22305 Hamburg",
  "barmer": "Lichtscheider Straße 89\n42285 Wuppertal",
  "dak-gesundheit": "Nagelsweg 27-31\n20097 Hamburg",
  "aok": "Rosenthaler Straße 31\n10178 Berlin"
};

type CancelMode = "ordinary" | "special_price_increase" | "special_claim" | "special_risk_drop" | "special_custom";

export function CancellationModal({ isOpen, onClose, insurance, userEmail }: CancellationModalProps) {
  const [senderName, setSenderName] = useState("");
  const [senderAddress, setSenderAddress] = useState("");
  const [senderCity, setSenderCity] = useState("");
  
  const [recipientCompany, setRecipientCompany] = useState("");
  const [recipientAddress, setRecipientAddress] = useState("");
  const [insuranceNumber, setInsuranceNumber] = useState("");
  
  const [cancelMode, setCancelMode] = useState<CancelMode>("ordinary");

  // Sonderkündigung wegen Beitragserhöhung (§ 40 VVG)
  const [oldCost, setOldCost] = useState("");
  const [newCost, setNewCost] = useState("");
  const [noticeDate, setNoticeDate] = useState("");

  // Sonderkündigung nach Schadensfall (§ 92 VVG)
  const [selectedClaimId, setSelectedClaimId] = useState<string>("custom");
  const [claimNumber, setClaimNumber] = useState("");
  const [claimDate, setClaimDate] = useState("");

  // Sonderkündigung wegen Risikowegfall (§ 80 VVG)
  const [riskReason, setRiskReason] = useState("Verkauf / Abmeldung des Fahrzeugs");
  const [riskDate, setRiskDate] = useState("");

  // Sonstige Sonderkündigung
  const [customReason, setCustomReason] = useState("");

  // Extras
  const [revokeSepa, setRevokeSepa] = useState(true);
  const [requestConfirmation, setRequestConfirmation] = useState(true);
  const [requestDataDeletion, setRequestDataDeletion] = useState(false);

  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (insurance) {
      const companyName = insurance.company || insurance.name || "Versicherungsgesellschaft";
      setRecipientCompany(companyName);

      let resolvedAddr = insurance.contact_info;
      if (!resolvedAddr || resolvedAddr.trim() === "" || resolvedAddr.includes("Musterstraße")) {
        const companyKey = companyName.toLowerCase();
        for (const [key, addr] of Object.entries(KNOWN_COMPANY_ADDRESSES)) {
          if (companyKey.includes(key)) {
            resolvedAddr = addr;
            break;
          }
        }
      }
      setRecipientAddress(resolvedAddr || "[Straße & Hausnummer]\n[PLZ & Ort]");
      setInsuranceNumber(insurance.insurance_number || "");
      
      if (insurance.cost) {
        setOldCost(insurance.cost.toFixed(2));
      }

      if (userEmail) {
        const formatted = userEmail.split("@")[0].replace(/\./g, " ");
        setSenderName(formatted.charAt(0).toUpperCase() + formatted.slice(1));
      }
    }
  }, [insurance, userEmail]);

  if (!isOpen || !insurance) return null;

  const todayStr = new Date().toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  });

  const handleClaimSelect = (claimId: string) => {
    setSelectedClaimId(claimId);
    if (claimId === "custom") {
      setClaimNumber("");
      setClaimDate("");
    } else if (insurance.claims) {
      const found = insurance.claims.find(c => String(c.id) === claimId);
      if (found) {
        setClaimNumber(found.claim_number || "");
        setClaimDate(found.claim_date || "");
      }
    }
  };

  const getCancellationBodyText = () => {
    switch (cancelMode) {
      case "special_price_increase": {
        const priceInfo = oldCost && newCost 
          ? `von ${oldCost} € auf ${newCost} €` 
          : newCost ? `auf ${newCost} €` : "";
        const noticeInfo = noticeDate ? ` (Mitteilung vom ${new Date(noticeDate).toLocaleDateString("de-DE")})` : "";
        
        return `hiermit mache ich von meinem gesetzlichen Sonderkündigungsrecht gemäß § 40 VVG (Versicherungsvertragsgesetz) Gebrauch und kündige meinen oben genannten Versicherungsvertrag außerordentlich aufgrund der von Ihnen angekündigten Beitragserhöhung${priceInfo ? ` ${priceInfo}` : ""}${noticeInfo} mit sofortiger Wirkung bzw. zum Zeitpunkt des Wirksamwerdens der Preisanpassung.`;
      }
      case "special_claim": {
        const claimInfo = claimNumber ? ` (Schadennummer: ${claimNumber}${claimDate ? ` vom ${new Date(claimDate).toLocaleDateString("de-DE")}` : ""})` : "";
        return `hiermit mache ich von meinem gesetzlichen Sonderkündigungsrecht gemäß § 92 VVG (Versicherungsvertragsgesetz) Gebrauch und kündige meinen oben genannten Versicherungsvertrag außerordentlich im Anschluss an die Regulierung bzw. Bearbeitung des Schadensfalls${claimInfo} mit sofortiger Wirkung bzw. zum nächstmöglichen Zeitpunkt.`;
      }
      case "special_risk_drop": {
        const dateInfo = riskDate ? ` zum ${new Date(riskDate).toLocaleDateString("de-DE")}` : "";
        return `hiermit kündige ich den oben genannten Versicherungsvertrag außerordentlich gemäß § 80 VVG aufgrund des vollständigen Wegfalls des versicherten Risikos (${riskReason || "Wegfall des Interesses"})${dateInfo}.`;
      }
      case "special_custom": {
        return `hiermit kündige ich meinen oben genannten Versicherungsvertrag außerordentlich aus folgendem Grund: ${customReason || "[Begründung der Sonderkündigung]"}.`;
      }
      case "ordinary":
      default: {
        return `hiermit kündige ich meinen oben genannten Versicherungsvertrag ordentlich zum nächstmöglichen Termin (Vertragsende).`;
      }
    }
  };

  const generateLetterText = () => {
    const mainBody = getCancellationBodyText();

    const extraLines: string[] = [];
    if (requestConfirmation) {
      extraLines.push("Ich bitte Sie, mir den Eingang dieser Kündigung sowie das genaue Vertragsende schriftlich zu bestätigen.");
    }
    if (revokeSepa) {
      extraLines.push("Einwilligungen zum Einzug von Beiträgen per SEPA-Lastschrift für diesen Vertrag widerrufe ich hiermit zum Kündigungstermin.");
    }
    if (requestDataDeletion) {
      extraLines.push("Des Weiteren bitte ich gemäß Art. 17 DSGVO um die Löschung meiner nicht mehr erforderlichen personenbezogenen Daten nach vollständiger Vertragsabwicklung.");
    }

    const subjectTitle = cancelMode === "ordinary" 
      ? `ORDENTLICHE KÜNDIGUNG DER VERSICHERUNG: ${insurance.name.toUpperCase()}`
      : `SONDERKÜNDIGUNG DER VERSICHERUNG: ${insurance.name.toUpperCase()}`;

    return `${senderName || "[Dein Name]"}
${senderAddress || "[Deine Straße & Hausnummer]"}
${senderCity || "[PLZ & Ort]"}

Datum: ${todayStr}

An:
${recipientCompany}
${recipientAddress}


${subjectTitle}
Versicherungsscheinnummer: ${insuranceNumber || "[Polizzen-Nummer]"}


Sehr geehrte Damen und Herren,

${mainBody}

${extraLines.join("\n\n")}

Mit freundlichen Grüßen,


_________________________________________
${senderName || "[Dein Name]"} (Unterschrift)`;
  };

  const handleCopyText = () => {
    navigator.clipboard.writeText(generateLetterText());
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handlePrint = () => {
    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      alert("Druckfenster konnte nicht geöffnet werden. Bitte erlaube Popups.");
      return;
    }

    const mainBodyHtml = getCancellationBodyText().replace(/\n/g, "<br/>");
    const subjectTitle = cancelMode === "ordinary"
      ? `ORDENTLICHE KÜNDIGUNG DER VERSICHERUNG: ${insurance.name.toUpperCase()}`
      : `SONDERKÜNDIGUNG DER VERSICHERUNG: ${insurance.name.toUpperCase()}`;

    const extrasHtml: string[] = [];
    if (requestConfirmation) extrasHtml.push("Ich bitte Sie, mir den Eingang dieser Kündigung sowie das genaue Vertragsende schriftlich zu bestätigen.");
    if (revokeSepa) extrasHtml.push("Einwilligungen zum Einzug von Beiträgen per SEPA-Lastschrift für diesen Vertrag widerrufe ich hiermit zum Kündigungstermin.");
    if (requestDataDeletion) extrasHtml.push("Des Weiteren bitte ich gemäß Art. 17 DSGVO um die Löschung meiner nicht mehr erforderlichen personenbezogenen Daten nach vollständiger Vertragsabwicklung.");

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Kündigung - ${insurance.name}</title>
          <style>
            @page {
              size: A4 portrait;
              margin: 15mm 20mm 15mm 20mm;
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
              font-family: Arial, "Helvetica Neue", Helvetica, sans-serif;
              font-size: 11pt;
              line-height: 1.55;
              color: #000000;
              margin: 0;
              padding: 0;
            }
            .header-info { margin-bottom: 30px; }
            .recipient { margin-bottom: 35px; font-weight: bold; font-size: 11pt; line-height: 1.4; }
            .subject { font-size: 11.5pt; font-weight: bold; margin-bottom: 25px; text-transform: uppercase; border-bottom: 1px solid #000; padding-bottom: 5px; }
            .content { margin-bottom: 40px; }
            .signature { margin-top: 55px; border-top: 1px solid #000000; width: 250px; padding-top: 6px; }
          </style>
        </head>
        <body>
          <div class="header-info">
            <div><strong>${senderName || "[Absender Name]"}</strong></div>
            <div>${senderAddress || "[Straße & Hausnummer]"}</div>
            <div>${senderCity || "[PLZ Ort]"}</div>
            <div style="text-align: right; margin-top: -30px;">Datum: ${todayStr}</div>
          </div>
          <br/><br/>
          <div class="recipient">
            ${recipientCompany}<br/>
            ${recipientAddress.replace(/\n/g, "<br/>")}
          </div>

          <div class="subject">
            ${subjectTitle}<br/>
            <span style="font-size: 10pt; font-weight: normal; text-transform: none;">Versicherungsscheinnummer: <strong>${insuranceNumber || "Nicht angegeben"}</strong></span>
          </div>

          <div class="content">
            Sehr geehrte Damen und Herren,<br/><br/>
            ${mainBodyHtml}<br/><br/>
            ${extrasHtml.join("<br/><br/>")}<br/><br/>
            Mit freundlichen Grüßen,
          </div>

          <div class="signature">
            Unterschrift (${senderName || "Versicherungsnehmer"})
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 overflow-y-auto">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl my-8">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-zinc-800 flex justify-between items-center bg-zinc-950/60">
          <div className="flex items-center gap-2">
            <span className="text-xl">✍️</span>
            <h2 className="text-lg font-bold text-white">Sonderkündigungsrechts-Assistent & Generator</h2>
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

          {/* CRITICAL WARNING BANNER */}
          <div className="p-4 rounded-xl bg-amber-950/60 border border-amber-800/80 text-amber-200 text-xs flex items-start gap-3 shadow-lg">
            <span className="text-lg shrink-0">⚠️</span>
            <div>
              <strong className="font-bold text-amber-100 uppercase tracking-wide block mb-1">
                Wichtiger Rechtshinweis:
              </strong>
              Prüfe alle eingetragenen Angaben (insbesondere Fristen, Polizzen-Nummer und Empfängeradresse) sorgfältig auf Richtigkeit, bevor du das Kündigungsschreiben ausdruckst, unterschreibst und versendest.
            </div>
          </div>

          {/* Step 1: Cancellation Mode Selector */}
          <div className="space-y-3 bg-zinc-950/40 p-4 rounded-xl border border-zinc-800/80">
            <Label className="text-xs font-bold text-indigo-300 uppercase tracking-wider block">
              1. Kündigungsart & Rechtsgrundlage wählen
            </Label>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <button
                type="button"
                onClick={() => setCancelMode("ordinary")}
                className={`p-3 rounded-xl border text-left transition-all ${
                  cancelMode === "ordinary"
                    ? "border-indigo-500 bg-indigo-950/50 text-white ring-1 ring-indigo-500"
                    : "border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                }`}
              >
                <div className="font-bold text-xs flex items-center justify-between">
                  <span>📅 Ordentliche Kündigung</span>
                  <span className="text-[10px] font-mono text-zinc-500">§ 11 VVG</span>
                </div>
                <p className="text-[11px] text-zinc-400 mt-1 leading-snug">
                  Fristgerechte Kündigung zum Vertragsende.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setCancelMode("special_price_increase")}
                className={`p-3 rounded-xl border text-left transition-all ${
                  cancelMode === "special_price_increase"
                    ? "border-indigo-500 bg-indigo-950/50 text-white ring-1 ring-indigo-500"
                    : "border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                }`}
              >
                <div className="font-bold text-xs flex items-center justify-between">
                  <span>📈 Sonderkündigung: Beitragserhöhung</span>
                  <span className="text-[10px] font-mono text-indigo-400 font-bold">§ 40 VVG</span>
                </div>
                <p className="text-[11px] text-zinc-400 mt-1 leading-snug">
                  Außerordentlich nach Erhöhung des Beitrags.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setCancelMode("special_claim")}
                className={`p-3 rounded-xl border text-left transition-all ${
                  cancelMode === "special_claim"
                    ? "border-indigo-500 bg-indigo-950/50 text-white ring-1 ring-indigo-500"
                    : "border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                }`}
              >
                <div className="font-bold text-xs flex items-center justify-between">
                  <span>💥 Sonderkündigung: Schadensfall</span>
                  <span className="text-[10px] font-mono text-indigo-400 font-bold">§ 92 VVG</span>
                </div>
                <p className="text-[11px] text-zinc-400 mt-1 leading-snug">
                  Nach Regulierung oder Ablehnung eines Schadens.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setCancelMode("special_risk_drop")}
                className={`p-3 rounded-xl border text-left transition-all ${
                  cancelMode === "special_risk_drop"
                    ? "border-indigo-500 bg-indigo-950/50 text-white ring-1 ring-indigo-500"
                    : "border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                }`}
              >
                <div className="font-bold text-xs flex items-center justify-between">
                  <span>🚗 Sonderkündigung: Risikowegfall</span>
                  <span className="text-[10px] font-mono text-indigo-400 font-bold">§ 80 VVG</span>
                </div>
                <p className="text-[11px] text-zinc-400 mt-1 leading-snug">
                  Fahrzeugverkauf, Abmeldung, Sterbefall etc.
                </p>
              </button>
            </div>
          </div>

          {/* Dynamic Extra Options for Special Cancellations */}
          {cancelMode === "special_price_increase" && (
            <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-800/50 space-y-3">
              <h3 className="text-xs font-bold text-indigo-300 uppercase tracking-wider">
                ⚙️ Angaben zur Beitragserhöhung (§ 40 VVG)
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-300">Bisheriger Beitrag (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={oldCost}
                    onChange={e => setOldCost(e.target.value)}
                    placeholder="45.00"
                    className="bg-zinc-900 border-zinc-800 text-xs text-white"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-300">Neuer Beitrag (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={newCost}
                    onChange={e => setNewCost(e.target.value)}
                    placeholder="52.00"
                    className="bg-zinc-900 border-zinc-800 text-xs text-rose-300 font-bold font-mono"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-300">Datum der Erhöhungsschreibens</Label>
                  <Input
                    type="date"
                    value={noticeDate}
                    onChange={e => setNoticeDate(e.target.value)}
                    className="bg-zinc-900 border-zinc-800 text-xs text-white"
                  />
                </div>
              </div>
            </div>
          )}

          {cancelMode === "special_claim" && (
            <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-800/50 space-y-3">
              <h3 className="text-xs font-bold text-indigo-300 uppercase tracking-wider">
                ⚙️ Angaben zum Schadensfall (§ 92 VVG)
              </h3>

              {insurance.claims && insurance.claims.length > 0 && (
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-300">Aus erfassten Schadensfällen wählen:</Label>
                  <select
                    value={selectedClaimId}
                    onChange={e => handleClaimSelect(e.target.value)}
                    className="w-full bg-zinc-900 border border-zinc-800 rounded-md p-2 text-xs text-white"
                  >
                    <option value="custom">-- Manuelle Eingabe --</option>
                    {insurance.claims.map((c, i) => (
                      <option key={c.id || i} value={String(c.id || i)}>
                        {c.claim_number || `Schadensfall #${i+1}`} ({c.claim_date ? new Date(c.claim_date).toLocaleDateString("de-DE") : "Datum k.A."}) - {c.description || "Keine Beschreibung"}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-300">Schadensnummer (Schaden-Ref)</Label>
                  <Input
                    value={claimNumber}
                    onChange={e => setClaimNumber(e.target.value)}
                    placeholder="SCH-2026-00123"
                    className="bg-zinc-900 border-zinc-800 text-xs text-white font-mono"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-300">Schadensdatum / Regulierungsdatum</Label>
                  <Input
                    type="date"
                    value={claimDate}
                    onChange={e => setClaimDate(e.target.value)}
                    className="bg-zinc-900 border-zinc-800 text-xs text-white"
                  />
                </div>
              </div>
            </div>
          )}

          {cancelMode === "special_risk_drop" && (
            <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-800/50 space-y-3">
              <h3 className="text-xs font-bold text-indigo-300 uppercase tracking-wider">
                ⚙️ Angaben zum Risikowegfall (§ 80 VVG)
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-300">Grund des Wegfalls</Label>
                  <Input
                    value={riskReason}
                    onChange={e => setRiskReason(e.target.value)}
                    placeholder="z.B. Verkauf des Fahrzeugs / Stilllegung / Wohnungsauflösung"
                    className="bg-zinc-900 border-zinc-800 text-xs text-white"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-zinc-300">Datum des Wegfalls</Label>
                  <Input
                    type="date"
                    value={riskDate}
                    onChange={e => setRiskDate(e.target.value)}
                    className="bg-zinc-900 border-zinc-800 text-xs text-white"
                  />
                </div>
              </div>
            </div>
          )}

          {cancelMode === "special_custom" && (
            <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-800/50 space-y-3">
              <h3 className="text-xs font-bold text-indigo-300 uppercase tracking-wider">
                ⚙️ Individuelle Begründung der Sonderkündigung
              </h3>
              <div className="space-y-1">
                <Label className="text-xs text-zinc-300">Sonderkündigungsgrund</Label>
                <Input
                  value={customReason}
                  onChange={e => setCustomReason(e.target.value)}
                  placeholder="z.B. Doppelversicherung / Umzug ins Ausland"
                  className="bg-zinc-900 border-zinc-800 text-xs text-white"
                />
              </div>
            </div>
          )}

          {/* Form Fields Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* Absender Details */}
            <div className="space-y-3 bg-zinc-950/40 p-4 rounded-xl border border-zinc-800/80">
              <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">2. Deine Daten (Absender)</h3>
              <div className="space-y-2">
                <Label htmlFor="sName" className="text-xs text-zinc-300">Name / Vorname</Label>
                <Input
                  id="sName"
                  value={senderName}
                  onChange={(e) => setSenderName(e.target.value)}
                  placeholder="Max Mustermann"
                  className="bg-zinc-900 border-zinc-800 text-xs text-white"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sAddr" className="text-xs text-zinc-300">Straße & Hausnummer</Label>
                <Input
                  id="sAddr"
                  value={senderAddress}
                  onChange={(e) => setSenderAddress(e.target.value)}
                  placeholder="Musterstraße 12"
                  className="bg-zinc-900 border-zinc-800 text-xs text-white"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sCity" className="text-xs text-zinc-300">PLZ & Ort</Label>
                <Input
                  id="sCity"
                  value={senderCity}
                  onChange={(e) => setSenderCity(e.target.value)}
                  placeholder="12345 Berlin"
                  className="bg-zinc-900 border-zinc-800 text-xs text-white"
                />
              </div>
            </div>

            {/* Vertrag & Empfänger Details */}
            <div className="space-y-3 bg-zinc-950/40 p-4 rounded-xl border border-zinc-800/80">
              <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">3. Vertrag & Empfänger</h3>
              <div className="space-y-2">
                <Label htmlFor="rComp" className="text-xs text-zinc-300">Versicherungsgesellschaft</Label>
                <Input
                  id="rComp"
                  value={recipientCompany}
                  onChange={(e) => setRecipientCompany(e.target.value)}
                  className="bg-zinc-900 border-zinc-800 text-xs text-white"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="rInsNo" className="text-xs text-zinc-300">Versicherungsscheinnummer</Label>
                <Input
                  id="rInsNo"
                  value={insuranceNumber}
                  onChange={(e) => setInsuranceNumber(e.target.value)}
                  placeholder="VSN-12345678"
                  className="bg-zinc-900 border-zinc-800 text-xs text-white font-mono"
                />
              </div>

              {/* Extra legal checkboxes */}
              <div className="space-y-2 pt-2 border-t border-zinc-800/60">
                <Label className="text-[11px] font-mono text-zinc-400 block uppercase">Rechtliche Zusatz-Klauseln:</Label>
                
                <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={requestConfirmation}
                    onChange={e => setRequestConfirmation(e.target.checked)}
                    className="rounded accent-indigo-500"
                  />
                  <span>Schriftliche Kündigungsbestätigung anfordern</span>
                </label>

                <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={revokeSepa}
                    onChange={e => setRevokeSepa(e.target.checked)}
                    className="rounded accent-indigo-500"
                  />
                  <span>SEPA-Lastschriftmandat zum Kündigungstermin widerrufen</span>
                </label>

                <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={requestDataDeletion}
                    onChange={e => setRequestDataDeletion(e.target.checked)}
                    className="rounded accent-indigo-500"
                  />
                  <span>Löschung personenbezogener Daten (Art. 17 DSGVO)</span>
                </label>
              </div>
            </div>

          </div>

          {/* Live Preview Text Box */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <Label className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                4. Live-Vorschau des Kündigungsschreibens
              </Label>
              {copied && <span className="text-xs text-emerald-400 font-semibold">✓ In Zwischenablage kopiert!</span>}
            </div>
            <textarea
              readOnly
              rows={11}
              value={generateLetterText()}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-4 text-xs font-mono text-zinc-300 leading-relaxed focus:outline-none"
            />
          </div>

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-zinc-800 bg-zinc-950/60 flex flex-col sm:flex-row justify-between items-center gap-3">
          <Button variant="outline" onClick={onClose} className="border-zinc-800 text-zinc-400 text-xs w-full sm:w-auto">
            Abbrechen
          </Button>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <Button
              type="button"
              variant="outline"
              onClick={handleCopyText}
              className="border-zinc-700 bg-zinc-900 text-zinc-200 text-xs hover:bg-zinc-800 w-full sm:w-auto"
            >
              📋 Text kopieren
            </Button>

            <Button
              type="button"
              onClick={handlePrint}
              className="theme-bg-accent text-white text-xs font-semibold theme-glow w-full sm:w-auto flex items-center gap-2"
            >
              🖨️ Drucken / PDF speichern
            </Button>
          </div>
        </div>

      </div>
    </div>
  );
}
