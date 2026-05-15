"use client";

import { useState } from "react";
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
  PlayCircle
} from "lucide-react";
import { mediaApi } from "@/lib/api";

interface OnboardingProps {
  onComplete: () => void;
  onSkip: () => void;
}

export default function Onboarding({ onComplete, onSkip }: OnboardingProps) {
  const [step, setStep] = useState(1);
  const [token, setToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConnectAnilist = async () => {
    if (!token.trim()) {
      setError("Please enter your AniList token.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const config = await mediaApi.getConfig();
      await mediaApi.updateConfig({
        ...config,
        anilist: { ...config.anilist, token: token.trim() }
      });
      
      // Force backend to reconnect with new token
      await mediaApi.reconnect();
      
      // Briefly wait to ensure backend registers the token
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Try to reconnect/validate
      const health = await mediaApi.getHealthStatus();
      if (health.api_connected) {
        onComplete();
      } else {
        setError("Token was saved but AniList is still unreachable. Is your token valid?");
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
      subtitle: "Your Ultimate Anime & Manga Companion",
      content: (
        <div className="space-y-8 animate-fade-in">
          <div className="grid grid-cols-2 gap-4">
            <FeatureCard 
              icon={<Monitor className="text-accent" />} 
              title="Stream & Track" 
              desc="Watch your favorite shows and sync progress automatically."
            />
            <FeatureCard 
              icon={<BookOpen className="text-secondary" />} 
              title="Manga Reader" 
              desc="A premium reading experience for your favorite manga."
            />
            <FeatureCard 
              icon={<Download className="text-green-400" />} 
              title="Downloads" 
              desc="Take your library offline with ease."
            />
            <FeatureCard 
              icon={<Layout className="text-orange-400" />} 
              title="Clean UI" 
              desc="Designed for clarity and visual excellence."
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
      title: "Connect Your Account",
      subtitle: "Sync your library and track your progress",
      content: (
        <div className="space-y-6 animate-fade-in">
          <p className="text-gray-400 text-sm leading-relaxed">
            Anicat works best when connected to <span className="text-white font-semibold">AniList</span>. 
            It's like a digital diary for your anime and manga. By connecting, your watch history stays synced across all your devices.
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

            <a 
              href="https://anilist.co/api/v2/oauth/authorize?client_id=20148&redirect_uri=https://anilist.co/api/v2/oauth/pin&response_type=token" 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center justify-between p-4 rounded-2xl bg-accent/10 border border-accent/20 hover:bg-accent/20 transition-all group"
            >
              <div className="flex items-center space-x-3">
                <div className="p-2 rounded-lg bg-accent text-white shadow-lg shadow-accent/20">
                  <Globe size={18} />
                </div>
                <div className="text-left">
                  <p className="text-sm font-bold text-white">1. Get your Secure Token</p>
                  <p className="text-[11px] text-accent font-medium">Click here to log in and copy the code</p>
                </div>
              </div>
              <ChevronRight size={18} className="text-accent group-hover:translate-x-1 transition-all" />
            </a>

            <div className="flex items-center justify-center space-x-2 text-[11px] text-gray-500 pt-1">
              <span>Don't have an AniList account?</span>
              <a 
                href="https://anilist.co/signup" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-accent hover:underline font-bold"
              >
                Sign up here
              </a>
            </div>
          </div>

          <div className="flex flex-col space-y-3 pt-2">
            <button 
              onClick={handleConnectAnilist}
              disabled={saving}
              className="w-full bg-accent hover:bg-accent-light text-white font-bold py-4 rounded-2xl flex items-center justify-center space-x-2 transition-all shadow-xl shadow-accent/20 active:scale-95 disabled:opacity-50"
            >
              {saving ? <Loader2 size={20} className="animate-spin" /> : (
                <span>Connect Account</span>
              )}
            </button>
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
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-6 bg-background/80 backdrop-blur-md animate-fade-in">
      <div className="max-w-xl w-full bg-surface border border-white/[0.08] rounded-[32px] overflow-hidden shadow-2xl relative">
        {/* Background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[500px] h-[300px] bg-accent/10 blur-[100px] -z-10" />
        
        <div className="p-10 lg:p-12 text-center">
          <div className="w-20 h-20 bg-accent/10 rounded-3xl flex items-center justify-center mx-auto mb-8 animate-pulse-glow">
            <img src="/pwa-logo.png?v=2" alt="Logo" className="w-12 h-12 object-contain" />
          </div>

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
            <div 
              key={s.id} 
              className={`h-1.5 rounded-full transition-all duration-300 ${s.id === step ? "w-8 bg-accent" : "w-1.5 bg-white/10"}`} 
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
