import hashlib
import json
import logging
import time
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import httpx
from httpx import Client, Response

from ..constants import APP_CACHE_DIR
from .networking import TIMEOUT

if TYPE_CHECKING:
    from httpx import Client

logger = logging.getLogger(__name__)

GRAPHQL_CACHE_DIR = APP_CACHE_DIR / "network" / "graphql"

# ── Rate Limiting ────────────────────────────────────────────────────────────
# AniList allows 90 requests per minute per user token.  We throttle at
# 80 req/min to leave headroom for other concurrent activity and always
# apply a minimum 700ms inter-request delay.  When a 429 is received,
# subsequent requests wait with exponential backoff (1s / 2s / 4s / 8s).

_DOMAIN_LOCKS: dict[str, threading.Lock] = {}
_DOMAIN_LAST_REQUEST: dict[str, float] = {}
_MIN_INTERVAL = 0.75  # seconds between requests (80 req/min, safely under 90 limit)
_BACKOFF_SECONDS = 1.0  # initial backoff on 429
_MAX_BACKOFF = 8.0  # cap backoff growth
_RETRIES_ON_429 = 2  # how many times to retry a 429 with backoff


def _domain_rate_limit(url: str) -> None:
    """Sleep if necessary to maintain the per-domain minimum request interval."""
    from urllib.parse import urlparse

    domain = urlparse(url).netloc or url
    lock = _DOMAIN_LOCKS.setdefault(domain, threading.Lock())
    with lock:
        now = time.time()
        last = _DOMAIN_LAST_REQUEST.get(domain, 0)
        wait = _MIN_INTERVAL - (now - last)
        if wait > 0:
            time.sleep(wait)
            now = time.time()
        _DOMAIN_LAST_REQUEST[domain] = now


def _handle_429_backoff(url: str, attempt: int) -> bool:
    """Calculate and sleep the backoff delay for a 429 response.

    Returns True if we should retry, False if we've exhausted retries.
    """
    if attempt >= _RETRIES_ON_429:
        return False
    delay = min(_BACKOFF_SECONDS * (2**attempt), _MAX_BACKOFF)
    logger.warning(
        f"[RATE LIMIT] 429 from {url}, backing off {delay:.1f}s (attempt {attempt + 1}/{_RETRIES_ON_429})"
    )
    time.sleep(delay)
    return True


class GraphQLCache:
    """A simple file-based cache for GraphQL responses."""

    def __init__(self, cache_dir: Path = GRAPHQL_CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, url: str, query: str, variables: dict) -> str:
        """Generate a unique key for the request."""
        key_data = f"{url}:{query}:{json.dumps(variables, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(
        self, url: str, query: str, variables: dict, ttl: int | float
    ) -> Optional[dict]:
        """Retrieve a cached response if it exists and is not expired."""
        key = self._get_cache_key(url, query, variables)
        cache_file = self.cache_dir / f"{key}.json"

        if not cache_file.exists():
            return None

        try:
            with cache_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            cached_at = data.get("cached_at", 0)
            if time.time() - cached_at > ttl:
                return None

            return data.get("response")
        except Exception as e:
            logger.debug(f"Failed to read cache file {cache_file}: {e}")
            return None

    def set(self, url: str, query: str, variables: dict, response_data: dict):
        """Store a response in the cache."""
        key = self._get_cache_key(url, query, variables)
        cache_file = self.cache_dir / f"{key}.json"

        try:
            data = {
                "cached_at": time.time(),
                "response": response_data,
                "url": url,
                "variables": variables,
            }
            with cache_file.open("w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Failed to write cache file {cache_file}: {e}")

    def invalidate(self, url: str, query: str, variables: dict):
        """Manually invalidate a cache entry."""
        key = self._get_cache_key(url, query, variables)
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                cache_file.unlink()
                logger.debug(f"Invalidated cache for {key}")
            except Exception as e:
                logger.warning(f"Failed to invalidate cache file {cache_file}: {e}")

    def clear(self):
        """Clear all cached responses."""
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete cache file {cache_file}: {e}")


