"use client";

import { useEffect, useState } from "react";
import { X, Play, Loader2, Star, Users, Calendar, Clock, Building2 } from "lucide-react";
import { mediaApi, type MediaItem, type Episode, type Character, type Review } from "@/lib/api";
import EpisodeList from "./EpisodeList";

interface MediaDetailProps {
  item: MediaItem;
  onClose: () => void;
}

export default function MediaDetail({ item, onClose }: MediaDetailProps) {
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [recommendations, setRecommendations] = useState<MediaItem[]>([]);
  const [activeTab, setActiveTab] = useState<"episodes" | "characters" | "reviews" | "recommendations">("episodes");
  const [loadingEps, setLoadingEps] = useState(true);
  const [loadingChars, setLoadingChars] = useState(false);
  const [loadingReviews, setLoadingReviews] = useState(false);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [fullItem, setFullItem] = useState<MediaItem>(item);
  const [rating, setRating] = useState(item.user_status?.score || 0);
  const [isUpdatingRating, setIsUpdatingRating] = useState(false);

  const title = fullItem.title.english || fullItem.title.romaji || "Unknown";

  useEffect(() => {
    // Reset all states when item.id changes to prevent "glitching"
    setFullItem(item);
    setEpisodes([]);
    setCharacters([]);
    setReviews([]);
    setRecommendations([]);
    setLoadingEps(true);
    setLoadingChars(false);
    setLoadingReviews(false);
    setLoadingRecs(false);
    setActiveTab("episodes");
    if (item.user_status?.score) setRating(item.user_status.score);
    else setRating(0);

    // Load full details
    mediaApi.getDetails(item.id)
      .then(data => {
        setFullItem(data);
        if (data.user_status?.score) setRating(data.user_status.score);
      })
      .catch(console.error);

    // Load episodes by default
    mediaApi.getEpisodes(item.id)
      .then(data => setEpisodes(data || []))
      .catch(err => {
        console.error("Failed to load episodes:", err);
        setEpisodes([]);
      })
      .finally(() => setLoadingEps(false));
  }, [item.id]);

  useEffect(() => {
    if (activeTab === "characters" && characters.length === 0) {
      setLoadingChars(true);
      mediaApi.getCharacters(item.id)
        .then(data => setCharacters(data.characters || []))
        .catch(console.error)
        .finally(() => setLoadingChars(false));
    } else if (activeTab === "reviews" && reviews.length === 0) {
      setLoadingReviews(true);
      mediaApi.getReviews(item.id)
        .then(setReviews)
        .catch(console.error)
        .finally(() => setLoadingReviews(false));
    } else if (activeTab === "recommendations" && recommendations.length === 0) {
      setLoadingRecs(true);
      mediaApi.getRecommendations(item.id)
        .then(setRecommendations)
        .catch(console.error)
        .finally(() => setLoadingRecs(false));
    }
  }, [activeTab, item.id, characters.length, reviews.length, recommendations.length]);

  const handleRate = async (score: number) => {
    setIsUpdatingRating(true);
    try {
      await mediaApi.updateStatus(item.id, undefined, score);
      setRating(score);
    } catch (err) {
      console.error("Failed to update rating:", err);
    } finally {
      setIsUpdatingRating(false);
    }
  };


  return (
    <div className="fixed inset-0 z-[100] flex">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className="relative ml-auto w-full max-w-2xl bg-surface border-l border-white/[0.06] overflow-y-auto animate-slide-in-right">
        {/* Banner */}
        <div className="relative h-64 lg:h-72 overflow-hidden">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={fullItem.banner_image || fullItem.cover_image.large}
            alt={title}
            className="absolute inset-0 w-full h-full object-cover brightness-[0.35]"
          />
          <div className="absolute inset-0 hero-gradient" />
          <div className="absolute inset-0 bg-gradient-to-r from-surface/60 to-transparent" />

          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 rounded-full bg-black/50 hover:bg-white/10 text-white transition-colors z-10"
          >
            <X size={20} />
          </button>

          {/* Title area */}
          <div className="absolute bottom-6 left-6 right-6 z-10 flex items-end space-x-5">
            <div className="w-28 h-40 rounded-lg overflow-hidden border border-white/10 shrink-0 shadow-2xl hidden sm:block">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={fullItem.cover_image.large}
                alt={title}
                className="w-full h-full object-cover"
              />
            </div>
            <div className="space-y-2 min-w-0">
              <div className="flex items-center space-x-2 text-xs font-semibold text-gray-300">
                <span className="text-accent">{fullItem.format || "TV"}</span>
                <span className="text-gray-600">•</span>
                <span>{fullItem.status}</span>
                {fullItem.episodes && (
                  <>
                    <span className="text-gray-600">•</span>
                    <span>{fullItem.episodes} eps</span>
                  </>
                )}
                {fullItem.average_score && (
                  <>
                    <span className="text-gray-600">•</span>
                    <div className="flex items-center text-yellow-400">
                      <Star size={10} fill="currentColor" className="mr-1" />
                      <span>{fullItem.average_score}%</span>
                    </div>
                  </>
                )}
              </div>
              <h2 className="text-2xl lg:text-3xl font-extrabold text-white leading-tight line-clamp-2">
                {title}
              </h2>
              {fullItem.genres && (
                <div className="flex flex-wrap gap-1.5">
                  {fullItem.genres.slice(0, 4).map(g => (
                    <span key={g} className="px-2 py-0.5 bg-white/[0.06] rounded-md text-[10px] font-semibold text-gray-400">
                      {g}
                    </span>
                  ))}
                  {fullItem.tags && fullItem.tags.slice(0, 3).map(tag => (
                    <span key={tag.name} className="px-2 py-0.5 bg-accent/10 border border-accent/20 rounded-md text-[10px] font-semibold text-accent/80">
                      #{tag.name}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* User Score / Rating */}
          <div className="absolute top-4 left-4 z-10">
            <div className="flex items-center space-x-1 bg-black/60 backdrop-blur-md p-2 rounded-xl border border-white/10 group/rating">
              {[...Array(10)].map((_, i) => (
                <button
                  key={i}
                  disabled={isUpdatingRating}
                  onClick={() => handleRate(i + 1)}
                  className={`transition-all ${isUpdatingRating ? "opacity-50 cursor-not-allowed" : "hover:scale-125"}`}
                >
                  <Star
                    size={14}
                    fill={i < rating ? "#facc15" : "transparent"}
                    className={i < rating ? "text-yellow-400" : "text-gray-500"}
                  />
                </button>
              ))}
              <span className="text-[10px] font-bold text-gray-400 ml-2 group-hover/rating:text-white transition-colors">
                {rating > 0 ? `${rating}/10` : "Rate"}
              </span>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">

          {/* Details Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-4 border-y border-white/[0.06]">
            {fullItem.studios && fullItem.studios.length > 0 && (
              <div className="space-y-1">
                <div className="flex items-center text-gray-500 space-x-1.5">
                  <Building2 size={12} />
                  <span className="text-[10px] font-bold uppercase tracking-wider">Studio</span>
                </div>
                <div className="text-xs text-gray-300 font-medium truncate">
                  {fullItem.studios.find(s => s.isAnimationStudio)?.name || fullItem.studios[0].name}
                </div>
              </div>
            )}
            {(fullItem.season || fullItem.seasonYear) && (
              <div className="space-y-1">
                <div className="flex items-center text-gray-500 space-x-1.5">
                  <Calendar size={12} />
                  <span className="text-[10px] font-bold uppercase tracking-wider">Season</span>
                </div>
                <div className="text-xs text-gray-300 font-medium">
                  {fullItem.season && fullItem.season.charAt(0) + fullItem.season.slice(1).toLowerCase()} {fullItem.seasonYear}
                </div>
              </div>
            )}
            {fullItem.popularity && (
              <div className="space-y-1">
                <div className="flex items-center text-gray-500 space-x-1.5">
                  <Users size={12} />
                  <span className="text-[10px] font-bold uppercase tracking-wider">Popularity</span>
                </div>
                <div className="text-xs text-gray-300 font-medium">
                  {fullItem.popularity.toLocaleString()}
                </div>
              </div>
            )}
            {fullItem.duration && (
              <div className="space-y-1">
                <div className="flex items-center text-gray-500 space-x-1.5">
                  <Clock size={12} />
                  <span className="text-[10px] font-bold uppercase tracking-wider">Duration</span>
                </div>
                <div className="text-xs text-gray-300 font-medium">
                  {fullItem.duration}m
                </div>
              </div>
            )}
          </div>

          {/* Airing Info */}
          {fullItem.next_airing && (
            <div className="bg-accent/5 border border-accent/10 rounded-xl p-4 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-accent/10 rounded-lg text-accent">
                  <Calendar size={18} />
                </div>
                <div>
                  <div className="text-[10px] font-bold text-accent uppercase tracking-widest">Next Episode</div>
                  <div className="text-sm text-gray-200 font-semibold">
                    Episode {fullItem.next_airing.episode} airing soon
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Description */}
          {fullItem.description && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider">Synopsis</h3>
              <p
                className="text-sm text-gray-400 leading-relaxed max-h-48 overflow-y-auto scrollbar-hide"
                dangerouslySetInnerHTML={{ __html: fullItem.description }}
              />
            </div>
          )}

          {/* Tabs */}
          <div className="flex space-x-1 p-1 bg-white/[0.03] border border-white/[0.06] rounded-xl">
            {(["episodes", "characters", "reviews", "recommendations"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 py-2 text-[10px] font-bold uppercase tracking-wider rounded-lg transition-all ${
                  activeTab === tab
                    ? "bg-accent text-white shadow-lg"
                    : "text-gray-500 hover:text-white"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="animate-fade-in">
            {activeTab === "episodes" && (
              <div className="space-y-3">
                <EpisodeList mediaId={item.id} episodes={episodes} loading={loadingEps} />
              </div>
            )}

            {activeTab === "characters" && (
              <div className="space-y-4">
                {loadingChars ? (
                  <div className="flex justify-center py-12"><Loader2 className="animate-spin text-accent" /></div>
                ) : characters.length > 0 ? (
                  <div className="grid grid-cols-2 gap-3">
                    {characters.map(char => (
                      <div key={char.id} className="flex items-center space-x-3 p-2 bg-white/[0.02] border border-white/[0.04] rounded-xl">
                        {char.image?.large && (
                          <img src={char.image.large} alt={char.name.full} className="w-12 h-12 rounded-lg object-cover" />
                        )}
                        <div className="min-w-0">
                          <div className="text-xs font-bold text-white truncate">{char.name.full}</div>
                          {char.name.native && <div className="text-[10px] text-gray-500 truncate">{char.name.native}</div>}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : <div className="text-center py-12 text-gray-600 text-xs">No characters found</div>}
              </div>
            )}

            {activeTab === "reviews" && (
              <div className="space-y-4">
                {loadingReviews ? (
                  <div className="flex justify-center py-12"><Loader2 className="animate-spin text-accent" /></div>
                ) : reviews.length > 0 ? (
                  <div className="space-y-4">
                    {reviews.map((rev, idx) => (
                      <div key={idx} className="p-4 bg-white/[0.02] border border-white/[0.04] rounded-xl space-y-2">
                        <div className="flex items-center space-x-2">
                          {rev.user.avatar_url && <img src={rev.user.avatar_url} className="w-6 h-6 rounded-full" />}
                          <span className="text-xs font-bold text-accent">{rev.user.name}</span>
                        </div>
                        {rev.summary && <div className="text-xs font-semibold text-gray-200">{rev.summary}</div>}
                        <p className="text-[11px] text-gray-500 line-clamp-4 hover:line-clamp-none transition-all">{rev.body}</p>
                      </div>
                    ))}
                  </div>
                ) : <div className="text-center py-12 text-gray-600 text-xs">No reviews found</div>}
              </div>
            )}

            {activeTab === "recommendations" && (
              <div className="space-y-4">
                {loadingRecs ? (
                  <div className="flex justify-center py-12"><Loader2 className="animate-spin text-accent" /></div>
                ) : recommendations.length > 0 ? (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                    {recommendations.map(rec => (
                      <button 
                        key={rec.id} 
                        onClick={() => mediaApi.getDetails(rec.id).then(setFullItem)}
                        className="group space-y-2 text-left"
                      >
                        <div className="aspect-[2/3] rounded-lg overflow-hidden border border-white/10">
                          <img src={rec.cover_image.large} className="w-full h-full object-cover transition-transform group-hover:scale-105" />
                        </div>
                        <div className="text-[10px] font-bold text-gray-400 line-clamp-1 group-hover:text-white">{rec.title.english || rec.title.romaji}</div>
                      </button>
                    ))}
                  </div>
                ) : <div className="text-center py-12 text-gray-600 text-xs">No recommendations found</div>}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
