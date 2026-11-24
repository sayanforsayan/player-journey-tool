"""
Data loader and filtering module for LILA BLACK player telemetry data.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import streamlit as st

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "processed_events.parquet"

MAP_CONFIGS = {
    "AmbroseValley": {
        "display_name": "Ambrose Valley (Primary Map)",
        "scale": 900.0,
        "origin_x": -370.0,
        "origin_z": -473.0,
        "minimap_file": "AmbroseValley_Minimap.png",
    },
    "GrandRift": {
        "display_name": "Grand Rift (Secondary Map)",
        "scale": 581.0,
        "origin_x": -290.0,
        "origin_z": -290.0,
        "minimap_file": "GrandRift_Minimap.png",
    },
    "Lockdown": {
        "display_name": "Lockdown (Close-Quarters Map)",
        "scale": 1000.0,
        "origin_x": -500.0,
        "origin_z": -500.0,
        "minimap_file": "Lockdown_Minimap.jpg",
    },
}

ALL_EVENT_TYPES = [
    "Position",
    "BotPosition",
    "Kill",
    "Killed",
    "BotKill",
    "BotKilled",
    "KilledByStorm",
    "Loot",
]


@st.cache_data(show_spinner=True)
def load_data(file_path: Optional[str] = None) -> pd.DataFrame:
    """Load the preprocessed master parquet file."""
    path = Path(file_path) if file_path else DATA_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"Preprocessed parquet data not found at '{path}'. "
            "Please run 'python scripts/preprocess.py' first."
        )

    df = pd.read_parquet(path)
    return df


def get_available_maps(df: pd.DataFrame) -> List[str]:
    """Get list of distinct maps available in the dataset."""
    return sorted(df["map_id"].unique().tolist())


def get_available_dates(df: pd.DataFrame, map_id: Optional[str] = None) -> List[str]:
    """Get list of available dates, optionally filtered by map."""
    filtered = df if not map_id else df[df["map_id"] == map_id]
    return sorted(filtered["date"].unique().tolist())


def get_matches_for_selection(
    df: pd.DataFrame, map_id: str, date: Optional[str] = None
) -> List[str]:
    """Get unique match IDs for a given map and optional date."""
    mask = df["map_id"] == map_id
    if date and date != "All Dates":
        mask = mask & (df["date"] == date)
    matches = df.loc[mask, "clean_match_id"].unique().tolist()
    return sorted(matches)


def get_match_info(df: pd.DataFrame, match_id: str) -> Dict:
    """Extract metadata for a specific match."""
    match_df = df[df["clean_match_id"] == match_id]
    if match_df.empty:
        return {}

    duration_sec = float(match_df["match_time_sec"].max())
    human_players = match_df[~match_df["is_bot"]]["user_id"].nunique()
    bot_players = match_df[match_df["is_bot"]]["user_id"].nunique()
    total_events = len(match_df)
    total_kills = (match_df["event"] == "Kill").sum()
    total_bot_kills = (match_df["event"] == "BotKill").sum()
    bot_kills_player = (match_df["event"] == "BotKilled").sum()
    storm_deaths = (match_df["event"] == "KilledByStorm").sum()
    loot_events = (match_df["event"] == "Loot").sum()
    date_val = str(match_df["date"].iloc[0])
    map_val = str(match_df["map_id"].iloc[0])

    return {
        "match_id": match_id,
        "date": date_val,
        "map_id": map_val,
        "duration_sec": duration_sec,
        "human_count": human_players,
        "bot_count": bot_players,
        "total_players": human_players + bot_players,
        "total_events": total_events,
        "player_kills": int(total_kills),
        "bot_kills": int(total_bot_kills),
        "player_killed_by_bot": int(bot_kills_player),
        "storm_deaths": int(storm_deaths),
        "loot_events": int(loot_events),
    }


def get_aggregate_stats(df: pd.DataFrame) -> Dict:
    """Compute top-level summary metrics for filtered dataset."""
    return {
        "total_events": len(df),
        "total_matches": df["clean_match_id"].nunique(),
        "total_players": df["user_id"].nunique(),
        "human_players": df[~df["is_bot"]]["user_id"].nunique(),
        "bot_players": df[df["is_bot"]]["user_id"].nunique(),
        "pvp_kills": int((df["event"] == "Kill").sum()),
        "bot_kills": int((df["event"] == "BotKill").sum()),
        "killed_by_bot": int((df["event"] == "BotKilled").sum()),
        "storm_deaths": int((df["event"] == "KilledByStorm").sum()),
        "loot_pickups": int((df["event"] == "Loot").sum()),
    }
