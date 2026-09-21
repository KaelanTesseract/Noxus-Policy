/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

const HTML_ESCAPES: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

/**
 * Escapes a value for safe interpolation into an HTML string. The print windows
 * build their whole page with document.write(); insurance names, companies and
 * policy numbers there often come from OCR/AI extraction of uploaded documents,
 * i.e. from whoever wrote the document, so they must never be inserted as raw HTML.
 */
export function escapeHtml(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value).replace(/[&<>"']/g, (ch) => HTML_ESCAPES[ch]);
}
