"""Download ZTF data as Parquet files. Requires pyarrow and pandas."""

from pathlib import Path

import pyvo


TAP_URL = "https://tap.alerce.online/tap"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

def _fix_object_columns(table):
    """Turn object into str"""
    for col in table.colnames:
        if table[col].dtype == object:
            table[col] = table[col].astype(str)
    return table

def run_query(query, maxrec):
    """Run a TAP query; report session errors and re-raise them."""
    try:
        tap = pyvo.dal.TAPService(TAP_URL)
        return _fix_object_columns(tap.search(query, maxrec=maxrec).to_table())
    except Exception as error:
        # Capture query-session failures as requested, without hiding them.
        print(f"TAP query failed: {error}")
        raise


def download_objects(output_dir=RAW_DIR):
    """Save the first 20,000 objects ordered by oid and return the table."""
    query = "SELECT TOP 20000 * FROM ztf.object ORDER BY oid ASC"
    objects = run_query(query, maxrec=20000)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    objects.write(output_dir / "objects.parquet", format="parquet", overwrite=True)
    return objects


def fetch_detection_batch(
    oids, batch_number, output_dir=RAW_DIR / "detection", maxrec=1_000_000
):
    """Save detections matching a batch of OIDs and return the table."""
    oid_list = ", ".join(f"'{oid}'" for oid in oids)
    query = f"SELECT * FROM ztf.detection WHERE oid IN ({oid_list})"
    detections = run_query(query, maxrec=maxrec)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    detections.write(
        output_dir / f"detections_{batch_number:04d}.parquet",
        format="parquet",
        overwrite=True,
    )
    return detections


def fetch_probability_batch(
    oids, batch_number, output_dir=RAW_DIR / "probability", maxrec=1_000_000
):
    """Save probabilities matching a batch of OIDs and return the table."""
    oid_list = ", ".join(f"'{oid}'" for oid in oids)
    query = f"SELECT * FROM ztf.probability WHERE oid IN ({oid_list})"
    probabilities = run_query(query, maxrec=maxrec)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    probabilities.write(
        output_dir / f"probabilities_{batch_number:04d}.parquet",
        format="parquet",
        overwrite=True,
    )
    return probabilities
