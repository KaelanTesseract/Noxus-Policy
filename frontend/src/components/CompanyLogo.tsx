"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState } from "react";

const DOMAIN_MAP: Record<string, string> = {
  "huk24": "huk24.de",
  "huk-coburg": "huk.de",
  "huk": "huk.de",
  "allianz": "allianz.de",
  "axa": "axa.de",
  "generali": "generali.de",
  "ergo": "ergo.de",
  "signal iduna": "signal-iduna.de",
  "devk": "devk.de",
  "lvm": "lvm.de",
  "debeka": "debeka.de",
  "r+v": "ruv.de",
  "r & v": "ruv.de",
  "gothaer": "gothaer.de",
  "barmenia": "barmenia.de",
  "cosmosdirekt": "cosmosdirekt.de",
  "hansemerkur": "hansemerkur.de",
  "vhv": "vhv.de",
  "nürnberger": "nuernberger.de",
  "nuernberger": "nuernberger.de",
  "zurich": "zurich.de",
  "hdi": "hdi.de",
  "adac": "adac.de",
  "arag": "arag.de",
  "wgv": "wgv.de",
  "provinzial": "provinzial.de",
  "helvetia": "helvetia.de",
  "haftpflichtkasse": "haftpflichtkasse.de",
  "die haftpflichtkasse": "haftpflichtkasse.de",
  "wwk": "wwk.de",
  "baloise": "baloise.de",
  "interrisk": "interrisk.de",
  "itzehoer": "itzehoer.de",
  "continentale": "continentale.de",
  "dfv": "deutsche-familienversicherung.de",
  "deutsche familienversicherung": "deutsche-familienversicherung.de",
  "die bayerische": "diebayerische.de",
  "bayerische": "diebayerische.de",
  "bavariadirekt": "bavariadirekt.de",
  "friday": "friday.de",
  "getsafe": "getsafe.eu",
  "feather": "feather-insurance.com",
  "hiscox": "hiscox.de",
  "wertgarantie": "wertgarantie.de",
  "agila": "agila.de",
  "uelzener": "uelzener.de",
  "sv sparkassenversicherung": "sparkassenversicherung.de",
  "sparkassen direkt": "sparkassendirekt.de"
};

function getDomainForCompany(company: string): string {
  if (!company) return "";
  const cleaned = company.toLowerCase().trim();

  for (const [key, domain] of Object.entries(DOMAIN_MAP)) {
    if (cleaned.includes(key)) {
      return domain;
    }
  }

  // Fallback domain extraction
  const firstWord = cleaned.split(" ")[0].replace(/[^a-z0-9]/g, "");
  if (firstWord && firstWord.length > 2) {
    return `${firstWord}.de`;
  }
  return "";
}

function getInitials(company: string): string {
  if (!company) return "POL";
  const words = company.trim().split(/\s+/);
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  return company.substring(0, 3).toUpperCase();
}

interface CompanyLogoProps {
  company: string;
  className?: string;
  size?: "sm" | "md" | "lg";
}

const FAILED_DOMAINS_KEY = "company_logo_failed_domains";

function isDomainKnownToFail(domain: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    const raw = window.localStorage.getItem(FAILED_DOMAINS_KEY);
    return raw ? JSON.parse(raw).includes(domain) : false;
  } catch (_) {
    return false;
  }
}

function rememberFailedDomain(domain: string) {
  if (typeof window === "undefined") return;
  try {
    const raw = window.localStorage.getItem(FAILED_DOMAINS_KEY);
    const failed: string[] = raw ? JSON.parse(raw) : [];
    if (!failed.includes(domain)) {
      failed.push(domain);
      window.localStorage.setItem(FAILED_DOMAINS_KEY, JSON.stringify(failed.slice(-200)));
    }
  } catch (_) {}
}

export function CompanyLogo({ company, className = "", size = "md" }: CompanyLogoProps) {
  const domain = getDomainForCompany(company);
  const [hasError, setHasError] = useState(() => isDomainKnownToFail(domain));

  const sizeClasses = {
    sm: "w-8 h-8 text-xs rounded-lg",
    md: "w-10 h-10 text-sm rounded-xl",
    lg: "w-12 h-12 text-base rounded-xl"
  };

  const imgSizes = {
    sm: "w-7 h-7",
    md: "w-9 h-9",
    lg: "w-11 h-11"
  };

  if (!domain || hasError) {
    return (
      <div 
        className={`${sizeClasses[size]} theme-bg-accent text-white font-extrabold font-mono flex items-center justify-center shadow-md border border-white/20 shrink-0 ${className}`}
        title={company}
      >
        {getInitials(company)}
      </div>
    );
  }

  const logoUrl = `https://www.google.com/s2/favicons?domain=${domain}&sz=128`;

  return (
    <div 
      className={`${sizeClasses[size]} bg-transparent flex items-center justify-center p-0 shrink-0 overflow-hidden ${className}`}
      title={company}
    >
      <img
        src={logoUrl}
        alt={`${company} Logo`}
        width={128}
        height={128}
        loading="lazy"
        decoding="async"
        onError={() => {
          rememberFailedDomain(domain);
          setHasError(true);
        }}
        className={`${imgSizes[size]} object-contain drop-shadow-md`}
      />
    </div>
  );
}
