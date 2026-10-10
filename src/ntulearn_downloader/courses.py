"""Discover and filter the user's NTULearn courses."""

import re
from typing import Any

from .client import NTULearnClient

_ACADEMIC_YEAR_RE = re.compile(
    r"(?<!\d)(?:AY\s*)?((?:19|20)?\d{2})\s*[-/–]\s*((?:20)?\d{2})(?!\d)",
    re.IGNORECASE,
)
_COMPACT_TERM_RE = re.compile(
    r"(?<![A-Z0-9])(?:AY\s*)?((?:20)?\d{2})\s*S([12])\b",
    re.IGNORECASE,
)
_SEMESTER_RE = re.compile(
    r"\b(?:semester|sem)\s*([12])\b",
    re.IGNORECASE,
)


async def list_courses(
    client: NTULearnClient,
    *,
    include_disabled: bool,
) -> list[dict[str, Any]]:
    enrollments = await client.get_my_enrollments()

    if not include_disabled:
        enrollments = [
            e
            for e in enrollments
            if (e.get("availability") or {}).get("available") == "Yes"
        ]

    course_ids = [
        e["courseId"]
        for e in enrollments
        if e.get("courseId")
    ]

    if not course_ids:
        return []

    courses = await client.get_courses_batch(course_ids)

    last_accessed = {
        e["courseId"]: e.get("lastAccessed")
        for e in enrollments
        if e.get("courseId")
    }

    result = []

    for course in courses:
        course_id = course.get("id")

        if not course_id:
            continue

        result.append(
            {
                "id": course_id,
                "courseId": course.get("courseId"),
                "title": (
                    course.get("name")
                    or course.get("displayName")
                    or course_id
                ),
                "lastAccessed": last_accessed.get(course_id),
            }
        )

    result.sort(
        key=lambda c: c.get("lastAccessed") or "",
        reverse=True,
    )

    return result


def choose_courses(
    courses: list[dict[str, Any]],
    patterns: list[str],
) -> list[dict[str, Any]]:
    if not patterns:
        return courses

    patterns = [p.casefold() for p in patterns]

    return [
        course
        for course in courses
        if any(
            p in str(course.get("title", "")).casefold()
            or p in str(course.get("id", "")).casefold()
            for p in patterns
        )
    ]


def filter_courses_by_time(
    courses: list[dict[str, Any]],
    *,
    year: int | None = None,
    semester: int | None = None,
) -> list[dict[str, Any]]:
    if year is None and semester is None:
        return courses

    selected = []

    for course in courses:
        label = " ".join(
            str(course.get(field) or "")
            for field in ("title", "id", "courseId")
        )
        compact_terms = _COMPACT_TERM_RE.findall(label)

        if year is not None:
            labeled_years = {
                int(value) + (2000 if len(value) == 2 else 0)
                for academic_year in _ACADEMIC_YEAR_RE.findall(label)
                for value in academic_year
            }
            labeled_years.update(
                int(value) + (2000 if len(value) == 2 else 0)
                for value, _ in compact_terms
            )
            if year not in labeled_years:
                continue

        semesters = set(_SEMESTER_RE.findall(label))
        semesters.update(semester_label for _, semester_label in compact_terms)
        if (
            semester is not None
            and str(semester) not in semesters
        ):
            continue

        selected.append(course)

    return selected
