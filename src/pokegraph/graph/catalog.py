from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from pokegraph.errors import InvalidQueryParameterError

_PACKAGE_QUERIES = Path(__file__).resolve().parent.parent / "queries"
_MAPPED_PACKAGE = "pokegraph.queries"
_REPO_QUERIES = Path(__file__).resolve().parents[3] / "queries"


def catalog_dir() -> Path:
    """Return the Cypher catalog directory (installed package or repo checkout)."""
    if (_PACKAGE_QUERIES / "encounters").is_dir():
        return _PACKAGE_QUERIES
    try:
        packaged = files(_MAPPED_PACKAGE)
        packaged_path = Path(str(packaged))
        if (packaged_path / "encounters").is_dir():
            return packaged_path
    except (ModuleNotFoundError, TypeError, FileNotFoundError, AttributeError):
        pass
    try:
        packaged = files("pokegraph").joinpath("queries")
        packaged_path = Path(str(packaged))
        if (packaged_path / "encounters").is_dir():
            return packaged_path
    except (ModuleNotFoundError, TypeError, FileNotFoundError):
        pass
    if (_REPO_QUERIES / "encounters").is_dir():
        return _REPO_QUERIES
    raise FileNotFoundError(
        "PokéGraph Cypher catalog was not found. Install the package with query files "
        "or run from the repository checkout."
    )


def catalog_file(relative_path: str) -> Path:
    path = catalog_dir().joinpath(*relative_path.split("/"))
    if not path.is_file():
        raise InvalidQueryParameterError(f"Catalog file {relative_path} is missing.")
    return path


def strip_cypher_comments(text: str) -> str:
    lines = [line for line in text.splitlines() if not line.strip().startswith("//")]
    return "\n".join(lines).strip()


def load_cypher(relative_path: str) -> str:
    return strip_cypher_comments(catalog_file(relative_path).read_text(encoding="utf-8"))
