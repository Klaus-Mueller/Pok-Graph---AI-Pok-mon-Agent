"""PokéGraph query client and PokéAPI source adapters."""

from .errors import (
    EntityNotFoundError,
    GraphUnavailableError,
    IncompatibleGameContextError,
    InvalidQueryParameterError,
    PokeGraphError,
    QueryTimeoutError,
    SourceFetchError,
    SourceNormalizationError,
)
from .graph.client import PokeGraphClient
from .graph.models import GameContext, QueryPage

__version__ = "0.1.0"

__all__ = [
    "EntityNotFoundError",
    "GameContext",
    "GraphUnavailableError",
    "IncompatibleGameContextError",
    "InvalidQueryParameterError",
    "PokeGraphClient",
    "PokeGraphError",
    "QueryPage",
    "QueryTimeoutError",
    "SourceFetchError",
    "SourceNormalizationError",
    "__version__",
]
