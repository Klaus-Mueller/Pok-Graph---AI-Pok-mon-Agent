from __future__ import annotations

import unittest

from pokegraph.errors import InvalidQueryParameterError
from pokegraph.graph.catalog import catalog_dir, load_cypher
from pokegraph.graph.registry import QUERY_EXTRAS, QUERY_PATHS, QueryRegistry, parse_query_header


class QueryRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = QueryRegistry.load()

    def test_catalog_files_exist(self) -> None:
        root = catalog_dir()
        for relative in QUERY_PATHS.values():
            self.assertTrue((root / relative).is_file(), relative)

    def test_header_matches_bound_params(self) -> None:
        for query_id, relative in QUERY_PATHS.items():
            text = (catalog_dir() / relative).read_text(encoding="utf-8")
            params, columns, _limitations = parse_query_header(text)
            spec = self.registry.get(query_id)
            self.assertEqual([param.name for param in spec.params], [param.name for param in params])
            self.assertEqual(spec.columns, columns)
            extra = QUERY_EXTRAS.get(query_id, ())
            known = {param.name for param in spec.params}
            for check in extra:
                self.assertIn(check.source_param, known)

    def test_defaults_fill_optional_nulls(self) -> None:
        bound = self.registry.bind(
            "learnsets.learnset_for_pokemon",
            {"pokemon_id": 25, "version_group_id": 10},
        )
        self.assertIsNone(bound["learn_method_id"])
        self.assertEqual(bound["skip"], 0)
        self.assertEqual(bound["limit"], 50)

    def test_unknown_parameter_rejected(self) -> None:
        with self.assertRaises(InvalidQueryParameterError):
            self.registry.bind(
                "discovery.find_pokemon_by_name",
                {"name": "pikachu", "popularity": 1},
            )

    def test_negative_pagination_rejected(self) -> None:
        with self.assertRaises(InvalidQueryParameterError):
            self.registry.bind("discovery.list_regions", {"skip": -1})
        with self.assertRaises(InvalidQueryParameterError):
            self.registry.bind("discovery.list_regions", {"limit": -5})

    def test_max_page_size(self) -> None:
        with self.assertRaises(InvalidQueryParameterError):
            self.registry.bind("discovery.list_regions", {"limit": 500}, max_page_size=200)
        clamped = self.registry.bind("discovery.list_regions", {}, max_page_size=20)
        self.assertEqual(clamped["limit"], 20)

    def test_invalid_level_range(self) -> None:
        with self.assertRaises(InvalidQueryParameterError):
            self.registry.bind(
                "encounters.pokemon_in_area",
                {
                    "location_area_id": 1,
                    "version_id": 1,
                    "min_level": 20,
                    "max_level": 10,
                },
            )

    def test_cypher_has_no_interpolated_values(self) -> None:
        text = load_cypher("encounters/locations_of_pokemon.cypher")
        self.assertIn("$pokemon_id", text)
        self.assertNotIn("pikachu", text)


if __name__ == "__main__":
    unittest.main()
