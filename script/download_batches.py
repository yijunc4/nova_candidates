"""Download detection and probability batches for the saved ZTF objects."""

from pathlib import Path
import sys

from astropy.table import Table
from tqdm.auto import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extract_data import RAW_DIR, fetch_detection_batch, fetch_probability_batch


BATCH_SIZE = 1000


if __name__ == "__main__":
    objects = Table.read(RAW_DIR / "objects.parquet", format="parquet")
    oids = objects["oid"].tolist()

    for batch_number, start in enumerate(
        tqdm(range(0, len(oids), BATCH_SIZE), desc="Downloading batches", unit="batch"),
        start=1,
    ):
        batch_oids = oids[start : start + BATCH_SIZE]
        tqdm.write(f"Batch {batch_number}: {len(batch_oids)} objects.")

        detection_path = RAW_DIR / "detection" / f"detections_{batch_number:04d}.parquet"
        if detection_path.exists():
            tqdm.write(f"Skipping existing {detection_path.name}.")
        else:
            detections = fetch_detection_batch(batch_oids, batch_number)
            tqdm.write(f"Saved {len(detections)} detections.")

        probability_path = RAW_DIR / "probability" / f"probabilities_{batch_number:04d}.parquet"
        if probability_path.exists():
            tqdm.write(f"Skipping existing {probability_path.name}.")
        else:
            probabilities = fetch_probability_batch(batch_oids, batch_number)
            tqdm.write(f"Saved {len(probabilities)} probabilities.")
