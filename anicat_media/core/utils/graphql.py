import hashlib
import json
import logging
import random
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
# AniList allows 90 requests per minute per user token. We use a token-bucket
# algorithm with a maximum burst of 5 tokens to allow for initial request
# batches, then refill at 90 tokens/min. When a 429 is received, the domain
# enters a global "cool-down" period that blocks ALL requests to that domain
# until the cooldown expires (driven by the Retry-After header or exponential
# backoff with jitter).
#
# Key improvements over the old interval-only limiter:
#   • Token bucket: tracks consumption over a 60s rolling window
#   • Retry-After: respects the server's requested wait time
#   • Jitter: randomizes backoff to prevent thundering herds
#   • Global cool-down: a single 429 pauses ALL requests to that domain

_DOMAIN_LOCKS: dict[str, threading.RLock] = {}
_DOMAIN_COOLDOWN_UNTIL: dict[str, float] = {}  # epoch when cool-down ends
_DOMAIN_IN_FLIGHT: dict[str, threading.Semaphore] = {}  # max 1 in-flight request per domain

# Token bucket state (per-domain)
_TOKEN_BUCKET_TOKENS: dict[str, float] = {}
_TOKEN_BUCKET_LAST_REFILL: dict[str, float] = {}
_TOKEN_BUCKET_CAPACITY = 90  # max tokens (requests per minute)
_TOKEN_BUCKET_REFILL_RATE = 90 / 60.0  # tokens per second
_TOKEN_BUCKET_BURST = 5  # initial burst to allow first batch through

_MIN_INTERVAL = 0.75  # minimum seconds between requests when within limit
_RETRIES_ON_429 = 3  # how many times to retry a 429 with backoff
_MAX_JITTER = 0.3  # max jitter fraction added to backoff delays


def _get_domain(url: str) -> str:
    """Extract the domain (netloc) from a URL."""
    from urllib.parse import urlparse

    return urlparse(url).netloc or url


def _domain_rate_limit(url: str) -> float:
    """Check and enforce rate limits for the given domain.

    MUST be called while holding the domain RLock.

    Returns the number of seconds to wait before sending (0 = go ahead).
    The caller should sleep OUTSIDE the lock after releasing it.
    """
    domain = _get_domain(url)
    now = time.time()

    # Check if domain is in cool-down (from a previous 429)
    cooldown_until = _DOMAIN_COOLDOWN_UNTIL.get(domain, 0)
    cool_down_wait = max(0.0, cooldown_until - now)

    # Token bucket: try to consume a token
    token_wait = 0.0
    last = _TOKEN_BUCKET_LAST_REFILL.get(domain, now)
    tokens = _TOKEN_BUCKET_TOKENS.get(domain, _TOKEN_BUCKET_BURST)

    # Refill tokens based on elapsed time
    elapsed = now - last
    tokens = min(_TOKEN_BUCKET_CAPACITY, tokens + elapsed * _TOKEN_BUCKET_REFILL_RATE)

    if tokens >= 1.0:
        tokens -= 1.0
    else:
        # Calculate wait time until next token is available
        token_wait = (1.0 - tokens) / _TOKEN_BUCKET_REFILL_RATE
        tokens = 0.0

    _TOKEN_BUCKET_TOKENS[domain] = tokens
    _TOKEN_BUCKET_LAST_REFILL[domain] = now

    # Return the maximum of the two waits (cool-down or token)
    return max(cool_down_wait, token_wait)


def _drain_token_bucket(url: str) -> None:
    """Drain all tokens for a domain after receiving a 429.

    MUST be called while holding the domain RLock.
    This prevents a burst of queued requests from all firing
    simultaneously after a cool-down period ends.
    """
    domain = _get_domain(url)
    _TOKEN_BUCKET_TOKENS[domain] = 0.0
    _TOKEN_BUCKET_LAST_REFILL[domain] = time.time()


def _compute_cool_down_delay(
    url: str, retry_after: float | None = None, attempt: int = 0
) -> float:
    """Compute the cool-down delay after receiving a 429.

    Uses the Retry-After header if available, otherwise falls back to
    jittered exponential backoff.

    Returns the delay in seconds. Does NOT sleep — caller is responsible.
    """
    import random as _random

    if retry_after is not None and retry_after > 0:
        # Use server-specified delay (add small jitter up to 10% or 1s)
        delay = retry_after + _random.uniform(0, min(1.0, retry_after * _MAX_JITTER))
    else:
        # Jittered exponential backoff: base * 2^attempt + random jitter
        base = 2.0
        delay = min(base * (2**attempt), 30.0)
        jitter = _random.uniform(0, delay * _MAX_JITTER)
        delay += jitter

    return delay


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


