"use client";

import { useEffect } from "react";

/**
 * Bridges all browser console output and unhandled errors to the
 * AniCat backend logging endpoint so that WebView diagnostics are
 * visible in the sidecar log.
 *
 * Returns nothing — this is a pure side-effect hook.
 */
export function useRemoteLogging() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    const safeStringify = (val: unknown): string => {
      try {
        if (val === null) return "null";
        if (val === undefined) return "undefined";
        if (typeof val === "object") {
          if (val instanceof Error) {
            return `${val.name}: ${val.message}\n${val.stack || ""}`;
          }
          const seen = new WeakSet();
          return JSON.stringify(val, (_key, value) => {
            if (typeof value === "object" && value !== null) {
              if (seen.has(value)) return "[Circular]";
              seen.add(value);
            }
            return value;
          });
        }
        return String(val);
      } catch {
        return `[Unstringifiable Object: ${(val as any)?.constructor?.name || typeof val}]`;
      }
    };

    const logToBackend = async (level: string, message: string, data?: unknown) => {
      try {
        await fetch("http://127.0.0.1:13370/api/actions/log", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            level,
            message,
            data: data ? { detail: safeStringify(data) } : undefined,
          }),
        });
      } catch {
        // Silently ignore log failures to avoid infinite loops
      }
    };

    const handleError = (event: ErrorEvent) => {
      logToBackend("error", `Uncaught Error: ${event.message} at ${event.filename}:${event.lineno}:${event.colno}`, event.error);
    };

    const handleRejection = (event: PromiseRejectionEvent) => {
      logToBackend("error", `Unhandled Rejection: ${event.reason}`, event.reason);
    };

    const originalConsoleError = console.error;
    const originalConsoleWarn = console.warn;
    const originalConsoleLog = console.log;

    console.error = (...args: unknown[]) => {
      originalConsoleError.apply(console, args as any[]);
      logToBackend("error", args.map(safeStringify).join(" "));
    };
    console.warn = (...args: unknown[]) => {
      originalConsoleWarn.apply(console, args as any[]);
      logToBackend("warn", args.map(safeStringify).join(" "));
    };
    console.log = (...args: unknown[]) => {
      originalConsoleLog.apply(console, args as any[]);
      logToBackend("info", args.map(safeStringify).join(" "));
    };

    window.addEventListener("error", handleError);
    window.addEventListener("unhandledrejection", handleRejection);

    logToBackend("info", "--- REMOTE WEBVIEW LOGGING BRIDGE INITIALIZED ---");
    logToBackend("info", `WebView User Agent: ${navigator.userAgent}`);

    return () => {
      window.removeEventListener("error", handleError);
      window.removeEventListener("unhandledrejection", handleRejection);
      console.error = originalConsoleError;
      console.warn = originalConsoleWarn;
      console.log = originalConsoleLog;
    };
  }, []);
}
