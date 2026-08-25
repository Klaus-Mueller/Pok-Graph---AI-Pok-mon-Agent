# pokegraph_ingest

PokéAPI → Neo4j ingestion for PokéGraph (KLA-119 prototype).

Fetches Pokémon from [PokéAPI](https://pokeapi.co/) via [PokeLance](https://github.com/FallenDeity/PokeLance) and writes idempotent graph data with the official Neo4j Python driver.

## What it writes

| Nodes | Relationships |
| --- | --- |
| `Pokemon`, `PokemonSpecies`, `Type`, `Ability`, `Move` | `SPECIES`, `HAS_TYPE`, `HAS_ABILITY`, `CAN_LEARN` |

Relationship writes use `CALL … IN TRANSACTIONS` so large move lists commit in batches.

By default the pipeline loads the full PokéAPI catalog
(`https://pokeapi.co/api/v2/pokemon?limit=100000&offset=0`, ~1351 entries).
Each entry needs Pokémon + species HTTP calls, so a full run can take tens of minutes.
A live progress bar shows count, rate, elapsed time, and ETA.

The local PokeLance checkout under `vendor/PokeLance` is ignored by Git.

## Setup

From the repository root:

1. Copy `.env.example` to `.env` and set `NEO4J_PASSWORD`.
2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# or: pip install -e .
```

## Run from the command line

### Module entry point

```bash
PYTHONPATH=src python -m pokegraph_ingest.ingest
```

With the project venv:

```bash
PYTHONPATH=src .venv/bin/python -m pokegraph_ingest.ingest
```

### Console script (editable install)

After `pip install -e .`:

```bash
pokegraph-ingest
```

## Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `NEO4J_URI` | yes | — | Aura / Neo4j bolt URI |
| `NEO4J_USERNAME` | yes | — | Database user |
| `NEO4J_PASSWORD` | yes | — | Database password |
| `NEO4J_DATABASE` | no | `neo4j` | Target database |
| `POKEGRAPH_POKEMON_NAMES` | no | *(unset = all)* | Comma-separated subset for short local runs |
| `POKEGRAPH_POKEAPI_POKEMON_LIST_URL` | no | full catalog URL above | Catalog list endpoint |
| `POKEGRAPH_POKEAPI_CACHE_SIZE` | no | `2000` | PokeLance cache size |

Example short run:

```bash
# in .env
POKEGRAPH_POKEMON_NAMES=pikachu,charizard,tyranitar
```

Leave `POKEGRAPH_POKEMON_NAMES` unset (or commented out) to ingest the full catalog.

## Package layout

| File | Role |
| --- | --- |
| [`config.py`](config.py) | Loads settings from `.env` |
| [`ingest.py`](ingest.py) | Catalog fetch, PokéAPI detail calls, Neo4j writes, progress UI |
| [`__init__.py`](__init__.py) | Package marker |
