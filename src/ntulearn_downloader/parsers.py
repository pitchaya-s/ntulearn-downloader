"""Extract downloadable Blackboard links from NTULearn HTML."""

from __future__ import annotations

import json

from bs4 import BeautifulSoup


def extract_all_files(
    html_body: str,
) -> list[dict[str, str | None]]:
    if not html_body:
        return []

    soup = BeautifulSoup(
        html_body,
        "html.parser",
    )

    results: list[
        dict[str, str | None]
    ] = []

    for tag in soup.find_all(
        "a",
        href=True,
    ):
        href = tag["href"]

        if "bbcswebdav" not in href:
            continue

        filename = (
            tag.get("data-bbfile")
            or None
        )

        if filename and filename.startswith("{"):
            try:
                parsed = json.loads(filename)

                filename = (
                    parsed.get("linkName")
                    or parsed.get("displayName")
                    or parsed.get("name")
                    or parsed.get("filename")
                    or filename
                )

            except (
                json.JSONDecodeError,
                AttributeError,
            ):
                pass

        results.append(
            {
                "url": href,
                "filename": filename,
                "link_text": (
                    tag.get_text(strip=True)
                    or None
                ),
            }
        )

    return results
