"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { mediaApi, type HealthStatus } from "@/lib/api";
import { getQueryClient } from "@/components/Providers";

export interface HealthPollingState {
  /** Current backend connection status. */
  connectionStatus: "checking" | "connected" | "failed";
  /** Human-readable error when connectionStatus === "failed". */
  connectionError: string | null;
  /** Latest full health payload from the backend. */
  healthStatus: HealthStatus | null;
  /** Whether the AniList API is reachable (offline = local-library mode). */
  isOffline: boolean;
  /** Whether the user has dismissed the offline banner for this session. */
  dismissedOffline: boolean;
  /** Unread AniList notification count. */
  notificationCount: number;
  /** Dismiss the offline banner (sticky for current session). */
  dismissOffline: () => void;
}

/**
 * Polls the AniCat backend health endpoint and derives connection
 * status, live-sync detection, offline mode, and notification count.
 *
 * - During initial boot: fast polling (1 s) with progressive
 *   back-off after 8 failed attempts.
 * - Once connected: slow polling (10 s).
 * - Detects `data_version` bumps and dispatches a global refresh
 *   so all views re-fetch their data.
 */
export function useHealthPolling(): HealthPollingState {
  const [connectionStatus, setConnectionStatus] = useState<
    "checking" | "connected" | "failed"
  >("checking");
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [isOffline, setIsOffline] = useState(false);
  const [dismissedOffline, setDismissedOffline] = useState(() => {
    if (typeof window !== "undefined") {
      return sessionStorage.getItem("anicat_offline_dismissed") === "true";
    }
    return false;
  });
  const [notificationCount, setNotificationCount] = useState(0);

  const lastDataVersion = useRef<number | null>(null);

  const dismissOffline = useCallback(() => {
    setDismissedOffline(true);
    sessionStorage.setItem("anicat_offline_dismissed", "true");
  }, []);

  useEffect(() => {
    let failedAttempts = 0;
    let isInitial = true;
    let checkInterval: ReturnType<typeof setInterval>;

    async function checkSystem() {
      try {
        const status = await mediaApi.getHealthStatus();
        setHealthStatus(status);
        setConnectionStatus("connected");
        setConnectionError(null);
        failedAttempts = 0;

        // Live Sync Detection
        if (status.data_version !== undefined) {
          if (
            lastDataVersion.current !== null &&
            status.data_version > lastDataVersion.current
          ) {
            console.log(
              `Live Sync: Data changed (version ${lastDataVersion.current} -> ${status.data_version}). Refreshing views...`
            );
            getQueryClient()?.invalidateQueries();
          }
          lastDataVersion.current = status.data_version;
        }

        // Offline Detection
        const shouldBeOffline =
          status.api_authenticated &&
          (status.is_offline || !status.api_connected);
        setIsOffline(shouldBeOffline);

        if (!shouldBeOffline) setDismissedOffline(false);
        setNotificationCount(status.unread_notifications || 0);

        // Transition to normal 10s polling
        if (isInitial) {
          isInitial = false;
          clearInterval(checkInterval);
          checkInterval = setInterval(checkSystem, 10000);
        }
      } catch (err: unknown) {
        failedAttempts++;
        const message =
          err instanceof Error ? err.message : String(err);
        console.error(`Health check failed (attempt ${failedAttempts}):`, err);

        if (isInitial) {
          setConnectionStatus("checking");

          if (failedAttempts >= 8) {
            isInitial = false;
            clearInterval(checkInterval);
            setConnectionStatus("failed");
            setConnectionError(
              message ||
                "Connection refused (backend sidecar unreachable on port 13370)."
            );
            checkInterval = setInterval(checkSystem, 10000);
          }
        } else {
          if (failedAttempts >= 6) {
            setConnectionStatus("failed");
            setConnectionError(
              message ||
                "Connection refused (backend sidecar unreachable on port 13370)."
            );
          }
        }
      }
    }

    // Start initial fast polling (every 1s)
    checkSystem();
    checkInterval = setInterval(checkSystem, 1000);

    return () => {
      clearInterval(checkInterval);
    };
    // Run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    connectionStatus,
    connectionError,
    healthStatus,
    isOffline,
    dismissedOffline,
    notificationCount,
    dismissOffline,
  };
}
