"""Download the first 20,000 ZTF objects to data/raw/objects.parquet."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extract_data import download_objects


if __name__ == "__main__":
    objects = download_objects()
    print(f"Downloaded {len(objects)} objects.")
