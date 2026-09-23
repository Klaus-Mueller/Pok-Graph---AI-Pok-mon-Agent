# pokegraph_api

HTTP wrapper around `PokeGraphClient` with an OpenAPI specification UI (Swagger / ReDoc), similar to the [Neo4j Aura API specification](https://neo4j.com/docs/aura/platform/api/specification/).

```bash
pip install -e ".[api]"
PYTHONPATH=src python -m pokegraph_api
```

| URL | What |
| --- | --- |
| http://127.0.0.1:8000/docs | Swagger UI — browse and **Try it out** |
| http://127.0.0.1:8000/redoc | Readable reference |
| http://127.0.0.1:8000/openapi.json | Raw OpenAPI 3 document |
| http://127.0.0.1:8000/v1/health | Database connectivity |

Uses the same `.env` Neo4j settings as ingest. The spec page loads even if Neo4j is unreachable.

## Question pilot

`POST /v1/agent/ask` is a deterministic Red/Green Blue-battle pilot. It routes
questions to reviewed read-only Cypher queries. It does not call a language model or vector
index. It returns `answered`, `needs_clarification`, or `insufficient_evidence`,
plus the exact query/chunk evidence, assumptions, and missing information.

The pilot supports Blue team questions, battle location/context, recorded Kanto
encounters at explicitly named locations, Route 22 type-only candidate comparison,
and the first battle's recorded outcome from Neo4j. It supports Japanese Red/Green versions
44/45 and the three original starters. It asks for missing game, battle, or
starter information when needed. Route 22 is the default location for Route 22
questions; an explicit empty location list never broadens the search.

Example:

```sh
curl -s http://127.0.0.1:8000/v1/agent/ask \
  -H 'content-type: application/json' \
  -d '{"question":"What team does Blue use in the first battle?"}'
```

That request asks for the missing game and starter. With context supplied:

```json
{"question":"What team does Blue use in the first battle?","game_version_id":44,"player_starter":"bulbasaur"}
```

For a Route 22 type comparison, specify the optional second encounter and
starter, or ask about Blue's optional second Route 22 battle; the pilot applies
`kanto-route-22` and states that move availability and Generation I chart accuracy
are unchecked. Encounter results describe records in the selected location, not
confirmed story progression or capture eligibility. Text answers cite the source
URL and chunk ID; graph answers return query ID, bound parameters, and rows.
