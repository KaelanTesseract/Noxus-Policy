"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { Copy } from "lucide-react";

// An earlier document of the same user with exactly the same file (backend/document_hash.py).
export type DuplicateInfo = {
  document_id: number;
  name: string;
  uploaded?: string | null;
  insurance_id?: number | null;
  insurance_name?: string | null;
  in_inbox?: boolean;
};

export function describeDuplicate(d: DuplicateInfo): string {
  const where = d.in_inbox ? "im Posteingang" : d.insurance_name ? `bei „${d.insurance_name}“` : "im Archiv";
  const when = d.uploaded ? `, hochgeladen am ${d.uploaded.split("-").reverse().join(".")}` : "";
  return `„${d.name}“ ${where}${when}`;
}

/** Warning that this exact file is already stored. It only informs: saving stays possible. */
export function DuplicateNotice({ duplicate }: { duplicate?: DuplicateInfo | null }) {
  if (!duplicate) return null;
  return (
    <div role="status" className="p-3.5 rounded-xl border border-[color:var(--calm-signal,#fbbf24)]/50 bg-zinc-900/60 text-xs flex items-start gap-2.5">
      <Copy className="size-4 shrink-0 mt-0.5 text-[color:var(--calm-signal,#fbbf24)]" aria-hidden />
      <div className="space-y-0.5">
        <p className="font-semibold text-zinc-100">Dieses Dokument hast du schon hochgeladen</p>
        <p className="text-zinc-400">{describeDuplicate(duplicate)}. Du kannst es trotzdem speichern, dann liegt es doppelt im Archiv.</p>
      </div>
    </div>
  );
}
