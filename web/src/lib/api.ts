const isBrowser = typeof window !== 'undefined';
const API_BASE_ORIGIN = isBrowser 
  ? (window.location.port === '3000' ? 'http://localhost:8000' : window.location.origin) 
  : 'http://localhost:8000';
const API_BASE_URL = `${API_BASE_ORIGIN}/api`;

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
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

export type MediaItem = {
  id: number;
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
  status?: string;
  format?: string;
  genres?: string[];
  average_score?: number;
  popularity?: number;
  favourites?: number;
  season?: string;
  seasonYear?: number;
  duration?: number;
  studios?: { name: string; isAnimationStudio: boolean }[];
  tags?: { name: string; rank: number }[];
  next_airing?: {
    episode: number;
    airing_at?: string;
  };
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

export const mediaApi = {
  getRecent: (type?: 'ANIME' | 'MANGA', limit = 10) => 
    fetchFromApi(`/media/recent?limit=${limit}${type ? `&type=${type}` : ''}`),
  
  getDetails: (id: number): Promise<MediaItem> => 
    fetchFromApi(`/media/${id}`),
  
  search: (query: string, type: 'ANIME' | 'MANGA' = 'ANIME', page = 1) => 
    fetchFromApi(`/media/search?query=${encodeURIComponent(query)}&type=${type}&page=${page}`),
    
  getEpisodes: (mediaId: number): Promise<Episode[]> =>
    fetchFromApi(`/media/${mediaId}/episodes`),

  getUserList: (status?: string, type?: string, page = 1) => 
    fetchFromApi(`/user/list?${status ? `status=${status}` : ''}${type ? `&type=${type}` : ''}&page=${page}`),
    
  getProfile: () => 
    fetchFromApi('/user/profile'),

  updateStatus: (media_id: number, status?: string, score?: number, progress?: number) =>
    fetchFromApi('/user/update', {
      method: 'POST',
      body: JSON.stringify({ media_id, status, score, progress })
    }),

  getCharacters: (mediaId: number): Promise<{ characters: Character[] }> =>
    fetchFromApi(`/media/${mediaId}/characters`),

  getReviews: (mediaId: number, page = 1): Promise<Review[]> =>
    fetchFromApi(`/media/${mediaId}/reviews?page=${page}`),

  getRecommendations: (mediaId: number, page = 1): Promise<MediaItem[]> =>
    fetchFromApi(`/media/${mediaId}/recommendations?page=${page}`),

  play: (mediaId: number, episode?: string) =>
    fetchFromApi(`/actions/play/${mediaId}${episode ? `?episode=${episode}` : ''}`, { method: 'POST' }),

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

  getConfig: () =>
    fetchFromApi('/config/'),

  updateConfig: (config: Record<string, unknown>) =>
    fetchFromApi('/config/', {
      method: 'PATCH',
      body: JSON.stringify(config)
    }),
};
