"""Resolve NTULearn authentication from environment, browser, or cache."""

import os

from dotenv import dotenv_values, find_dotenv

from .cache import read_cached_cookie, write_cached_cookie
from .cookie import read_bbrouter_cookie


def resolve_cookie() -> str:
    explicit = os.getenv("NTULEARN_COOKIE", "").strip()
    if not explicit:
        explicit = (
            dotenv_values(find_dotenv(usecwd=True)).get("NTULEARN_COOKIE") or ""
        ).strip()

    if explicit:
        return explicit

    cookie = read_bbrouter_cookie()

    if cookie:
        write_cached_cookie(cookie)
        return cookie

    cached = read_cached_cookie()

    if cached:
        return cached

    raise RuntimeError(
        "No NTULearn session found. Log into "
        "https://ntulearn.ntu.edu.sg in your browser and try again."
    )
