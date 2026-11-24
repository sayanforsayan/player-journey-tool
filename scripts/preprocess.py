#!/usr/bin/env python3
"""
Preprocess raw player telemetry parquet files from game sessions.
Bakes 1,243 separate files across 5 days into a single optimized master parquet file.
"""

import os
import sys
import glob
import argparse
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

# Map configuration specs provided in telemetry README
MAP_CONFIGS = {
    "AmbroseValley": {
        "scale": 900.0,
        "origin_x": -370.0,
        "origin_z": -473.0,
        "minimap": "AmbroseValley_Minimap.png",
    },
    "GrandRift": {
        "scale": 581.0,
        "origin_x": -290.0,
        "origin_z": -290.0,
        "minimap": "GrandRift_Minimap.png",
    },
    "Lockdown": {
        "scale": 1000.0,
        "origin_x": -500.0,
        "origin_z": -500.0,
        "minimap": "Lockdown_Minimap.jpg",
    },
}

DATE_MAP = {
    "February_10": "2026-02-10",
    "February_11": "2026-02-11",
    "February_12": "2026-02-12",
    "February_13": "2026-02-13",
    "February_14": "2026-02-14",
}


def compute_pixel_coords(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized calculation of UV and pixel coordinates (1024x1024)."""
    pixel_x = pd.Series(index=df.index, dtype="float32")
    pixel_y = pd.Series(index=df.index, dtype="float32")
    norm_u = pd.Series(index=df.index, dtype="float32")
    norm_v = pd.Series(index=df.index, dtype="float32")

    for map_id, cfg in MAP_CONFIGS.items():
        mask = df["map_id"] == map_id
        if not mask.any():
            continue

        u = (df.loc[mask, "x"] - cfg["origin_x"]) / cfg["scale"]
        v = (df.loc[mask, "z"] - cfg["origin_z"]) / cfg["scale"]

        norm_u.loc[mask] = u
        norm_v.loc[mask] = v
        pixel_x.loc[mask] = (u * 1024.0).round(2)
        pixel_y.loc[mask] = ((1.0 - v) * 1024.0).round(2)

    df["u"] = norm_u
    df["v"] = norm_v
    df["pixel_x"] = pixel_x
    df["pixel_y"] = pixel_y
    return df


def preprocess(input_dir: str, output_path: str):
    input_path = Path(input_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    day_folders = sorted(
        [d for d in input_path.iterdir() if d.is_dir() and d.name.startswith("February_")]
    )
    if not day_folders:
        raise ValueError(f"No February_* folders found in {input_dir}")

    all_dfs = []
    total_files = 0
    print(f"Starting data preprocessing from: {input_dir}")

    for day_dir in day_folders:
        day_name = day_dir.name
        std_date = DATE_MAP.get(day_name, day_name)
        files = [f for f in day_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
        print(f"  Reading {day_name} ({std_date}): {len(files)} files...")

        day_dfs = []
        for file_path in files:
            try:
                table = pq.read_table(str(file_path))
                pdf = table.to_pandas()
                pdf["date"] = std_date
                pdf["source_day"] = day_name
                day_dfs.append(pdf)
                total_files += 1
            except Exception as e:
                print(f"    Warning: Error reading {file_path.name}: {e}")

        if day_dfs:
            combined_day = pd.concat(day_dfs, ignore_index=True)
            all_dfs.append(combined_day)

    print(f"Total files parsed: {total_files}")
    master_df = pd.concat(all_dfs, ignore_index=True)
    print(f"Combined total raw rows: {len(master_df):,}")

    # 1. Decode event column (stored as binary bytes in parquet)
    print("Decoding event strings...")
    master_df["event"] = master_df["event"].apply(
        lambda e: e.decode("utf-8") if isinstance(e, (bytes, bytearray)) else str(e)
    )

    # 2. Add is_bot column
    # Bots have numeric user_ids (e.g., '1440', '382'), Humans have UUIDs (36 chars)
    print("Classifying bots vs human players...")
    master_df["is_bot"] = master_df["user_id"].astype(str).str.isdigit() | (
        master_df["event"].isin(["BotPosition", "BotKill", "BotKilled"]) & (master_df["user_id"].str.len() < 10)
    )

    # 3. Clean match_id (strip .nakama-0 suffix)
    print("Cleaning match_id strings...")
    master_df["clean_match_id"] = master_df["match_id"].astype(str).str.replace(".nakama-0", "", regex=False)

    # 4. Normalize timestamps to match-elapsed seconds
    # ATTENTION TO DETAIL FIX:
    # Parquet schema specifies `ts` as timestamp[ms], but raw integers are actually Unix epoch in SECONDS
    # (e.g., 1770760465 is Feb 10, 2026 21:54:25 UTC).
    # Interpreting them directly as milliseconds made match lengths 0.8s instead of ~800s.
    print("Normalizing timestamps to match-relative elapsed time (seconds)...")
    raw_epoch_sec = master_df["ts"].astype("int64")
    master_df["real_timestamp"] = pd.to_datetime(raw_epoch_sec, unit="s", utc=True)
    min_epoch_per_match = master_df.groupby("clean_match_id")["ts"].transform(
        lambda s: s.astype("int64").min()
    )
    master_df["match_time_sec"] = (raw_epoch_sec - min_epoch_per_match).astype("float32")

    # 5. Precompute pixel coordinates (pixel_x, pixel_y) and UV
    print("Computing map UV and pixel coordinates...")
    master_df = compute_pixel_coords(master_df)

    # 6. Sort chronologically per match and user
    master_df = master_df.sort_values(by=["clean_match_id", "user_id", "ts"]).reset_index(drop=True)

    # Optimize datatypes for compact parquet storage
    master_df["user_id"] = master_df["user_id"].astype("category")
    master_df["clean_match_id"] = master_df["clean_match_id"].astype("category")
    master_df["map_id"] = master_df["map_id"].astype("category")
    master_df["event"] = master_df["event"].astype("category")
    master_df["date"] = master_df["date"].astype("category")
    master_df["source_day"] = master_df["source_day"].astype("category")
    master_df["is_bot"] = master_df["is_bot"].astype("bool")
    master_df["x"] = master_df["x"].astype("float32")
    master_df["y"] = master_df["y"].astype("float32")
    master_df["z"] = master_df["z"].astype("float32")
    master_df["pixel_x"] = master_df["pixel_x"].astype("float32")
    master_df["pixel_y"] = master_df["pixel_y"].astype("float32")
    master_df["match_time_sec"] = master_df["match_time_sec"].astype("float32")

    print(f"Writing baked parquet to {output_path}...")
    master_df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=False)

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Done! Master dataset baked successfully.")
    print(f"  Rows: {len(master_df):,}")
    print(f"  Matches: {master_df['clean_match_id'].nunique():,}")
    print(f"  Players: {master_df['user_id'].nunique():,}")
    print(f"  File size: {file_size_mb:.2f} MB")
    print(f"  Event distribution:\n{master_df['event'].value_counts().to_string()}")


if __name__ == "__main__":
    default_base = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Preprocess player telemetry data")
    parser.add_argument(
        "--input-dir",
        default=str(default_base / "player_data"),
        help="Path to raw player_data folder",
    )
    parser.add_argument(
        "--output-file",
        default=str(default_base / "data" / "processed_events.parquet"),
        help="Path to write processed parquet",
    )
    args = parser.parse_args()
    preprocess(args.input_dir, args.output_file)
