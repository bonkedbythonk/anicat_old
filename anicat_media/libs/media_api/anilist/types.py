from typing import List, Literal, Optional, TypedDict


class AnilistPageInfo(TypedDict):
    total: int
    perPage: int
    currentPage: int
    hasNextPage: bool


class AnilistMediaTitle(TypedDict):
    english: str
    romaji: str


class AnilistImage(TypedDict):
    medium: str
    extraLarge: str
    small: str
    large: str


class AnilistCurrentlyLoggedInUser(TypedDict):
    id: int
    name: str
    bannerImage: Optional[str]
    avatar: AnilistImage
    token: str
    about: Optional[str]
    statistics: Optional[dict]
    favourites: Optional[dict]


class AnilistViewer(TypedDict):
    Viewer: AnilistCurrentlyLoggedInUser


class AnilistViewerData(TypedDict):
    data: AnilistViewer


class AnilistUser(TypedDict):
    name: str
    about: Optional[str]
    avatar: AnilistImage
    bannerImage: Optional[str]


class AnilistUserInfo(TypedDict):
    User: AnilistUser


class AnilistUserData(TypedDict):
    data: AnilistUserInfo


class AnilistMediaTrailer(TypedDict):
    id: str
    site: str


class AnilistStudio(TypedDict):
    name: str
    favourites: int
    isAnimationStudio: bool


class AnilistStudioNodes(TypedDict):
    nodes: list[AnilistStudio]


class AnilistMediaTag(TypedDict):
    name: str
    rank: int


class AnilistDateObject(TypedDict):
    day: int
    month: int
    year: int


class AnilistMediaNextAiringEpisode(TypedDict):
    timeUntilAiring: int
    airingAt: int
    episode: int


class AnilistMediaRanking(TypedDict):
    rank: int
    context: str


class AnilistExternalLink(TypedDict):
    url: str
    site: str
    icon: str


class AnilistName(TypedDict):
    full: str


class AnilistCharacter(TypedDict):
    name: AnilistName
    gender: str | None
    dateOfBirth: AnilistDateObject | None
    age: int
    image: AnilistImage
    description: str


class AnilistVoiceActor(TypedDict):
    name: AnilistName
    image: AnilistImage


class AnilistCharactersEdge(TypedDict):
    node: list[AnilistCharacter]
    voiceActors: list[AnilistVoiceActor]


class AnilistCharactersEdges(TypedDict):
    edges: list[AnilistCharactersEdge]


AnilistMediaListStatus = Literal[
    "CURRENT", "PLANNING", "COMPLETED", "DROPPED", "PAUSED", "REPEATING"
]


class AnilistMediaList_(TypedDict):
    id: int
    progress: int
    status: AnilistMediaListStatus
    score: float | int | None


class AnilistMediaListProperties(TypedDict):
    status: AnilistMediaListStatus
    score: float
    scoreRaw: int
    progress: int
    repeat: int
    priority: bool
    private: bool
    notes: str
    hiddenFromStatusLists: bool


class StreamingEpisode(TypedDict):
    title: str
    thumbnail: str


class AnilistReview(TypedDict):
    summary: str
    user: AnilistCurrentlyLoggedInUser
    body: Optional[str]


class AnilistReviewPage(TypedDict):
    pageInfo: AnilistPageInfo
    reviews: list[AnilistReview]


class AnilistReviewPages(TypedDict):
    Page: AnilistReviewPage


class AnilistReviews(TypedDict):
    data: AnilistReviewPages


class AnilistReviewNodes(TypedDict):
    nodes: list[AnilistReview]


class AnilistBaseMediaDataSchema(TypedDict):
    """
    This a convenience class is used to type the received Anilist data to enhance dev experience
    """

    id: int
    idMal: int
    title: AnilistMediaTitle
    coverImage: AnilistImage
    trailer: AnilistMediaTrailer | None
    popularity: int
    favourites: int
    averageScore: int
    genres: list[str]
    episodes: int | None
    description: str | None
    studios: AnilistStudioNodes
    tags: list[AnilistMediaTag]
    startDate: AnilistDateObject
    endDate: AnilistDateObject
    status: str
    nextAiringEpisode: AnilistMediaNextAiringEpisode
    season: str
    streamingEpisodes: list[StreamingEpisode]
    chapters: int
    seasonYear: int
    duration: int
    synonyms: list[str]
    countryOfOrigin: str
    source: str
    hashtag: str | None
    siteUrl: str
    reviews: AnilistReviewNodes
    bannerImage: str | None
    rankings: list[AnilistMediaRanking]
    externalLinks: list[AnilistExternalLink]
    characters: AnilistCharactersEdges
    format: str
    mediaListEntry: AnilistMediaList_ | None


class AnilistPage(TypedDict):
    media: list[AnilistBaseMediaDataSchema]
    pageInfo: AnilistPageInfo


class AnilistPages(TypedDict):
    Page: AnilistPage


class AnilistDataSchema(TypedDict):
    data: AnilistPages


class AnilistMediaList(TypedDict):
    media: AnilistBaseMediaDataSchema
    status: AnilistMediaListStatus
    progress: int
    score: int
    repeat: int
    notes: str
    startDate: AnilistDateObject
    completedAt: AnilistDateObject
    createdAt: str


class AnilistMediaListPage(TypedDict):
    pageInfo: AnilistPageInfo
    mediaList: list[AnilistMediaList]


class AnilistMediaListPages(TypedDict):
    Page: AnilistMediaListPage


class AnilistMediaLists(TypedDict):
    data: AnilistMediaListPages


class AnilistNotification(TypedDict):
    id: int
    type: str
    episode: int
    contexts: List[str]
    createdAt: int  # This is a Unix timestamp
    media: AnilistBaseMediaDataSchema  # This will be a partial response


class AnilistNotificationPage(TypedDict):
    pageInfo: AnilistPageInfo
    notifications: list[AnilistNotification]


class AnilistNotificationPages(TypedDict):
    Page: AnilistNotificationPage


class AnilistNotifications(TypedDict):
    data: AnilistNotificationPages
