"use client";

import { useState, useCallback } from "react";
import { mediaApi } from "@/lib/api";
import { dispatchRefresh } from "@/lib/events";

export interface UseProgressEditorReturn {
  isEditing: boolean;
  editValue: string;
  setEditValue: (value: string) => void;
  startEditing: (currentProgress: number) => void;
  cancelEditing: () => void;
  commitProgress: (mediaId: number, newProgress: number) => void;
}

/**
 * Manages the inline progress-editing UI state for media items.
 *
 * Usage:
 *   const progress = useProgressEditor();
 *   // In your JSX:
 *   {progress.isEditing ? (
 *     <input value={progress.editValue} ... />
 *   ) : (
 *     <span onClick={() => progress.startEditing(item.progress)}>Edit</span>
 *   )}
 */
export function useProgressEditor(): UseProgressEditorReturn {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState("");

  const startEditing = useCallback((currentProgress: number) => {
    setEditValue(String(currentProgress));
    setIsEditing(true);
  }, []);

  const cancelEditing = useCallback(() => {
    setIsEditing(false);
    setEditValue("");
  }, []);

  const commitProgress = useCallback(
    (mediaId: number, newProgress: number) => {
      // Close the editing UI immediately — don't block on the network call
      setIsEditing(false);
      mediaApi.updateStatus(mediaId, undefined, undefined, newProgress)
        .then(() => dispatchRefresh())
        .catch((err) => console.error("Failed to update progress:", err));
    },
    []
  );

  return {
    isEditing,
    editValue,
    setEditValue: setEditValue,
    startEditing,
    cancelEditing,
    commitProgress,
  };
}
