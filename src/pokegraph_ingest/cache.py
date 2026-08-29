from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EnrichmentCache:
    """Tracks which PokéAPI resources have already been enriched this run."""

    location_areas: set[int] = field(default_factory=set)
    locations: set[int] = field(default_factory=set)
    versions: set[int] = field(default_factory=set)
    version_groups: set[int] = field(default_factory=set)
    types: set[int] = field(default_factory=set)
    moves: set[int] = field(default_factory=set)
    evolution_chains: set[int] = field(default_factory=set)
    source_ensured: bool = False
