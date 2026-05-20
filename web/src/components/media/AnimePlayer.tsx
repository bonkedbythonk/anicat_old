"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { X, Play, Pause, RotateCcw, Volume2, VolumeX, Maximize, Minimize, Loader2, ArrowRight, Video, PictureInPicture2 } from "lucide-react";
import { API_BASE_ORIGIN, mediaApi } from "@/lib/api";

interface AnimePlayerProps {
  mediaId: number;
  malId?: number;
  episodeNumber: string;
  totalEpisodes?: number;
  onClose: () => void;
  onEpisodeCompleted?: (episodeNum: string) => void;
  onPlayNextEpisode?: () => void;
  hasNextEpisode?: boolean;
}

export default function AnimePlayer({
  mediaId,
  malId,
  episodeNumber,
  totalEpisodes,
  onClose,
  onEpisodeCompleted,
  onPlayNextEpisode,
  hasNextEpisode = false
}: AnimePlayerProps) {
  const [resolved, setResolved] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [skipTimes, setSkipTimes] = useState<Array<{ type: string; start: number; end: number }>>([]);
  const [activeSkip, setActiveSkip] = useState<{ type: string; start: number; end: number } | null>(null);
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [userRating, setUserRating] = useState<number | null>(null);
  const [isSubmittingRating, setIsSubmittingRating] = useState(false);
  const [ratingSuccess, setRatingSuccess] = useState(false);
  const [autoplayCountdown, setAutoplayCountdown] = useState<number | null>(null);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("anicat_player_volume");
      return saved !== null ? parseFloat(saved) : 1;
    }
    return 1;
  });
  const [isMuted, setIsMuted] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("anicat_player_muted") === "true";
    }
    return false;
  });
  const [showControls, setShowControls] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [isHoveredControls, setIsHoveredControls] = useState(false);
  const [autoSkipEnabled, setAutoSkipEnabled] = useState(false);
  
  // Resume position persistence — save/restore playback position per episode
  const resumeKey = `anicat_resume_${mediaId}_${episodeNumber}`;

  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const controlsTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Load volume, auto-skip, mute from localStorage on mount
  useEffect(() => {
    const savedAutoSkip = localStorage.getItem("anicat_auto_skip");
    if (savedAutoSkip !== null) {
      setAutoSkipEnabled(savedAutoSkip === "true");
    }
  }, []);

  // Fetch resolved stream URL on mount or episode change
  useEffect(() => {
    setLoading(true);
    setError(null);
    setResolved(null);
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);

    mediaApi.resolveStream(mediaId, episodeNumber)
      .then(data => {
        setResolved(data);
      })
      .catch(err => {
        console.error("Failed to resolve stream:", err);
        setError("Failed to locate high-quality video servers. Try again shortly.");
        setLoading(false);
      });
  }, [mediaId, episodeNumber]);

  // Netflix-style Autoplay Countdown timer
  useEffect(() => {
    if (autoplayCountdown === null) return;
    if (autoplayCountdown <= 0) {
      setAutoplayCountdown(null);
      if (onPlayNextEpisode) onPlayNextEpisode();
      return;
    }
    const timer = setTimeout(() => {
      setAutoplayCountdown(prev => (prev !== null ? prev - 1 : null));
    }, 1000);
    return () => clearTimeout(timer);
  }, [autoplayCountdown, onPlayNextEpisode]);

  // Synchronize AniSkip intro/outro time retrieval
  useEffect(() => {
    setSkipTimes([]);
    setActiveSkip(null);
    if (!mediaId || !episodeNumber) return;

    const epNum = parseInt(episodeNumber, 10);
    if (isNaN(epNum)) return;

    // AniSkip API requires MyAnimeList (MAL) ID. Fall back to AniList ID if MAL ID is unavailable.
    const queryId = malId || mediaId;
    console.log(`[AniSkip] Fetching skip times for ID ${queryId} (MAL ID: ${malId || "N/A"}, AniList ID: ${mediaId}), Ep: ${epNum}`);

    fetch(`https://api.aniskip.com/v2/skip-times/${queryId}/${epNum}?types[]=op&types[]=ed&episodeLength=0`)
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data && data.found && data.results) {
          const times = data.results.map((r: any) => ({
            type: r.skipType,
            start: r.interval.startTime,
            end: r.interval.endTime
          }));
          console.log(`[AniSkip] Found skip times for ID ${queryId}:`, times);
          setSkipTimes(times);
        } else {
          console.log(`[AniSkip] No skip times found for ID ${queryId}. Using standard 90s fallback.`);
          // Standard 90s fallback intro starting at 0:00 to 1:30
          setSkipTimes([{ type: "op", start: 0, end: 90 }]);
        }
      })
      .catch(err => {
        console.error("[AniSkip] Error querying skip API:", err);
        setSkipTimes([{ type: "op", start: 0, end: 90 }]);
      });
  }, [mediaId, malId, episodeNumber]);

  // Synchronize dynamic HLS.js streaming
  useEffect(() => {
    if (!resolved) return;
    const video = videoRef.current;
    if (!video) return;

    let nativeCleanup: (() => void) | null = null;

    import("hls.js").then((M) => {
      const Hls = M.default;
      
      const isChrome = /Chrome/i.test(navigator.userAgent) || /Chromium/i.test(navigator.userAgent);
      const isWebKitApple = /iPad|iPhone|iPod|Macintosh/i.test(navigator.userAgent) && 
                            /WebKit/i.test(navigator.userAgent) && 
                            !isChrome;
      const canPlayNative = !isChrome && (!!video.canPlayType("application/vnd.apple.mpegurl") || isWebKitApple);

      if (canPlayNative) {
        // Enforce native HLS playback for Apple WebKit (Tauri macOS WebView / Safari)
        const streamUrl = resolved.stream_url.startsWith("http") 
          ? resolved.stream_url 
          : `${API_BASE_ORIGIN}${resolved.stream_url}`;
        
        console.log("[Player] Loading native Apple WebKit HLS stream:", streamUrl);
        video.src = streamUrl;
        
        const handleLoadedMetadata = () => {
          console.log("[Player] Native WebKit metadata loaded. Starting playback...");
          // Apply saved volume immediately
          video.volume = isMuted ? 0 : volume;
          // Restore resume position, preferring server-provided start_time over local
          const savedPos = sessionStorage.getItem(resumeKey);
          if (resolved.start_time) {
            video.currentTime = resolved.start_time;
          } else if (savedPos) {
            video.currentTime = parseFloat(savedPos);
          }
          video.play()
            .then(() => setIsPlaying(true))
            .catch((e) => {
              console.warn("[Player] Playback autoplay blocked or failed:", e);
              setIsPlaying(false);
            });
        };

        const handleNativeError = (e: any) => {
          console.error("[Player] Native HLS playback error encountered:", video.error);
          setError("Native streaming connection was unexpectedly closed.");
        };

        video.addEventListener("loadedmetadata", handleLoadedMetadata);
        video.addEventListener("error", handleNativeError);

        nativeCleanup = () => {
          video.removeEventListener("loadedmetadata", handleLoadedMetadata);
          video.removeEventListener("error", handleNativeError);
        };
      } else if (Hls.isSupported()) {
        // Use Hls.js MSE fallback for non-Apple environments (Chrome, Firefox, Windows, Linux)
        if (hlsRef.current) {
          hlsRef.current.destroy();
        }

        const hls = new Hls({
          maxMaxBufferLength: 30,
          enableWorker: true,
          lowLatencyMode: true
        });
        hlsRef.current = hls;

        const streamUrl = resolved.stream_url.startsWith("http") 
          ? resolved.stream_url 
          : `${API_BASE_ORIGIN}${resolved.stream_url}`;
        
        console.log("[Player] Loading HLS.js stream:", streamUrl);
        hls.loadSource(streamUrl);
        hls.attachMedia(video);

        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          console.log("[Player] HLS.js manifest parsed successfully.");
          if (resolved.start_time) {
            video.currentTime = resolved.start_time;
          }
          video.play()
            .then(() => setIsPlaying(true))
            .catch(() => setIsPlaying(false));
        });

        let mediaRecoverAttempts = 0;
        let networkRecoverAttempts = 0;

        hls.on(Hls.Events.ERROR, (event, data) => {
          console.log("[Player][HLS Error]", { type: data.type, details: data.details, fatal: data.fatal });
          if (data.fatal) {
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                networkRecoverAttempts++;
                if (networkRecoverAttempts <= 3) {
                  console.log(`[Player][HLS Error] Fatal network error (attempt ${networkRecoverAttempts}/3). Attempting to reload HLS stream...`);
                  hls.startLoad();
                } else {
                  console.log("[Player][HLS Error] Network recovery attempts exhausted.");
                  setError("Streaming connection timed out. Check your internet connection.");
                  hls.destroy();
                }
                break;
              case Hls.ErrorTypes.MEDIA_ERROR:
                mediaRecoverAttempts++;
                if (mediaRecoverAttempts === 1) {
                  console.log("[Player][HLS Error] Fatal media error (attempt 1/3). Attempting to recover media...");
                  hls.recoverMediaError();
                } else if (mediaRecoverAttempts === 2) {
                  console.log("[Player][HLS Error] Fatal media error (attempt 2/3). Swapping audio codec and recovering...");
                  hls.swapAudioCodec();
                  hls.recoverMediaError();
                } else {
                  console.log("[Player][HLS Error] Media recovery attempts exhausted. Codec is likely unsupported.");
                  setError("This video format is not natively supported by your browser. Try launching in MPV instead!");
                  hls.destroy();
                }
                break;
              default:
                console.log("[Player][HLS Error] Fatal unrecoverable HLS error:", data.type, data.details);
                setError("Streaming connection was unexpectedly closed.");
                hls.destroy();
                break;
            }
          }
        });
      } else if (canPlayNative) {
        // Generic HLS fallback (in case Hls.js is not supported but native HLS is, and not explicitly Safari/Mac)
        const streamUrl = resolved.stream_url.startsWith("http") 
          ? resolved.stream_url 
          : `${API_BASE_ORIGIN}${resolved.stream_url}`;
        
        console.log("[Player] Loading native fallback HLS stream:", streamUrl);
        video.src = streamUrl;
        const handleGenericLoadedMetadata = () => {
          video.volume = isMuted ? 0 : volume;
          const savedPos = sessionStorage.getItem(resumeKey);
          if (resolved.start_time) {
            video.currentTime = resolved.start_time;
          } else if (savedPos) {
            video.currentTime = parseFloat(savedPos);
          }
          video.play()
            .then(() => setIsPlaying(true))
            .catch(() => setIsPlaying(false));
        };
        video.addEventListener("loadedmetadata", handleGenericLoadedMetadata);
        nativeCleanup = () => {
          video.removeEventListener("loadedmetadata", handleGenericLoadedMetadata);
        };
      } else {
        setError("Playback format is not supported by your system.");
      }
    });

    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
      if (nativeCleanup) {
        nativeCleanup();
      }
    };
  }, [resolved]);

  // Sync fullscreen state
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

  // Periodic watch progress tracking to backend
  useEffect(() => {
    if (!resolved || !isPlaying) return;

    const interval = setInterval(() => {
      const video = videoRef.current;
      if (video && video.duration) {
        mediaApi.trackPlayback(mediaId, episodeNumber, video.currentTime, video.duration)
          .then(res => {
            if (res.completed && onEpisodeCompleted) {
              onEpisodeCompleted(episodeNumber);
              const isFinal = totalEpisodes ? parseInt(episodeNumber, 10) === totalEpisodes : !hasNextEpisode;
              if (isFinal) {
                setIsPlaying(false);
                video.pause();
                setShowRatingModal(true);
              }
            }
          })
          .catch(console.error);
      }
    }, 10000); // Track progress every 10s

    return () => clearInterval(interval);
  }, [resolved, isPlaying, mediaId, episodeNumber, onEpisodeCompleted, totalEpisodes, hasNextEpisode]);

  // Sync volume state to video tag
  useEffect(() => {
    const video = videoRef.current;
    if (video) {
      video.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  // Mouse movement hides controls after 3 seconds
  const resetControlsTimeout = useCallback(() => {
    setShowControls(true);
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current);
    }
    if (!isHoveredControls && isPlaying) {
      controlsTimeoutRef.current = setTimeout(() => {
        setShowControls(false);
      }, 3000);
    }
  }, [isPlaying, isHoveredControls]);

  useEffect(() => {
    resetControlsTimeout();
    return () => {
      if (controlsTimeoutRef.current) clearTimeout(controlsTimeoutRef.current);
    };
  }, [resetControlsTimeout]);

  // Track playback time updates
  const handleTimeUpdate = () => {
    const video = videoRef.current;
    if (video) {
      const time = video.currentTime;
      setCurrentTime(time);
      if (video.duration) {
        setDuration(video.duration);
      }

      // Save resume position every 5 seconds
      if (Math.floor(time) % 5 === 0 && time > 1) {
        try {
          localStorage.setItem(resumeKey, String(time));
        } catch {}
      }

      // Check active skip times
      if (skipTimes.length > 0) {
        const matchingSkip = skipTimes.find(s => time >= s.start && time < s.end);
        if (matchingSkip) {
          setActiveSkip(matchingSkip);
          if (autoSkipEnabled) {
            console.log(`[AniSkip] Auto-skipping ${matchingSkip.type} from ${time}s to ${matchingSkip.end}s`);
            handleSeek(matchingSkip.end);
            return;
          }
        } else {
          setActiveSkip(null);
        }
      } else {
        setActiveSkip(null);
      }
    }
  };

  const handleTogglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (isPlaying) {
      video.pause();
      setIsPlaying(false);
    } else {
      video.play().catch(console.error);
      setIsPlaying(true);
    }
    resetControlsTimeout();
  }, [isPlaying, resetControlsTimeout]);

  const handleSeek = (time: number) => {
    const video = videoRef.current;
    if (video) {
      const newTime = Math.max(0, Math.min(duration, time));
      video.currentTime = newTime;
      setCurrentTime(newTime);
      resetControlsTimeout();
    }
  };

  const handleVolumeChange = (newVal: number) => {
    const vol = Math.max(0, Math.min(1, newVal));
    setVolume(vol);
    setIsMuted(vol === 0);
    localStorage.setItem("anicat_player_volume", vol.toString());
    localStorage.setItem("anicat_player_muted", (vol === 0).toString());
    resetControlsTimeout();
  };

  const handleToggleMute = () => {
    const newMute = !isMuted;
    setIsMuted(newMute);
    localStorage.setItem("anicat_player_muted", newMute.toString());
    resetControlsTimeout();
  };

  const handleToggleFullscreen = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    if (!document.fullscreenElement) {
      if (container.requestFullscreen) {
        container.requestFullscreen();
      } else if ((container as any).webkitRequestFullscreen) {
        (container as any).webkitRequestFullscreen();
      } else if ((container as any).mozRequestFullScreen) {
        (container as any).mozRequestFullScreen();
      } else if ((container as any).msRequestFullscreen) {
        (container as any).msRequestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if ((document as any).webkitExitFullscreen) {
        (document as any).webkitExitFullscreen();
      } else if ((document as any).mozCancelFullScreen) {
        (document as any).mozCancelFullScreen();
      } else if ((document as any).msExitFullscreen) {
        (document as any).msExitFullscreen();
      }
    }
    resetControlsTimeout();
  }, [resetControlsTimeout]);

  const handleTogglePip = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;

    try {
      if (document.pictureInPictureElement) {
        document.exitPictureInPicture();
      } else if (document.pictureInPictureEnabled) {
        video.requestPictureInPicture();
      }
    } catch (e) {
      console.warn("[Player] Picture-in-Picture not supported:", e);
    }
  }, []);

  const handleClose = useCallback(() => {
    const video = videoRef.current;
    if (video && video.duration && resolved) {
      mediaApi.trackPlayback(mediaId, episodeNumber, video.currentTime, video.duration)
        .catch(console.error)
        .finally(() => onClose());
    } else {
      onClose();
    }
  }, [resolved, mediaId, episodeNumber, onClose]);

  const handleOpenExternalMpv = () => {
    mediaApi.play(mediaId, episodeNumber)
      .then(() => onClose())
      .catch(err => {
        console.error("Failed to spawn MPV:", err);
        alert("Failed to spawn MPV. Make sure it is installed and compiled correctly.");
      });
  };

  // Keyboard controls listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (document.activeElement?.tagName === "INPUT" || document.activeElement?.tagName === "SELECT") {
        return;
      }

      switch (e.key) {
        case " ":
          e.preventDefault();
          handleTogglePlay();
          break;
        case "ArrowRight":
          e.preventDefault();
          handleSeek(currentTime + 10);
          break;
        case "ArrowLeft":
          e.preventDefault();
          handleSeek(currentTime - 10);
          break;
        case "ArrowUp":
          e.preventDefault();
          handleVolumeChange(volume + 0.05);
          break;
        case "ArrowDown":
          e.preventDefault();
          handleVolumeChange(volume - 0.05);
          break;
        case "f":
        case "F":
          e.preventDefault();
          handleToggleFullscreen();
          break;
        case "m":
        case "M":
          e.preventDefault();
          handleToggleMute();
          break;
        case "Escape":
          e.preventDefault();
          if (document.fullscreenElement) {
            document.exitFullscreen();
          } else {
            handleClose();
          }
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleTogglePlay, currentTime, volume, handleToggleFullscreen, handleToggleMute, handleClose, duration]);

  // Format seconds to HH:MM:SS or MM:SS
  const formatTime = (secs: number) => {
    if (isNaN(secs)) return "00:00";
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = Math.floor(secs % 60);

    const formattedM = m.toString().padStart(2, "0");
    const formattedS = s.toString().padStart(2, "0");

    if (h > 0) {
      return `${h}:${formattedM}:${formattedS}`;
    }
    return `${formattedM}:${formattedS}`;
  };

  return (
    <div
      ref={containerRef}
      onMouseMove={resetControlsTimeout}
      onMouseLeave={() => isPlaying && setShowControls(false)}
      className="fixed inset-0 z-[200] bg-[#050505] flex flex-col items-center justify-center select-none overflow-hidden transform-gpu will-change-[transform,opacity]"
    >
      {loading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/90 space-y-4 z-40">
          <Loader2 className="animate-spin text-accent" size={48} />
          <p className="text-sm font-semibold tracking-wider text-white/60">RESOLVING SECURE SERVERS...</p>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/95 space-y-5 z-40 p-6 text-center">
          <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center border border-red-500/20 text-red-500">
            <X size={32} />
          </div>
          <div className="space-y-1.5 max-w-sm">
            <h3 className="text-lg font-bold text-white">Stream Error</h3>
            <p className="text-xs text-gray-500 leading-relaxed">{error}</p>
          </div>
          <div className="flex space-x-3 pt-2">
            <button
              onClick={handleClose}
              className="px-5 py-2.5 bg-white/[0.04] border border-white/5 hover:bg-white/[0.08] text-white rounded-xl text-xs font-bold transition-all"
            >
              Exit Player
            </button>
            <button
              onClick={handleOpenExternalMpv}
              className="px-5 py-2.5 bg-accent hover:bg-accent-light text-white rounded-xl text-xs font-bold transition-all flex items-center space-x-2"
            >
              <Video size={14} />
              <span>Launch in MPV</span>
            </button>
          </div>
        </div>
      )}

      {/* Main Video Element */}
      <video
        ref={videoRef}
        onClick={handleTogglePlay}
        onTimeUpdate={handleTimeUpdate}
        onDurationChange={handleTimeUpdate}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onPlaying={() => {
          setIsPlaying(true);
          setLoading(false);
        }}
        onWaiting={() => setLoading(true)}
        onLoadedData={() => setLoading(false)}
        onEnded={() => {
          setIsPlaying(false);
          const video = videoRef.current;
          if (video && video.duration) {
            mediaApi.trackPlayback(mediaId, episodeNumber, video.duration, video.duration)
              .then(res => {
                if (onEpisodeCompleted) {
                  onEpisodeCompleted(episodeNumber);
                }
                const isFinal = totalEpisodes ? parseInt(episodeNumber, 10) === totalEpisodes : !hasNextEpisode;
                if (isFinal) {
                  setShowRatingModal(true);
                } else if (hasNextEpisode && onPlayNextEpisode) {
                  setAutoplayCountdown(8); // Start 8s countdown
                }
              })
              .catch(console.error);
          }
        }}
        className={`w-full h-full object-contain cursor-pointer bg-black transform-gpu will-change-[transform,opacity] ${resolved ? "block" : "hidden"}`}
        playsInline
      />

      {/* Glassmorphic Top Controls Bar */}
      <div
        className={`absolute top-0 inset-x-0 p-5 bg-gradient-to-b from-black/80 to-transparent flex items-center justify-between transition-all duration-500 z-30 ${
          showControls ? "translate-y-0 opacity-100" : "-translate-y-full opacity-0 pointer-events-none"
        }`}
      >
        <div className="flex flex-col space-y-1">
          <h2 className="text-lg font-extrabold text-white tracking-wide drop-shadow-md">
            {resolved ? resolved.title : "Streaming Media"}
          </h2>
          <p className="text-xs font-semibold text-accent tracking-widest drop-shadow-md">
            EPISODE {resolved ? resolved.episode : episodeNumber}
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleOpenExternalMpv}
            title="Upscale & watch using your local GPU-accelerated MPV client"
            className="flex items-center space-x-2 px-4 py-2 bg-white/[0.06] hover:bg-white/[0.12] active:scale-95 text-white/90 rounded-xl text-xs font-bold transition-all border border-white/5 shadow-md shadow-black/20"
          >
            <Video size={14} className="text-accent" />
            <span>Open in MPV</span>
          </button>

          <button
            onClick={handleClose}
            className="p-3 bg-white/[0.06] hover:bg-white/[0.12] active:scale-95 text-white rounded-xl transition-all border border-white/5 shadow-md shadow-black/20"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Giant Center Play/Pause Indicator */}
      <div
        onClick={handleTogglePlay}
        className={`absolute inset-0 flex items-center justify-center bg-black/10 z-20 cursor-pointer transition-opacity duration-300 ${
          !isPlaying && showControls ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      >
        <div className="w-20 h-20 rounded-full bg-black/40 backdrop-blur-md border border-white/10 flex items-center justify-center text-accent hover:scale-110 hover:text-white transition-all shadow-2xl">
          <Play size={32} fill="currentColor" className="ml-1" />
        </div>
      </div>

      {/* Glassmorphic Footer Controls Bar */}
      <div
        onMouseEnter={() => setIsHoveredControls(true)}
        onMouseLeave={() => {
          setIsHoveredControls(false);
          resetControlsTimeout();
        }}
        className={`absolute bottom-0 inset-x-0 p-6 bg-gradient-to-t from-black/90 to-transparent flex flex-col space-y-4 transition-all duration-500 z-30 ${
          showControls ? "translate-y-0 opacity-100" : "translate-y-full opacity-0 pointer-events-none"
        }`}
      >
        {/* Seek timeline progress bar */}
        <div className="group flex items-center space-x-3 w-full cursor-pointer">
          <span className="text-[10px] font-mono text-white/60 select-none">
            {formatTime(currentTime)}
          </span>

          <input
            type="range"
            min={0}
            max={duration || 100}
            value={currentTime}
            onChange={(e) => handleSeek(parseFloat(e.target.value))}
            className="flex-1 h-1.5 bg-white/10 hover:h-2 rounded-lg appearance-none cursor-pointer outline-none accent-accent transition-all progress-slider-accent"
            style={{
              background: `linear-gradient(to right, var(--color-accent) 0%, var(--color-accent) ${
                duration ? (currentTime / duration) * 100 : 0
              }%, rgba(255,255,255,0.1) ${
                duration ? (currentTime / duration) * 100 : 0
              }%, rgba(255,255,255,0.1) 100%)`
            }}
          />

          <span className="text-[10px] font-mono text-white/60 select-none">
            {formatTime(duration)}
          </span>
        </div>

        {/* Media Buttons Row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <button
              onClick={handleTogglePlay}
              className="p-2.5 bg-accent hover:bg-accent-light active:scale-90 text-white rounded-full transition-all shadow-md shadow-accent/20"
            >
              {isPlaying ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" className="ml-0.5" />}
            </button>

            <button
              onClick={() => handleSeek(currentTime - 10)}
              className="text-white/60 hover:text-white transition-colors"
              title="Rewind 10 seconds"
            >
              <RotateCcw size={18} />
            </button>

            {/* Volume and Slider */}
            <div className="flex items-center space-x-2 group/vol">
              <button
                onClick={handleToggleMute}
                className="text-white/60 hover:text-white transition-colors"
              >
                {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
              </button>
              
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={isMuted ? 0 : volume}
                onChange={(e) => handleVolumeChange(parseFloat(e.target.value))}
                className="w-0 group-hover/vol:w-16 h-1 bg-white/20 rounded-lg appearance-none cursor-pointer outline-none accent-white transition-all overflow-hidden duration-300"
              />
            </div>

            {/* Playback speed selector */}
            <div className="relative">
              <select
                value={playbackSpeed}
                onChange={(e) => {
                  const sp = parseFloat(e.target.value);
                  setPlaybackSpeed(sp);
                  if (videoRef.current) videoRef.current.playbackRate = sp;
                }}
                className="bg-white/[0.04] border border-white/5 rounded-lg px-2 py-1 text-[10px] font-extrabold text-white/80 cursor-pointer outline-none appearance-none hover:bg-white/[0.08] transition-all"
              >
                <option value="0.75" className="bg-[#050505]">0.75x</option>
                <option value="1" className="bg-[#050505]">1.0x</option>
                <option value="1.25" className="bg-[#050505]">1.25x</option>
                <option value="1.5" className="bg-[#050505]">1.5x</option>
                <option value="2" className="bg-[#050505]">2.0x</option>
              </select>
            </div>

            {/* Auto-Skip Toggle */}
            <div className="flex items-center">
              <button
                onClick={() => {
                  const newval = !autoSkipEnabled;
                  setAutoSkipEnabled(newval);
                  localStorage.setItem("anicat_auto_skip", newval.toString());
                }}
                className={`px-2.5 py-1 rounded-lg text-[9px] uppercase tracking-wider font-black transition-all border flex items-center space-x-1.5 active:scale-95 duration-200 ${
                  autoSkipEnabled
                    ? "bg-accent/10 border-accent/20 text-accent hover:bg-accent/20"
                    : "bg-white/[0.04] border-white/5 text-white/50 hover:text-white/80 hover:bg-white/[0.08]"
                }`}
                title="Automatically skip openings and endings using crowdsourced AniSkip times"
              >
                <span className={`w-1 h-1 rounded-full ${autoSkipEnabled ? 'bg-accent animate-pulse' : 'bg-white/30'}`} />
                <span>Auto-Skip</span>
              </button>
            </div>
          </div>

          <div className="flex items-center space-x-6">
            {hasNextEpisode && onPlayNextEpisode && (
              <button
                onClick={onPlayNextEpisode}
                className="flex items-center space-x-2 px-4 py-2 bg-accent/15 hover:bg-accent/25 active:scale-95 text-accent rounded-xl text-xs font-bold transition-all border border-accent/20 shadow-md shadow-accent/5"
              >
                <span>Next Episode</span>
                <ArrowRight size={14} />
              </button>
            )}

            <button
              onClick={handleTogglePip}
              className="text-white/60 hover:text-white transition-colors"
              title="Picture in Picture"
            >
              <PictureInPicture2 size={18} />
            </button>

            <button
              onClick={handleToggleFullscreen}
              className="text-white/60 hover:text-white transition-colors"
            >
              {isFullscreen ? <Minimize size={18} /> : <Maximize size={18} />}
            </button>
          </div>
        </div>
      </div>

      {/* Skip Intro/Outro Overlay Button */}
      {activeSkip && (
        <button
          onClick={() => handleSeek(activeSkip.end)}
          className="absolute bottom-24 right-8 z-[240] flex items-center space-x-2 px-5 py-3 bg-black/60 hover:bg-black/85 backdrop-blur-xl border border-white/10 text-white font-extrabold rounded-xl shadow-2xl transition-all active:scale-95 animate-fade-in text-xs uppercase tracking-widest cursor-pointer group"
        >
          <span>Skip {activeSkip.type === 'op' ? 'Intro' : 'Outro'}</span>
          <ArrowRight size={14} className="text-accent group-hover:translate-x-1 transition-transform" />
        </button>
      )}

      {/* End-of-Series Rating Modal */}
      {showRatingModal && (
        <div className="absolute inset-0 bg-black/80 backdrop-blur-2xl z-[250] flex items-center justify-center p-6 animate-fade-in select-none">
          <div className="max-w-md w-full bg-white/[0.02] border border-white/[0.08] rounded-3xl p-8 space-y-6 shadow-2xl text-center relative overflow-hidden transform-gpu will-change-[transform,opacity] scale-in">
            {/* Ambient gold glow */}
            <div className="absolute -top-16 -left-16 w-32 h-32 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute -bottom-16 -right-16 w-32 h-32 bg-accent/10 rounded-full blur-3xl pointer-events-none" />

            <div className="space-y-2">
              <span className="text-[10px] font-black text-amber-400 uppercase tracking-[0.2em]">Series Completed 🎉</span>
              <h2 className="text-2xl font-black text-white leading-tight">
                {resolved ? resolved.title : "Congratulations!"}
              </h2>
              <p className="text-xs text-gray-500 max-w-xs mx-auto leading-relaxed">
                You've watched the final episode! How would you rate this series on AniList?
              </p>
            </div>

            {/* Stars Row (1 to 10) */}
            <div className="flex items-center justify-center space-x-1.5 py-4">
              {[...Array(10)].map((_, index) => {
                const starVal = index + 1;
                return (
                  <button
                    key={starVal}
                    onClick={() => setUserRating(starVal)}
                    className="p-1 transition-all active:scale-75 hover:scale-125 cursor-pointer"
                    title={`${starVal} / 10`}
                  >
                    <svg
                      className={`w-6 h-6 transition-all ${
                        userRating && starVal <= userRating
                          ? "text-amber-400 fill-amber-400 drop-shadow-[0_0_8px_rgba(245,158,11,0.5)]"
                          : "text-gray-700 fill-transparent hover:text-amber-400/60"
                      }`}
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.907c.969 0 1.371 1.24.588 1.81l-3.97 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.971-2.888a1 1 0 00-1.176 0l-3.97 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.97-2.888c-.784-.57-.38-1.81.588-1.81h4.907a1 1 0 00.95-.69l1.519-4.674z"
                      />
                    </svg>
                  </button>
                );
              })}
            </div>

            {/* Selected score label */}
            {userRating !== null && (
              <div className="text-sm font-extrabold text-amber-400 animate-pulse">
                Score: {userRating} / 10 ({userRating <= 4 ? "Weak" : userRating <= 6 ? "Decent" : userRating <= 8 ? "Great!" : "Masterpiece! 🏆"})
              </div>
            )}

            {/* Buttons Row */}
            <div className="flex flex-col space-y-2 pt-2">
              <button
                onClick={async () => {
                  if (userRating === null) return;
                  setIsSubmittingRating(true);
                  try {
                    await mediaApi.updateStatus(mediaId, "completed", userRating);
                    setRatingSuccess(true);
                    setTimeout(() => {
                      setIsSubmittingRating(false);
                      setShowRatingModal(false);
                      handleClose();
                    }, 1200);
                  } catch (e) {
                    console.error("Failed to submit rating:", e);
                    setIsSubmittingRating(false);
                    alert("Failed to submit rating. List entry updated without score.");
                    setShowRatingModal(false);
                    handleClose();
                  }
                }}
                disabled={userRating === null || isSubmittingRating}
                className="w-full py-3.5 bg-accent hover:bg-accent-light disabled:opacity-30 disabled:pointer-events-none text-white font-extrabold rounded-2xl transition-all active:scale-95 text-xs uppercase tracking-widest shadow-lg shadow-accent/20 cursor-pointer flex items-center justify-center space-x-2"
              >
                {isSubmittingRating ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    <span>{ratingSuccess ? "Syncing completed!" : "Syncing list entry..."}</span>
                  </>
                ) : (
                  <span>Rate & Mark Completed</span>
                )}
              </button>

              <button
                onClick={() => {
                  setShowRatingModal(false);
                  handleClose();
                }}
                disabled={isSubmittingRating}
                className="w-full py-3 bg-white/[0.04] hover:bg-white/[0.08] text-gray-400 hover:text-white font-bold rounded-2xl transition-all active:scale-95 text-xs tracking-wider cursor-pointer"
              >
                Skip & Exit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Netflix-Style Auto-Play Countdown Overlay */}
      {autoplayCountdown !== null && (
        <div className="absolute inset-0 bg-black/85 backdrop-blur-2xl z-[250] flex items-center justify-center p-6 animate-fade-in select-none">
          <div className="max-w-sm w-full bg-white/[0.02] border border-white/[0.08] rounded-3xl p-8 space-y-6 shadow-2xl text-center relative overflow-hidden transform-gpu will-change-[transform,opacity] scale-in">
            {/* Ambient accent pulse */}
            <div className="absolute -top-16 -left-16 w-32 h-32 bg-accent/15 rounded-full blur-3xl pointer-events-none animate-pulse" />
            <div className="absolute -bottom-16 -right-16 w-32 h-32 bg-accent/10 rounded-full blur-3xl pointer-events-none animate-pulse" />

            <div className="space-y-2">
              <span className="text-[10px] font-black text-accent uppercase tracking-[0.2em] animate-pulse">Up Next 🎬</span>
              <h2 className="text-2xl font-black text-white leading-tight">
                Episode {!isNaN(parseInt(episodeNumber, 10)) ? parseInt(episodeNumber, 10) + 1 : "Next Episode"}
              </h2>
              <p className="text-xs text-gray-500 max-w-xs mx-auto leading-relaxed">
                Starting in <span className="font-extrabold text-accent text-sm animate-ping duration-1000 inline-block w-4">{autoplayCountdown}</span> seconds...
              </p>
            </div>

            {/* Circular progress loader representation */}
            <div className="relative w-20 h-20 mx-auto flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                {/* Background ring */}
                <circle
                  cx="40"
                  cy="40"
                  r="34"
                  className="stroke-white/[0.04]"
                  strokeWidth="4"
                  fill="transparent"
                />
                {/* Active progress ring */}
                <circle
                  cx="40"
                  cy="40"
                  r="34"
                  className="stroke-accent transition-all duration-1000 ease-linear"
                  strokeWidth="4"
                  fill="transparent"
                  strokeDasharray="213.6"
                  strokeDashoffset={213.6 - (213.6 * autoplayCountdown) / 8}
                />
              </svg>
              {/* Play icon in center */}
              <div className="absolute inset-0 flex items-center justify-center text-accent">
                <Play size={20} fill="currentColor" className="ml-0.5" />
              </div>
            </div>

            {/* Buttons Row */}
            <div className="flex flex-col space-y-2 pt-2">
              <button
                onClick={() => {
                  setAutoplayCountdown(null);
                  if (onPlayNextEpisode) onPlayNextEpisode();
                }}
                className="w-full py-3.5 bg-accent hover:bg-accent-light text-white font-extrabold rounded-2xl transition-all active:scale-95 text-xs uppercase tracking-widest shadow-lg shadow-accent/20 cursor-pointer"
              >
                Play Now
              </button>

              <button
                onClick={() => setAutoplayCountdown(null)}
                className="w-full py-3 bg-white/[0.04] hover:bg-white/[0.08] text-gray-400 hover:text-white font-bold rounded-2xl transition-all active:scale-95 text-xs tracking-wider cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
