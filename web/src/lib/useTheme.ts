"use client";

import { useEffect } from "react";

// UX-21: Map month to season for attic renovation theme
function getSeasonClass(): string {
  const month = new Date().getMonth(); // 0-11
  if (month >= 11 || month <= 1) return "season-winter";
  if (month >= 2 && month <= 4) return "season-spring";
  if (month >= 5 && month <= 7) return "season-summer";
  return "season-autumn";
}

/**
 * Listens to system-level `prefers-color-scheme` changes and
 * localStorage `anicat_theme` overrides to keep `<html>` class
 * attributes in sync. Also applies seasonal accent variants (UX-21).
 */
export function useTheme() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const applyTheme = () => {
      const theme = localStorage.getItem("anicat_theme") || "system";
      const isDarkSystem = mediaQuery.matches;

      document.documentElement.classList.remove("light", "dark", "system");
      document.documentElement.classList.add(theme);

      if (theme === "light" || (theme === "system" && !isDarkSystem)) {
        document.documentElement.classList.add("light");
      } else {
        document.documentElement.classList.add("dark");
      }
    };

    const applySeason = () => {
      // Remove old season classes
      document.documentElement.classList.remove(
        "season-winter", "season-spring", "season-summer", "season-autumn"
      );
      document.documentElement.classList.add(getSeasonClass());
    };

    applyTheme();
    applySeason();

    const listener = () => {
      const theme = localStorage.getItem("anicat_theme") || "system";
      if (theme === "system") {
        document.documentElement.classList.add("theme-transition");
        applyTheme();
        setTimeout(() => {
          document.documentElement.classList.remove("theme-transition");
        }, 300);
      }
    };

    mediaQuery.addEventListener("change", listener);

    const storageListener = (e: StorageEvent) => {
      if (e.key === "anicat_theme") {
        document.documentElement.classList.add("theme-transition");
        applyTheme();
        setTimeout(() => {
          document.documentElement.classList.remove("theme-transition");
        }, 300);
      }
    };
    window.addEventListener("storage", storageListener);

    return () => {
      mediaQuery.removeEventListener("change", listener);
      window.removeEventListener("storage", storageListener);
    };
  }, []);
}
