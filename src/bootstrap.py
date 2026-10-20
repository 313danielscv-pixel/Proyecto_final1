"""Create the derived artefacts needed by the application when they are absent."""

from __future__ import annotations

from pathlib import Path

from src.data_pipeline import DEFAULT_OUTPUT, DEFAULT_REPORT, run_pipeline
from src.fetch_eurostat_context import OUTPUT as EUROSTAT_OUTPUT
from src.fetch_eurostat_context import fetch_context
from src.train_model import METRICS_PATH, MODEL_PATH, train_and_evaluate


def ensure_application_assets() -> None:
    """Build local artefacts from the included pilot data and public context."""
    if not EUROSTAT_OUTPUT.exists():
        fetch_context()
    if not DEFAULT_OUTPUT.exists() or not DEFAULT_REPORT.exists():
        run_pipeline()
    if not MODEL_PATH.exists() or not METRICS_PATH.exists():
        train_and_evaluate()


def assets_exist(paths: tuple[Path, ...]) -> bool:
    """Return whether every required application artefact is available."""
    return all(path.exists() for path in paths)
