import csv
from viral_mint.csv_export import export_snapshots_csv
from viral_mint.history import Snapshot, SnapshotStore

def test_export_csv_and_data_quality(tmp_path):
    db = tmp_path / "db.sqlite3"
    output = tmp_path / "exports" / "snapshots.csv"
    row = Snapshot("2026-10-20T10:00:00+00:00", "solana", "mint", "pool", "MINT",
                   None, None, 50.0, 2, 1, 30, ("missing price",))
    with SnapshotStore(db) as store:
        store.add(row)
    result = export_snapshots_csv(str(db), str(output))
    assert result["rows_exported"] == 1
    assert result["data_quality"]["missing_price_rows"] == 1
    with output.open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    assert records[0]["pair_address"] == "pool"
    assert records[0]["warnings"] == "missing price"
