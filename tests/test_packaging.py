from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pokegraph.graph.catalog import catalog_dir, load_cypher
from pokegraph.graph.registry import QueryRegistry

REPO_ROOT = Path(__file__).resolve().parents[1]


class CatalogPackagingTests(unittest.TestCase):
    def test_catalog_dir_loads_cypher(self) -> None:
        self.assertTrue((catalog_dir() / "encounters" / "locations_of_pokemon.cypher").is_file())
        text = load_cypher("learnsets/learnset_for_pokemon.cypher")
        self.assertIn("MATCH", text)
        self.assertNotIn("// query:", text)

    def test_registry_loads_from_package_path(self) -> None:
        registry = QueryRegistry.load()
        self.assertIn("$pokemon_id", registry.cypher("encounters.locations_of_pokemon"))

    def test_wheel_includes_cypher(self) -> None:
        if os.getenv("POKEGRAPH_WHEEL_TEST") != "1":
            self.skipTest("Set POKEGRAPH_WHEEL_TEST=1 to build and install a wheel")
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "PYTHONPATH": ""}
            subprocess.run(
                [sys.executable, "-m", "pip", "wheel", str(REPO_ROOT), "-w", tmp, "--no-deps"],
                check=True,
                cwd=tmp,
                env=env,
            )
            wheels = list(Path(tmp).glob("pokegraph-*.whl"))
            self.assertTrue(wheels, "wheel was not built")
            venv = Path(tmp) / "venv"
            subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
            python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            subprocess.run([str(python), "-m", "pip", "install", str(wheels[0])], check=True)
            script = (
                "from pokegraph.graph.catalog import catalog_dir, load_cypher; "
                "assert (catalog_dir() / 'encounters' / 'locations_of_pokemon.cypher').is_file(); "
                "assert '$pokemon_id' in load_cypher('encounters/locations_of_pokemon.cypher')"
            )
            subprocess.run([str(python), "-c", script], check=True)


if __name__ == "__main__":
    unittest.main()
