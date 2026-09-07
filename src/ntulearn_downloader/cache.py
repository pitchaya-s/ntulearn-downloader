"""Best-effort storage of the last working BbRouter cookie."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_SERVICE = "ntulearn-downloader"
_USERNAME = "BbRouter"


def _get_keyring(
    module: Any | None = None,
) -> Any | None:
    if module is not None:
        return module

    try:
        import keyring
    except ImportError:
        return None

    return keyring


def read_cached_cookie(
    *,
    module: Any | None = None,
) -> str | None:
    keyring = _get_keyring(module)

    if keyring is None:
        return None

    try:
        value = keyring.get_password(
            _SERVICE,
            _USERNAME,
        )
    except Exception as exc: # noqa: BLE001
        logger.debug(
            "Cookie cache read failed: %s",
            exc,
        )
        return None

    if _is_valid(value):
        return value

    return None


def write_cached_cookie(
    value: str,
    *,
    module: Any | None = None,
) -> bool:
    if not _is_valid(value):
        return False

    keyring = _get_keyring(module)

    if keyring is None:
        return False

    try:
        keyring.set_password(
            _SERVICE,
            _USERNAME,
            value,
        )
    except Exception as exc: # noqa: BLE001
        logger.debug(
            "Cookie cache write failed: %s",
            exc,
        )
        return False

    return True


def delete_cached_cookie(
    *,
    module: Any | None = None,
) -> None:
    keyring = _get_keyring(module)

    if keyring is None:
        return

    try:
        keyring.delete_password(
            _SERVICE,
            _USERNAME,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "Cookie cache delete failed: %s",
            exc,
        )


def _is_valid(
    value: str | None,
) -> bool:
    return bool(value) and value.startswith("expires:")
