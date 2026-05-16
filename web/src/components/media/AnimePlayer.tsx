"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { X, Play, Pause, RotateCcw, Volume2, VolumeX, Maximize, Minimize, Loader2, ArrowRight, Video } from "lucide-react";
import { API_BASE_ORIGIN, mediaApi } from "@/lib/api";

interface AnimePlayerProps {
  mediaId: number;
  episodeNumber: string;
  onClose: () => void;
  onEpisodeCompleted?: (episodeNum: string) => void;
  onPlayNextEpisode?: () => void;
  hasNextEpisode?: boolean;
}

export default function AnimePlayer({
  mediaId,
  episodeNumber,
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
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [isHoveredControls, setIsHoveredControls] = useState(false);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const controlsTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Load volume preference
  useEffect(() => {
    const savedVol = localStorage.getItem("anicat_player_volume");
    if (savedVol !== null) {
      setVolume(parseFloat(savedVol));
    }
    const savedMuted = localStorage.getItem("anicat_player_muted");
    if (savedMuted !== null) {
      setIsMuted(savedMuted === "true");
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
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to resolve stream:", err);
        setError("Failed to locate high-quality video servers. Try again shortly.");
        setLoading(false);
      });
  }, [mediaId, episodeNumber]);

  // Synchronize dynamic HLS.js streaming
  useEffect(() => {
    if (!resolved) return;
    const video = videoRef.current;
    if (!video) return;

    import("hls.js").then((M) => {
      const Hls = M.default;
      if (Hls.isSupported()) {
        if (hlsRef.current) {
          hlsRef.current.destroy();
        }

        const hls = new Hls({
          maxMaxBufferLength: 30,
          enableWorker: true,
          lowLatencyMode: true
        });
        hlsRef.current = hls;

        const streamUrl = `${API_BASE_ORIGIN}${resolved.stream_url}`;
        hls.loadSource(streamUrl);
        hls.attachMedia(video);

        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          if (resolved.start_time) {
            video.currentTime = resolved.start_time;
          }
          video.play()
            .then(() => setIsPlaying(true))
            .catch(() => setIsPlaying(false));
        });

        hls.on(Hls.Events.ERROR, (event, data) => {
          if (data.fatal) {
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                hls.startLoad();
                break;
              case Hls.ErrorTypes.MEDIA_ERROR:
                hls.recoverMediaError();
                break;
              default:
                setError("Streaming connection was unexpectedly closed.");
                break;
            }
          }
        });
      } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
        // Safari fallback
        const streamUrl = `${API_BASE_ORIGIN}${resolved.stream_url}`;
        video.src = streamUrl;
        video.addEventListener("loadedmetadata", () => {
          if (resolved.start_time) {
            video.currentTime = resolved.start_time;
          }
          video.play()
            .then(() => setIsPlaying(true))
            .catch(() => setIsPlaying(false));
        });
      } else {
        setError("Playback format is not supported by your system.");
      }
    });

    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
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
            }
          })
          .catch(console.error);
      }
    }, 10000); // Track progress every 10s

    return () => clearInterval(interval);
  }, [resolved, isPlaying, mediaId, episodeNumber, onEpisodeCompleted]);

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
      setCurrentTime(video.currentTime);
      if (video.duration) {
        setDuration(video.duration);
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
      className="fixed inset-0 z-50 bg-[#050505] flex flex-col items-center justify-center select-none overflow-hidden"
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
      {resolved && (
        <video
          ref={videoRef}
          onClick={handleTogglePlay}
          onTimeUpdate={handleTimeUpdate}
          onDurationChange={handleTimeUpdate}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          className="w-full h-full object-contain cursor-pointer"
          playsInline
        />
      )}

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
              onClick={handleToggleFullscreen}
              className="text-white/60 hover:text-white transition-colors"
            >
              {isFullscreen ? <Minimize size={18} /> : <Maximize size={18} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
