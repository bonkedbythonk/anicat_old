"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { mediaApi } from "@/lib/api";
import { ChevronDown, ChevronUp, Terminal } from "lucide-react";

/**
 * Live-updating update log viewer for the update overlay.
 * Polls /api/status/update/logs every 2s while the update is in progress.
 * Auto-scrolls to the bottom on new content.
 */
export default function UpdateLogViewer() {
  const [showLogs, setShowLogs] = useState(false);
  const [logs, setLogs] = useState("");
  const [updating, setUpdating] = useState(true);
  const [pollFailed, setPollFailed] = useState(false);
  const logEndRef = useRef<HTMLDivElement>(null);

  // Poll update logs
  useEffect(() => {
    if (!showLogs) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const res = await mediaApi.getUpdateLogs(200);
        if (cancelled) return;
        setLogs(res.logs);
        setUpdating(res.updating);
        setPollFailed(false);
      } catch {
        if (!cancelled) setPollFailed(true);
      }
    };

    poll();
    const interval = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [showLogs]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (showLogs && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, showLogs]);

  const displayMessage = useCallback(() => {
    if (logs) return logs;
    if (pollFailed) return "Update in progress - the application will restart automatically.\n";
    return "Waiting for update to start...";
  }, [logs, pollFailed]);

  return (
    <div className="w-full max-w-lg mx-auto">
      <button
        onClick={() => setShowLogs(!showLogs)}
        className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] text-xs font-bold text-gray-400 hover:text-white transition-all"
      >
        <Terminal size={12} />
        <span>{showLogs ? "Hide Update Logs" : "Show Update Logs"}</span>
        {showLogs ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      {showLogs && (
        <div className="mt-3 p-3 rounded-xl bg-black/60 border border-white/[0.06] max-h-48 overflow-y-auto text-left font-mono text-[10px] leading-relaxed whitespace-pre-wrap break-all text-gray-400 scrollbar-hide">
          {displayMessage()}
          <div ref={logEndRef} />
        </div>
      )}
    </div>
  );
}
