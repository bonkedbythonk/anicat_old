"use client";

import { useEffect, useState } from "react";

export default function AmbientBackground() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return <div className="fixed inset-0 bg-black -z-50" />;

  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none -z-50 bg-black">
      {/* Base deep background */}
      <div className="absolute inset-0 bg-[#0a0a0c]" />
      
      {/* Animated Mesh Gradient blobs */}
      <div 
        className="absolute w-[80vw] h-[80vw] rounded-full mix-blend-screen filter blur-[100px] opacity-40 animate-blob"
        style={{
          background: 'radial-gradient(circle, rgba(94,92,230,0.8) 0%, rgba(94,92,230,0) 70%)',
          top: '-10%',
          left: '-10%',
          animation: 'blob 20s infinite alternate',
        }}
      />
      <div 
        className="absolute w-[70vw] h-[70vw] rounded-full mix-blend-screen filter blur-[120px] opacity-30 animate-blob animation-delay-2000"
        style={{
          background: 'radial-gradient(circle, rgba(191,90,242,0.6) 0%, rgba(191,90,242,0) 70%)',
          top: '40%',
          right: '-20%',
          animation: 'blob 25s infinite alternate-reverse',
        }}
      />
      <div 
        className="absolute w-[90vw] h-[90vw] rounded-full mix-blend-screen filter blur-[150px] opacity-20 animate-blob animation-delay-4000"
        style={{
          background: 'radial-gradient(circle, rgba(10,132,255,0.5) 0%, rgba(10,132,255,0) 70%)',
          bottom: '-20%',
          left: '20%',
          animation: 'blob 30s infinite alternate',
        }}
      />
      
      {/* Noise texture overlay to prevent banding */}
      <div className="absolute inset-0 opacity-[0.03] bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />
    </div>
  );
}
