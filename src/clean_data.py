"""Normalize selected ALeRCE columns from pandas DataFrames.

The calling scripts handle Parquet input/output and supply all parameters.
MJD timestamps are converted to timezone-aware UTC, rounded to milliseconds.
"""

import numpy as np
import pandas as pd


def _select_and_normalize(data, dtypes):
    """Select fields and restore nulls from the raw Astropy .mask columns."""
    cleaned = data.loc[:, list(dtypes)].astype(dtypes)
    for column in dtypes:
        # Astropy's Parquet output stores missingness in companion columns.
        mask_column = f"{column}.mask"
        if mask_column in data.columns:
            cleaned[column] = cleaned[column].mask(data[mask_column])
    return cleaned


def clean_objects(objects):
    """Normalize the six essential object fields and add UTC timestamps."""
    cleaned = _select_and_normalize(
        objects,
        {
            "oid": "string",
            "meanra": "float64",
            "meandec": "float64",
            "ndet": "Int64",
            "firstmjd": "float64",
            "lastmjd": "float64",
        },
    )
    for source, target in (
        ("firstmjd", "first_observed_at"),
        ("lastmjd", "last_observed_at"),
    ):
        cleaned[target] = pd.to_datetime(
            cleaned[source], unit="D", origin="1858-11-17", utc=True
        ).dt.round("ms")
    return cleaned.drop_duplicates(ignore_index=True)


def clean_detection_batch(detections):
    """Normalize one batch, drop invalid measurements, and print their count."""
    cleaned = _select_and_normalize(
        detections,
        {
            "oid": "string",
            "candid": "string",
            "mjd": "float64",
            "fid": "Int64",
            "magpsf": "float64",
            "sigmapsf": "float64",
            "isdiffpos": "Int64",
            "parent_candid": "string",
            "ra": "float64",
            "dec": "float64",
        },
    )
    valid = (
        np.isfinite(cleaned["magpsf"])
        & np.isfinite(cleaned["sigmapsf"])
        & cleaned["sigmapsf"].gt(0)
        & np.isfinite(cleaned["mjd"])
    ).fillna(False).astype(bool)
    print(f"Dropped {(~valid).sum()} invalid detection rows.")
    cleaned = cleaned.loc[valid].copy()

    cleaned["observed_at"] = pd.to_datetime(
        cleaned["mjd"], unit="D", origin="1858-11-17", utc=True
    ).dt.round("ms")

    # Collapse identical rows only; never choose between conflicting records.
    return cleaned.drop_duplicates(ignore_index=True)


def clean_probability_batch(probabilities):
    """Normalize one batch, preserving all classifiers and versions for SQL."""
    cleaned = _select_and_normalize(
        probabilities,
        {
            "oid": "string",
            "classifier_name": "string",
            "classifier_version": "string",
            "class_name": "string",
            "probability": "float64",
            "ranking": "Int64",
        },
    )
    return cleaned.drop_duplicates(ignore_index=True)
