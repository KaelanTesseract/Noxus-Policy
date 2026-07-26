"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface CancellationModalProps {
  isOpen: boolean;
  onClose: () => void;
  insurance: {
    name: string;
    company?: string;
    insurance_number?: string;
    cancellation_date?: string;
    contact_info?: string;
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

export function CancellationModal({ isOpen, onClose, insurance, userEmail }: CancellationModalProps) {
  const [senderName, setSenderName] = useState("");
  const [senderAddress, setSenderAddress] = useState("");
  const [senderCity, setSenderCity] = useState("");
  
  const [recipientCompany, setRecipientCompany] = useState("");
  const [recipientAddress, setRecipientAddress] = useState("");
  const [insuranceNumber, setInsuranceNumber] = useState("");
  
  const [cancellationType, setCancellationType] = useState<"ordinary" | "extraordinary">("ordinary");
  const [cancellationReason, setCancellationReason] = useState("Beitragserhöhung");
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
      if (userEmail) {
        setSenderName(userEmail.split("@")[0].replace(/\./g, " "));
      }
    }
  }, [insurance, userEmail]);

  if (!isOpen || !insurance) return null;

  const todayStr = new Date().toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  });

  const generateLetterText = () => {
    const cancelText = cancellationType === "ordinary"
      ? "hiermit kündige ich meinen oben genannten Versicherungsvertrag ordentlich zum nächstmöglichen Zeitpunkt."
      : `hiermit kündige ich meinen oben genannten Versicherungsvertrag außerordentlich aufgrund von: ${cancellationReason}.`;

    return `${senderName || "[Dein Name]"}
${senderAddress || "[Deine Straße & Hausnummer]"}
${senderCity || "[PLZ & Ort]"}

Datum: ${todayStr}

An:
${recipientCompany}
${recipientAddress}


KÜNDIGUNG DER VERSICHERUNG: ${insurance.name.toUpperCase()}
Versicherungsscheinnummer: ${insuranceNumber || "[Polizzen-Nummer]"}


Sehr geehrte Damen und Herren,

${cancelText}

Ich bitte Sie, mir den Eingang dieser Kündigung sowie das genaue Vertragsende schriftlich zu bestätigen.

Einwilligungen zum Einzug von Beiträgen per SEPA-Lastschrift für diesen Vertrag widerrufe ich hiermit zum Kündigungstermin.

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
      alert("Druckfenster konnte nicht geöffnet werden. Bitte Erlaube Popups.");
      return;
    }

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title></title>
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
              line-height: 1.5;
              color: #000000;
              margin: 0;
              padding: 0;
            }
            .header-info { margin-bottom: 35px; }
            .recipient { margin-bottom: 40px; font-weight: bold; font-size: 11pt; line-height: 1.4; }
            .subject { font-size: 12pt; font-weight: bold; margin-bottom: 25px; text-transform: uppercase; }
            .content { margin-bottom: 45px; white-space: pre-line; }
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
            Kündigung der Versicherung: ${insurance.name}<br/>
            <span style="font-size: 10pt; font-weight: normal;">Versicherungsscheinnummer: ${insuranceNumber || "Nicht angegeben"}</span>
          </div>

          <div class="content">
${cancellationType === "ordinary" 
  ? "Sehr geehrte Damen und Herren,\n\nhiermit kündige ich meinen oben genannten Versicherungsvertrag ordentlich zum nächstmöglichen Zeitpunkt."
  : `Sehr geehrte Damen und Herren,\n\nhiermit kündige ich meinen oben genannten Versicherungsvertrag außerordentlich aufgrund von: ${cancellationReason}.`}

Ich bitte Sie, mir den Eingang dieser Kündigung sowie das genaue Vertragsende schriftlich zu bestätigen.

Einwilligungen zum Einzug von Beiträgen per SEPA-Lastschrift für diesen Vertrag widerrufe ich hiermit zum Kündigungstermin.

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
        <div className="px-6 py-4 border-b border-zinc-800 flex justify-between items-center bg-zinc-950/50">
          <div className="flex items-center gap-2">
            <span className="text-xl">✍️</span>
            <h2 className="text-lg font-bold text-white">Kündigungsschreiben-Generator</h2>
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
                Wichtiger Sicherheitshinweis:
              </strong>
              Bitte überprüfe alle eingetragenen Angaben (insbesondere Kündigungsfrist, Versicherten- / Polizzen-Nummer und Empfängeradresse) sorgfältig auf Richtigkeit, bevor du das Kündigungsschreiben ausdruckst, unterschreibst und versendest!
            </div>
          </div>

          {/* Form Fields Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* Absender Details */}
            <div className="space-y-3 bg-zinc-950/40 p-4 rounded-xl border border-zinc-800/80">
              <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">1. Deine Daten (Absender)</h3>
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
              <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">2. Vertrag & Empfänger</h3>
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
              <div className="space-y-2">
                <Label htmlFor="cType" className="text-xs text-zinc-300">Kündigungsart</Label>
                <select
                  id="cType"
                  value={cancellationType}
                  onChange={(e) => setCancellationType(e.target.value as any)}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-md p-2 text-xs text-white"
                >
                  <option value="ordinary">Ordentliche Kündigung (zum nächstmöglichen Termin)</option>
                  <option value="extraordinary">Außerordentliche Kündigung (Sonderkündigung)</option>
                </select>
              </div>

              {cancellationType === "extraordinary" && (
                <div className="space-y-2 pt-1">
                  <Label htmlFor="cReason" className="text-xs text-zinc-300">Grund für Sonderkündigung</Label>
                  <Input
                    id="cReason"
                    value={cancellationReason}
                    onChange={(e) => setCancellationReason(e.target.value)}
                    placeholder="z.B. Beitragserhöhung / Schadensfall"
                    className="bg-zinc-900 border-zinc-800 text-xs text-white"
                  />
                </div>
              )}
            </div>

          </div>

          {/* Live Preview Text Box */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <Label className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                3. Vorschau des Dokumentes
              </Label>
              {copied && <span className="text-xs text-emerald-400 font-semibold">✓ In Zwischenablage kopiert!</span>}
            </div>
            <textarea
              readOnly
              rows={10}
              value={generateLetterText()}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-4 text-xs font-mono text-zinc-300 leading-relaxed focus:outline-none"
            />
          </div>

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-zinc-800 bg-zinc-950/50 flex flex-col sm:flex-row justify-between items-center gap-3">
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
