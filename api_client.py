"""Упрощённый HTTP-клиент для miniapp_api."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, MutableMapping, Optional

import aiohttp

from config import API_BASE_URL, BOT_TOKEN

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=15, connect=5)


def _build_url(path: str) -> str:
    cleaned = path if path.startswith("/") else f"/{path}"
    return f"{API_BASE_URL.rstrip('/')}{cleaned}"


async def api_get(
    path: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    headers: Optional[Mapping[str, str]] = None,
    use_bot_token: bool = False,
) -> aiohttp.ClientResponse:
    return await _request(
        "GET",
        path,
        params=params,
        headers=headers,
        use_bot_token=use_bot_token,
    )


async def api_post(
    path: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    json: Optional[Any] = None,
    data: Optional[MutableMapping[str, Any] | Iterable[tuple[str, Any]]] = None,
    headers: Optional[Mapping[str, str]] = None,
    use_bot_token: bool = False,
) -> aiohttp.ClientResponse:
    return await _request(
        "POST",
        path,
        params=params,
        json=json,
        data=data,
        headers=headers,
        use_bot_token=use_bot_token,
    )


async def api_delete(
    path: str,
    *,
    headers: Optional[Mapping[str, str]] = None,
    use_bot_token: bool = False,
) -> aiohttp.ClientResponse:
    return await _request(
        "DELETE",
        path,
        headers=headers,
        use_bot_token=use_bot_token,
    )


async def _request(
    method: str,
    path: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    json: Optional[Any] = None,
    data: Optional[MutableMapping[str, Any] | Iterable[tuple[str, Any]]] = None,
    headers: Optional[Mapping[str, str]] = None,
    use_bot_token: bool = False,
) -> aiohttp.ClientResponse:
    url = _build_url(path)
    session_headers = {}
    if headers:
        session_headers.update(headers)
    if use_bot_token:
        session_headers.setdefault("Authorization", BOT_TOKEN)
    session = aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT)
    try:
        response = await session.request(
            method,
            url,
            params=params,
            json=json,
            data=data,
            headers=session_headers,
        )
        return ResponseWrapper(session, response)
    except Exception:
        await session.close()
        raise


class ResponseWrapper:
    """Контекстный менеджер для автоматического закрытия ClientSession."""

    __slots__ = ("_session", "_response")

    def __init__(self, session: aiohttp.ClientSession, response: aiohttp.ClientResponse):
        self._session = session
        self._response = response

    def __await__(self):
        return self._finalize().__await__()

    async def _finalize(self) -> aiohttp.ClientResponse:
        return self._response

    async def json(self) -> Any:
        async with self:
            return await self._response.json()

    async def text(self) -> str:
        async with self:
            return await self._response.text()

    async def read(self) -> bytes:
        async with self:
            return await self._response.read()

    @property
    def status(self) -> int:
        return self._response.status

    async def __aenter__(self) -> aiohttp.ClientResponse:
        return self._response

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._session.close()

