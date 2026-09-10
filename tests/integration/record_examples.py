"""Read-only recorder for queries/examples against a populated database."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from tests.integration.query_lib import (
    QUERIES_DIR,
    REPO_ROOT,
    connect_driver,
    listing_params,
    load_cypher,
    query_path,
    records_to_dicts,
)

EXAMPLES_DIR = QUERIES_DIR / "examples"
MAIN_QUERIES = (
    ("discovery", "dataset_fingerprint.cypher"),
    ("discovery", "list_versions_with_data.cypher"),
    ("discovery", "list_version_groups_with_data.cypher"),
    ("discovery", "resolve_version_group.cypher"),
    ("discovery", "find_pokemon_by_name.cypher"),
    ("encounters", "pokemon_in_area.cypher"),
    ("encounters", "locations_of_pokemon.cypher"),
    ("encounters", "compare_versions.cypher"),
    ("learnsets", "learnset_for_pokemon.cypher"),
    ("learnsets", "who_learns_move.cypher"),
    ("evolutions", "evolutions_from_species.cypher"),
    ("evolutions", "evolution_chain.cypher"),
    ("matchups", "type_effectiveness.cypher"),
    ("matchups", "offensive_coverage_by_types.cypher"),
    ("matchups", "offensive_coverage_by_learnset.cypher"),
)


def _run(session, *parts: str, **params):
    return records_to_dicts(session.run(load_cypher(query_path(*parts)), **params))


def _pick_versions(versions: list[dict]) -> tuple[dict, dict]:
    with_encounters = [row for row in versions if row.get("encounter_count")]
    by_name = {row["version_name"]: row for row in with_encounters}
    if "heartgold" in by_name and "soulsilver" in by_name:
        return by_name["heartgold"], by_name["soulsilver"]
    if len(with_encounters) < 2:
        raise RuntimeError("Need at least two GameVersion rows with encounters")
    first = with_encounters[0]
    second = next(
        (row for row in with_encounters if row["version_group_id"] != first["version_group_id"]),
        with_encounters[1],
    )
    return first, second


def _pick_second_group(groups: list[dict], primary_group_id: int | None) -> dict | None:
    return next((row for row in groups if row["version_group_id"] != primary_group_id), None)


def _explain(session, *parts: str, **params) -> str:
    query = "EXPLAIN\n" + load_cypher(query_path(*parts))
    summary = session.run(query, **params).consume()
    plan = summary.plan
    if plan is None:
        return "(no plan returned)"
    return "\n".join(_format_plan(plan))


def _format_plan(plan, indent: int = 0) -> list[str]:
    if isinstance(plan, dict):
        operator = plan.get("operatorType") or plan.get("operator_type") or "?"
        arguments = plan.get("args") or plan.get("arguments") or {}
        children = plan.get("children") or []
    else:
        operator = getattr(plan, "operator_type", "?")
        arguments = getattr(plan, "arguments", None) or {}
        children = getattr(plan, "children", None) or []
    estimated = ""
    if "EstimatedRows" in arguments:
        estimated = f" estimated_rows={arguments['EstimatedRows']}"
    lines = [f"{'  ' * indent}{operator}{estimated}"]
    for child in children:
        lines.extend(_format_plan(child, indent + 1))
    return lines


def record(session) -> None:
    fingerprint = _run(session, "discovery", "dataset_fingerprint.cypher")[0]
    versions = _run(
        session,
        "discovery",
        "list_versions_with_data.cypher",
        **listing_params(limit=200),
    )
    groups = _run(
        session,
        "discovery",
        "list_version_groups_with_data.cypher",
        **listing_params(limit=200),
    )
    version_a, version_b = _pick_versions(versions)
    second_group = _pick_second_group(groups, version_a.get("version_group_id"))

    areas = _run(
        session,
        "discovery",
        "list_location_areas.cypher",
        **listing_params(
            region_id=None,
            location_id=None,
            location_area_id=None,
            version_id=version_a["version_id"],
            limit=10,
        ),
    )
    if not areas:
        raise RuntimeError("No location areas with encounters for version_a")
    area = areas[0]

    area_pokemon = _run(
        session,
        "encounters",
        "pokemon_in_area.cypher",
        **listing_params(
            location_area_id=area["location_area_id"],
            version_id=version_a["version_id"],
            method_id=None,
            min_level=None,
            max_level=None,
            limit=10,
        ),
    )
    if not area_pokemon:
        raise RuntimeError("No encounters in the selected area/version")
    pokemon = area_pokemon[0]

    pikachu = _run(
        session,
        "discovery",
        "find_pokemon_by_name.cypher",
        **listing_params(name="pikachu", limit=5),
    )
    pokemon_id = pikachu[0]["pokemon_id"] if pikachu else pokemon["pokemon_id"]
    species_id = pikachu[0]["species_id"] if pikachu and pikachu[0].get("species_id") else None
    if species_id is None:
        eevee = _run(
            session,
            "discovery",
            "find_species_by_name.cypher",
            **listing_params(name="eevee", limit=5),
        )
        species_id = eevee[0]["species_id"] if eevee else pokemon_id

    thunderbolt = _run(
        session,
        "discovery",
        "find_move_by_name.cypher",
        **listing_params(name="thunderbolt", limit=5),
    )
    electric = _run(
        session,
        "matchups",
        "defensive_profile.cypher",
        **listing_params(pokemon_id=pokemon_id, limit=20),
    )
    attacker_type_id = next(
        (row["attacker_type_id"] for row in electric if row.get("attacker_type_name") == "electric"),
        electric[0]["attacker_type_id"] if electric else None,
    )
    defender_pokemon_id = next(
        (row["pokemon_id"] for row in area_pokemon if row["pokemon_id"] != pokemon_id),
        pokemon_id,
    )
    move_id = thunderbolt[0]["move_id"] if thunderbolt else None
    version_group_id = version_a.get("version_group_id")
    if move_id is None and version_group_id is not None:
        learnset = _run(
            session,
            "learnsets",
            "learnset_for_pokemon.cypher",
            **listing_params(
                pokemon_id=pokemon_id,
                version_group_id=version_group_id,
                learn_method_id=None,
                limit=5,
            ),
        )
        if learnset:
            move_id = learnset[0]["move_id"]

    params = {
        "skip": 0,
        "limit": 10,
        "version_id": version_a["version_id"],
        "version_id_a": version_a["version_id"],
        "version_id_b": version_b["version_id"],
        "version_group_id": version_group_id,
        "second_version_group_id": second_group["version_group_id"] if second_group else None,
        "location_area_id": area["location_area_id"],
        "pokemon_id": pokemon_id,
        "species_id": species_id,
        "move_id": move_id,
        "attacker_type_id": attacker_type_id,
        "defender_pokemon_id": defender_pokemon_id,
        "method_id": None,
        "min_level": 10,
        "max_level": 20,
        "learn_method_id": None,
        "version_name_a": version_a["version_name"],
        "version_name_b": version_b["version_name"],
        "version_group_name": version_a.get("version_group_name"),
        "second_version_group_name": second_group["version_group_name"] if second_group else None,
        "location_area_name": area.get("location_area_name"),
    }

    query_params = {
        "discovery/dataset_fingerprint.cypher": {},
        "discovery/list_versions_with_data.cypher": listing_params(limit=10),
        "discovery/list_version_groups_with_data.cypher": listing_params(limit=10),
        "discovery/resolve_version_group.cypher": {
            "version_id": params["version_id"],
            "version_group_id": params["version_group_id"],
        },
        "discovery/find_pokemon_by_name.cypher": listing_params(name="pikachu", limit=10),
        "encounters/pokemon_in_area.cypher": listing_params(
            location_area_id=params["location_area_id"],
            version_id=params["version_id"],
            method_id=None,
            min_level=params["min_level"],
            max_level=params["max_level"],
            limit=10,
        ),
        "encounters/locations_of_pokemon.cypher": listing_params(
            pokemon_id=params["pokemon_id"],
            version_id=params["version_id"],
            method_id=None,
            min_level=None,
            max_level=None,
            limit=10,
        ),
        "encounters/compare_versions.cypher": listing_params(
            version_id_a=params["version_id_a"],
            version_id_b=params["version_id_b"],
            location_area_id=params["location_area_id"],
            limit=10,
        ),
        "learnsets/learnset_for_pokemon.cypher": listing_params(
            pokemon_id=params["pokemon_id"],
            version_group_id=params["version_group_id"],
            learn_method_id=None,
            limit=10,
        ),
        "learnsets/who_learns_move.cypher": listing_params(
            move_id=params["move_id"],
            version_group_id=params["version_group_id"],
            learn_method_id=None,
            limit=10,
        ),
        "evolutions/evolutions_from_species.cypher": listing_params(
            species_id=params["species_id"],
            limit=10,
        ),
        "evolutions/evolution_chain.cypher": listing_params(
            species_id=params["species_id"],
            limit=10,
        ),
        "matchups/type_effectiveness.cypher": {
            "attacker_type_id": params["attacker_type_id"],
            "defender_pokemon_id": params["defender_pokemon_id"],
        },
        "matchups/offensive_coverage_by_types.cypher": listing_params(
            pokemon_id=params["pokemon_id"],
            defender_pokemon_id=params["defender_pokemon_id"],
            limit=10,
        ),
        "matchups/offensive_coverage_by_learnset.cypher": listing_params(
            pokemon_id=params["pokemon_id"],
            version_group_id=params["version_group_id"],
            defender_pokemon_id=params["defender_pokemon_id"],
            learn_method_id=None,
            limit=10,
        ),
    }

    results = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": fingerprint,
        "queries": {},
    }
    plan_sections = [
        "# Example EXPLAIN plans",
        "",
        "Recorded read-only against the live graph. Extra property indexes are **not** added unless a plan shows a hot LabelScan that listing limits cannot contain.",
        "",
        f"Fingerprint: `{fingerprint}`",
        "",
    ]

    for folder, filename in MAIN_QUERIES:
        key = f"{folder}/{filename}"
        bound = query_params[key]
        rows = _run(session, folder, filename, **bound)
        results["queries"][key] = {"parameters": bound, "row_count": len(rows), "rows": rows}
        plan_sections.append(f"## `{key}`")
        plan_sections.append("")
        plan_sections.append("```")
        plan_sections.append(_explain(session, folder, filename, **bound))
        plan_sections.append("```")
        plan_sections.append("")

    index_note = (
        "No additional indexes were added from this pass. Identity lookups use existing "
        "uniqueness constraints. Name discovery may LabelScan; add a `name` index only if "
        "agent traffic makes that scan expensive."
    )
    plan_sections.append("## Index decision")
    plan_sections.append("")
    plan_sections.append(index_note)

    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(EXAMPLES_DIR / "parameters.json", params)
    _write_json(EXAMPLES_DIR / "expected-results.json", results)
    (EXAMPLES_DIR / "plans.md").write_text("\n".join(plan_sections) + "\n", encoding="utf-8")


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    driver, database = connect_driver()
    if driver is None:
        raise SystemExit("Set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD before recording examples.")
    try:
        driver.verify_connectivity()
        from neo4j import READ_ACCESS

        with driver.session(database=database, default_access_mode=READ_ACCESS) as session:
            record(session)
    finally:
        driver.close()
    print(f"Wrote {EXAMPLES_DIR.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
