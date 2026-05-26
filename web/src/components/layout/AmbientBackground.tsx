"use client";

import { useEffect, useState } from "react";

type SkinConfig = {
  base: string;
  blobs: Array<{
    gradient: string;
    size: string;
    opacity: string;
    blur: string;
    position: Record<string, string>;
    duration: string;
    direction: string;
  }>;
};

const SKIN_CONFIGS: Record<string, SkinConfig> = {
  "neon-abyss": {
    base: "var(--background)",
    blobs: [
      {
        gradient: "radial-gradient(circle, rgba(94,92,230,0.8) 0%, rgba(94,92,230,0) 70%)",
        size: "80vw",
        opacity: "0.15",
        blur: "100px",
        position: { top: "-10%", left: "-10%" },
        duration: "20s",
        direction: "alternate",
      },
      {
        gradient: "radial-gradient(circle, rgba(191,90,242,0.6) 0%, rgba(191,90,242,0) 70%)",
        size: "70vw",
        opacity: "0.10",
        blur: "120px",
        position: { top: "40%", right: "-20%" },
        duration: "25s",
        direction: "alternate-reverse",
      },
      {
        gradient: "radial-gradient(circle, rgba(10,132,255,0.5) 0%, rgba(10,132,255,0) 70%)",
        size: "90vw",
        opacity: "0.05",
        blur: "150px",
        position: { bottom: "-20%", left: "20%" },
        duration: "30s",
        direction: "alternate",
      },
    ],
  },
  "sakura-zen": {
    base: "var(--background)",
    blobs: [
      {
        gradient: "radial-gradient(circle, rgba(220,100,150,0.75) 0%, rgba(220,100,150,0) 70%)",
        size: "90vw",
        opacity: "0.13",
        blur: "120px",
        position: { top: "-15%", left: "-15%" },
        duration: "18s",
        direction: "alternate",
      },
      {
        gradient: "radial-gradient(circle, rgba(154,184,154,0.6) 0%, rgba(154,184,154,0) 70%)",
        size: "75vw",
        opacity: "0.09",
        blur: "140px",
        position: { bottom: "-10%", right: "-15%" },
        duration: "24s",
        direction: "alternate-reverse",
      },
      {
        gradient: "radial-gradient(circle, rgba(232,160,180,0.5) 0%, rgba(232,160,180,0) 70%)",
        size: "60vw",
        opacity: "0.07",
        blur: "100px",
        position: { top: "30%", left: "30%" },
        duration: "28s",
        direction: "alternate",
      },
    ],
  },
  "retro-manga": {
    base: "var(--background)",
    blobs: [],
  },
  "forest-moss": {
    base: "var(--background)",
    blobs: [
      {
        gradient: "radial-gradient(circle, rgba(16,185,129,0.7) 0%, rgba(16,185,129,0) 70%)",
        size: "85vw",
        opacity: "0.12",
        blur: "110px",
        position: { top: "-10%", left: "-10%" },
        duration: "22s",
        direction: "alternate",
      },
      {
        gradient: "radial-gradient(circle, rgba(52,211,153,0.5) 0%, rgba(52,211,153,0) 70%)",
        size: "75vw",
        opacity: "0.08",
        blur: "130px",
        position: { bottom: "-15%", right: "-15%" },
        duration: "26s",
        direction: "alternate-reverse",
      },
      {
        gradient: "radial-gradient(circle, rgba(6,78,59,0.6) 0%, rgba(6,78,59,0) 70%)",
        size: "65vw",
        opacity: "0.06",
        blur: "90px",
        position: { top: "35%", left: "25%" },
        duration: "32s",
        direction: "alternate",
      },
    ],
  },
};

export default function AmbientBackground() {
  const [mounted, setMounted] = useState(false);
  const [skin, setSkin] = useState<string>("neon-abyss");

  useEffect(() => {
    setMounted(true);

    const readSkin = () => {
      const style = document.documentElement.getAttribute("data-style") || "neon-abyss";
      setSkin(style);
    };

    readSkin();

    // React to skin changes
    const observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.type === "attributes" && m.attributeName === "data-style") {
          readSkin();
        }
      }
    });
    observer.observe(document.documentElement, { attributes: true });

    const onStorage = (e: StorageEvent) => {
      if (e.key === "anicat_ui_style") readSkin();
    };
    window.addEventListener("storage", onStorage);

    return () => {
      observer.disconnect();
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const config = SKIN_CONFIGS[skin] ?? SKIN_CONFIGS["neon-abyss"];

  if (!mounted) return <div className="fixed inset-0 -z-50" style={{ background: config.base }} />;

  return (
    <div
      className={`fixed inset-0 overflow-hidden pointer-events-none -z-50 ${skin === 'retro-manga' ? 'ambient-bg-manga' : ''}`}
      style={{ background: config.base, transition: "background 0.4s ease" }}
    >
      {config.blobs.map((blob, i) => (
        <div
          key={i}
          className="absolute rounded-full mix-blend-screen ambient-blob"
          style={{
            width: blob.size,
            height: blob.size,
            background: blob.gradient,
            opacity: blob.opacity,
            filter: `blur(${blob.blur})`,
            animation: `blob ${blob.duration} infinite ${blob.direction}`,
            animationDelay: `${i * 4}s`,
            ...blob.position,
          }}
        />
      ))}

      {/* Noise texture overlay */}
      <div className="absolute inset-0 opacity-[0.03] bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />
    </div>
  );
}
