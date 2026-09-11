from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CACHE_FORMAT_VERSION = 1


def cache_key(resource: str, identifier: str | int, format_version: int = CACHE_FORMAT_VERSION) -> str:
    return f"{resource}/{identifier}/v{format_version}"


@dataclass(frozen=True)
class CacheRecord:
    resource: str
    identifier: str
    retrieved_at: datetime
    source_url: str
    source_version: str | None
    adapter_version: str
    payload_hash: str | None
    data: dict[str, Any]


class DiskCache:
    """Normalized source payloads on disk. Hits preserve the original retrieved_at."""

    def __init__(self, root: Path | None, *, ttl_s: float | None = None) -> None:
        self._root = root
        self._ttl_s = ttl_s

    def get(self, resource: str, identifier: str | int) -> CacheRecord | None:
        path = self._path(resource, identifier)
        if path is None or not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(payload.get("format_version", 0)) != CACHE_FORMAT_VERSION:
            return None
        retrieved_at = datetime.fromisoformat(payload["retrieved_at"])
        expires_at = payload.get("expires_at")
        if expires_at:
            expiry = datetime.fromisoformat(expires_at)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) >= expiry:
                return None
        elif self._ttl_s is not None:
            age = datetime.now(timezone.utc) - retrieved_at
            if age.total_seconds() >= self._ttl_s:
                return None
        return CacheRecord(
            resource=payload["resource"],
            identifier=str(payload["identifier"]),
            retrieved_at=retrieved_at,
            source_url=payload.get("source_url") or "",
            source_version=payload.get("source_version"),
            adapter_version=payload.get("adapter_version") or "",
            payload_hash=payload.get("payload_hash"),
            data=payload["data"],
        )

    def put(
        self,
        resource: str,
        identifier: str | int,
        data: dict[str, Any],
        *,
        retrieved_at: datetime,
        source_url: str,
        source_version: str | None,
        adapter_version: str,
        payload_hash: str | None,
    ) -> None:
        path = self._path(resource, identifier)
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        expires_at = None
        if self._ttl_s is not None:
            expires_at = datetime.fromtimestamp(
                retrieved_at.timestamp() + self._ttl_s,
                tz=timezone.utc,
            ).isoformat()
        document = {
            "format_version": CACHE_FORMAT_VERSION,
            "resource": resource,
            "identifier": str(identifier),
            "retrieved_at": retrieved_at.isoformat(),
            "expires_at": expires_at,
            "source_url": source_url,
            "source_version": source_version,
            "adapter_version": adapter_version,
            "payload_hash": payload_hash,
            "data": data,
        }
        path.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")

    def _path(self, resource: str, identifier: str | int) -> Path | None:
        if self._root is None:
            return None
        safe = str(identifier).replace("/", "_")
        return self._root / resource / safe / f"v{CACHE_FORMAT_VERSION}.json"
