"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import type { MediaItem } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AppState {
  /** Current media selected for detail drawer. */
  selectedItem: MediaItem | null;
  /** Whether to auto-trigger "play" when opening detail. */
  initialAction: "play" | null;
  /** Media currently open in the anime player overlay. */
  playingItem: MediaItem | null;
  /** Episode number currently playing. */
  playingEpisode: string | null;
  /** Media currently open in the manga reader overlay. */
  readingItem: MediaItem | null;
  /** Chapter number currently being read. */
  readingChapter: string | null;
}

export interface AppStateActions {
  selectItem: (item: MediaItem, action?: "play") => void;
  closeDetail: () => void;
  startPlayback: (item: MediaItem, episode: string) => void;
  closePlayback: () => void;
  startReading: (item: MediaItem, chapter: string) => void;
  closeReader: () => void;
  setEpisode: (episode: string) => void;
}

const AppStateContext = createContext<
  (AppState & AppStateActions) | null
>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null);
  const [initialAction, setInitialAction] = useState<"play" | null>(null);
  const [playingItem, setPlayingItem] = useState<MediaItem | null>(null);
  const [playingEpisode, setPlayingEpisode] = useState<string | null>(null);
  const [readingItem, setReadingItem] = useState<MediaItem | null>(null);
  const [readingChapter, setReadingChapter] = useState<string | null>(null);

  const selectItem = useCallback((item: MediaItem, action?: "play") => {
    setSelectedItem(item);
    setInitialAction(action || null);
  }, []);

  const closeDetail = useCallback(() => {
    setSelectedItem(null);
    setInitialAction(null);
  }, []);

  const startPlayback = useCallback((item: MediaItem, episode: string) => {
    setPlayingItem(item);
    setPlayingEpisode(episode);
  }, []);

  const closePlayback = useCallback(() => {
    setPlayingItem(null);
    setPlayingEpisode(null);
  }, []);

  const startReading = useCallback((item: MediaItem, chapter: string) => {
    setReadingItem(item);
    setReadingChapter(chapter);
  }, []);

  const closeReader = useCallback(() => {
    setReadingItem(null);
    setReadingChapter(null);
  }, []);

  const setEpisode = useCallback((episode: string) => {
    setPlayingEpisode(episode);
  }, []);

  const value: AppState & AppStateActions = {
    selectedItem,
    initialAction,
    playingItem,
    playingEpisode,
    readingItem,
    readingChapter,
    selectItem,
    closeDetail,
    startPlayback,
    closePlayback,
    startReading,
    closeReader,
    setEpisode,
  };

  return (
    <AppStateContext.Provider value={value}>
      {children}
    </AppStateContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Consumer hook
// ---------------------------------------------------------------------------

export function useAppState(): AppState & AppStateActions {
  const ctx = useContext(AppStateContext);
  if (!ctx) {
    throw new Error("useAppState must be used within an <AppStateProvider>");
  }
  return ctx;
}
