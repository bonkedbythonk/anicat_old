"use client";

import { useEffect } from "react";

/**
 * Listens to system-level `prefers-color-scheme` changes and
 * localStorage `anicat_theme` overrides to keep `<html>` class
 * attributes in sync.
 *
 * Supported theme values: "light", "dark", "system".
 *
 * Returns nothing — this is a pure side-effect hook.
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

    applyTheme();

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
