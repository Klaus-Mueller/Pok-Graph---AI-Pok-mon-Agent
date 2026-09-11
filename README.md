# PokéGraph — AI Pokémon Agent

AI agent project for exploring Pokémon data as a Neo4j graph.

## Query client

The reusable Python library is [`src/pokegraph/`](src/pokegraph/). Scripts (and later HTTP/MCP) use `PokeGraphClient` against the Cypher catalog — not the Neo4j driver or PokeLance.

```bash
pip install -e .
PYTHONPATH=src python examples/query_catalog.py --name pikachu --area pallet-town
```

See [`src/pokegraph/README.md`](src/pokegraph/README.md) for the client API, errors, and environment variables.

Interactive OpenAPI / Swagger UI (Try it out against Neo4j):

```bash
pip install -e ".[api]"
PYTHONPATH=src python -m pokegraph_api
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Ingestion

PokéAPI → Neo4j loading lives in [`src/pokegraph_ingest/`](src/pokegraph_ingest/). Install the ingest extra so the pipeline can use PokeLance through `PokeApiSource`:

```bash
pip install -e ".[ingest]"
```

See [`src/pokegraph_ingest/README.md`](src/pokegraph_ingest/README.md) for setup, CLI usage, environment variables, and graph schema.

## Query catalog

Parameterized Cypher for discovery, encounters, learnsets, evolutions, and matchups lives in [`queries/`](queries/). See [`queries/README.md`](queries/README.md) for contracts, parameter domains, and deferred trainer/progression scope.
