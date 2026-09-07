"""Resolve NTULearn authentication from browser, environment, or cache."""

import os

from .cache import read_cached_cookie, write_cached_cookie
from .cookie import read_bbrouter_cookie


def resolve_cookie() -> str:
    cookie = read_bbrouter_cookie()

    if cookie:
        write_cached_cookie(cookie)
        return cookie

    explicit = os.getenv("NTULEARN_COOKIE", "").strip()

    if explicit:
        return explicit

    cached = read_cached_cookie()

    if cached:
        return cached

    raise RuntimeError(
        "No NTULearn session found. Log into "
        "https://ntulearn.ntu.edu.sg in your browser and try again."
    )
