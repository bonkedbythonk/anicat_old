const isBrowser = typeof window !== 'undefined';
const DEFAULT_API_BASE_ORIGIN = 'http://127.0.0.1:13370';

export const API_BASE_ORIGIN = process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_BASE_ORIGIN;
export const API_BASE_URL = `${API_BASE_ORIGIN}/api`;

if (isBrowser) {
  console.log('API_BASE_URL:', API_BASE_URL);
}

export async function fetchFromApi(endpoint: string, options: RequestInit = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    // Prefer structured detail (FastAPI uses `detail`) then `message`, else fallback
    const detail = errorData.detail ?? errorData.message ?? errorData ?? null;
    const message = detail ? (typeof detail === 'string' ? detail : JSON.stringify(detail)) : `API error: ${response.status} ${response.statusText}`;
    if (isBrowser) {
      console.error('API ERROR', { endpoint, status: response.status, statusText: response.statusText, errorData });
    }
    throw new Error(`${endpoint} - ${message}`);
  }

  return response.json();
}

// ─── Types ────────────────────────────────────────────

export type MediaItem = {
  id: number;
  type?: "ANIME" | "MANGA";
  title: {
    english?: string;
    romaji?: string;
  };
  cover_image: {
    large: string;
  };
  banner_image?: string;
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
  unread_notifications?: number;
  current_version?: string;
  data_version?: number;
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

  getChapterPages: (mediaId: number, chapterNumber: string): Promise<{ thumbnails: string[], title: string }> =>
    fetchFromApi(`/media/${mediaId}/chapter/${chapterNumber}/pages`),

  // ─── Playback ───────────────────────────────────────
  play: (mediaId: number, episode?: string) =>
    fetchFromApi(`/actions/play/${mediaId}${episode ? `?episode=${episode}` : ''}`, { method: 'POST' }),

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

  trackPlayback: (mediaId: number, episode: string, currentTime: number, totalTime: number): Promise<{
    status: string;
    completed: boolean;
    synced: boolean;
  }> =>
    fetchFromApi('/actions/playback/track', {
      method: 'POST',
      body: JSON.stringify({ media_id: mediaId, episode, current_time: currentTime, total_time: totalTime })
    }),

  playNext: (mediaId: number) =>
    fetchFromApi(`/actions/play/${mediaId}`, { method: 'POST' }),

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

  checkUpdate: (): Promise<{ status: string; update_available: boolean; message: string }> =>
    fetchFromApi('/status/check-update', { method: 'POST' }),

  triggerUpdate: (): Promise<{ status: string; message: string }> =>
    fetchFromApi('/status/update', { method: 'POST' }),

  getHealthStatus: (): Promise<HealthStatus> =>
    fetchFromApi('/status/health'),
    
  reconnect: (): Promise<{ status: string; message: string }> =>
    fetchFromApi('/status/reconnect', { method: 'POST' }),

  openUrl: (url: string) =>
    fetchFromApi(`/actions/open?url=${encodeURIComponent(url)}`),

  getLogs: (lines = 100): Promise<{ logs: string }> =>
    fetchFromApi(`/status/logs?lines=${lines}`),
};
