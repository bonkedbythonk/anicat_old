"use client";

import { X } from "lucide-react";

interface HelpModalProps {
  onClose: () => void;
}

export default function HelpModal({ onClose }: HelpModalProps) {
  const shortcuts = [
    { key: "1 - 9", desc: "Switch views (Home, Library, Schedule, ...)" },
    { key: "K  or  /", desc: "Search" },
    { key: "Esc", desc: "Close detail drawer" },
    { key: ",", desc: "Settings" },
    { key: "?", desc: "Toggle this help menu" },
  ];

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/85 animate-fade-in" onClick={onClose}>
      <div 
        className="border border-border rounded-3xl p-8 max-w-md w-full shadow-2xl relative" 
        style={{ backgroundColor: "var(--background)" }}
        onClick={e => e.stopPropagation()}
      >
        <button onClick={onClose} className="absolute top-6 right-6 text-gray-500 hover:text-white transition-colors">
          <X size={20} />
        </button>
        <h2 className="text-2xl font-extrabold text-white mb-6">Keyboard Shortcuts</h2>
        <div className="space-y-3">
          {shortcuts.map((s) => (
            <div key={s.key} className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-400">{s.desc}</span>
              <kbd className="px-3 py-1.5 bg-white/[0.05] border border-white/[0.1] rounded-lg text-xs font-bold text-white shadow-sm font-mono">
                {s.key}
              </kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
