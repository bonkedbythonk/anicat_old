"use client";

import { useState, useEffect, useRef, useCallback } from "react";

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
  const cursorRef = useRef<{ x: number; y: number }>({ x: 0.5, y: 0.5 });
  const rafRef = useRef<number | null>(null);

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

  // Track mouse position via requestAnimationFrame (not passive listeners
  // that fire on every pixel move — this is throttled to 60fps)
  useEffect(() => {
    if (!enabled) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (rafRef.current !== null) return; // already scheduled
      rafRef.current = requestAnimationFrame(() => {
        cursorRef.current = {
          x: e.clientX / window.innerWidth,
          y: e.clientY / window.innerHeight,
        };
        rafRef.current = null;
      });
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
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

  return { enabled, cursorRef, toggle, setEnabled };
}

export default useLiquidGlass;
