"use client"
/**
 * Copyright (c) 2026 Dennis Guse. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in project root.
 */

import { useEffect, useState, createContext, useContext } from "react";

export type ColorTheme = "indigo" | "emerald" | "violet" | "cyan" | "amber" | "rose";

// Only one style ships today; the type stays a union and STYLES stays a list so a
// future theme can be added by appending an id here, an entry below, and a matching
// `html[data-style="..."] { ... }` block in globals.css (see the comment there).
export type StyleTheme = "dark-glass";

export const STYLES: {
  id: StyleTheme;
  name: string;
  mode: "dark" | "light";
  desc: string;
  previewBg: string;
  previewCard: string;
  previewBorder: string;
}[] = [
  {
    id: "dark-glass",
    name: "Dark Neon Glass (Standard)",
    mode: "dark",
    desc: "Dunkles Glasmorphismus-Design mit Neoneffekten & transparenten Glaskarten.",
    previewBg: "#09090b",
    previewCard: "#18181b",
    previewBorder: "#27272a"
  }
];

export const THEMES: { id: ColorTheme; name: string; color: string; bgGradient: string }[] = [
  { id: "indigo", name: "Indigo Night", color: "#6366f1", bgGradient: "from-indigo-900/20" },
  { id: "emerald", name: "Emerald Forest", color: "#10b981", bgGradient: "from-emerald-900/20" },
  { id: "violet", name: "Violet Cyber", color: "#a855f7", bgGradient: "from-purple-900/20" },
  { id: "cyan", name: "Ocean Deep", color: "#06b6d4", bgGradient: "from-cyan-900/20" },
  { id: "amber", name: "Sunset Amber", color: "#f59e0b", bgGradient: "from-amber-900/20" },
  { id: "rose", name: "Rose Crimson", color: "#f43f5e", bgGradient: "from-rose-900/20" },
];

interface ThemeContextType {
  theme: ColorTheme;
  setTheme: (t: ColorTheme) => void;
  styleTheme: StyleTheme;
  setStyleTheme: (s: StyleTheme) => void;
  showCostChart: boolean;
  setShowCostChart: (show: boolean) => void;
}

const ThemeContext = createContext<ThemeContextType>({
  theme: "indigo",
  setTheme: () => {},
  styleTheme: "dark-glass",
  setStyleTheme: () => {},
  showCostChart: true,
  setShowCostChart: () => {}
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ColorTheme>("indigo");
  const [styleTheme, setStyleThemeState] = useState<StyleTheme>("dark-glass");
  const [showCostChart, setShowCostChartState] = useState<boolean>(true);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedTheme = localStorage.getItem("app-theme") as ColorTheme;
      const savedStyle = localStorage.getItem("app-style") as StyleTheme;
      const savedChart = localStorage.getItem("app-show-cost-chart");

      if (savedTheme && THEMES.some(t => t.id === savedTheme)) {
        setThemeState(savedTheme);
        document.documentElement.setAttribute("data-theme", savedTheme);
      } else {
        document.documentElement.setAttribute("data-theme", "indigo");
      }

      if (savedStyle && STYLES.some(s => s.id === savedStyle)) {
        setStyleThemeState(savedStyle);
        document.documentElement.setAttribute("data-style", savedStyle);
      } else {
        document.documentElement.setAttribute("data-style", "dark-glass");
      }

      if (savedChart !== null) {
        setShowCostChartState(savedChart === "true");
      }
    }
  }, []);

  const setTheme = (newTheme: ColorTheme) => {
    setThemeState(newTheme);
    if (typeof window !== "undefined") {
      localStorage.setItem("app-theme", newTheme);
      document.documentElement.setAttribute("data-theme", newTheme);
    }
  };

  const setStyleTheme = (newStyle: StyleTheme) => {
    setStyleThemeState(newStyle);
    if (typeof window !== "undefined") {
      localStorage.setItem("app-style", newStyle);
      document.documentElement.setAttribute("data-style", newStyle);
    }
  };

  const setShowCostChart = (show: boolean) => {
    setShowCostChartState(show);
    if (typeof window !== "undefined") {
      localStorage.setItem("app-show-cost-chart", String(show));
    }
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, styleTheme, setStyleTheme, showCostChart, setShowCostChart }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
