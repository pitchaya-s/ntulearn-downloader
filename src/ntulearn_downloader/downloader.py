"""Recursively traverse NTULearn course content and download files."""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from .auth import resolve_cookie
from .client import BbRouterExpiredError, BlackboardAPIError, NTULearnClient
from .courses import choose_courses, list_courses
from .parsers import extract_all_files

BASE_URL = os.getenv(
    "NTULEARN_BASE_URL",
    "https://ntulearn.ntu.edu.sg",
)


@dataclass
class Stats:
    courses: int = 0
    folders: int = 0
    items: int = 0
    downloaded: int = 0
    skipped: int = 0
    failed: int = 0
    bytes_downloaded: int = 0


def sanitize_component(
    value: str,
    fallback: str = "untitled",
) -> str:
    value = re.sub(
        r'[\\/*?:"<>|\x00-\x1f]',
        "_",
        value or "",
    )
    value = re.sub(r"\s+", " ", value).strip().strip(".")

    if value in {"", ".", ".."}:
        return fallback

    return value[:180].rstrip()


def filename_from_url(url: str) -> str:
    path = urlsplit(url).path
    return unquote(path.rsplit("/", 1)[-1]) or "download"


def human_bytes(size: int) -> str:
    value = float(size)

    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"

        value /= 1024

    return f"{size} B"


async def resolve_content_files(
    client: NTULearnClient,
    course_id: str,
    content_id: str,
) -> list[tuple[str, str | None]]:
    item = await client.get_content_item(
        course_id,
        content_id,
    )

    handler_id = (
        item.get("contentHandler") or {}
    ).get("id")

    pairs: list[tuple[str, str | None]] = []

    if handler_id == "resource/x-bb-file":
        attachments = await client.get_attachments(
            course_id,
            content_id,
        )

        for attachment in attachments:
            attachment_id = attachment.get("id")

            if not attachment_id:
                continue

            url = await client.get_attachment_download_url(
                course_id,
                content_id,
                attachment_id,
            )

            pairs.append(
                (url, attachment.get("fileName"))
            )

    else:
        body = item.get("body") or ""
        files = extract_all_files(body)

        if not files:
            description = item.get("description") or {}

            raw = (
                description.get("rawText")
                if isinstance(description, dict)
                else description
            ) or ""

            files = extract_all_files(raw)

        for file in files:
            url = file.get("url")

            if url:
                pairs.append(
                    (url, file.get("filename"))
                )

    return list(dict.fromkeys(pairs))


async def download_item_files(
    client: NTULearnClient,
    *,
    course_id: str,
    content_id: str,
    destination: Path,
    overwrite: bool,
    dry_run: bool,
    stats: Stats,
) -> None:
    try:
        pairs = await resolve_content_files(
            client,
            course_id,
            content_id,
        )
    except (BlackboardAPIError, ValueError) as exc:
        stats.failed += 1
        print(
            f"    ! could not inspect {content_id}: {exc}",
            file=sys.stderr,
        )
        return

    used_names: set[str] = set()

    for url, detected_filename in pairs:
        filename = sanitize_component(
            detected_filename or filename_from_url(url),
            "download",
        )

        candidate = filename
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        n = 2

        while candidate in used_names:
            candidate = f"{stem} ({n}){suffix}"
            n += 1

        used_names.add(candidate)

        dest = destination / candidate

        if dest.exists() and not overwrite:
            stats.skipped += 1
            print(f"    = {dest} (exists)")
            continue

        if dry_run:
            stats.downloaded += 1
            print(f"    -> {dest}")
            continue

        destination.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            content, _content_type = (
                await client.download_bytes(url)
            )

            temp = dest.with_name(
                dest.name + ".part"
            )

            temp.write_bytes(content)
            temp.replace(dest)

            stats.downloaded += 1
            stats.bytes_downloaded += len(content)

            print(
                f"    + {dest} "
                f"({human_bytes(len(content))})"
            )

        except (
            BlackboardAPIError,
            ValueError,
            OSError,
        ) as exc:
            stats.failed += 1

            try:
                dest.with_name(
                    dest.name + ".part"
                ).unlink(missing_ok=True)
            except OSError:
                pass

            print(
                f"    ! failed {dest.name}: {exc}",
                file=sys.stderr,
            )


