import httpx
import pytest

from app.ingest import fetch as f

UA = "ZenithBot/1.0 (education; contact via site)"


class Clock:
    def __init__(self):
        self.t = 100.0
        self.slept = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


@pytest.fixture()
def env(monkeypatch):
    c = Clock()
    monkeypatch.setattr(f, "_now", c.now)
    monkeypatch.setattr(f, "_sleep", c.sleep)
    f.reset()
    return c


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_disallowed_path_is_never_requested(env):
    seen = []

    def h(req):
        seen.append(req.url.path)
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private/\n")
        return httpx.Response(200, content=b"data")

    with client(h) as c:
        assert f.fetch("https://a.example/public/x", user_agent=UA, client=c) == b"data"
        with pytest.raises(f.Disallowed):
            f.fetch("https://a.example/private/x", user_agent=UA, client=c)
    assert "/private/x" not in seen and seen.count("/robots.txt") == 1      # robots.txt is cached per host


def test_missing_robots_means_allowed_but_server_error_means_wait(env):
    with client(lambda r: httpx.Response(404) if r.url.path == "/robots.txt" else httpx.Response(200, content=b"ok")) as c:
        assert f.fetch("https://b.example/x", user_agent=UA, client=c) == b"ok"
    f.reset()
    with client(lambda r: httpx.Response(503) if r.url.path == "/robots.txt" else httpx.Response(200, content=b"ok")) as c:
        with pytest.raises(f.Disallowed):
            f.fetch("https://c.example/x", user_agent=UA, client=c)


def test_429_with_retry_after_waits_then_succeeds(env):
    calls = {"n": 0}

    def h(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        calls["n"] += 1
        return httpx.Response(429, headers={"Retry-After": "2"}) if calls["n"] == 1 else httpx.Response(200, content=b"fine")

    with client(h) as c:
        assert f.fetch("https://d.example/x", user_agent=UA, client=c) == b"fine"
    assert any(s >= 2 for s in env.slept)


def test_gives_up_after_repeated_429(env):
    with client(lambda r: httpx.Response(404) if r.url.path == "/robots.txt" else httpx.Response(429)) as c:
        with pytest.raises(f.FetchError):
            f.fetch("https://e.example/x", user_agent=UA, client=c)


def test_oversize_body_is_refused(env):
    big = b"x" * (f.MAX_BYTES + 1)
    with client(lambda r: httpx.Response(404) if r.url.path == "/robots.txt" else httpx.Response(200, content=big)) as c:
        with pytest.raises(f.FetchError, match="too large"):
            f.fetch("https://g.example/x", user_agent=UA, client=c)


def test_requests_to_one_host_are_spaced_at_least_a_second(env):
    with client(lambda r: httpx.Response(404) if r.url.path == "/robots.txt" else httpx.Response(200, content=b"1")) as c:
        f.fetch("https://h.example/a", user_agent=UA, client=c)
        before = env.t
        f.fetch("https://h.example/b", user_agent=UA, client=c)
    assert env.t - before >= 1.0 - 1e-9


def test_only_http_and_https_are_fetched(env):
    with client(lambda r: httpx.Response(200)) as c:
        for bad in ("file:///etc/passwd", "ftp://x/y", "gopher://x"):
            with pytest.raises(f.FetchError):
                f.fetch(bad, user_agent=UA, client=c)
