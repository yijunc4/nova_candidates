"""Clean raw objects and batches into matching Parquet files in data/interim."""

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
INTERIM_DIR = ROOT / "data" / "interim"

sys.path.insert(0, str(ROOT))

from src.clean_data import (
    clean_detection_batch,
    clean_objects,
    clean_probability_batch,
)


if __name__ == "__main__":
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)

    objects = pd.read_parquet(RAW_DIR / "objects.parquet")
    cleaned_objects = clean_objects(objects)
    objects_output = INTERIM_DIR / "objects.parquet"
    cleaned_objects.to_parquet(objects_output, index=False)
    print(f"Saved {len(cleaned_objects)} objects to {objects_output}.")

    for folder, pattern, clean_batch in (
        ("detection", "detections_*.parquet", clean_detection_batch),
        ("probability", "probabilities_*.parquet", clean_probability_batch),
    ):
        output_dir = INTERIM_DIR / folder
        output_dir.mkdir(parents=True, exist_ok=True)

        for input_path in sorted((RAW_DIR / folder).glob(pattern)):
            print(f"Cleaning {input_path.name}.")
            batch = pd.read_parquet(input_path)
            cleaned_batch = clean_batch(batch)
            output_path = output_dir / input_path.name
            cleaned_batch.to_parquet(output_path, index=False)
            print(f"Saved {len(cleaned_batch)} rows to {output_path}.")
