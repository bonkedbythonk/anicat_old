"use client";

import { useEffect, useRef, type RefObject } from "react";

interface CursorPos {
  x: number;
  y: number;
}

interface LiquidGlassOverlayProps {
  /** Ref tracking normalized cursor position (0-1 on each axis). */
  cursorRef: RefObject<CursorPos>;
  /** Whether the liquid glass effect is enabled. When false, renders nothing. */
  enabled: boolean;
}

/**
 * Liquid Glass Overlay — a subtle, cursor-following refractive effect.
 *
 * SAFETY: This component renders NOTHING when `enabled` is false (zero DOM
 * overhead). When enabled, it uses a lightweight CSS radial gradient that
 * follows the cursor — NO backdrop-filter, NO translateZ, NO will-change,
 * NO backface-visibility, NO @property rules. All of those crash WKWebView
 * on macOS 26.
 *
 * The effect is achieved with a single absolutely-positioned div with a
 * radial-gradient background whose position is updated via
 * requestAnimationFrame. This keeps GPU compositing to a minimum while
 * still producing a visible "glass lens" effect.
 */
export default function LiquidGlassOverlay({
  cursorRef,
  enabled,
}: LiquidGlassOverlayProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const overlay = overlayRef.current;
    if (!overlay) return;

    let running = true;

    const updatePosition = () => {
      if (!running) return;
      const { x, y } = cursorRef.current;
      // Move the radial gradient center to follow the cursor
      overlay.style.setProperty("--lg-x", `${x * 100}%`);
      overlay.style.setProperty("--lg-y", `${y * 100}%`);
      rafRef.current = requestAnimationFrame(updatePosition);
    };

    rafRef.current = requestAnimationFrame(updatePosition);

    return () => {
      running = false;
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [enabled, cursorRef]);

  if (!enabled) return null;

  return (
    <div
      ref={overlayRef}
      aria-hidden="true"
      className="fixed inset-0 pointer-events-none z-0"
      style={{
        background: `
          radial-gradient(
            800px circle at var(--lg-x, 50%) var(--lg-y, 50%),
            color-mix(in srgb, var(--accent-color) 50%, transparent) 0%,
            color-mix(in srgb, var(--secondary-color) 30%, transparent) 30%,
            transparent 60%
          )
        `,
        opacity: 0.8,
        transition: 'opacity 0.5s ease',
      }}
    />
  );
}
