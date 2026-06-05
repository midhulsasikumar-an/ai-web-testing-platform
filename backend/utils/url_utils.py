"""URL canonicalization utilities.

Different code paths may receive the same logical website in slightly
different forms:

    https://www.saucedemo.com
    https://www.saucedemo.com/
    HTTPS://WWW.Saucedemo.COM
    https://www.saucedemo.com/?utm_source=test

If each variant is stored verbatim, every consumer that groups by URL
(dashboards, history pages, reports, comparisons, AI telemetry) ends
up with duplicate entries. This module produces a single canonical
string for the same logical website so grouping, filtering, and
merging all work consistently.

Rules (in order)
----------------

1. If the input is empty / not a string, return it unchanged.
2. Strip whitespace.
3. Lower-case the scheme and host.
4. If no scheme is present, default to ``https://`` (the user typed
   a bare ``example.com`` -- we treat it as https).
5. Drop an empty ``path`` (i.e. a trailing ``/`` at the end of the
   origin).
6. Drop common tracking query parameters (``utm_*``, ``fbclid``,
   ``gclid``) but preserve any other query.
7. Drop a trailing ``?`` if the query is now empty.
8. Drop a ``default`` port (``80`` for http, ``443`` for https).
9. Drop a trailing ``/`` again after the steps above.
10. Drop a fragment (the ``#`` portion is a UI affordance, not part
    of the canonical website identity).

Anything that is not a string, or is malformed in a way the parser
cannot handle, is returned unchanged. We never raise -- the goal is
best-effort canonicalization, not validation.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "gbraid",
    "wbraid",
    "mc_cid",
    "mc_eid",
    "yclid",
    "msclkid",
    "igshid",
    "ref",
}


def _ensure_scheme(url: str) -> str:
    if "://" in url:
        return url
    return f"https://{url}"


def _drop_default_port(netloc: str, scheme: str) -> str:
    if not netloc:
        return netloc
    if "@" in netloc:
        userinfo, _, host_part = netloc.rpartition("@")
        host = host_part
        userinfo_prefix = f"{userinfo}@"
    else:
        host = netloc
        userinfo_prefix = ""
    if ":" not in host:
        return netloc
    host_only, _, port = host.rpartition(":")
    if not port.isdigit():
        return netloc
    if (scheme == "https" and port == "443") or (scheme == "http" and port == "80"):
        return f"{userinfo_prefix}{host_only}"
    return netloc


def canonicalize_url(url: Any) -> Any:
    """Return a canonical form of ``url`` suitable for grouping.

    Non-string inputs are returned unchanged. Malformed URLs are also
    returned unchanged (the parser will simply emit them back as-is).
    """
    if not isinstance(url, str):
        return url
    text = url.strip()
    if not text:
        return text

    with_scheme = _ensure_scheme(text)
    try:
        parts = urlsplit(with_scheme)
    except ValueError:
        return text

    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc
    if netloc:
        # Lower-case the host portion but preserve any userinfo
        if "@" in netloc:
            userinfo, _, host = netloc.rpartition("@")
            host = host.lower()
            netloc = f"{userinfo}@{host}"
        else:
            netloc = netloc.lower()
        netloc = _drop_default_port(netloc, scheme)

    # Path: strip a single trailing slash on an otherwise-empty path.
    path = parts.path or ""
    if path == "/":
        path = ""
    # If the path is just "/" repeated, collapse it to nothing too.
    while path.endswith("/") and path != "/":
        path = path[:-1]

    # Query: drop tracking parameters, preserve the rest, normalise order.
    query_pairs: Iterable = []
    if parts.query:
        try:
            query_pairs = parse_qsl(parts.query, keep_blank_values=True)
        except ValueError:
            query_pairs = []
    filtered_pairs = [
        (key, value)
        for key, value in query_pairs
        if str(key).lower() not in _TRACKING_PARAMS
    ]
    # Sort to make the canonical form deterministic.
    filtered_pairs.sort(key=lambda kv: (str(kv[0]).lower(), str(kv[1])))
    query = urlencode(filtered_pairs, doseq=True)

    # Fragment: always dropped for canonical identity.
    fragment = ""

    rebuilt = urlunsplit((scheme, netloc, path, query, fragment))
    if rebuilt.endswith("?"):
        rebuilt = rebuilt[:-1]
    # Final safety: strip any trailing slash that re-appeared.
    if rebuilt.endswith("/") and "://" in rebuilt:
        prefix, _, tail = rebuilt.partition("://")
        if "/" not in tail:
            rebuilt = prefix + "://" + tail
    return rebuilt


def canonical_hostname(url: Any) -> str:
    """Return the host portion of a canonical URL, or ``""``."""
    canonical = canonicalize_url(url)
    if not isinstance(canonical, str) or not canonical:
        return ""
    try:
        return (urlsplit(canonical).hostname or "").lower()
    except ValueError:
        return ""


def extract_website(url: Any) -> str:
    """Return the canonical URL string for use as a ``website`` field."""
    return canonicalize_url(url) if isinstance(url, str) else ""


__all__ = [
    "canonicalize_url",
    "canonical_hostname",
    "extract_website",
]
