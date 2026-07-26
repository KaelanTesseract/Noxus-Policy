"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useState, useEffect } from "react";
import { APP_VERSION, APP_COPYRIGHT, GITHUB_REPO } from "@/lib/version";

export function Footer() {
  const [latestVersion, setLatestVersion] = useState<string | null>(null);

  useEffect(() => {
    // Quietly check GitHub API for new release
    fetch(`https://api.github.com/repos/${GITHUB_REPO}/releases/latest`)
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data && data.tag_name) {
          const remoteTag = data.tag_name.trim();
          if (remoteTag !== APP_VERSION && remoteTag !== APP_VERSION.replace("v", "")) {
            setLatestVersion(remoteTag);
          }
        }
      })
      .catch(() => {});
  }, []);

  return (
    <footer className="mt-auto py-4 border-t border-zinc-800/60 text-xs text-zinc-500 font-mono bg-zinc-950/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 md:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap justify-center sm:justify-start">
          <span className="text-zinc-400 font-medium">{APP_COPYRIGHT}</span>
          <span>•</span>
          <span>Open Source Software (MIT)</span>
          <span>•</span>
          <span className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 font-semibold">
            {APP_VERSION}
          </span>
        </div>

        {latestVersion ? (
          <a
            href={`https://github.com/${GITHUB_REPO}/releases`}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 px-3 py-1 rounded-full bg-amber-950/60 border border-amber-800/80 text-amber-300 text-xs font-semibold hover:bg-amber-900/60 transition-all animate-pulse shadow-lg"
          >
            <span className="w-2 h-2 rounded-full bg-amber-400"></span>
            <span>✨ Neue Version {latestVersion} verfügbar! (Tippe 'update' im Terminal)</span>
          </a>
        ) : (
          <div className="flex items-center gap-3 text-zinc-500">
            <a 
              href={`https://github.com/${GITHUB_REPO}`} 
              target="_blank" 
              rel="noreferrer"
              className="hover:text-zinc-300 transition-colors flex items-center gap-1.5"
            >
              <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
              </svg>
              <span>GitHub Repository</span>
            </a>
          </div>
        )}
      </div>
    </footer>
  );
}
