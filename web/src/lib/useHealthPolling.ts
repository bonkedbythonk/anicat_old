"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { mediaApi, type HealthStatus } from "@/lib/api";
import { getQueryClient } from "@/components/Providers";

// Frontend version from package.json — used to detect stale backend
const FRONTEND_VERSION = "4.32.0";
let _versionMismatchWarned = false;

async function showNativeNotification(title: string, body: string) {
  try {
    const { isPermissionGranted, requestPermission, sendNotification } = await import("@tauri-apps/plugin-notification");
    let permissionGranted = await isPermissionGranted();
    if (!permissionGranted) {
      const permission = await requestPermission();
      permissionGranted = permission === "granted";
    }
    if (permissionGranted) {
      sendNotification({ title, body });
    }
  } catch (err) {
    console.warn("Tauri native notification failed, falling back to Web Notification API:", err);
    if ("Notification" in window) {
      if (Notification.permission === "granted") {
        new Notification(title, { body });
      } else if (Notification.permission !== "denied") {
        Notification.requestPermission().then(permission => {
          if (permission === "granted") {
            new Notification(title, { body });
          }
        });
      }
    }
  }
}

async function requestNotificationPermission() {
  try {
    const { isPermissionGranted, requestPermission } = await import("@tauri-apps/plugin-notification");
    const permissionGranted = await isPermissionGranted();
    if (!permissionGranted) {
      await requestPermission();
    }
  } catch (err) {
    console.warn("Tauri notification permission check failed, trying Web Notification permission:", err);
    if ("Notification" in window && Notification.permission !== "granted" && Notification.permission !== "denied") {
      await Notification.requestPermission();
    }
  }
}

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
  const lastNotificationCount = useRef<number>(0);
  const lastSeenNotificationId = useRef<number | null>(null);
  // Debounce invalidateQueries so rapid version bumps only trigger one refetch wave
  const invalidateDebounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function debouncedInvalidate() {
    if (invalidateDebounceTimer.current) clearTimeout(invalidateDebounceTimer.current);
    invalidateDebounceTimer.current = setTimeout(() => {
      getQueryClient()?.invalidateQueries();
    }, 500);
  }

  const dismissOffline = useCallback(() => {
    setDismissedOffline(true);
    sessionStorage.setItem("anicat_offline_dismissed", "true");
  }, []);

  useEffect(() => {
    // Request desktop notification permission on mount
    requestNotificationPermission();

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

        // Version Mismatch Detection — warn if backend is older than frontend
        if (
          status.current_version &&
          status.current_version !== "unknown" &&
          status.current_version !== FRONTEND_VERSION &&
          !_versionMismatchWarned
        ) {
          _versionMismatchWarned = true;
          console.warn(
            `Version mismatch: frontend ${FRONTEND_VERSION}, backend ${status.current_version}. ` +
            "The backend may need to be rebuilt or restarted."
          );
        }

        // Live Sync Detection
        if (status.data_version !== undefined) {
          if (
            lastDataVersion.current !== null &&
            status.data_version > lastDataVersion.current
          ) {
            console.log(
              `Live Sync: Data changed (version ${lastDataVersion.current} -> ${status.data_version}). Refreshing views...`
            );
            debouncedInvalidate();
          }
          lastDataVersion.current = status.data_version;
        }

        // Offline Detection
        const shouldBeOffline =
          status.api_authenticated &&
          (status.is_offline || !status.api_connected);
        setIsOffline(shouldBeOffline);

        if (!shouldBeOffline) setDismissedOffline(false);
        const newUnreadCount = status.unread_notifications || 0;
        setNotificationCount(newUnreadCount);

        // Fetch notifications and trigger desktop alerts if new ones arrived
        if (status.api_authenticated && !shouldBeOffline) {
          try {
            if (lastSeenNotificationId.current === null) {
              const notifs = await mediaApi.getNotifications();
              const notificationsList = notifs || [];
              const maxId = notificationsList.reduce((max, n) => Math.max(max, n.id), 0);
              lastSeenNotificationId.current = maxId;
              lastNotificationCount.current = newUnreadCount;
            } else if (newUnreadCount > lastNotificationCount.current) {
              const notifs = await mediaApi.getNotifications();
              const notificationsList = notifs || [];
              const newNotifications = notificationsList.filter(n => n.id > lastSeenNotificationId.current!);
              
              for (const notif of newNotifications) {
                const title = "AniCat Release Alert";
                const body = `${notif.contexts?.[0] ?? ""}${notif.episode || ""}${notif.contexts?.[1] ?? ""}${notif.media?.title?.english || notif.media?.title?.romaji || ""}${notif.contexts?.[2] ?? ""}`;
                await showNativeNotification(title, body);
              }
              
              if (notificationsList.length > 0) {
                const maxId = notificationsList.reduce((max, n) => Math.max(max, n.id), 0);
                lastSeenNotificationId.current = Math.max(lastSeenNotificationId.current, maxId);
              }
              lastNotificationCount.current = newUnreadCount;
            } else {
              lastNotificationCount.current = newUnreadCount;
            }
          } catch (err) {
            console.error("Failed to check notifications for desktop alerts:", err);
          }
        }

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

    // Start initial polling (every 3s — backend boot takes ~2s, no need to hammer at 1s)
    checkSystem();
    checkInterval = setInterval(checkSystem, 3000);

    return () => {
      clearInterval(checkInterval);
      if (invalidateDebounceTimer.current) clearTimeout(invalidateDebounceTimer.current);
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
