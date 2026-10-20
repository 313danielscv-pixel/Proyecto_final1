from pathlib import Path

from src.data_pipeline import DEFAULT_DATABASE, build_risk_snapshots, load_pilot_tables


def test_snapshot_pipeline_generates_one_row_per_lot_day() -> None:
    tables = load_pilot_tables(Path(DEFAULT_DATABASE))
    snapshots = build_risk_snapshots(tables)

    assert not snapshots.empty
    assert snapshots.duplicated(subset=["lote_id", "snapshot_date"]).sum() == 0
    assert set(snapshots["hubo_merma"].unique()).issubset({0, 1})
    assert (snapshots["dias_restantes"] >= 0).all()
