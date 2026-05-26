const isBrowser = typeof window !== 'undefined';
const DEFAULT_API_PORT = 13370;
const DEFAULT_API_BASE_ORIGIN = `http://127.0.0.1:${DEFAULT_API_PORT}`;

export const API_BASE_ORIGIN = process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_BASE_ORIGIN;
export const API_BASE_URL = `${API_BASE_ORIGIN}/api`;

if (isBrowser) {
  console.log('API_BASE_URL:', API_BASE_URL);
}

export async function fetchFromApi(endpoint: string, options: RequestInit & { silent?: boolean; timeout?: number } = {}) {
  const { silent, timeout = 15000, ...fetchOptions } = options;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      },
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorData: any = {};
      try {
        errorData = await response.json();
      } catch (e) {
        // Ignored
      }
      const detail = errorData.detail ?? errorData.message ?? errorData ?? null;
      const message = detail ? (typeof detail === 'string' ? detail : JSON.stringify(detail)) : `API error: ${response.status} ${response.statusText}`;
      // UX-19: Only log errors for non-silent (user-initiated) requests
      if (!silent && isBrowser) {
        console.error('API ERROR', { endpoint, status: response.status, statusText: response.statusText, errorData });
      }
      throw new Error(`${endpoint} - ${message}`);
    }

    try {
      return await response.json();
    } catch (e) {
      return {};
    }
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}

// ─── Types ────────────────────────────────────────────

export type MediaItem = {
  id: number;
  id_mal?: number;
  type?: "ANIME" | "MANGA";
  title: {
    english?: string;
    romaji?: string;
  };
  cover_image: {
    large: string;
  };
  banner_image?: string;
  trailer?: {
    id: string;
    site: string;
    thumbnail_url?: string;
  };
  description?: string;
  episodes?: number;
  chapters?: number;
  duration?: number;
  status?: string;
  format?: string;
  genres?: string[];
  average_score?: number;
  popularity?: number;
  favourites?: number;
  season?: string;
  seasonYear?: number;
  studios?: { name: string; isAnimationStudio: boolean }[];
  tags?: { name: string; rank: number }[];
  next_airing?: {
    episode: number;
    airing_at?: string;
  };
  end_date?: string;
  user_status?: {
    status?: string;
    progress?: number;
    score?: number;
  };
  // UX-12: Smart Playlist recommendation reason
  playlist_reason?: string;
  // Relation type (SEQUEL, PREQUEL, SIDE_STORY, etc.)
  relation_type?: string;
};

export type Episode = {
  number: string | number;
  title: string;
  download_status: string;
  is_downloaded: boolean;
};

export type QueueItem = {
  media_id: number;
  media_title: string;
  episode_number: string;
  status: string;
  error_message?: string;
  cover_image?: string;
};

export type Character = {
  id: number;
  name: {
    full: string;
    native?: string;
  };
  image?: {
    large?: string;
  };
  description?: string;
};

export type Review = {
  summary?: string;
  body: string;
  user: {
    name: string;
    avatar_url?: string;
  };
};

export type Notification = {
  id: number;
  type: string;
  episode?: number;
  contexts: string[];
  created_at: string;
  media: MediaItem;
};

export type UserProfile = {
  id: number;
  name: string;
  avatar_url?: string;
  banner_url?: string;
  unread_notifications?: number;
  about?: string;
  anime_count?: number;
  minutes_watched?: number;
  episodes_watched?: number;
  manga_count?: number;
  chapters_read?: number;
  volumes_read?: number;
  genres?: { genre: string; count: number; meanScore?: number }[];
  favorite_anime?: MediaItem[];
  favorite_manga?: MediaItem[];
};

export type PlaybackStatus = {
  media_id: number;
  media_title: string;
  episode: string;
  started_at: string;
  started_at_dt?: string;
} | null;

export type HealthStatus = {
  api_connected: boolean;
  api_authenticated: boolean;
  worker_running: boolean;
  is_offline: boolean;
  update_available?: boolean;
  updating?: boolean;
  unread_notifications?: number;
  current_version?: string;
  data_version?: number;
  provider_status?: string | null;
};

export type SearchFilters = {
  genre?: string;
  year?: number;
  min_score?: number;
  status?: string;
  format?: string;
};

export type MediaSearchResult = {
  page_info: {
    total: number;
    current_page: number;
    has_next_page: boolean;
    per_page: number;
  };
  media: MediaItem[];
};

// ─── API Client ───────────────────────────────────────