_cache = GraphQLCache()


def clear_graphql_cache():
    """Clear the entire GraphQL cache."""
    _cache.clear()


def load_graphql_from_file(file: Path) -> str:
    """
    Reads and returns the content of a .gql file.

    Args:
        file: The Path object pointing to the .gql file.

    Returns:
        The string content of the file.
    """
    try:
        return file.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error(f"GraphQL file not found at: {file}")
        raise


def execute_graphql_query_with_get_request(
    url: str, httpx_client: Client, graphql_file: Path, variables: dict
) -> Response:
    query = load_graphql_from_file(graphql_file)
    params = {"query": query, "variables": json.dumps(variables)}
    response = httpx_client.get(url, params=params, timeout=TIMEOUT)
    return response


def execute_graphql(
    url: str,
    httpx_client: Client,
    graphql_file: Path,
    variables: dict,
    headers: dict | None = None,
    use_cache: bool = False,
    ttl: int = 3600,
    force_refresh: bool = False,
) -> Response:
    query = load_graphql_from_file(graphql_file)

    if use_cache and not force_refresh:
        cached_data = _cache.get(url, query, variables, ttl)
        if cached_data:
            logger.debug(f"Returning cached response for {graphql_file.name}")
            return Response(
                status_code=200,
                content=json.dumps(cached_data).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )

    json_body = {"query": query, "variables": variables}

    # Rate-limit and retry-with-backoff loop
    for attempt in range(_RETRIES_ON_429 + 1):
        _domain_rate_limit(url)

        try:
            response = httpx_client.post(
                url, json=json_body, headers=headers, timeout=TIMEOUT
            )
        except httpx.RequestError as e:
            logger.warning(f"GraphQL request failed for {graphql_file.name}: {e}")
            # Offline fallback for network-level failures
            cached_data = _cache.get(url, query, variables, ttl=float("inf"))
            if cached_data:
                logger.info(
                    f"Returning expired cached response for {graphql_file.name} as offline fallback."
                )
                return Response(
                    status_code=200,
                    content=json.dumps(cached_data).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "X-Offline-Fallback": "true",
                    },
                )
            raise

        if response.status_code == 200:
            if use_cache:
                try:
                    _cache.set(url, query, variables, response.json())
                except Exception as e:
                    logger.warning(f"Failed to cache response: {e}")
            return response

        # 429 — retry with backoff
        if response.status_code == 429:
            if _handle_429_backoff(url, attempt):
                continue
            # Exhausted retries — try offline cache fallback
            cached_data = _cache.get(url, query, variables, ttl=float("inf"))
            if cached_data:
                logger.info(
                    f"Returning cached response for {graphql_file.name} after 429 exhaustion."
                )
                return Response(
                    status_code=200,
                    content=json.dumps(cached_data).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "X-Offline-Fallback": "true",
                    },
                )
            logger.warning(
                f"GraphQL 429 exhausted retries for {graphql_file.name}: {response.text}"
            )
            response.raise_for_status()

        # 5xx — treat as potentially transient, try cache fallback
        if response.status_code >= 500:
            cached_data = _cache.get(url, query, variables, ttl=float("inf"))
            if cached_data:
                logger.info(
                    f"Returning cached response for {graphql_file.name} after 5xx."
                )
                return Response(
                    status_code=200,
                    content=json.dumps(cached_data).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "X-Offline-Fallback": "true",
                    },
                )
            logger.warning(
                f"GraphQL request failed with status code {response.status_code}: {response.text}"
            )
            response.raise_for_status()

        # Other errors (4xx except 429)
        logger.warning(
            f"GraphQL request failed with status code {response.status_code}: {response.text}"
        )
        response.raise_for_status()

    raise RuntimeError(
        "Unreachable: GraphQL query execution loop ended without returning or raising."
    )


def invalidate_graphql_cache(url: str, graphql_file: Path, variables: dict):
    """Utility to invalidate a specific cache entry from outside."""
    query = load_graphql_from_file(graphql_file)
    _cache.invalidate(url, query, variables)