def _parse_retry_after(response: Response) -> float | None:
    """Parse the Retry-After header from a 429 response.

    Returns the number of seconds to wait, or None if the header
    is absent or unparseable.
    """
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return None
    try:
        # Try parsing as integer seconds
        return float(retry_after)
    except ValueError:
        # Try parsing as HTTP-date
        try:
            from email.utils import parsedate_to_datetime
            retry_time = parsedate_to_datetime(retry_after)
            wait = (retry_time.timestamp() - time.time())
            return max(0, wait)
        except Exception:
            return None


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
    domain = _get_domain(url)
    lock = _DOMAIN_LOCKS.setdefault(domain, threading.RLock())
    in_flight = _DOMAIN_IN_FLIGHT.setdefault(domain, threading.Semaphore(1))

    # ── Retry loop ──────────────────────────────────────────────────────
    # KEY DESIGN: The RLock is held ONLY for microsecond-scale state
    # mutations (token bucket, cool-down) — NEVER for I/O or sleep.
    # A semaphore limits in-flight HTTP requests to 1 per domain,
    # preventing the race where multiple threads get tokens before
    # a 429 triggers the global cool-down.
    for attempt in range(_RETRIES_ON_429 + 1):
        # ── Phase 1: Rate-limit check (inside lock) ──
        with lock:
            wait = _domain_rate_limit(url)

        # ── Phase 2: Wait for rate limit / cool-down (outside lock) ──
        if wait > 0:
            time.sleep(wait)

        # ── Phase 3: Acquire in-flight slot, then make HTTP request ──
        in_flight.acquire()
        try:
            response = httpx_client.post(
                url, json=json_body, headers=headers, timeout=TIMEOUT
            )
        except httpx.RequestError as e:
            in_flight.release()
            logger.warning(
                f"GraphQL request failed for {graphql_file.name}: {e}"
            )
            # Offline fallback for network-level failures
            cached_data = _cache.get(url, query, variables, ttl=float("inf"))
            if cached_data:
                logger.info(
                    f"Returning expired cached response for {graphql_file.name} "
                    f"as offline fallback."
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

        # ── Phase 4: Success ──
        if response.status_code == 200:
            in_flight.release()
            if use_cache:
                try:
                    _cache.set(url, query, variables, response.json())
                except Exception as e:
                    logger.warning(f"Failed to cache response: {e}")
            return response

        # ── Phase 5: 429 — set cool-down, drain tokens, sleep ──
        if response.status_code == 429:
            if attempt >= _RETRIES_ON_429:
                in_flight.release()
                cached_data = _cache.get(url, query, variables, ttl=float("inf"))
                if cached_data:
                    logger.info(
                        f"Returning cached response for {graphql_file.name} "
                        f"after 429 exhaustion."
                    )
                    return Response(
                        status_code=200,
                        content=json.dumps(cached_data).encode("utf-8"),
                        headers={
                            "Content-Type": "application/json",
                            "X-Offline-Fallback": "true",
                        },
                    )
                logger.error(
                    f"[AniList] Rate limited (429) exhausted "
                    f"{_RETRIES_ON_429} retries. Giving up."
                )
                response.raise_for_status()

            # Compute cool-down delay and set state (inside lock)
            in_flight.release()  # release before sleeping
            retry_after = _parse_retry_after(response)
            delay = _compute_cool_down_delay(url, retry_after=retry_after, attempt=attempt)

            with lock:
                _DOMAIN_COOLDOWN_UNTIL[domain] = time.time() + delay
                _drain_token_bucket(url)  # prevent burst after cool-down

            logger.warning(
                f"[AniList] Rate limited (429). Cooling down {delay:.1f}s "
                f"(attempt {attempt + 1}/{_RETRIES_ON_429}, "
                f"source: {'server' if retry_after else 'jittered'})"
            )

            # ── Sleep outside lock ──
            time.sleep(delay)
            continue

        # ── Phase 6: 5xx — try cache fallback ──
        if response.status_code >= 500:
            in_flight.release()
            cached_data = _cache.get(url, query, variables, ttl=float("inf"))
            if cached_data:
                logger.info(
                    f"Returning cached response for {graphql_file.name} "
                    f"after 5xx."
                )
                return Response(
                    status_code=200,
                    content=json.dumps(cached_data).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "X-Offline-Fallback": "true",
                    },
                )
            logger.error(
                f"[AniList] API request failed with status code "
                f"{response.status_code}"
            )
            response.raise_for_status()

        # ── Phase 7: Other 4xx — don't retry ──
        in_flight.release()
        logger.error(
            f"[AniList] API request failed with status code "
            f"{response.status_code}"
        )
        response.raise_for_status()

    raise RuntimeError(
        "Unreachable: GraphQL query execution loop ended without returning or raising."
    )


def invalidate_graphql_cache(url: str, graphql_file: Path, variables: dict):
    """Utility to invalidate a specific cache entry from outside."""
    query = load_graphql_from_file(graphql_file)
    _cache.invalidate(url, query, variables)
