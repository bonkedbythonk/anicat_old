"use client";

import { useEffect, useState, useRef } from "react";

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
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const mouseRef = useRef<{ x: number | null; y: number | null }>({ x: null, y: null });

  useEffect(() => {
    const readSkin = () => {
      const style = document.documentElement.getAttribute("data-style") || "neon-abyss";
      setSkin(style);
    };

    // Defer state updates to prevent synchronous render cascade warnings in React 19
    const frameId = requestAnimationFrame(() => {
      setMounted(true);
      readSkin();
    });

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
      cancelAnimationFrame(frameId);
      observer.disconnect();
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  // Falling sakura petals / forest leaves canvas effect
  useEffect(() => {
    if (skin !== "sakura-zen" && skin !== "forest-moss") return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let isActive = true;

    // Resize handler
    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);

    // Track mouse coordinates for interactive displacement force field
    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };
    const handleMouseLeave = () => {
      mouseRef.current = { x: null, y: null };
    };
    window.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseleave", handleMouseLeave);

    // Pause canvas updates when app is in background to preserve system resources
    const handleVisibilityChange = () => {
      isActive = document.visibilityState === "visible";
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);

    // Set up lightweight particles (petals for sakura, leaves for forest)
    const isSakura = skin === "sakura-zen";
    const particleCount = 28;
    const colors = isSakura
      ? [
          "rgba(232, 160, 180, 0.65)", // soft accent pink
          "rgba(242, 191, 206, 0.70)", // light pastel pink
          "rgba(255, 218, 224, 0.55)", // bright lavender pink
          "rgba(220, 100, 150, 0.45)", // deep rose pink
        ]
      : [
          "rgba(16, 185, 129, 0.50)",  // emerald green
          "rgba(52, 211, 153, 0.55)",  // minty leaf green
          "rgba(4, 120, 87, 0.40)",    // deep forest pine
          "rgba(110, 190, 150, 0.45)", // pale foliage green
        ];

    const particles: Array<{
      x: number;
      y: number;
      r: number;
      d: number;
      color: string;
      tiltAngle: number;
      tiltAngleIncremental: number;
    }> = [];

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * window.innerWidth,
        y: Math.random() * window.innerHeight,
        r: Math.random() * 8 + 6, // 6px to 14px size
        d: Math.random() * 2 + 1, // weight/fall speed factor
        color: colors[Math.floor(Math.random() * colors.length)],
        tiltAngle: Math.random() * Math.PI,
        tiltAngleIncremental: Math.random() * 0.02 + 0.01,
      });
    }

    const animate = () => {
      if (!isActive) {
        animationFrameId = requestAnimationFrame(animate);
        return;
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // Update angle rotation and drift coordinates
        p.tiltAngle += p.tiltAngleIncremental;
        p.y += (1 + p.r / 10) * 0.4 * p.d;
        p.x += Math.sin(p.tiltAngle) * 0.25;

        // Interactive mouse avoidance physics (displacement force field)
        if (mouseRef.current.x !== null && mouseRef.current.y !== null) {
          const dx = p.x - mouseRef.current.x;
          const dy = p.y - mouseRef.current.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 130) {
            const force = (130 - dist) / 130;
            // Push particles away from the cursor
            p.x += (dx / dist) * force * 4.5;
            p.y += (dy / dist) * force * 4.5;
          }
        }

        // Screen wraps to keep constant falling cycle
        if (p.y > canvas.height + 20) {
          p.y = -20;
          p.x = Math.random() * canvas.width;
        }
        if (p.x > canvas.width + 20) {
          p.x = -20;
        } else if (p.x < -20) {
          p.x = canvas.width + 20;
        }

        // Render particle
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.tiltAngle);

        if (isSakura) {
          // Sakura Petal: organic shape with wabi-sabi cleft/notch at the tip
          ctx.beginPath();
          ctx.moveTo(0, p.r); // Base
          ctx.bezierCurveTo(-p.r * 1.4, p.r * 0.5, -p.r * 1.2, -p.r * 0.5, -p.r * 0.4, -p.r);
          ctx.lineTo(-p.r * 0.25, -p.r * 0.95);
          ctx.lineTo(0, -p.r * 0.68); // Notch dip
          ctx.lineTo(p.r * 0.25, -p.r * 0.95);
          ctx.lineTo(p.r * 0.4, -p.r);
          ctx.bezierCurveTo(p.r * 1.2, -p.r * 0.5, p.r * 1.4, p.r * 0.5, 0, p.r);
          ctx.closePath();

          // Smooth gradient for premium depth
          const grad = ctx.createLinearGradient(0, p.r, 0, -p.r);
          grad.addColorStop(0, p.color);
          grad.addColorStop(1, "rgba(255, 240, 244, 0.85)"); // bright tip
          ctx.fillStyle = grad;
          ctx.fill();

          // Organic veins (midrib)
          ctx.beginPath();
          ctx.moveTo(0, p.r * 0.8);
          ctx.lineTo(0, -p.r * 0.35);
          ctx.strokeStyle = "rgba(255, 255, 255, 0.30)";
          ctx.lineWidth = 0.6;
          ctx.stroke();

          // Subtle lateral veins
          ctx.beginPath();
          ctx.moveTo(0, p.r * 0.4);
          ctx.quadraticCurveTo(-p.r * 0.25, p.r * 0.2, -p.r * 0.45, -p.r * 0.05);
          ctx.moveTo(0, p.r * 0.2);
          ctx.quadraticCurveTo(p.r * 0.25, 0, p.r * 0.45, -p.r * 0.25);
          ctx.strokeStyle = "rgba(255, 255, 255, 0.18)";
          ctx.lineWidth = 0.4;
          ctx.stroke();
        } else {
          // Forest Leaf: slender pointed shape
          ctx.beginPath();
          ctx.moveTo(0, p.r); // Base
          ctx.quadraticCurveTo(-p.r * 0.80, 0, 0, -p.r); // Tip
          ctx.quadraticCurveTo(p.r * 0.80, 0, 0, p.r); // Right side
          ctx.closePath();

          // Linear gradient for light reflection
          const grad = ctx.createLinearGradient(0, p.r, 0, -p.r);
          grad.addColorStop(0, p.color);
          grad.addColorStop(1, "rgba(52, 211, 153, 0.85)"); // soft emerald green tip
          ctx.fillStyle = grad;
          ctx.fill();

          // Midrib
          ctx.beginPath();
          ctx.moveTo(0, p.r * 0.95);
          ctx.lineTo(0, -p.r * 0.95);
          ctx.strokeStyle = "rgba(255, 255, 255, 0.35)";
          ctx.lineWidth = 0.7;
          ctx.stroke();

          // Side branching veins
          ctx.beginPath();
          // Left side
          ctx.moveTo(0, p.r * 0.5);
          ctx.lineTo(-p.r * 0.35, p.r * 0.1);
          ctx.moveTo(0, p.r * 0.15);
          ctx.lineTo(-p.r * 0.45, -p.r * 0.2);
          ctx.moveTo(0, -p.r * 0.2);
          ctx.lineTo(-p.r * 0.35, -p.r * 0.5);
          
          // Right side
          ctx.moveTo(0, p.r * 0.5);
          ctx.lineTo(p.r * 0.35, p.r * 0.1);
          ctx.moveTo(0, p.r * 0.15);
          ctx.lineTo(p.r * 0.45, -p.r * 0.2);
          ctx.moveTo(0, -p.r * 0.2);
          ctx.lineTo(p.r * 0.35, -p.r * 0.5);

          ctx.strokeStyle = "rgba(255, 255, 255, 0.20)";
          ctx.lineWidth = 0.4;
          ctx.stroke();
        }

        ctx.restore();
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener("resize", resizeCanvas);
      window.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseleave", handleMouseLeave);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      cancelAnimationFrame(animationFrameId);
    };
  }, [skin]);

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

      {/* Falling Sakura / Forest Leaves Canvas */}
      {(skin === "sakura-zen" || skin === "forest-moss") && (
        <canvas
          ref={canvasRef}
          className="absolute inset-0 w-full h-full pointer-events-none"
        />
      )}

      {/* Noise texture overlay */}
      <div className="absolute inset-0 opacity-[0.03] bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />
    </div>
  );
}
