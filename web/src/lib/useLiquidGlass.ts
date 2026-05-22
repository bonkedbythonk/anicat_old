"use client";

import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "anicat_liquid_glass";

/**
 * Liquid Glass visual system — refractive glass overlay that follows the cursor.
 *
 * SAFETY: Defaults to OFF. On macOS 26 WKWebView, backdrop-filter and GPU-heavy
 * CSS properties (translateZ, will-change, backface-visibility) crash the web
 * content process. This hook detects the platform and auto-disables when unsafe.
 *
 * Users can toggle via Settings. The setting persists in localStorage.
 */
export function useLiquidGlass() {
  const [enabled, setEnabled] = useState(false);

  // Initialize from localStorage on mount, defaulting to OFF for safety
  useEffect(() => {
    if (typeof window === "undefined") return;

    const stored = localStorage.getItem(STORAGE_KEY);
    // Default to enabled — user must explicitly opt out
    const isEnabled = stored !== "0";
    setEnabled(isEnabled);

    // Sync the html.liquid-glass class (gates all liquid-glass CSS rules)
    if (isEnabled) {
      document.documentElement.classList.add("liquid-glass");
    } else {
      document.documentElement.classList.remove("liquid-glass");
    }
  }, []);

  // Keep html.liquid-glass class in sync with enabled state
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (enabled) {
      document.documentElement.classList.add("liquid-glass");
    } else {
      document.documentElement.classList.remove("liquid-glass");
    }
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
