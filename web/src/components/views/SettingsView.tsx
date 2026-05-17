"use client";

import { useState, useEffect } from "react";
import { Loader2, CheckCircle2, Save, Cpu, PlayCircle, HardDrive, Globe, Activity, RotateCcw, XCircle, AlertCircle, Download } from "lucide-react";
import { mediaApi, type HealthStatus, API_BASE_ORIGIN } from "@/lib/api";
import ErrorBanner from "@/components/ErrorBanner";

interface SettingsViewProps {
  health: HealthStatus | null;
  onUpdateStarted?: (message?: string) => void;
}

export default function SettingsView({ health, onUpdateStarted }: SettingsViewProps) {
  const [config, setConfig] = useState<Record<string, Record<string, unknown>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState<"general" | "stream" | "downloads" | "anilist" | "registry" | "maintenance">("general");
  const [registryStats, setRegistryStats] = useState<any>(null);
  const [backingUp, setBackingUp] = useState(false);
  const [backupUrl, setBackupUrl] = useState<string | null>(null);
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [stagedHasUpdate, setStagedHasUpdate] = useState(health?.update_available || false);
  const [updateMessage, setUpdateMessage] = useState<{ text: string; type: "success" | "error" | null }>({ text: "", type: null });
  const [options, setOptions] = useState<Record<string, any> | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const hasUpdate = Boolean(health?.update_available || stagedHasUpdate);

  useEffect(() => {
    mediaApi.getConfig()
      .then(setConfig)
      .catch(console.error)
      .finally(() => setLoading(false));
    // Fetch server-supported option lists for UI selects
    mediaApi.getConfigOptions().then(setOptions).catch(() => {/* ignore */});
  }, []);

  const handleOpenLogs = async () => {
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("open_logs_folder");
    } catch (err) {
      console.error("Failed to open logs:", err);
      setErrorMessage("Could not open logs folder automatically.");
      setTimeout(() => setErrorMessage(null), 6000);
    }
  };

  const handleUpdate = async () => {
    setCheckingUpdate(true);
    setUpdateMessage({ text: "", type: null });
    try {
      if (!hasUpdate) {
        // If we don't know of an update yet, check for one first!
        const res = await mediaApi.checkUpdate();
        if (res.status === "success") {
          setStagedHasUpdate(res.update_available);
          setUpdateMessage({ text: res.message, type: "success" });
        } else {
          setUpdateMessage({ text: res.message, type: "error" });
        }
      } else {
        // If we already know there is an update, trigger the installation!
        const res = await mediaApi.triggerUpdate();
        if (res.status === "success") {
          setStagedHasUpdate(false);
          if (onUpdateStarted) {
            onUpdateStarted(res.message);
          }
        } else {
          setUpdateMessage({ text: res.message, type: "error" });
        }
      }
    } catch (err) {
      console.error("Update failed:", err);
      setUpdateMessage({ text: "Failed to process update action.", type: "error" });
    } finally {
      setCheckingUpdate(false);
    }
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await mediaApi.updateConfig(config);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err: any) {
      console.error("Save failed:", err);
      // Attempt to show structured server errors if present
      const msg = err?.message || "Unknown error";
      setErrorMessage("Save failed: " + msg);
      setTimeout(() => setErrorMessage(null), 6000);
    } finally {
      setSaving(false);
    }
  };

  const updateField = (section: string, field: string, value: unknown) => {
    setConfig(prev => prev ? {
      ...prev,
      [section]: { ...prev[section], [field]: value }
    } : null);
  };

  useEffect(() => {
    if (activeTab === "registry" && !registryStats) {
      mediaApi.getRegistryStats().then(setRegistryStats).catch(console.error);
    }
  }, [activeTab, registryStats]);

  const handleBackup = async () => {
    setBackingUp(true);
    setBackupUrl(null);
    try {
      await mediaApi.triggerBackup();
      setBackupUrl(`${API_BASE_ORIGIN}/api/registry/backup/download`);
    } finally {
      setBackingUp(false);
    }
  };

  if (loading || !config) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-accent" size={36} />
      </div>
    );
  }

  const tabs = [
    { id: "general", label: "Core", icon: Cpu },
    { id: "stream", label: "Streaming", icon: PlayCircle },
    { id: "downloads", label: "Downloads", icon: HardDrive },
    { id: "anilist", label: "AniList", icon: Globe },
    { id: "registry", label: "Registry", icon: Activity },
    { id: "maintenance", label: "Maintenance", icon: RotateCcw },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {errorMessage && <ErrorBanner message={errorMessage} />}
      <div className="flex items-end justify-between">
        <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight text-white">Settings</h1>
        <button
          onClick={handleSave}
          disabled={saving}
          className={`flex items-center space-x-2 px-6 py-3 rounded-xl font-bold text-sm transition-all active:scale-95 ${
            saved
              ? "bg-green-500 text-white"
              : "bg-accent text-white hover:bg-accent-light shadow-lg shadow-accent/20"
          }`}
        >
          {saving ? <Loader2 size={16} className="animate-spin" /> : saved ? <CheckCircle2 size={16} /> : <Save size={16} />}
          <span>{saved ? "Saved!" : "Save"}</span>
        </button>
      </div>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Tab nav */}
        <div className="lg:w-52 flex lg:flex-col space-x-2 lg:space-x-0 lg:space-y-1 overflow-x-auto scrollbar-hide shrink-0">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center space-x-3 px-4 py-3 rounded-xl font-semibold text-sm whitespace-nowrap transition-all ${
                activeTab === tab.id
                  ? "bg-accent text-white shadow-lg"
                  : "text-gray-500 hover:text-white hover:bg-white/[0.04]"
              }`}
            >
              <tab.icon size={17} />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Settings form */}
        <div className="flex-1 space-y-6 max-w-2xl">
          {activeTab === "general" && (
            <div className="space-y-6 animate-fade-in">
              <SettingField
                label="Anime Provider"
                description="Where to scrape video content from."
              >
                <select
                  value={String(config.general?.provider || "animepahe")}
                  onChange={(e) => updateField("general", "provider", e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
                >
                  <option value="animepahe">AnimePahe (Standard)</option>
                </select>
              </SettingField>

              <SettingField
                label="Manga Provider"
                description="Where to scrape manga chapters from."
              >
                <select
                  value={String(config.general?.manga_provider || "mangakatana")}
                  onChange={(e) => updateField("general", "manga_provider", e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
                >
                  <option value="mangakatana">MangaKatana (High Speed)</option>
                </select>
              </SettingField>

              <SettingField
                label="Media Tracker"
                description="The source for your list and metadata."
              >
                <select
                  value={String(config.general?.media_api || "anilist")}
                  onChange={(e) => updateField("general", "media_api", e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
                >
                  <option value="anilist">AniList</option>
                  <option value="jikan">Jikan / MyAnimeList</option>
                </select>
              </SettingField>

              <SettingField
                label="Time Format"
                description="How dates and times should be displayed."
              >
                <select
                  value={String(config.general?.time_format || "12h")}
                  onChange={(e) => updateField("general", "time_format", e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
                >
                  <option value="12h">12-hour (AM/PM)</option>
                  <option value="24h">24-hour</option>
                </select>
              </SettingField>

              <SettingField
                label="Update Branch"
                description="Choose whether to fetch updates from the stable or nightly development branch."
              >
                <select
                  value={String(config.general?.update_branch || "stable")}
                  onChange={(e) => updateField("general", "update_branch", e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
                >
                  <option value="stable">Stable (main branch)</option>
                  <option value="nightly">Nightly (nightly branch)</option>
                </select>
              </SettingField>
            </div>
          )}

          {activeTab === "stream" && (
            <div className="space-y-6 animate-fade-in">
              <SettingField label="Quality" description="Preferred playback quality.">
                <select
                  value={String(config.stream?.quality || "1080")}
                  onChange={(e) => updateField("stream", "quality", e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
                >
                  {(options?.stream?.quality ?? ["1080", "720", "480", "360"]).map((q: string) => (
                    <option key={q} value={q}>{q.endsWith('p') ? q : `${q}p`}</option>
                  ))}
                </select>
              </SettingField>

              <SettingField label="Translation Type" description="Sub or dub.">
                <select
                  value={String(config.stream?.translation_type || "sub")}
                  onChange={(e) => updateField("stream", "translation_type", e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
                >
                  <option value="sub">Subtitled (JP)</option>
                  <option value="dub">Dubbed (EN)</option>
                </select>
              </SettingField>

              <SettingField label="Player Type" description="Choose between native cinematic in-app player or external MPV.">
                <select
                  value={String(config.stream?.player_type || "embedded")}
                  onChange={(e) => updateField("stream", "player_type", e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all appearance-none cursor-pointer"
                >
                  {(options?.stream?.player_type ?? ["embedded", "external"]).map((p: string) => (
                    <option key={p} value={p}>{p === 'embedded' ? 'Embedded Cinematic Overlay (In-App HLS)' : 'External Media Player (MPV client with Anime4K upscaling)'}</option>
                  ))}
                </select>
              </SettingField>
            </div>
          )}

          {activeTab === "downloads" && (
            <div className="space-y-6 animate-fade-in">
              <SettingField label="Downloads Directory" description="Where downloaded media is stored on disk.">
                <div className="relative">
                  <HardDrive size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600" />
                  <input
                    type="text"
                    value={String(config.downloads?.downloads_dir || "")}
                    onChange={(e) => updateField("downloads", "downloads_dir", e.target.value)}
                    className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl py-3.5 pl-11 pr-4 text-sm font-medium focus:border-accent/40 outline-none transition-all"
                  />
                </div>
              </SettingField>
            </div>
          )}

          {activeTab === "anilist" && (
            <div className="space-y-6 animate-fade-in">
              <SettingField label="AniList Token" description="Your AniList API token for authentication.">
                <input
                  type="password"
                  value={String(config.anilist?.token || "")}
                  onChange={(e) => updateField("anilist", "token", e.target.value)}
                  placeholder="Paste your token here..."
                  className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl p-3.5 text-sm font-medium focus:border-accent/40 outline-none transition-all placeholder:text-gray-700"
                />
                <button
                  id="logout-btn"
                  data-confirmed="false"
                  onClick={async () => {
                    const btn = document.getElementById('logout-btn');
                    if (btn?.getAttribute('data-confirmed') === 'true') {
                      // Direct logout to avoid state racing
                      mediaApi.updateConfig({ anilist: { token: "" } })
                        .then(() => window.location.reload())
                        .catch(err => {
                          console.error("Logout failed:", err);
                          alert("Logout failed. Please try again.");
                        });
                    } else {
                      if (btn) {
                        btn.setAttribute('data-confirmed', 'true');
                        btn.innerHTML = '<span>Are you sure? Click again to Logout</span>';
                        btn.className = "mt-2 text-xs font-bold text-red-400 transition-colors flex items-center space-x-1";
                      }
                    }
                  }}
                  className="mt-2 text-xs font-bold text-red-400/60 hover:text-red-400 transition-colors flex items-center space-x-1"
                >
                  <XCircle size={12} />
                  <span>Logout from AniList</span>
                </button>
              </SettingField>
            </div>
          )}

          {activeTab === "maintenance" && (
            <div className="space-y-8 animate-fade-in">
              {/* Application Update */}
              <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-white">Application Update</h3>
                    <p className="text-sm text-gray-500 mt-1">Check for the latest features and bug fixes.</p>
                  </div>
                  <div className="px-3 py-1 bg-white/[0.04] rounded-lg border border-white/[0.1] text-[10px] font-mono text-gray-400">
                    {health?.current_version || "v1.2.4"}
                  </div>
                </div>
                <div className="flex flex-col space-y-3 pt-2">
                  <button
                    onClick={handleUpdate}
                    disabled={checkingUpdate}
                    className={`flex items-center justify-center space-x-2 py-3 rounded-xl font-bold transition-all shadow-lg shadow-accent/20 disabled:opacity-50 ${
                      hasUpdate ? "bg-green-600 hover:bg-green-500 text-white shadow-green-500/20" : "bg-accent text-white hover:bg-accent-light"
                    }`}
                  >
                    {checkingUpdate ? <Loader2 size={16} className="animate-spin" /> : hasUpdate ? <Download size={16} /> : <RotateCcw size={16} />}
                    <span>{checkingUpdate ? (hasUpdate ? "Updating..." : "Checking...") : hasUpdate ? "Install Update" : "Check for Updates"}</span>
                  </button>
                  {updateMessage.text && (
                    <div className={`p-3 rounded-xl text-xs font-semibold flex items-center space-x-2 animate-fade-in ${
                      updateMessage.type === "success" ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"
                    }`}>
                      {updateMessage.type === "success" ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                      <span>{updateMessage.text}</span>
                    </div>
                  )}
                  <p className="text-[10px] text-center text-gray-600">Build: {new Date().toLocaleDateString()}</p>
                </div>
              </div>

              {/* Debugging & Logs */}
              <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-bold text-white">Technical Diagnostics</h3>
                  <button 
                    onClick={async () => {
                      try {
                        const logs = await mediaApi.getLogs(50);
                        const report = [
                          `Anicat Version: ${health?.current_version || "unknown"}`,
                          `Platform: ${window.navigator.platform}`,
                          `User Agent: ${window.navigator.userAgent}`,
                          `API Connected: ${health?.api_connected}`,
                          `API Authenticated: ${health?.api_authenticated}`,
                          `Is Offline: ${health?.is_offline}`,
                          `Data Version: ${health?.data_version}`,
                          `Timestamp: ${new Date().toISOString()}`,
                          `\n--- LATEST LOGS ---\n`,
                          logs.logs
                        ].join('\n');
                        await navigator.clipboard.writeText(report);
                        setErrorMessage("Debug report copied to clipboard!");
                        setTimeout(() => setErrorMessage(null), 4000);
                      } catch (err) {
                        setErrorMessage("Failed to generate report.");
                        setTimeout(() => setErrorMessage(null), 6000);
                      }
                    }}
                    className="text-[10px] font-bold text-accent hover:text-accent-light flex items-center space-x-1"
                  >
                    <Save size={12} />
                    <span>Copy Debug Report</span>
                  </button>
                </div>

                <div className="space-y-3">
                  <button 
                    onClick={handleOpenLogs}
                    className="w-full py-2.5 bg-white/[0.04] hover:bg-white/[0.07] text-white/70 rounded-xl text-xs font-bold transition-all border border-white/5 flex items-center justify-center space-x-2"
                  >
                    <HardDrive size={14} />
                    <span>Open Log Directory</span>
                  </button>

                  <div className="relative">
                    <pre className="w-full h-40 bg-black/40 rounded-xl p-3 text-[10px] font-mono text-gray-500 overflow-y-auto scrollbar-hide border border-white/5">
                      {health ? "Fetching latest logs..." : "Engine offline."}
                      <LogViewer />
                    </pre>
                  </div>
                </div>
              </div>

              {/* Danger Zone */}
              <div className="p-6 rounded-2xl bg-red-500/5 border border-red-500/10 space-y-4">
                <h3 className="text-lg font-bold text-red-400/80">Danger Zone</h3>
                
                <button
                  id="clear-registry-btn"
                  data-confirmed="false"
                  onClick={() => {
                    const btn = document.getElementById('clear-registry-btn');
                    if (btn?.getAttribute('data-confirmed') === 'true') {
                      mediaApi.wipeRegistry().then(() => {
                        if (btn) {
                          btn.innerHTML = 'Registry Wiped! Restarting...';
                          btn.className = "w-full py-3 bg-green-500/20 text-green-400 rounded-xl text-sm font-bold transition-all border border-green-500/30";
                          setTimeout(() => window.location.reload(), 1500);
                        }
                      });
                    } else {
                      if (btn) {
                        btn.setAttribute('data-confirmed', 'true');
                        btn.innerHTML = 'Are you sure? This will wipe your history!';
                        btn.className = "w-full py-3 bg-red-500/20 text-red-400 rounded-xl text-sm font-bold transition-all border border-red-500/30";
                      }
                    }
                  }}
                  className="w-full py-3 border border-red-500/20 text-red-400/60 rounded-xl text-sm font-bold hover:bg-red-500/10 transition-all"
                >
                  Clear Local Registry
                </button>
              </div>

              {/* Reset Setup */}
              <div className="pt-4 border-t border-white/[0.06]">
                <button 
                  onClick={() => {
                    const btn = document.getElementById('reset-onboarding-btn');
                    if (btn?.getAttribute('data-confirmed') === 'true') {
                      localStorage.removeItem("anicat_onboarding_seen");
                      window.location.reload();
                    } else {
                      if (btn) {
                        btn.setAttribute('data-confirmed', 'true');
                        btn.innerHTML = '<span>Are you sure? Click again to Reset</span>';
                        btn.className = "w-full py-3 px-4 rounded-xl bg-red-500/20 text-red-400 text-[10px] font-bold transition-all border border-red-500/30 flex items-center justify-center space-x-2";
                      }
                    }
                  }}
                  id="reset-onboarding-btn"
                  data-confirmed="false"
                  className="w-full py-3 px-4 rounded-xl bg-white/[0.03] hover:bg-white/[0.06] text-gray-400 text-[10px] font-bold transition-all border border-white/[0.08] flex items-center justify-center space-x-2"
                >
                  <RotateCcw size={12} />
                  <span>Reset Onboarding Setup</span>
                </button>
              </div>
            </div>
          )}

          {activeTab === "registry" && (
            <div className="space-y-6 animate-fade-in">
              <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.06] space-y-4">
                <h2 className="text-lg font-bold text-white">Registry Management</h2>
                <p className="text-sm text-gray-400">
                  Your registry stores offline metadata, playback progress, and download tracking.
                </p>
                <div className="pt-4 border-t border-white/[0.04]">
                  <button
                    onClick={handleBackup}
                    disabled={backingUp}
                    className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-accent text-white hover:bg-accent-light transition-all font-bold text-sm disabled:opacity-50"
                  >
                    {backingUp ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                    <span>{backingUp ? "Creating Backup..." : "Backup Registry"}</span>
                  </button>
                  {backupUrl && (
                    <a
                      href={backupUrl}
                      download
                      className="inline-flex items-center space-x-2 mt-4 px-5 py-2.5 rounded-xl bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30 transition-all font-bold text-sm"
                    >
                      <Download size={16} />
                      <span>Download Latest Backup</span>
                    </a>
                  )}
                </div>
              </div>

              {registryStats && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
                    <div className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2">Total Media</div>
                    <div className="text-3xl font-extrabold text-white">
                      {registryStats.registry?.total_media_breakdown?.total || 0}
                    </div>
                  </div>
                  <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
                    <div className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-2">Episodes Downloaded</div>
                    <div className="text-3xl font-extrabold text-white">
                      {registryStats.downloads?.downloaded || 0}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function LogViewer() {
  const [logs, setLogs] = useState<string>("");

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await mediaApi.getLogs(50);
        setLogs(res.logs);
      } catch (err) {
        setLogs("Could not fetch logs.");
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  return <div className="mt-2 text-gray-400 whitespace-pre-wrap">{logs}</div>;
}

function SettingField({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2.5 p-5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
      <label className="text-xs font-bold text-accent uppercase tracking-wider">{label}</label>
      {children}
      {description && <p className="text-[11px] text-gray-600">{description}</p>}
    </div>
  );
}
