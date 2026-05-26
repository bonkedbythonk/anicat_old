"use client";

import { useState, useEffect } from "react";
import { 
  Sparkles, 
  ArrowRight, 
  Monitor, 
  BookOpen, 
  Download, 
  ShieldCheck, 
  Globe, 
  Loader2, 
  X, 
  ChevronRight,
  User,
  Layout,
  PlayCircle,
  RotateCcw,
  Calendar,
  Bell,
  Sun,
  Moon,
  Palette,
  Leaf
} from "lucide-react";
import { mediaApi } from "@/lib/api";
import type { UiStyle } from "@/lib/useTheme";

interface OnboardingProps {
  onComplete: () => void;
  onSkip: () => void;
}

export default function Onboarding({ onComplete, onSkip }: OnboardingProps) {
  const [step, setStep] = useState(1);
  const [token, setToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Theme/style state
  const [selectedTheme, setSelectedTheme] = useState<"system" | "dark" | "light">("system");
  const [selectedStyle, setSelectedStyle] = useState<UiStyle>("neon-abyss");

  // Playback customization states
  const [config, setConfig] = useState<any>(null);
  const [playerType, setPlayerType] = useState("embedded");
  const [shaderProfile, setShaderProfile] = useState("balanced");
  const [translationType, setTranslationType] = useState("sub");
  const [localAutoSkip, setLocalAutoSkip] = useState(false);
  // UX-27: Auto-detect MPV availability
  const [mpvAvailable, setMpvAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    mediaApi.getConfig()
      .then((cfg) => {
        setConfig(cfg);
        if (cfg?.stream) {
          setPlayerType(cfg.stream.player_type || "embedded");
          setShaderProfile(cfg.stream.shader_profile || "balanced");
          setTranslationType(cfg.stream.translation_type || "sub");
        }
      })
      .catch(console.error);

    // UX-27: Check MPV availability
    mediaApi.getMpvAvailable()
      .then(res => setMpvAvailable(res.available))
      .catch(() => setMpvAvailable(false));

    if (typeof window !== "undefined") {
      const savedAutoSkip = localStorage.getItem("anicat_auto_skip");
      setLocalAutoSkip(savedAutoSkip === "true");
    }
  }, []);

  const handleApplyTheme = () => {
    if (typeof window === "undefined") return;
    localStorage.setItem("anicat_theme", selectedTheme);
    localStorage.setItem("anicat_ui_style", selectedStyle);

    // Apply theme class
    document.documentElement.classList.remove("light", "dark", "system");
    document.documentElement.classList.add(selectedTheme);
    if (selectedTheme === "light" || (selectedTheme === "system" && window.matchMedia("(prefers-color-scheme: light)").matches)) {
      document.documentElement.classList.add("light");
    } else {
      document.documentElement.classList.add("dark");
    }

    // Apply style
    document.documentElement.setAttribute("data-style", selectedStyle);
    // Load fonts if needed
    if (selectedStyle === "sakura-zen") {
      if (!document.getElementById("font-noto-serif-jp")) {
        const link = document.createElement("link");
        link.id = "font-noto-serif-jp";
        link.rel = "stylesheet";
        link.href = "https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;600;700&display=swap";
        document.head.appendChild(link);
      }
    } else if (selectedStyle === "retro-manga") {
      if (!document.getElementById("font-retro-manga")) {
        const link = document.createElement("link");
        link.id = "font-retro-manga";
        link.rel = "stylesheet";
        link.href = "https://fonts.googleapis.com/css2?family=Bangers&family=Noto+Sans+JP:wght@400;700&display=swap";
        document.head.appendChild(link);
      }
    }

    setStep(3);
  };

  const handleSavePlaybackSettings = async () => {
    setSaving(true);
    setError(null);
    try {
      await mediaApi.updateConfig({
        stream: {
          player_type: playerType,
          shader_profile: shaderProfile,
          translation_type: translationType,
        }
      });
      localStorage.setItem("anicat_auto_skip", String(localAutoSkip));
      setStep(4); // Advance to AniList connection step
    } catch (err: any) {
      setError("Failed to save playback preferences.");
    } finally {
      setSaving(false);
    }
  };

  const handleConnectAnilist = async () => {
    if (!token.trim()) {
      setError("Please enter your AniList token.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      // Direct update for just the token
      await mediaApi.updateConfig({
        anilist: { token: token.trim() }
      });
      
      // The backend should automatically reconnect on token update now
      // but we force it just in case
      const res = await mediaApi.reconnect();
      
      if (res.status === "success") {
        onComplete();
        // Force a full reload to clear all caches
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

  const steps = [
    {
      id: 1,
      title: "Welcome to Anicat",
      subtitle: "Your Anime & Manga Hub",
      content: (
        <div className="space-y-8 animate-fade-in">
          {/* Logo */}
          <div className="flex justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/anicat_logo.png"
              alt="Anicat"
              className="w-32 h-auto anicat-logo"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <FeatureCard 
              icon={<Monitor className="text-accent" />} 
              title="Stream & Sync" 
              desc="Watch anime, track progress across devices."
            />
            <FeatureCard 
              icon={<BookOpen className="text-secondary" />} 
              title="Manga Reader" 
              desc="Read manga with a clean, distraction-free viewer."
            />
            <FeatureCard 
              icon={<Calendar className="text-purple-400" />} 
              title="Schedule" 
              desc="See what's airing today and never miss an episode."
            />
            <FeatureCard 
              icon={<Bell className="text-amber-400" />} 
              title="Notifications" 
              desc="Get desktop alerts when new episodes drop."
            />
            <FeatureCard 
              icon={<Download className="text-green-400" />} 
              title="Downloads" 
              desc="Save episodes for offline watching."
            />
            <FeatureCard 
              icon={<Layout className="text-rose-400" />} 
              title="Clean Design" 
              desc="Dark-themed, glassmorphic, built for clarity."
            />
          </div>
          <button 
            onClick={() => setStep(2)}
            className="w-full bg-accent hover:bg-accent-light text-white font-bold py-4 rounded-2xl flex items-center justify-center space-x-2 transition-all shadow-xl shadow-accent/20 active:scale-95"
          >
            <span>Get Started</span>
            <ArrowRight size={20} />
          </button>
        </div>
      )
    },
    {
      id: 2,
      title: "Choose Your Look",
      subtitle: "Pick a theme and style that suits you",
      content: (
        <div className="space-y-6 animate-fade-in">
          {/* Theme selection */}
          <div className="space-y-3">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider text-left block">Theme</label>
            <div className="grid grid-cols-3 gap-3">
              <button
                onClick={() => setSelectedTheme("system")}
                className={`flex flex-col items-center gap-2 p-4 rounded-2xl border-2 transition-all ${
                  selectedTheme === "system"
                    ? "border-accent bg-accent/10 shadow-lg shadow-accent/10"
                    : "border-white/[0.06] hover:border-white/[0.15] bg-white/[0.02]"
                }`}
              >
                <Monitor size={24} className={selectedTheme === "system" ? "text-accent" : "text-gray-400"} />
                <span className={`text-xs font-bold ${selectedTheme === "system" ? "text-accent" : "text-gray-400"}`}>System</span>
              </button>
              <button
                onClick={() => setSelectedTheme("dark")}
                className={`flex flex-col items-center gap-2 p-4 rounded-2xl border-2 transition-all ${
                  selectedTheme === "dark"
                    ? "border-accent bg-accent/10 shadow-lg shadow-accent/10"
                    : "border-white/[0.06] hover:border-white/[0.15] bg-white/[0.02]"
                }`}
              >
                <Moon size={24} className={selectedTheme === "dark" ? "text-accent" : "text-gray-400"} />
                <span className={`text-xs font-bold ${selectedTheme === "dark" ? "text-accent" : "text-gray-400"}`}>Dark</span>
              </button>
              <button
                onClick={() => setSelectedTheme("light")}
                className={`flex flex-col items-center gap-2 p-4 rounded-2xl border-2 transition-all ${
                  selectedTheme === "light"
                    ? "border-accent bg-accent/10 shadow-lg shadow-accent/10"
                    : "border-white/[0.06] hover:border-white/[0.15] bg-white/[0.02]"
                }`}
              >
                <Sun size={24} className={selectedTheme === "light" ? "text-accent" : "text-gray-400"} />
                <span className={`text-xs font-bold ${selectedTheme === "light" ? "text-accent" : "text-gray-400"}`}>Light</span>
              </button>
            </div>
          </div>

          {/* Style selection */}
          <div className="space-y-3">
            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider text-left block">Style</label>
            <div className="grid grid-cols-1 gap-2">
              {/* Neon Abyss */}
              <button
                onClick={() => setSelectedStyle("neon-abyss")}
                className={`flex items-center gap-4 p-4 rounded-2xl border-2 transition-all text-left ${
                  selectedStyle === "neon-abyss"
                    ? "border-[#0A84FF] bg-[#0A84FF]/10 shadow-lg shadow-[#0A84FF]/10"
                    : "border-white/[0.06] hover:border-white/[0.15] bg-white/[0.02]"
                }`}
              >
                <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: "linear-gradient(135deg, #050505, #0d0d1a)" }}>
                  <Sparkles size={18} className="text-[#0A84FF]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-white">Neon Abyss</div>
                  <div className="text-[11px] text-gray-500">Deep black / Apple glass — the classic Anicat look</div>
                </div>
                {selectedStyle === "neon-abyss" && (
                  <div className="w-5 h-5 rounded-full bg-[#0A84FF] flex items-center justify-center shrink-0">
                    <svg width="10" height="10" viewBox="0 0 8 8" fill="none"><path d="M1 4l2 2 4-4" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  </div>
                )}
              </button>

              {/* Sakura Zen */}
              <button
                onClick={() => setSelectedStyle("sakura-zen")}
                className={`flex items-center gap-4 p-4 rounded-2xl border-2 transition-all text-left ${
                  selectedStyle === "sakura-zen"
                    ? "border-[#e8a0b4] bg-[#e8a0b4]/10 shadow-lg shadow-[#e8a0b4]/10"
                    : "border-white/[0.06] hover:border-white/[0.15] bg-white/[0.02]"
                }`}
              >
                <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: "linear-gradient(135deg, #130910, #1f1222)" }}>
                  <Palette size={18} className="text-[#e8a0b4]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-white">Sakura Zen</div>
                  <div className="text-[11px] text-gray-500">Soft pastel / Japanese editorial — calm and elegant</div>
                </div>
                {selectedStyle === "sakura-zen" && (
                  <div className="w-5 h-5 rounded-full flex items-center justify-center shrink-0" style={{ background: "#e8a0b4" }}>
                    <svg width="10" height="10" viewBox="0 0 8 8" fill="none"><path d="M1 4l2 2 4-4" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  </div>
                )}
              </button>

              {/* Retro Manga */}
              <button
                onClick={() => setSelectedStyle("retro-manga")}
                className={`flex items-center gap-4 p-4 rounded-2xl border-2 transition-all text-left ${
                  selectedStyle === "retro-manga"
                    ? "border-[#e8272c] bg-[#e8272c]/10 shadow-lg shadow-[#e8272c]/10"
                    : "border-white/[0.06] hover:border-white/[0.15] bg-white/[0.02]"
                }`}
              >
                <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: "linear-gradient(135deg, #191410, #2a221c)" }}>
                  <BookOpen size={18} className="text-[#e8272c]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-white">Retro Manga</div>
                  <div className="text-[11px] text-gray-500">Aged paper / halftone dots — vintage comic aesthetic</div>
                </div>
                {selectedStyle === "retro-manga" && (
                  <div className="w-5 h-5 rounded-full bg-[#e8272c] flex items-center justify-center shrink-0">
                    <svg width="10" height="10" viewBox="0 0 8 8" fill="none"><path d="M1 4l2 2 4-4" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  </div>
                )}
              </button>

              {/* Forest Moss */}
              <button
                onClick={() => setSelectedStyle("forest-moss")}
                className={`flex items-center gap-4 p-4 rounded-2xl border-2 transition-all text-left ${
                  selectedStyle === "forest-moss"
                    ? "border-[#10b981] bg-[#10b981]/10 shadow-lg shadow-[#10b981]/10"
                    : "border-white/[0.06] hover:border-white/[0.15] bg-white/[0.02]"
                }`}
              >
                <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style={{ background: "linear-gradient(135deg, #050f0b, #0a1a12)" }}>
                  <Leaf size={18} className="text-[#10b981]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-white">Forest Moss</div>
                  <div className="text-[11px] text-gray-500">Organic green / Fresh woodland — immersive and clean</div>
                </div>
                {selectedStyle === "forest-moss" && (
                  <div className="w-5 h-5 rounded-full flex items-center justify-center shrink-0" style={{ background: "#10b981" }}>
                    <svg width="10" height="10" viewBox="0 0 8 8" fill="none"><path d="M1 4l2 2 4-4" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  </div>
                )}
              </button>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setStep(1)}
              className="flex-1 bg-white/[0.04] hover:bg-white/[0.08] text-white font-bold py-4 rounded-2xl transition-all active:scale-95 border border-white/[0.08]"
            >
              Back
            </button>
            <button
              onClick={handleApplyTheme}
              className="flex-[2] bg-accent hover:bg-accent-light text-white font-bold py-4 rounded-2xl flex items-center justify-center space-x-2 transition-all shadow-xl shadow-accent/20 active:scale-95"
            >
              <span>Continue</span>
              <ArrowRight size={20} />
            </button>
          </div>
        </div>
      )
    },
    {
      id: 3,
      title: "Set Up Playback",
      subtitle: "Choose how you want to watch",
      content: (
        <div className="space-y-5 text-left animate-fade-in">
          <div className="space-y-4 bg-white/[0.01] border border-white/[0.04] p-5 rounded-xl">
            {/* Player Type Selection */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Video Player</label>
              <select
                value={playerType}
                onChange={(e) => setPlayerType(e.target.value)}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer text-white"
              >
                <option value="embedded" className="bg-surface">Built-in Player (simple, no setup)</option>
                <option value="external" className="bg-surface" disabled={mpvAvailable === false}>
                  External Player - MPV (best quality, GPU upscaling){mpvAvailable === false ? ' [Not Installed]' : ''}
                </option>
              </select>
              {mpvAvailable === false && (
                <p className="text-[10px] text-amber-400/80 font-medium mt-1">
                  MPV is not detected on your system. Install it for the best viewing experience.
                </p>
              )}
            </div>

            {/* Shaders Quality */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Visual Quality (MPV)</label>
              <select
                value={shaderProfile}
                onChange={(e) => setShaderProfile(e.target.value)}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer text-white"
              >
                <option value="off" className="bg-surface">Standard</option>
                <option value="balanced" className="bg-surface">High Quality (GPU enhanced)</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Auto Skip Selection */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Skip Intros</label>
                <select
                  value={localAutoSkip ? "true" : "false"}
                  onChange={(e) => setLocalAutoSkip(e.target.value === "true")}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer text-white"
                >
                  <option value="false" className="bg-surface">Manual</option>
                  <option value="true" className="bg-surface">Auto-skip OP/ED</option>
                </select>
              </div>

              {/* Translation Selection */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Audio Language</label>
                <select
                  value={translationType}
                  onChange={(e) => setTranslationType(e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer text-white"
                >
                  <option value="sub" className="bg-surface">Subbed (Japanese)</option>
                  <option value="dub" className="bg-surface">Dubbed (English)</option>
                </select>
              </div>
            </div>
          </div>

          {error && (
            <p className="text-red-400 text-xs font-semibold animate-shake">{error}</p>
          )}

          <div className="flex gap-3 pt-2">
            <button 
              onClick={() => setStep(2)}
              disabled={saving}
              className="flex-1 bg-white/[0.04] hover:bg-white/[0.08] text-white font-bold py-4 rounded-2xl transition-all active:scale-95 border border-white/[0.08] disabled:opacity-50"
            >
              Back
            </button>
            <button 
              onClick={handleSavePlaybackSettings}
              disabled={saving}
              className="flex-[2] bg-accent hover:bg-accent-light text-white font-bold py-4 rounded-2xl flex items-center justify-center space-x-2 transition-all shadow-xl shadow-accent/20 active:scale-95 disabled:opacity-50"
            >
              {saving ? <Loader2 size={20} className="animate-spin" /> : (
                <>
                  <span>Save & Continue</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </div>
        </div>
      )
    },
    {
      id: 4,
      title: "Connect AniList",
      subtitle: "Sync your watch history and lists",
      content: (
        <div className="space-y-6 animate-fade-in">
          <p className="text-gray-400 text-sm leading-relaxed">
            Anicat works best with <span className="text-white font-semibold">AniList</span>. 
            It keeps your watch history, ratings, and lists synced across all your devices. Your data stays private — the token only reads and updates your lists.
          </p>

          <div className="space-y-4">
            <div className="relative group">
              <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-accent transition-colors">
                <ShieldCheck size={20} />
              </div>
              <input 
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Paste your Secure Token here..."
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-2xl py-4 pl-12 pr-6 text-sm font-medium focus:outline-none focus:border-accent/40 focus:bg-white/[0.05] transition-all"
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
                  <p className="text-[11px] text-accent font-medium">Click Authorize, then copy the long token from the box on the page</p>
                </div>
              </div>
              <ChevronRight size={18} className="text-accent group-hover:translate-x-1 transition-all" />
            </button>

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
                       onComplete();
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

          <div className="flex flex-col space-y-3 pt-2">
            <div className="flex gap-3">
              <button 
                onClick={() => setStep(3)}
                disabled={saving}
                className="flex-1 bg-white/[0.04] hover:bg-white/[0.08] text-white font-bold py-4 rounded-2xl transition-all active:scale-95 border border-white/[0.08] disabled:opacity-50"
              >
                Back
              </button>
              <button 
                onClick={handleConnectAnilist}
                disabled={saving}
                className="flex-[2] bg-accent hover:bg-accent-light text-white font-bold py-4 rounded-2xl flex items-center justify-center space-x-2 transition-all shadow-xl shadow-accent/20 active:scale-95 disabled:opacity-50"
              >
                {saving ? <Loader2 size={20} className="animate-spin" /> : (
                  <span>Connect Account</span>
                )}
              </button>
            </div>
            <button 
              onClick={onSkip}
              className="w-full py-3 text-gray-500 hover:text-white font-semibold text-sm transition-colors"
            >
              I'll do this later (Browse Offline)
            </button>
          </div>
        </div>
      )
    }
  ];

  const currentStep = steps.find(s => s.id === step)!;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-6 bg-black/90 animate-fade-in">
      <div 
        className="max-w-xl w-full max-h-[90vh] border border-border rounded-2xl overflow-y-auto scrollbar-hide shadow-2xl relative"
        style={{ backgroundColor: "var(--background)" }}
      >
        {/* Background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[500px] h-[300px] bg-accent/10 blur-[100px] -z-10" />
        
        <div className="p-6 sm:p-10 lg:p-12 text-center">

          <h1 className="text-3xl lg:text-4xl font-black text-white tracking-tight mb-2">
            {currentStep.title}
          </h1>
          <p className="text-gray-500 font-medium mb-10">
            {currentStep.subtitle}
          </p>

          {currentStep.content}
        </div>

        {/* Progress dots */}
        <div className="pb-8 flex justify-center space-x-2">
          {steps.map((s) => (
            <button 
              key={s.id} 
              onClick={() => setStep(s.id)}
              className={`h-1.5 rounded-full transition-all duration-300 focus:outline-none ${s.id === step ? "w-8 bg-accent" : "w-1.5 bg-white/10 hover:bg-white/30"}`}
              title={`Go to step ${s.id}`}
              aria-label={`Go to step ${s.id}`}
            />
          ))}
        </div>

        <button 
          onClick={onSkip}
          className="absolute top-6 right-6 p-2 rounded-full bg-white/[0.03] text-gray-600 hover:text-white hover:bg-white/10 transition-all"
        >
          <X size={20} />
        </button>
      </div>
    </div>
  );
}

function FeatureCard({ icon, title, desc }: { icon: React.ReactNode, title: string, desc: string }) {
  return (
    <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.04] text-left space-y-3 hover:bg-white/[0.04] transition-all">
      <div className="w-10 h-10 rounded-xl bg-white/[0.03] flex items-center justify-center">
        {icon}
      </div>
      <div>
        <h3 className="text-sm font-bold text-white">{title}</h3>
        <p className="text-[11px] text-gray-500 leading-tight mt-1">{desc}</p>
      </div>
    </div>
  );
}
