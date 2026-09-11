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
