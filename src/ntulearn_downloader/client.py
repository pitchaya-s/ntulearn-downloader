"""Minimal Blackboard REST client used by ntulearn-downloader."""

import asyncio
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx


class BbRouterExpiredError(Exception):
    """Raised when the NTULearn session cookie has expired."""

    def __init__(self) -> None:
        super().__init__(
            "NTULearn session expired. "
            "Open NTULearn in your browser and log in again."
        )


class BlackboardAPIError(Exception):
    """Raised for Blackboard API errors other than HTTP 401."""

    def __init__(
        self,
        status_code: int,
        body: str,
        *,
        path: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.body = body
        self.path = path

        where = f" at {path}" if path else ""
        snippet = body[:300].replace("\n", " ")

        super().__init__(
            f"Blackboard API error {status_code}{where}: {snippet}"
        )


class NTULearnClient:
    def __init__(
        self,
        base_url: str,
        cookie_value: str,
    ) -> None:
        if cookie_value.startswith("BbRouter="):
            cookie_value = cookie_value.removeprefix("BbRouter=")

        self._base_url = base_url.rstrip("/")

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Cookie": f"BbRouter={cookie_value}",
                "Accept": "application/json",
            },
            timeout=30.0,
            follow_redirects=True,
        )

        # External Blackboard CDN downloads should not receive
        # the user's NTULearn cookie.
        self._external_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self._client.aclose()
        await self._external_client.aclose()

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        response = await self._client.get(
            path,
            params=params,
        )

        if response.status_code == 401:
            raise BbRouterExpiredError()

        if not response.is_success:
            raise BlackboardAPIError(
                response.status_code,
                response.text,
                path=path,
            )

        return response.json()

    async def _get_paginated(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> list[Any]:
        params = dict(params or {})
        params.setdefault("limit", 200)

        results: list[Any] = []

        while True:
            data = await self._get(path, params)
            results.extend(data.get("results", []))

            next_page = (
                data.get("paging", {})
                .get("nextPage")
            )

            if not next_page:
                break

            next_page = next_page.removeprefix(self._base_url)

            path = next_page
            params = {}

        return results

    # ------------------------------------------------------------------
    # Courses
    # ------------------------------------------------------------------

    async def get_my_enrollments(
        self,
    ) -> list[dict[str, Any]]:
        return await self._get_paginated(
            "/learn/api/public/v1/users/me/courses"
        )

    async def get_course(
        self,
        course_id: str,
    ) -> dict[str, Any]:
        return await self._get(
            f"/learn/api/public/v1/courses/{course_id}"
        )

    async def get_courses_batch(
        self,
        course_ids: list[str],
    ) -> list[dict[str, Any]]:
        tasks = [
            self.get_course(course_id)
            for course_id in course_ids
        ]

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        courses: list[dict[str, Any]] = []

        for course_id, result in zip(
            course_ids,
            results,
        ):
            if isinstance(result, Exception):
                courses.append(
                    {
                        "id": course_id,
                        "name": course_id,
                    }
                )
            else:
                courses.append(result)

        return courses

    # ------------------------------------------------------------------
    # Course content
    # ------------------------------------------------------------------

    async def get_course_contents(
        self,
        course_id: str,
    ) -> list[dict[str, Any]]:
        return await self._get_paginated(
            f"/learn/api/public/v1/courses/"
            f"{course_id}/contents"
        )

    async def get_content_children(
        self,
        course_id: str,
        content_id: str,
    ) -> list[dict[str, Any]]:
        return await self._get_paginated(
            f"/learn/api/public/v1/courses/"
            f"{course_id}/contents/"
            f"{content_id}/children"
        )

    async def get_content_item(
        self,
        course_id: str,
        content_id: str,
    ) -> dict[str, Any]:
        return await self._get(
            f"/learn/api/public/v1/courses/"
            f"{course_id}/contents/{content_id}"
        )

    async def get_attachments(
        self,
        course_id: str,
        content_id: str,
    ) -> list[dict[str, Any]]:
        return await self._get_paginated(
            f"/learn/api/public/v1/courses/"
            f"{course_id}/contents/"
            f"{content_id}/attachments"
        )

    async def get_attachment_download_url(
        self,
        course_id: str,
        content_id: str,
        attachment_id: str,
    ) -> str:
        path = (
            f"/learn/api/public/v1/courses/"
            f"{course_id}/contents/{content_id}"
            f"/attachments/{attachment_id}/download"
        )

        response = await self._client.get(
            path,
            follow_redirects=False,
        )

        if response.status_code == 401:
            raise BbRouterExpiredError()

        if response.status_code in (
            301,
            302,
            303,
            307,
            308,
        ):
            location = response.headers.get("location")

            if location:
                return location

        if response.is_success:
            return path

        raise BlackboardAPIError(
            response.status_code,
            response.text,
            path=path,
        )

    # ------------------------------------------------------------------
    # Downloads
    # ------------------------------------------------------------------

    async def download_bytes(
        self,
        url: str,
    ) -> tuple[bytes, str | None]:
        response = await self._download_response(url)

        if response.status_code == 401:
            raise BbRouterExpiredError()

        if not response.is_success:
            raise BlackboardAPIError(
                response.status_code,
                response.text,
                path=url,
            )

        return (
            response.content,
            response.headers.get("content-type"),
        )

    async def _download_response(
        self,
        url: str,
    ) -> httpx.Response:
        parsed = urlsplit(url)

        # Relative NTULearn URL.
        if not parsed.scheme and not parsed.netloc:
            return await self._client.get(url)

        if parsed.scheme not in {"http", "https"}:
            raise ValueError(
                f"Unsafe download URL scheme: {parsed.scheme}"
            )

        base = urlsplit(self._base_url)

        # Same NTULearn origin.
        if (
            parsed.scheme == base.scheme
            and parsed.hostname == base.hostname
            and (
                parsed.port or _default_port(parsed.scheme)
            )
            == (
                base.port or _default_port(base.scheme)
            )
        ):
            path = urlunsplit(
                (
                    "",
                    "",
                    parsed.path or "/",
                    parsed.query,
                    "",
                )
            )

            return await self._client.get(path)

        # Blackboard-hosted CDN/resource.
        host = parsed.hostname or ""

        if host.endswith(".blackboard.com"):
            return await self._external_client.get(url)

        raise ValueError(
            f"Unsafe download URL host: {host}"
        )


def _default_port(
    scheme: str,
) -> int | None:
    if scheme == "http":
        return 80

    if scheme == "https":
        return 443

    return None
