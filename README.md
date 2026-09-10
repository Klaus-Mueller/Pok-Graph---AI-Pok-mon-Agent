# PokéGraph — AI Pokémon Agent

AI agent project for exploring Pokémon data as a Neo4j graph.

## Ingestion

PokéAPI → Neo4j loading lives in [`src/pokegraph_ingest/`](src/pokegraph_ingest/).

See [`src/pokegraph_ingest/README.md`](src/pokegraph_ingest/README.md) for setup, CLI usage, environment variables, and graph schema.

## Query catalog

Parameterized Cypher for discovery, encounters, learnsets, evolutions, and matchups lives in [`queries/`](queries/). See [`queries/README.md`](queries/README.md) for contracts, parameter domains, and deferred trainer/progression scope.
