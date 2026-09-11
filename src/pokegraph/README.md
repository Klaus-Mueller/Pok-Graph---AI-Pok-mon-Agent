# pokegraph

Read-only Python client for the PokéGraph Cypher catalog, plus a PokéAPI source adapter used by ingestion.

Querying the graph never calls PokéAPI. The HTTP layer in [`../pokegraph_api/`](../pokegraph_api/) wraps this client and serves an OpenAPI / Swagger UI.

## Install

```bash
pip install -e .
# ingestion extra (PokeLance + aiohttp):
pip install -e ".[ingest]"
# HTTP specification UI (FastAPI / Swagger):
pip install -e ".[api]"
```

## Query the catalog

```python
from pokegraph import PokeGraphClient

async with PokeGraphClient.from_environment() as graph:
    areas = await graph.find_location_areas(name="pallet-town", limit=10)
    moves = await graph.learnset_for_pokemon(pokemon_id=25, version_id=15)
```

`learnset_for_pokemon` and other learnset methods resolve `GameVersion → VersionGroup`. If both ids are supplied and are not linked, the client raises `IncompatibleGameContextError`.

Empty pages mean no matching records. Missing required ids raise `EntityNotFoundError`.

Matchup methods report stored type charts only. They do not claim generation-specific battle rules.

A ready-to-run script lives at [`examples/query_catalog.py`](../../examples/query_catalog.py).

## OpenAPI specification UI

Same idea as the [Neo4j Aura API specification](https://neo4j.com/docs/aura/platform/api/specification/): browse the contract and use **Try it out** against the connected database.

```bash
pip install -e ".[api]"
PYTHONPATH=src python -m pokegraph_api
# or: pokegraph-api
```

Then open:

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (`/` redirects here)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- Raw OpenAPI: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

The UI talks to the same Neo4j settings as ingest (`.env`). Example IDs from HeartGold/SoulSilver are prefilled (`pokemon_id=25`, `version_id=15`, `location_area_id=184`).

## Configuration

| Variable | Purpose |
| --- | --- |
| `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` | Write or default connection |
| `NEO4J_READ_USERNAME` / `NEO4J_READ_PASSWORD` | Optional read-only database user |
| `NEO4J_DATABASE` | Database name (`neo4j`) |
| `POKEGRAPH_QUERY_TIMEOUT_S` | Per-query timeout (default 30) |
| `POKEGRAPH_MAX_PAGE_SIZE` | Maximum `$limit` (default 200) |

Driver `READ_ACCESS` does not replace database permissions. Use a read credential when the database has one.

The client verifies connectivity without applying schema. Schema apply stays in `pokegraph-ingest` / `pokegraph-schema`.

## Source adapter

`pokegraph.sources.pokeapi.PokeApiSource` is the only module that imports PokeLance. It returns project models (`Pokemon`, `Move`, …) with `source_url`, `source_version`, `retrieved_at`, and `adapter_version`. When PokéAPI does not expose a revision, `source_version` is `"unavailable"`.
