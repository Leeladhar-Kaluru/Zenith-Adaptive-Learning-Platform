"""A polite HTTP fetcher: obeys robots.txt, spaces requests per host, backs off on 429/503, and caps response size."""
from __future__ import annotations

import time
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

MAX_BYTES = 15 * 1024 * 1024
MIN_GAP_S = 1.0
MAX_RETRIES = 3
MAX_WAIT_S = 60.0

_now = time.monotonic
_sleep = time.sleep
_robots: dict[str, RobotFileParser | None] = {}
_last: dict[str, float] = {}


class FetchError(RuntimeError):
    pass


class Disallowed(FetchError):
    pass


def reset() -> None:
    _robots.clear()
    _last.clear()


def _space_out(host: str) -> None:
    wait = MIN_GAP_S - (_now() - _last.get(host, -1e9))
    if wait > 0:
        _sleep(wait)
    _last[host] = _now()


def _robots_for(origin: str, host: str, user_agent: str, client: httpx.Client) -> RobotFileParser | None:
    if origin in _robots:
        return _robots[origin]
    url, r = f"{origin}/robots.txt", None
    for _ in range(4):
        _space_out(host)
        r = client.get(url, headers={"User-Agent": user_agent})
        if r.status_code not in (301, 302, 303, 307, 308):
            break
        nxt = urljoin(url, r.headers.get("Location", ""))
        if urlsplit(nxt).hostname != host:       # a policy we cannot read from this host is not permission
            raise Disallowed(f"{host} sends robots.txt to another host; not fetching.")
        url = nxt
    else:
        raise Disallowed(f"{host} robots.txt redirects too many times; not fetching.")
    if r.status_code >= 500 or r.status_code in (401, 403, 429):
        raise Disallowed(f"{host} robots.txt is unavailable ({r.status_code}); not fetching until it answers.")
    parser = None
    if r.status_code < 400:
        parser = RobotFileParser()
        parser.parse(r.text.splitlines())
    _robots[origin] = parser          # 4xx: no robots.txt, everything allowed
    return parser


def _retry_after(r: httpx.Response, attempt: int) -> float:
    try:
        return min(MAX_WAIT_S, max(0.0, float(r.headers.get("Retry-After", ""))))
    except ValueError:
        return min(MAX_WAIT_S, 2.0 ** attempt)


def fetch(url: str, *, user_agent: str, client: httpx.Client | None = None) -> bytes:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise FetchError("Only http and https addresses can be fetched.")
    own = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=False)
    try:
        origin, host = f"{parts.scheme}://{parts.netloc}", parts.hostname
        parser = _robots_for(origin, host, user_agent, client)
        if parser is not None and not parser.can_fetch(user_agent, url):
            raise Disallowed(f"robots.txt on {host} does not allow fetching this address.")
        for attempt in range(MAX_RETRIES + 1):
            _space_out(host)
            with client.stream("GET", url, headers={"User-Agent": user_agent}) as r:
                if r.status_code in (429, 503):
                    if attempt == MAX_RETRIES:
                        raise FetchError(f"{host} kept asking us to slow down ({r.status_code}). Try again later.")
                    _sleep(_retry_after(r, attempt))
                    continue
                if r.status_code >= 300:           # redirects are not followed: the checked address is the address fetched
                    raise FetchError(f"{host} answered {r.status_code}.")
                chunks, size = [], 0
                for chunk in r.iter_bytes():
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise FetchError("The file is too large to import.")
                    chunks.append(chunk)
                return b"".join(chunks)
        raise FetchError("Could not fetch the file.")
    finally:
        if own:
            client.close()
