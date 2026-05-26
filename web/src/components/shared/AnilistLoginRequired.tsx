"use client";

import { useState } from "react";
import { ShieldCheck, Globe, Loader2, RotateCcw, ChevronRight } from "lucide-react";
import { mediaApi } from "@/lib/api";
import type { ViewName } from "@/components/layout/Sidebar";

interface AnilistLoginRequiredProps {
  viewName: ViewName;
}

export default function AnilistLoginRequired({ viewName }: AnilistLoginRequiredProps) {
  const [token, setToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const viewLabels: Record<string, string> = {
    home: "your Home feed",
    manga: "the Manga browser",
    lists: "your Lists",
    notifications: "Notifications",
    profile: "your Profile",
  };

  const handleConnectAnilist = async () => {
    if (!token.trim()) {
      setError("Please enter your AniList token.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await mediaApi.updateConfig({
        anilist: { token: token.trim() }
      });
      const res = await mediaApi.reconnect();
      
      if (res.status === "success") {
        window.location.reload();
      } else {
        setError(res.message || "Connection failed. Please check your token.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to save token.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 animate-fade-in text-center max-w-xl mx-auto">
      <div className="relative mb-6">
        <div className="absolute -inset-4 bg-accent/20 rounded-full blur-xl animate-pulse" />
        <div className="relative p-6 bg-white/[0.02] border border-white/[0.08] rounded-full shadow-2xl">
          <ShieldCheck size={48} className="text-accent" />
        </div>
      </div>

      <h2 className="text-2xl font-black tracking-tight text-white mb-3">
        AniList Connection Required
      </h2>
      
      <p className="text-gray-400 text-sm leading-relaxed mb-8">
        Accessing {viewLabels[viewName] || "this section"} requires a connected AniList account.
        Syncing your account lets you track progress, manage lists, and receive updates.
      </p>

      <div className="w-full bg-white/[0.01] border border-white/[0.06] rounded-3xl p-6 space-y-6 text-left">
        <div className="relative group">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-accent transition-colors">
            <ShieldCheck size={20} />
          </div>
          <input 
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Paste your Secure Token here..."
            className="w-full bg-white/[0.03] border border-white/[0.08] rounded-2xl py-4 pl-12 pr-6 text-sm font-medium focus:outline-none focus:border-accent/40 focus:bg-white/[0.05] transition-all text-white"
          />
        </div>
        
        {error && (
          <p className="text-red-400 text-xs font-semibold animate-shake">{error}</p>
        )}

        <button 
          onClick={() => mediaApi.openUrl("https://anilist.co/api/v2/oauth/authorize?client_id=20148&response_type=token")}
          className="w-full flex items-center justify-between p-4 rounded-2xl bg-accent/10 border border-accent/20 hover:bg-accent/20 transition-all group"
        >
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-accent text-white shadow-lg shadow-accent/20">
              <Globe size={18} />
            </div>
            <div className="text-left">
              <p className="text-sm font-bold text-white">1. Get your Secure Token</p>
              <p className="text-[11px] text-accent font-medium">Authorize with AniList and copy the code from the page</p>
            </div>
          </div>
          <ChevronRight size={18} className="text-accent group-hover:translate-x-1 transition-all" />
        </button>

        <div className="flex gap-3">
          <button 
            onClick={handleConnectAnilist}
            disabled={saving}
            className="w-full bg-accent hover:bg-accent-light text-white font-bold py-4 rounded-2xl flex items-center justify-center space-x-2 transition-all shadow-xl shadow-accent/20 active:scale-95 disabled:opacity-50"
          >
            {saving ? <Loader2 size={20} className="animate-spin" /> : (
              <span>Connect Account</span>
            )}
          </button>
        </div>

        <div className="flex flex-col items-center space-y-2 pt-1">
          <div className="flex items-center justify-center space-x-2 text-[11px] text-gray-500">
            <span>Don't have an AniList account?</span>
            <button 
              onClick={() => mediaApi.openUrl("https://anilist.co/signup")}
              className="text-accent hover:underline font-bold"
            >
              Sign up here
            </button>
          </div>
          <button 
            onClick={async () => {
               setSaving(true);
               try {
                 const health = await mediaApi.getHealthStatus();
                 if (health.api_authenticated) {
                   window.location.reload();
                 } else {
                   setError("Still no token detected. Open AniList authorization and paste the token above.");
                 }
               } finally {
                 setSaving(false);
               }
            }}
            className="text-[10px] text-gray-600 hover:text-accent transition-colors flex items-center space-x-1"
          >
            <RotateCcw size={10} />
            <span>Refresh Status</span>
          </button>
        </div>
      </div>
    </div>
  );
}