async def walk_content(
    client: NTULearnClient,
    *,
    course_id: str,
    items: list[dict[str, Any]],
    destination: Path,
    overwrite: bool,
    dry_run: bool,
    stats: Stats,
    visited: set[str],
    depth: int = 0,
    max_depth: int = 30,
) -> None:
    if depth > max_depth:
        stats.failed += 1
        return

    for item in items:
        content_id = item.get("id")

        if not content_id or content_id in visited:
            continue

        visited.add(content_id)
        stats.items += 1

        title = sanitize_component(
            item.get("title") or content_id,
            content_id,
        )

        has_children = bool(
            item.get("hasChildren")
        )

        item_destination = (
            destination / title
            if has_children
            else destination
        )

        if has_children:
            stats.folders += 1
            print(f"  [{title}]")

        await download_item_files(
            client,
            course_id=course_id,
            content_id=content_id,
            destination=item_destination,
            overwrite=overwrite,
            dry_run=dry_run,
            stats=stats,
        )

        if not has_children:
            continue

        try:
            children = (
                await client.get_content_children(
                    course_id,
                    content_id,
                )
            )
        except BlackboardAPIError as exc:
            stats.failed += 1
            print(
                f"    ! could not open {title}: {exc}",
                file=sys.stderr,
            )
            continue

        await walk_content(
            client,
            course_id=course_id,
            items=children,
            destination=item_destination,
            overwrite=overwrite,
            dry_run=dry_run,
            stats=stats,
            visited=visited,
            depth=depth + 1,
            max_depth=max_depth,
        )


async def run(args: argparse.Namespace) -> int:
    output = Path(
        args.output
    ).expanduser().resolve()

    if not args.dry_run:
        output.mkdir(
            parents=True,
            exist_ok=True,
        )

    client = NTULearnClient(
        BASE_URL,
        resolve_cookie(),
    )

    stats = Stats()

    try:
        courses = await list_courses(
            client,
            include_disabled=args.include_disabled,
        )

        if args.all:
            selected = courses
        else:
            selected = choose_courses(
                courses,
                args.course or [],
            )

        if not selected:
            print("No matching NTULearn courses found.")
            return 1

        print(f"Destination: {output}")
        print(f"Courses: {len(selected)}")

        for course in selected:
            course_id = course["id"]
            course_title = sanitize_component(
                course["title"],
                course_id,
            )

            stats.courses += 1

            print(
                f"\n=== {course_title} ==="
            )

            try:
                top_level = (
                    await client.get_course_contents(
                        course_id
                    )
                )
            except BlackboardAPIError as exc:
                stats.failed += 1
                print(
                    f"! could not list course: {exc}",
                    file=sys.stderr,
                )
                continue

            await walk_content(
                client,
                course_id=course_id,
                items=top_level,
                destination=output / course_title,
                overwrite=args.overwrite,
                dry_run=args.dry_run,
                stats=stats,
                visited=set(),
                max_depth=args.max_depth,
            )

    except BbRouterExpiredError:
        print(
            "NTULearn session expired. "
            "Log into NTULearn again.",
            file=sys.stderr,
        )
        return 2

    finally:
        await client.close()

    print("\n=== Summary ===")
    print(f"Courses processed: {stats.courses}")
    print(f"Downloaded:        {stats.downloaded}")
    print(f"Already present:   {stats.skipped}")
    print(f"Failed:            {stats.failed}")

    if not args.dry_run:
        print(
            f"Data downloaded:   "
            f"{human_bytes(stats.bytes_downloaded)}"
        )

    return 0 if stats.failed == 0 else 3
