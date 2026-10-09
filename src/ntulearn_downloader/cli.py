"""Command-line interface for ntulearn-downloader."""

import argparse
import asyncio
import os
import sys

from .downloader import run


def _parse_year(value: str) -> int:
    if not value.isdecimal() or len(value) not in {2, 4}:
        raise argparse.ArgumentTypeError(
            "year must be 2 or 4 digits, such as 25 or 2025"
        )

    year = int(value)
    return year + 2000 if len(value) == 2 else year


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ntulearn-download",
        description="Recursively download files from NTULearn courses.",
    )

    parser.add_argument(
        "-o",
        "--output",
        default=os.getenv("NTULEARN_DOWNLOAD_DIR", "./NTULearn"),
        help="Destination root (default: ./NTULearn).",
    )

    selection = parser.add_mutually_exclusive_group(required=True)

    selection.add_argument(
        "--all",
        action="store_true",
        help="Download all available courses.",
    )

    selection.add_argument(
        "-c",
        "--course",
        action="append",
        metavar="TEXT",
        help="Download matching course. Can be repeated.",
    )

    parser.add_argument(
        "--include-disabled",
        action="store_true",
        help="Include unavailable/old courses.",
    )

    parser.add_argument(
        "-y",
        "--year",
        type=_parse_year,
        metavar="YEAR",
        help="Filter by academic year start (e.g. 2025 or 25).",
    )

    parser.add_argument(
        "-s",
        "--semester",
        type=int,
        choices=(1, 2),
        metavar="1|2",
        help="Filter by semester.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing files.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show downloads without writing files.",
    )

    parser.add_argument(
        "--max-depth",
        type=int,
        default=30,
        help="Maximum content-folder depth.",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.max_depth < 1:
        parser.error("--max-depth must be at least 1")

    try:
        code = asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        code = 130
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        code = 2

    raise SystemExit(code)


if __name__ == "__main__":
    main()
