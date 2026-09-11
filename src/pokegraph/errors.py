from __future__ import annotations


class PokeGraphError(Exception):
    """Base error for the PokéGraph client and sources."""


class InvalidQueryParameterError(PokeGraphError):
    """A catalog parameter is missing, unknown, or outside its allowed range."""


class IncompatibleGameContextError(PokeGraphError):
    """A GameVersion and VersionGroup pair is not linked in the graph."""


class EntityNotFoundError(PokeGraphError):
    """A required graph entity id does not exist."""

    def __init__(self, entity: str, entity_id: int) -> None:
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} {entity_id} was not found")


class GraphUnavailableError(PokeGraphError):
    """The database could not be reached."""


class QueryTimeoutError(PokeGraphError):
    """A read query exceeded the configured timeout."""


class SourceFetchError(PokeGraphError):
    """A remote source could not be fetched."""


class SourceNormalizationError(PokeGraphError):
    """A source payload could not be turned into a project model."""
