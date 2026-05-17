"use client";

import React from "react";

export default function ErrorBanner({ message, type = "error" }: { message: string | null; type?: "error" | "success" }) {
  if (!message) return null;
  return (
    <div className={`p-3 rounded-xl text-sm font-semibold flex items-center space-x-3 animate-fade-in ${
      type === "success" ? "bg-green-500/10 text-green-300 border border-green-500/20" : "bg-red-500/10 text-red-300 border border-red-500/20"
    }`}>
      <span className="flex-1">{message}</span>
      <button onClick={() => { /* no-op, parent controls visibility */ }} className="opacity-60 hover:opacity-100">✕</button>
    </div>
  );
}
