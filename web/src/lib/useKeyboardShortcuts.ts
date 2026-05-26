"use client";

import { useEffect, useRef } from "react";

type ViewName = "home" | "manga" | "search" | "lists" | "downloads" | "library" | "settings" | "notifications" | "profile" | "schedule";

interface UseKeyboardShortcutsOptions {
  onNavigate: (view: ViewName) => void;
  onCloseDetail: () => void;
  onToggleHelp: () => void;
}

// UX-28: Track previous view for back-to-context after player close
let _previousView: ViewName = "home";

export function getPreviousView(): ViewName {
  return _previousView;
}

export default function useKeyboardShortcuts({
  onNavigate,
  onCloseDetail,
  onToggleHelp,
}: UseKeyboardShortcutsOptions) {
  const callbacksRef = useRef({ onNavigate, onCloseDetail, onToggleHelp });

  // Sync callbacks to ref on every render
  useEffect(() => {
    callbacksRef.current = { onNavigate, onCloseDetail, onToggleHelp };
  });

  useEffect(() => {
    // UX-01: Expose navigation to native macOS menu bar via eval bridge
    (window as any).__anicat_navigate__ = (view: ViewName) => {
      _previousView = view;
      callbacksRef.current.onNavigate(view);
    };
    (window as any).__anicat_toggle_help__ = () => callbacksRef.current.onToggleHelp();

    return () => {
      delete (window as any).__anicat_navigate__;
      delete (window as any).__anicat_toggle_help__;
    };
  }, []);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement)?.tagName;
      const isInput = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" ||
        (e.target as HTMLElement)?.isContentEditable;

      // UX-02: Command-key combos (primary) + single-key fallbacks (non-input only)
      const meta = e.metaKey || e.ctrlKey;

      if (meta && e.key === "k") {
        e.preventDefault();
        _previousView = "search";
        callbacksRef.current.onNavigate("search");
        return;
      }
      if (meta && e.key === ",") {
        e.preventDefault();
        _previousView = "settings";
        callbacksRef.current.onNavigate("settings");
        return;
      }
      if (meta && e.shiftKey && e.key === "?") {
        e.preventDefault();
        callbacksRef.current.onToggleHelp();
        return;
      }
      if (meta && e.key >= "1" && e.key <= "9") {
        e.preventDefault();
        const views: ViewName[] = ["home", "library", "schedule", "manga", "lists", "downloads", "notifications", "profile", "settings"];
        const idx = parseInt(e.key) - 1;
        if (idx < views.length) {
          _previousView = views[idx];
          callbacksRef.current.onNavigate(views[idx]);
        }
        return;
      }

      if (isInput) return;

      // Single-key triggers for navigating when not typing
      if (e.key >= "1" && e.key <= "9") {
        const views: ViewName[] = ["home", "library", "schedule", "manga", "lists", "downloads", "notifications", "profile", "settings"];
        const idx = parseInt(e.key) - 1;
        if (idx < views.length) {
          _previousView = views[idx];
          callbacksRef.current.onNavigate(views[idx]);
        }
        return;
      }

      switch (e.key) {
        case "/":
        case "k":
        case "K":
          e.preventDefault();
          _previousView = "search";
          callbacksRef.current.onNavigate("search");
          break;
        case ",":
          e.preventDefault();
          _previousView = "settings";
          callbacksRef.current.onNavigate("settings");
          break;
        case "Escape":
          callbacksRef.current.onCloseDetail();
          break;
        case "?":
          e.preventDefault();
          callbacksRef.current.onToggleHelp();
          break;
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);
}