export const mediaApi = {
  // ─── Discovery ──────────────────────────────────────
  getRecent: (type?: 'ANIME' | 'MANGA', limit = 10): Promise<MediaSearchResult> => 
    fetchFromApi(`/media/recent?limit=${limit}${type ? `&type=${type}` : ''}`),
  
  getTrending: (type: 'ANIME' | 'MANGA' = 'ANIME', perPage = 15): Promise<MediaSearchResult> =>
    fetchFromApi(`/media/trending?type=${type}&per_page=${perPage}`),

  getSeasonal: (type: 'ANIME' | 'MANGA' = 'ANIME', perPage = 15): Promise<MediaSearchResult> =>
    fetchFromApi(`/media/seasonal?type=${type}&per_page=${perPage}`),

  getSchedule: (daysBefore = 1, daysAfter = 1, page = 1, perPage = 50, mediaIds?: number[]): Promise<MediaSearchResult> => {
    let url = `/media/schedule?days_before=${daysBefore}&days_after=${daysAfter}&page=${page}&per_page=${perPage}`;
    if (mediaIds && mediaIds.length > 0) {
      mediaIds.forEach(id => {
        url += `&media_ids=${id}`;
      });
    }
    return fetchFromApi(url);
  },

  // ─── Details ────────────────────────────────────────
  getDetails: (id: number): Promise<MediaItem> => 
    fetchFromApi(`/media/${id}`),
  
  // ─── Search ─────────────────────────────────────────
  search: (query: string, type: 'ANIME' | 'MANGA' = 'ANIME', page = 1, filters?: SearchFilters): Promise<MediaSearchResult> => {
    const params = new URLSearchParams({
      query,
      type,
      page: String(page),
    });
    if (filters?.genre) params.set('genre', filters.genre);
    if (filters?.year) params.set('year', String(filters.year));
    if (filters?.min_score) params.set('min_score', String(filters.min_score));
    if (filters?.status) params.set('status', filters.status);
    if (filters?.format) params.set('format', filters.format);
    return fetchFromApi(`/media/search?${params.toString()}`);
  },
    
  getEpisodes: (mediaId: number): Promise<Episode[]> =>
    fetchFromApi(`/media/${mediaId}/episodes`),

  clearProviderCache: (mediaId: number) =>
    fetchFromApi(`/media/${mediaId}/clear-provider-cache`, { method: 'POST' }),

  // ─── User Lists ─────────────────────────────────────
  getUserList: (status?: string, type?: string, page = 1): Promise<MediaSearchResult> => 
    fetchFromApi(`/user/list?${status ? `status=${status}` : ''}${type ? `&type=${type}` : ''}&page=${page}`),
    
  getProfile: (): Promise<UserProfile> => 
    fetchFromApi('/user/profile'),

  updateStatus: (media_id: number, status?: string, score?: number, progress?: number) =>
    fetchFromApi('/user/update', {
      method: 'POST',
      body: JSON.stringify({ media_id, status, score, progress })
    }),

  deleteFromList: (mediaId: number) =>
    fetchFromApi(`/user/${mediaId}`, { method: 'DELETE' }),

  // ─── Media Extras ───────────────────────────────────
  getCharacters: (mediaId: number): Promise<{ characters: Character[] }> =>
    fetchFromApi(`/media/${mediaId}/characters`),

  getReviews: (mediaId: number, page = 1): Promise<Review[]> =>
    fetchFromApi(`/media/${mediaId}/reviews?page=${page}`),

  getRecommendations: (mediaId: number, page = 1): Promise<MediaItem[]> =>
    fetchFromApi(`/media/${mediaId}/recommendations?page=${page}`),

  getRelations: (mediaId: number): Promise<MediaItem[]> =>
    fetchFromApi(`/media/${mediaId}/relations`),

  getChapterPages: (mediaId: number, chapterNumber: string): Promise<{ thumbnails: string[], title: string }> =>
    fetchFromApi(`/media/${mediaId}/chapter/${chapterNumber}/pages`),

  // ─── Playback ───────────────────────────────────────
  play: async (mediaId: number, episode?: string) => {
    const params = new URLSearchParams();
    if (episode) params.append('episode', episode);
    params.append('fullscreen', 'true');
    const queryString = params.toString() ? `?${params.toString()}` : '';
    return fetchFromApi(`/actions/play/${mediaId}${queryString}`, { method: 'POST' });
  },

  resolveStream: (mediaId: number, episode?: string): Promise<{
    stream_url: string;
    raw_stream_url: string;
    title: string;
    episode: string;
    start_time: number | null;
    media_id: number;
    headers: Record<string, string>;
  }> =>
    fetchFromApi(`/actions/play/${mediaId}/resolve${episode ? `?episode=${episode}` : ''}`, { method: 'POST' }),

  // C4: Re-resolve an expired/failed stream URL without full playback re-init
  renewStream: (mediaId: number, episode: string): Promise<{
    stream_url: string;
    raw_stream_url: string;
    title: string;
    episode: string;
    start_time: number | null;
    media_id: number;
    headers: Record<string, string>;
  }> =>
    fetchFromApi('/actions/stream/renew', {
      method: 'POST',
      body: JSON.stringify({ media_id: mediaId, episode })
    }),

  trackPlayback: (mediaId: number, episode: string, currentTime: number, totalTime: number): Promise<{
    status: string;
    completed: boolean;
    synced: boolean;
  }> =>
    fetchFromApi('/actions/playback/track', {
      method: 'POST',
      body: JSON.stringify({ media_id: mediaId, episode, current_time: currentTime, total_time: totalTime })
    }),

  playNext: async (mediaId: number) => {
    return fetchFromApi(`/actions/play/${mediaId}?fullscreen=true`, { method: 'POST' });
  },

  getPlaybackStatus: (): Promise<PlaybackStatus> =>
    fetchFromApi('/status/playback'),

  clearPlaybackStatus: () =>
    fetchFromApi('/status/playback', { method: 'DELETE' }),

  // ─── Download Queue ─────────────────────────────────
  getQueue: (): Promise<QueueItem[]> =>
    fetchFromApi('/queue/'),

  addToQueue: (mediaId: number, episodes: string[]) =>
    fetchFromApi(`/queue/add?media_id=${mediaId}`, {
      method: 'POST',
      body: JSON.stringify(episodes)
    }),

  retryQueue: () =>
    fetchFromApi('/queue/retry', { method: 'POST' }),

  removeFromQueue: (mediaId: number, episode: string) =>
    fetchFromApi(`/queue/${mediaId}/${episode}`, { method: 'DELETE' }),

  // ─── Config ─────────────────────────────────────────
  getConfig: () =>
    fetchFromApi('/config/'),

  updateConfig: (config: Record<string, unknown>) =>
    fetchFromApi('/config/', {
      method: 'PATCH',
      body: JSON.stringify(config)
    }),

  getConfigOptions: (): Promise<Record<string, any>> =>
    fetchFromApi('/config/options'),

  // ─── Notifications ──────────────────────────────────
  getNotifications: (): Promise<Notification[]> =>
    fetchFromApi('/notifications/'),

  markNotificationsAsRead: () =>
    fetchFromApi('/notifications/read', { method: 'POST' }),

  // ─── Registry & Health ──────────────────────────────
  getRegistryStats: () =>
    fetchFromApi('/registry/stats'),

  triggerBackup: () =>
    fetchFromApi('/registry/backup', { method: 'POST' }),

  wipeRegistry: () =>
    fetchFromApi('/registry/wipe', { method: 'POST' }),

  // ─── Update Logs ──────────────────────────────────
  getUpdateLogs: (lines = 200): Promise<{ logs: string; updating: boolean }> =>
    fetchFromApi('/status/update/logs', { method: 'GET' }),

  checkUpdate: (): Promise<{ status: string; update_available: boolean; message: string; version?: string; release_notes?: string; release_url?: string }> =>
    fetchFromApi('/status/check-update', { method: 'POST' }),

  triggerUpdate: (branch?: 'stable' | 'nightly'): Promise<{ status: string; message: string }> =>
    fetchFromApi('/status/update', {
      method: 'POST',
      body: branch ? JSON.stringify({ branch }) : undefined
    }),

  // ─── Smart Playlist ───────────────────────────────────
  getSmartPlaylist: (): Promise<MediaSearchResult> =>
    fetchFromApi('/media/smart-playlist'),

  getHealthStatus: (): Promise<HealthStatus> =>
    fetchFromApi('/status/health'),
    
  reconnect: (): Promise<{ status: string; message: string }> =>
    fetchFromApi('/status/reconnect', { method: 'POST' }),

  openUrl: (url: string) =>
    fetchFromApi(`/actions/open?url=${encodeURIComponent(url)}`),

  getLogs: (lines = 100): Promise<{ logs: string }> =>
    fetchFromApi(`/status/logs?lines=${lines}`),

  // UX-27: Check if MPV is installed for onboarding
  getMpvAvailable: (): Promise<{ available: boolean; path?: string }> =>
    fetchFromApi('/status/mpv-available'),
};
