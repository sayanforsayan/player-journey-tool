"""
Data loader and filtering module for LILA BLACK player telemetry data.
Designed with friendly helpers for Level Designers.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import streamlit as st

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "processed_events.parquet"

MAP_CONFIGS = {
    "AmbroseValley": {
        "display_name": "Ambrose Valley",
        "tagline": "Large Mountain Valley (900m)",
        "description": "Open terrain featuring high ridgelines, a central river basin, and peripheral extraction pads.",
        "scale": 900.0,
        "origin_x": -370.0,
        "origin_z": -473.0,
        "minimap_file": "AmbroseValley_Minimap.png",
    },
    "GrandRift": {
        "display_name": "Grand Rift",
        "tagline": "Canyon & Chasm (581m)",
        "description": "Bisected by a deep gorge with bridge crossings and rapid lane rotations.",
        "scale": 581.0,
        "origin_x": -290.0,
        "origin_z": -290.0,
        "minimap_file": "GrandRift_Minimap.png",
    },
    "Lockdown": {
        "display_name": "Lockdown",
        "tagline": "Industrial CQB Facility (1000m)",
        "description": "Dense indoor rooms, interconnected industrial corridors, and tight choke points.",
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


def format_seconds_to_mmss(seconds: float) -> str:
    """Convert raw seconds into MM:SS format for readable timestamps."""
    sec = int(round(seconds))
    mins = sec // 60
    rem_sec = sec % 60
    return f"{mins:02d}:{rem_sec:02d}"


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


@st.cache_data
def get_match_catalogue(df: pd.DataFrame, map_id: str, date: Optional[str] = None) -> List[Dict]:
    """
    Build a human-friendly list of matches for level designers.
    Provides duration in MM:SS, player count, and key highlights.
    """
    mask = df["map_id"] == map_id
    if date and date != "All Dates":
        mask = mask & (df["date"] == date)

    subset = df[mask]
    if subset.empty:
        return []

    # Aggregate key stats per match
    grouped = subset.groupby("clean_match_id", observed=True).agg(
        date=("date", "first"),
        duration_sec=("match_time_sec", "max"),
        humans=("is_bot", lambda s: (~s).sum()),
        human_users=("user_id", lambda s: s[~subset.loc[s.index, "is_bot"]].nunique()),
        bot_users=("user_id", lambda s: s[subset.loc[s.index, "is_bot"]].nunique()),
        pvp_kills=("event", lambda s: (s == "Kill").sum()),
        bot_kills=("event", lambda s: (s == "BotKill").sum()),
        storm_deaths=("event", lambda s: (s == "KilledByStorm").sum()),
        loot_count=("event", lambda s: (s == "Loot").sum()),
    ).reset_index()

    matches = []
    for _, row in grouped.iterrows():
        mid = row["clean_match_id"]
        dur_str = format_seconds_to_mmss(row["duration_sec"])
        total_kills = row["pvp_kills"] + row["bot_kills"]
        storm = row["storm_deaths"]

        # Build friendly label
        tags = []
        if storm > 0:
            tags.append(f"⚡ {storm} Storm Death")
        if row["pvp_kills"] > 0:
            tags.append(f"⚔️ {row['pvp_kills']} PvP Kill")
        elif total_kills > 0:
            tags.append(f"🎯 {total_kills} Kills")

        tag_str = f" • {', '.join(tags)}" if tags else ""
        friendly_label = (
            f"Match {mid[:8]}... ({dur_str} • {row['human_users']} Player{'s' if row['human_users'] != 1 else ''}{tag_str})"
        )

        matches.append({
            "match_id": mid,
            "label": friendly_label,
            "date": str(row["date"]),
            "duration_sec": float(row["duration_sec"]),
            "human_users": int(row["human_users"]),
            "bot_users": int(row["bot_users"]),
            "total_kills": int(total_kills),
            "storm_deaths": int(storm),
            "loot_count": int(row["loot_count"]),
        })

    return matches


def get_match_info(df: pd.DataFrame, match_id: str) -> Dict:
    """Extract metadata for a specific match with designer-friendly formatting."""
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
        "duration_str": format_seconds_to_mmss(duration_sec),
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
