"use client";

import { useEffect } from "react";

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
  useEffect(() => {
    // UX-01: Expose navigation to native macOS menu bar via eval bridge
    (window as any).__anicat_navigate__ = (view: ViewName) => {
      _previousView = view;
      onNavigate(view);
    };
    (window as any).__anicat_toggle_help__ = () => onToggleHelp();

    return () => {
      delete (window as any).__anicat_navigate__;
      delete (window as any).__anicat_toggle_help__;
    };
  }, [onNavigate, onToggleHelp]);

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
        onNavigate("search");
        return;
      }
      if (meta && e.key === ",") {
        e.preventDefault();
        _previousView = "settings";
        onNavigate("settings");
        return;
      }
      if (meta && e.shiftKey && e.key === "?") {
        e.preventDefault();
        onToggleHelp();
        return;
      }
      if (meta && e.key >= "1" && e.key <= "9") {
        e.preventDefault();
        const views: ViewName[] = ["home", "library", "schedule", "manga", "lists", "downloads", "notifications", "profile", "settings"];
        const idx = parseInt(e.key) - 1;
        if (idx < views.length) {
          _previousView = views[idx];
          onNavigate(views[idx]);
        }
        return;
      }

      if (isInput) return;

      // Single-key fallbacks for power users (no modifier)
      switch (e.key) {
        case "/":
          e.preventDefault();
          _previousView = "search";
          onNavigate("search");
          break;
        case "Escape":
          onCloseDetail();
          break;
        case "?":
          e.preventDefault();
          onToggleHelp();
          break;
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onNavigate, onCloseDetail, onToggleHelp]);
}
