from __future__ import annotations

import re
from typing import Any


def resource_id(resource: Any) -> int | None:
    url = getattr(resource, "url", "") or ""
    match = re.search(r"/(\d+)/?$", url)
    return int(match.group(1)) if match else None


def resource_name(resource: Any) -> str:
    return getattr(resource, "name", "") or ""
