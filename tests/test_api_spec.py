from __future__ import annotations

import unittest

from pokegraph_api.app import create_app


class OpenApiSpecTests(unittest.TestCase):
    def test_spec_lists_catalog_groups(self) -> None:
        spec = create_app().openapi()
        self.assertEqual(spec["info"]["title"], "PokéGraph Query API")
        paths = spec["paths"]
        self.assertIn("/v1/discovery/pokemon", paths)
        self.assertIn("/v1/encounters/of-pokemon", paths)
        self.assertIn("/v1/learnsets/pokemon/{pokemon_id}", paths)
        self.assertIn("/v1/evolutions/chain", paths)
        self.assertIn("/v1/matchups/effectiveness", paths)
        self.assertTrue(any(getattr(route, "path", None) == "/docs" for route in create_app().routes))
        tags = {tag["name"] for tag in spec.get("tags", [])} | {
            operation.get("tags", [None])[0]
            for path in paths.values()
            for operation in path.values()
            if isinstance(operation, dict)
        }
        self.assertTrue({"Discovery", "Encounters", "Learnsets", "Evolutions", "Matchups"} <= tags)


if __name__ == "__main__":
    unittest.main()
