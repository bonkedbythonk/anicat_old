"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { X, ChevronLeft, ChevronRight, Loader2, Maximize2, Minimize2, Book, FileText, ScrollText } from "lucide-react";
import { mediaApi } from "@/lib/api";

interface MangaReaderProps {
  mediaId: number;
  chapterNumber: string;
  initialPage?: number;
  onClose: () => void;
  onProgressUpdate?: (chapterNum: string) => void;
}

type ReadingMode = "single" | "double" | "vertical";

export default function MangaReader({ mediaId, chapterNumber, initialPage = 0, onClose, onProgressUpdate }: MangaReaderProps) {
  const [pages, setPages] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [readingMode, setReadingMode] = useState<ReadingMode>("single");
  const [showControls, setShowControls] = useState(true);
  const [loadedImages, setLoadedImages] = useState<Set<number>>(new Set());
  
  const containerRef = useRef<HTMLDivElement>(null);
  const controlsTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastActionRef = useRef<number>(0);

  // Sync fullscreen state with browser
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isFull = !!(
        document.fullscreenElement || 
        (document as any).webkitFullscreenElement || 
        (document as any).mozFullScreenElement || 
        (document as any).msFullscreenElement
      );
      setIsFullscreen(isFull);
    };
    
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("webkitfullscreenchange", handleFullscreenChange);
    document.addEventListener("mozfullscreenchange", handleFullscreenChange);
    document.addEventListener("MSFullscreenChange", handleFullscreenChange);
    
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener("webkitfullscreenchange", handleFullscreenChange);
      document.removeEventListener("mozfullscreenchange", handleFullscreenChange);
      document.removeEventListener("MSFullscreenChange", handleFullscreenChange);
    };
  }, []);

  // Persist current page
  useEffect(() => {
    if (!loading && pages.length > 0) {
      localStorage.setItem(`anicat_manga_${mediaId}_${chapterNumber}_page`, currentPage.toString());
    }
  }, [currentPage, mediaId, chapterNumber, loading, pages.length]);

  useEffect(() => {
    setLoading(true);
    mediaApi.getChapterPages(mediaId, chapterNumber)
      .then(data => {
        setPages(data.thumbnails || []);
        setLoading(false);
        
        // Restore saved page if not provided in props
        if (initialPage === 0) {
          const savedPage = localStorage.getItem(`anicat_manga_${mediaId}_${chapterNumber}_page`);
          if (savedPage) {
            setCurrentPage(parseInt(savedPage));
          }
        }

        if (window.innerWidth > 1024) {
          setReadingMode("double");
        }
      })
      .catch(err => {
        console.error("Failed to load manga pages:", err);
        setError("Failed to load chapter pages. Please try again.");
        setLoading(false);
      });
  }, [mediaId, chapterNumber, initialPage]);

  // Pre-load next pages logic
  useEffect(() => {
    if (pages.length > 0) {
      const nextPages = pages.slice(currentPage, currentPage + 6);
      nextPages.forEach((src, idx) => {
        const globalIdx = currentPage + idx;
        if (!loadedImages.has(globalIdx)) {
          const img = new Image();
          img.src = getProxyUrl(src);
          img.onload = () => {
            setLoadedImages(prev => new Set(prev).add(globalIdx));
          };
        }
      });
    }
  }, [currentPage, pages, loadedImages]);

  const handleNext = useCallback(() => {
    const now = Date.now();
    if (now - lastActionRef.current < 250) return; // Debounce
    lastActionRef.current = now;

    if (readingMode === "vertical") return;
    const step = readingMode === "double" ? 2 : 1;
    setCurrentPage(prev => Math.min(pages.length - 1, prev + step));
  }, [readingMode, pages.length]);

  const handlePrev = useCallback(() => {
    const now = Date.now();
    if (now - lastActionRef.current < 250) return; // Debounce
    lastActionRef.current = now;

    if (readingMode === "vertical") return;
    const step = readingMode === "double" ? 2 : 1;
    setCurrentPage(prev => Math.max(0, prev - step));
  }, [readingMode]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case "ArrowRight":
        case " ":
          e.preventDefault();
          handleNext();
          break;
        case "ArrowLeft":
          e.preventDefault();
          handlePrev();
          break;
        case "f":
        case "F":
          toggleFullscreen();
          break;
        case "Escape":
          if (!document.fullscreenElement) onClose();
          break;
        case "m":
        case "M":
          setReadingMode(prev => prev === "single" ? "double" : prev === "double" ? "vertical" : "single");
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleNext, handlePrev, onClose]);

  const toggleFullscreen = () => {
    const element = containerRef.current as any;
    if (!element) return;

    const isFull = !!(
      document.fullscreenElement || 
      (document as any).webkitFullscreenElement || 
      (document as any).webkitIsFullScreen ||
      (document as any).mozFullScreenElement || 
      (document as any).msFullscreenElement
    );

    try {
      if (!isFull) {
        if (element.requestFullscreen) {
          element.requestFullscreen().catch((e: any) => alert("Fullscreen error: " + e.message));
        } else if (element.webkitRequestFullscreen) {
          element.webkitRequestFullscreen();
        } else if (element.webkitRequestFullScreen) {
          element.webkitRequestFullScreen();
        } else if (element.mozRequestFullScreen) {
          element.mozRequestFullScreen();
        } else if (element.msRequestFullscreen) {
          element.msRequestFullscreen();
        } else {
          alert("Your browser does not support fullscreen requests on this element.");
        }
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen().catch((e: any) => alert("Exit fullscreen error: " + e.message));
        } else if ((document as any).webkitExitFullscreen) {
          (document as any).webkitExitFullscreen();
        } else if ((document as any).webkitCancelFullScreen) {
          (document as any).webkitCancelFullScreen();
        } else if ((document as any).mozCancelFullScreen) {
          (document as any).mozCancelFullScreen();
        } else if ((document as any).msExitFullscreen) {
          (document as any).msExitFullscreen();
        }
      }
    } catch (err: any) {
      alert("Critical fullscreen error: " + err.message);
    }
  };

  const handleFinish = () => {
    const isAtEnd = readingMode === "vertical" ? true : // Vertical mode button is at the bottom
                   (readingMode === "single" ? currentPage === pages.length - 1 : 
                    currentPage >= pages.length - 2);
    
    if (!isAtEnd) {
      console.warn("[MangaReader] handleFinish called but not at end of chapter");
      return;
    }

    // Clear saved page for this chapter since it's finished
    localStorage.removeItem(`anicat_manga_${mediaId}_${chapterNumber}_page`);
    
    if (onProgressUpdate) onProgressUpdate(chapterNumber);
    onClose();
  };

  const handleMouseMove = () => {
    setShowControls(true);
    if (controlsTimeoutRef.current) clearTimeout(controlsTimeoutRef.current);
    controlsTimeoutRef.current = setTimeout(() => setShowControls(false), 3000);
  };

  const getProxyUrl = (url: string) => {
    return `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/media/manga/proxy?url=${encodeURIComponent(url)}`;
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-[200] bg-black flex flex-col items-center justify-center">
        <Loader2 className="animate-spin text-accent mb-4" size={48} />
        <p className="text-gray-400 font-medium">Loading Chapter {chapterNumber}...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 z-[200] bg-black flex flex-col items-center justify-center p-6 text-center">
        <div className="bg-red-500/10 text-red-500 p-4 rounded-xl mb-6 max-w-md border border-red-500/20">
          <p className="font-bold mb-1">Error</p>
          <p className="text-sm">{error}</p>
        </div>
        <button onClick={onClose} className="px-6 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors font-bold">
          Close Reader
        </button>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      onMouseMove={handleMouseMove}
      className="fixed inset-0 z-[200] bg-[#050505] flex flex-col items-center select-none overflow-hidden"
    >
      {/* Header Controls */}
      <div className={`fixed top-0 inset-x-0 z-50 bg-gradient-to-b from-black/95 to-transparent p-6 transition-opacity duration-300 ${showControls ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"}`}>
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <button onClick={onClose} className="p-3 rounded-xl bg-white/5 hover:bg-white/10 text-white transition-all border border-white/5">
              <X size={20} />
            </button>
            <div>
              <h2 className="text-xs font-bold text-accent uppercase tracking-[0.2em] mb-1">Chapter</h2>
              <p className="text-xl font-black text-white">{chapterNumber}</p>
            </div>
          </div>

          <div className="flex items-center space-x-3 bg-black/60 backdrop-blur-xl p-1.5 rounded-2xl border border-white/10 shadow-2xl">
            <button onClick={() => setReadingMode("single")} className={`p-2.5 rounded-xl transition-all ${readingMode === "single" ? "bg-accent text-white" : "text-gray-500 hover:text-white"}`}><FileText size={18} /></button>
            <button onClick={() => setReadingMode("double")} className={`p-2.5 rounded-xl transition-all ${readingMode === "double" ? "bg-accent text-white" : "text-gray-500 hover:text-white"}`}><Book size={18} /></button>
            <button onClick={() => setReadingMode("vertical")} className={`p-2.5 rounded-xl transition-all ${readingMode === "vertical" ? "bg-accent text-white" : "text-gray-500 hover:text-white"}`}><ScrollText size={18} /></button>
            <div className="w-px h-6 bg-white/10 mx-1" />
            <button 
              onClick={() => {
                console.log("Fullscreen button clicked");
                toggleFullscreen();
              }} 
              className="p-2.5 rounded-xl text-gray-500 hover:text-white transition-all cursor-pointer z-[60]"
            >
              {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
            </button>
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className={`flex-1 w-full overflow-y-auto scroll-smooth scrollbar-hide ${readingMode === "vertical" ? "" : "flex items-center justify-center"}`}>
        {readingMode === "vertical" ? (
          <div className="max-w-3xl w-full mx-auto py-32 space-y-4">
            {pages.map((page, idx) => (
              <div key={idx} className="relative min-h-[400px] flex items-center justify-center bg-white/[0.02] rounded-lg overflow-hidden">
                {!loadedImages.has(idx) && <Loader2 className="animate-spin text-white/10" size={32} />}
                <img 
                  src={getProxyUrl(page)} 
                  alt={`Page ${idx + 1}`} 
                  className={`w-full h-auto transition-opacity duration-300 ${loadedImages.has(idx) ? "opacity-100" : "opacity-0"}`} 
                  onLoad={() => setLoadedImages(prev => new Set(prev).add(idx))}
                />
              </div>
            ))}
            <div className="pt-20 pb-10 flex justify-center">
              <button onClick={handleFinish} className="px-12 py-4 bg-accent text-white rounded-full font-black text-sm shadow-2xl">Finish Reading</button>
            </div>
          </div>
        ) : (
          <div className="relative w-full h-full flex items-center justify-center p-4 lg:p-8">
            <div className="absolute inset-y-0 left-0 w-1/4 z-10 cursor-w-resize" onClick={handlePrev} />
            <div className="absolute inset-y-0 right-0 w-1/4 z-10 cursor-e-resize" onClick={handleNext} />

            <div className={`flex items-center justify-center h-full gap-1 transition-all ${readingMode === "double" ? "w-full" : "max-w-3xl"}`}>
              {readingMode === "double" ? (
                <>
                  <div className="flex-1 h-full flex items-center justify-end">
                    <div className="relative max-h-full">
                      {!loadedImages.has(currentPage) && <div className="absolute inset-0 flex items-center justify-center bg-white/[0.02]"><Loader2 className="animate-spin text-white/10" size={32} /></div>}
                      <img 
                        key={pages[currentPage]} 
                        src={getProxyUrl(pages[currentPage])} 
                        className={`transition-all duration-500 object-contain bg-black shadow-2xl ${showControls ? "max-h-[calc(100vh-220px)]" : "max-h-screen"}`} 
                      />
                    </div>
                  </div>
                  {currentPage + 1 < pages.length && (
                    <div className="flex-1 h-full flex items-center justify-start border-l border-white/5">
                      <div className="relative max-h-full">
                        {!loadedImages.has(currentPage + 1) && <div className="absolute inset-0 flex items-center justify-center bg-white/[0.02]"><Loader2 className="animate-spin text-white/10" size={32} /></div>}
                        <img 
                          key={pages[currentPage + 1]} 
                          src={getProxyUrl(pages[currentPage + 1])} 
                          className={`transition-all duration-500 object-contain bg-black shadow-2xl ${showControls ? "max-h-[calc(100vh-220px)]" : "max-h-screen"}`} 
                        />
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="relative h-full flex items-center justify-center">
                  {!loadedImages.has(currentPage) && <div className="absolute inset-0 flex items-center justify-center bg-white/[0.02]"><Loader2 className="animate-spin text-white/10" size={32} /></div>}
                  <img 
                    key={pages[currentPage]} 
                    src={getProxyUrl(pages[currentPage])} 
                    className={`transition-all duration-500 object-contain bg-black shadow-2xl ${showControls ? "max-h-[calc(100vh-220px)]" : "max-h-screen"}`} 
                  />
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      {readingMode !== "vertical" && (
        <div className={`fixed bottom-0 inset-x-0 z-50 bg-gradient-to-t from-black/95 to-transparent p-8 transition-opacity duration-300 ${showControls ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"}`}>
          <div className="max-w-5xl mx-auto flex flex-col space-y-6">
            <input type="range" min="0" max={pages.length - 1} value={currentPage} onChange={(e) => setCurrentPage(parseInt(e.target.value))} className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer accent-accent" />
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <button onClick={handlePrev} disabled={currentPage === 0} className="p-3 rounded-xl bg-white/5 hover:bg-white/10 text-white disabled:opacity-20"><ChevronLeft size={24} /></button>
                <button onClick={handleNext} disabled={currentPage >= pages.length - (readingMode === "double" ? 2 : 1)} className="p-3 rounded-xl bg-white/5 hover:bg-white/10 text-white disabled:opacity-20"><ChevronRight size={24} /></button>
                <div className="text-sm font-black text-white/40 tabular-nums">
                  <span className="text-white">{currentPage + 1}{readingMode === "double" && currentPage + 1 < pages.length ? `-${currentPage + 2}` : ""}</span> / {pages.length}
                </div>
              </div>
              {((readingMode === "single" && currentPage === pages.length - 1) || 
                (readingMode === "double" && currentPage >= pages.length - 2)) && (
                <button onClick={handleFinish} className="px-10 py-3.5 bg-accent text-white rounded-2xl font-black text-sm shadow-2xl animate-fade-in">Finish Reading</button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
