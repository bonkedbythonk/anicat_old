"use client";

import { useEffect } from "react";

// Map month to preset for seasonal option
function getSeasonPreset(): string {
  const month = new Date().getMonth(); // 0-11
  if (month >= 11 || month <= 1) return "preset-ocean";
  if (month >= 2 && month <= 4) return "preset-sakura";
  if (month >= 5 && month <= 7) return "preset-forest";
  return "preset-sunset";
}

/**
 * Listens to system-level `prefers-color-scheme` changes and
 * localStorage `anicat_theme` overrides to keep `<html>` class
 * attributes in sync. Also applies color presets.
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

    const applyPreset = () => {
      const preset = localStorage.getItem("anicat_color_preset") || "preset-default";
      
      document.documentElement.classList.remove(
        "preset-sakura", "preset-ocean", "preset-forest", 
        "preset-sunset", "preset-amethyst", "preset-ruby", "preset-default"
      );

      if (preset === "seasonal") {
        document.documentElement.classList.add(getSeasonPreset());
      } else if (preset !== "preset-default") {
        document.documentElement.classList.add(preset);
      }
    };

    applyTheme();
    applyPreset();

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
      if (e.key === "anicat_color_preset") {
        document.documentElement.classList.add("theme-transition");
        applyPreset();
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
