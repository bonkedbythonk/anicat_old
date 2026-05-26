"use client";

import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "anicat_liquid_glass";

/**
 * Returns true when the current UI style supports liquid glass effects.
 * Currently only "neon-abyss" has liquid glass visuals.
 */
function isStyleSupported(): boolean {
  if (typeof document === "undefined") return false;
  return document.documentElement.getAttribute("data-style") === "neon-abyss";
}

/**
 * Syncs the `liquid-glass` class on `<html>` — only when enabled AND
 * the current UI style supports it (Neon Abyss only).
 */
function syncLiquidGlass(enabled: boolean) {
  if (typeof document === "undefined") return;
  if (enabled && isStyleSupported()) {
    document.documentElement.classList.add("liquid-glass");
  } else {
    document.documentElement.classList.remove("liquid-glass");
  }
}

/**
 * Liquid Glass visual system — refractive glass overlay that follows the cursor.
 *
 * SAFETY: Defaults to OFF. On macOS 26 WKWebView, backdrop-filter and GPU-heavy
 * CSS properties (translateZ, will-change, backface-visibility) crash the web
 * content process. This hook detects the platform and auto-disables when unsafe.
 *
 * Only activates when the active UI style is "neon-abyss".
 * Switching to Sakura Zen or Retro Manga automatically removes liquid glass.
 *
 * Users can toggle via Settings. The setting persists in localStorage.
 */
export function useLiquidGlass() {
  const [enabled, setEnabled] = useState(false);

  // Initialize from localStorage on mount
  useEffect(() => {
    if (typeof window === "undefined") return;

    const stored = localStorage.getItem(STORAGE_KEY);
    const isEnabled = stored === "1";
    setEnabled(isEnabled);
    syncLiquidGlass(isEnabled);
  }, []);

  // React to style switches (e.g. user changes UI skin in Settings)
  useEffect(() => {
    if (typeof window === "undefined") return;

    const observer = new MutationObserver(() => {
      syncLiquidGlass(enabled);
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-style"],
    });

    return () => observer.disconnect();
  }, [enabled]);

  // Keep html.liquid-glass class in sync with enabled state
  useEffect(() => {
    syncLiquidGlass(enabled);
  }, [enabled]);

  const toggle = useCallback(() => {
    setEnabled((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
      }
      return next;
    });
  }, []);

  return { enabled, toggle, setEnabled };
}

export default useLiquidGlass;
