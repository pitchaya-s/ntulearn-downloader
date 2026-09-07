"""Read the NTULearn BbRouter cookie from local browsers."""

import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

NTULEARN_DOMAIN = "ntulearn.ntu.edu.sg"
COOKIE_NAME = "BbRouter"

DEFAULT_BROWSERS = (
    "firefox",
    "chrome",
    "edge",
    "brave",
)


def read_bbrouter_cookie(
    *,
    browsers: tuple[str, ...] = DEFAULT_BROWSERS,
    module: Any | None = None,
    retries: int = 2,
    retry_delay: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> str | None:
    """Return a valid BbRouter cookie from a supported browser."""

    if module is None:
        try:
            import browser_cookie3
        except ImportError:
            return None

        module = browser_cookie3

    delay = retry_delay

    for attempt in range(retries + 1):
        for browser in browsers:
            getter = getattr(
                module,
                browser,
                None,
            )

            if getter is None:
                continue

            try:
                cookie_jar = getter(
                    domain_name=NTULEARN_DOMAIN
                )
            except Exception as exc: # noqa: BLE001
                logger.debug(
                    "Could not read %s cookies: %s",
                    browser,
                    exc,
                )
                continue

            for cookie in cookie_jar:
                if (
                    cookie.name == COOKIE_NAME
                    and _is_valid(cookie.value)
                ):
                    logger.debug(
                        "Found BbRouter cookie in %s",
                        browser,
                    )

                    return cookie.value

        if attempt < retries:
            sleep(delay)
            delay *= 2

    return None


def _is_valid(
    value: str | None,
) -> bool:
    return bool(value) and value.startswith("expires:")
