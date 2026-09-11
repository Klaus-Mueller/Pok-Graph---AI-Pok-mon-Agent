from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from neo4j import READ_ACCESS, AsyncDriver, AsyncGraphDatabase, Query
from neo4j.exceptions import (
    ClientError,
    ServiceUnavailable,
    SessionExpired,
    TransientError,
)

from pokegraph.config import Neo4jSettings
from pokegraph.errors import GraphUnavailableError, QueryTimeoutError


def _is_timeout(exc: BaseException) -> bool:
    code = getattr(exc, "code", "") or ""
    text = f"{code} {exc}".lower()
    return "timeout" in text or "timed out" in text

RecordRow = dict[str, Any]
RunFn = Callable[[str, dict[str, Any], float], Awaitable[list[Any]]]


def create_driver(settings: Neo4jSettings, *, read_only: bool = False) -> AsyncDriver:
    auth = settings.read_auth if read_only else settings.write_auth
    return AsyncGraphDatabase.driver(settings.uri, auth=auth)


class GraphConnection:
    """Shared async driver with a session per read operation."""

    def __init__(
        self,
        settings: Neo4jSettings,
        *,
        driver: AsyncDriver | None = None,
        run: RunFn | None = None,
    ) -> None:
        self._settings = settings
        self._driver = driver
        self._owns_driver = driver is None and run is None
        self._run = run

    @classmethod
    def from_environment(cls) -> "GraphConnection":
        return cls(Neo4jSettings.from_environment())

    async def open(self) -> None:
        if self._run is not None:
            return
        if self._driver is None:
            self._driver = create_driver(self._settings, read_only=True)
            self._owns_driver = True
        try:
            await self._driver.verify_connectivity()
        except ServiceUnavailable as exc:
            raise GraphUnavailableError("Neo4j is not reachable.") from exc

    async def close(self) -> None:
        if self._owns_driver and self._driver is not None:
            await self._driver.close()
            self._driver = None

    async def verify_connectivity(self) -> None:
        await self.open()

    async def __aenter__(self) -> "GraphConnection":
        await self.open()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def execute_read(
        self,
        cypher: str,
        params: dict[str, Any],
        *,
        timeout_s: float | None = None,
    ) -> list[Any]:
        timeout = self._settings.query_timeout_s if timeout_s is None else timeout_s
        if self._run is not None:
            try:
                return await self._run(cypher, params, timeout)
            except ServiceUnavailable as exc:
                raise GraphUnavailableError("Neo4j is not reachable.") from exc
        if self._driver is None:
            raise GraphUnavailableError("Graph connection is closed.")
        try:
            async with self._driver.session(
                database=self._settings.database,
                default_access_mode=READ_ACCESS,
            ) as session:
                result = await session.run(Query(cypher, timeout=timeout), **params)
                records = [record async for record in result]
                await result.consume()
                return records
        except ServiceUnavailable as exc:
            raise GraphUnavailableError("Neo4j is not reachable.") from exc
        except SessionExpired as exc:
            raise GraphUnavailableError("The Neo4j session expired.") from exc
        except TransientError as exc:
            if _is_timeout(exc):
                raise QueryTimeoutError("The catalog query timed out.") from exc
            raise GraphUnavailableError("Neo4j is temporarily unavailable.") from exc
        except ClientError as exc:
            if _is_timeout(exc):
                raise QueryTimeoutError("The catalog query timed out.") from exc
            raise
