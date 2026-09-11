"""Query the ingested graph through PokeGraphClient — no driver or PokeLance."""

from __future__ import annotations

import argparse
import asyncio
import json

from pokegraph import PokeGraphClient


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run a few catalog lookups against Neo4j.")
    parser.add_argument("--name", default="pikachu", help="Pokémon name to resolve")
    parser.add_argument("--area", default="pallet-town", help="Location area name to resolve")
    parser.add_argument("--version-id", type=int, default=None, help="GameVersion id for learnsets")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    async with PokeGraphClient.from_environment() as graph:
        await graph.verify_connectivity()
        pokemon = await graph.find_pokemon(args.name, limit=args.limit)
        areas = await graph.find_location_areas(args.area, limit=args.limit)
        payload = {
            "pokemon": pokemon.rows,
            "location_areas": areas.rows,
        }
        if pokemon.rows and args.version_id is not None:
            moves = await graph.learnset_for_pokemon(
                pokemon.rows[0]["pokemon_id"],
                version_id=args.version_id,
                limit=args.limit,
            )
            payload["learnset"] = {
                "context": {
                    "version_id": moves.context.version_id,
                    "version_group_id": moves.context.version_group_id,
                    "version_group_name": moves.context.version_group_name,
                },
                "limitations": list(moves.limitations),
                "rows": moves.rows,
            }
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
