from pathlib import Path

from src.demo_data import DEMO_DIRECTORY, build_demo_bundle


def test_demo_bundle_contains_real_and_scenario_files() -> None:
    paths = build_demo_bundle()

    assert set(paths) == {"sales", "inventory", "costs", "lots"}
    assert all(Path(path).exists() for path in paths.values())
    assert (DEMO_DIRECTORY / "README_DEMO.json").exists()
