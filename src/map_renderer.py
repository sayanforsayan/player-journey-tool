"""
Plotly minimap visualization engine for LILA BLACK player journey replay and heatmaps.
"""

from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

MINIMAPS_DIR = Path(__file__).resolve().parent.parent / "minimaps"

# Event styling specifications
EVENT_STYLES = {
    "Kill": {
        "name": "PvP Kill (Human eliminated Human)",
        "color": "#FF2A2A",  # Bright Crimson Red
        "symbol": "cross",
        "size": 13,
        "desc": "PvP Kill",
    },
    "Killed": {
        "name": "PvP Death (Human killed by Human)",
        "color": "#7B0000",  # Dark Crimson
        "symbol": "x",
        "size": 13,
        "desc": "PvP Death",
    },
    "BotKill": {
        "name": "Bot Kill (Human eliminated Bot)",
        "color": "#FF9E00",  # Neon Amber / Orange
        "symbol": "triangle-up",
        "size": 11,
        "desc": "Bot Kill (Player -> Bot)",
    },
    "BotKilled": {
        "name": "Killed by Bot (Human died to Bot)",
        "color": "#B5179E",  # Vivid Purple
        "symbol": "triangle-down",
        "size": 11,
        "desc": "Player Killed by Bot",
    },
    "KilledByStorm": {
        "name": "Storm Death (Zone Elimination)",
        "color": "#00F0FF",  # Neon Cyan
        "symbol": "hexagon",
        "size": 14,
        "desc": "Killed by Storm",
    },
    "Loot": {
        "name": "Loot Pickup",
        "color": "#FFD166",  # Bright Gold
        "symbol": "diamond",
        "size": 8,
        "desc": "Item Looted",
    },
}

MAP_FILENAMES = {
    "AmbroseValley": "AmbroseValley_Minimap.png",
    "GrandRift": "GrandRift_Minimap.png",
    "Lockdown": "Lockdown_Minimap.jpg",
}

# Distinct qualitative colors for player journeys
PLAYER_PALETTE = px.colors.qualitative.Dark24 + px.colors.qualitative.Light24


def get_minimap_image(map_id: str) -> Optional[Image.Image]:
    """Load minimap image."""
    filename = MAP_FILENAMES.get(map_id)
    if not filename:
        return None

    path = MINIMAPS_DIR / filename
    if path.exists():
        return Image.open(path)

    return None


def create_base_minimap_figure(map_id: str) -> go.Figure:
    """Create a Plotly figure with the 1024x1024 minimap background."""
    fig = go.Figure()
    img = get_minimap_image(map_id)

    if img is not None:
        fig.add_layout_image(
            dict(
                source=img,
                xref="x",
                yref="y",
                x=0,
                y=0,
                sizex=1024,
                sizey=1024,
                sizing="stretch",
                opacity=0.9,
                layer="below",
                xanchor="left",
                yanchor="top",
            )
        )

    # Configure axes with 1:1 aspect ratio and reversed Y-axis (top-left is 0,0)
    fig.update_xaxes(
        range=[0, 1024],
        showgrid=False,
        zeroline=False,
        visible=False,
        fixedrange=False,
    )
    fig.update_yaxes(
        range=[1024, 0],  # Critical trap fix: inverted range puts 0 at the top
        scaleanchor="x",
        scaleratio=1,
        showgrid=False,
        zeroline=False,
        visible=False,
        fixedrange=False,
    )

    fig.update_layout(
        plot_bgcolor="#0E1117",
        paper_bgcolor="#0E1117",
        margin=dict(l=10, r=10, t=30, b=10),
        width=820,
        height=820,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(color="#E0E0E0", size=11),
            bgcolor="rgba(14, 17, 23, 0.8)",
            bordercolor="#2A2E39",
            borderwidth=1,
        ),
        dragmode="pan",
    )
    return fig


def render_match_replay(
    match_df: pd.DataFrame,
    map_id: str,
    current_time_sec: float,
    show_humans: bool = True,
    show_bots: bool = True,
    show_paths: bool = True,
    show_events: bool = True,
    selected_events: Optional[List[str]] = None,
) -> go.Figure:
    """
    Render single match timeline replay.
    Draws trajectories and events up to `current_time_sec`.
    """
    fig = create_base_minimap_figure(map_id)

    # Filter by user category
    mask = pd.Series(True, index=match_df.index)
    if not show_humans and not show_bots:
        return fig
    elif not show_humans:
        mask = mask & match_df["is_bot"]
    elif not show_bots:
        mask = mask & (~match_df["is_bot"])

    active_match_df = match_df[mask]

    # Data up to current timeline playback scrubber
    current_df = active_match_df[active_match_df["match_time_sec"] <= current_time_sec]

    # 1. Draw Player / Bot Trajectory Paths
    if show_paths and not current_df.empty:
        # Separate humans and bots
        unique_users = current_df["user_id"].unique()
        for idx, user_id in enumerate(unique_users):
            user_data = current_df[current_df["user_id"] == user_id]
            # Include position points and events that have coordinates
            if user_data.empty:
                continue

            is_bot = bool(user_data["is_bot"].iloc[0])
            user_color = (
                "#707E94"
                if is_bot
                else PLAYER_PALETTE[idx % len(PLAYER_PALETTE)]
            )
            name_label = f"Bot #{user_id}" if is_bot else f"Player {str(user_id)[:8]}..."

            # Path line
            fig.add_trace(
                go.Scatter(
                    x=user_data["pixel_x"],
                    y=user_data["pixel_y"],
                    mode="lines",
                    name=name_label,
                    line=dict(
                        color=user_color,
                        width=1.5 if is_bot else 2.5,
                        dash="dot" if is_bot else "solid",
                    ),
                    opacity=0.55 if is_bot else 0.85,
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

            # Current position head marker (last known location)
            last_point = user_data.iloc[-1]
            # Only show head marker if updated within the last 30s
            is_active = (current_time_sec - last_point["match_time_sec"]) <= 30.0
            fig.add_trace(
                go.Scatter(
                    x=[last_point["pixel_x"]],
                    y=[last_point["pixel_y"]],
                    mode="markers",
                    name=name_label,
                    marker=dict(
                        size=9 if is_bot else 12,
                        color=user_color,
                        symbol="circle",
                        line=dict(color="#FFFFFF", width=1.5 if is_active else 0.5),
                        opacity=0.9 if is_active else 0.4,
                    ),
                    customdata=[[
                        name_label,
                        last_point["event"],
                        last_point["match_time_sec"],
                        last_point["y"],
                        last_point["x"],
                        last_point["z"],
                    ]],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Status: %{customdata[1]}<br>"
                        "Elapsed Time: %{customdata[2]:.1f}s<br>"
                        "Elevation: %{customdata[3]:.1f}m<br>"
                        "World Pos: (%{customdata[4]:.1f}, %{customdata[5]:.1f})<extra></extra>"
                    ),
                    showlegend=False,
                )
            )

    # 2. Draw Discrete Gameplay Events
    if show_events and not current_df.empty:
        filter_events = selected_events if selected_events else list(EVENT_STYLES.keys())
        events_df = current_df[
            current_df["event"].isin(filter_events)
            & ~current_df["event"].isin(["Position", "BotPosition"])
        ]

        for event_type, style in EVENT_STYLES.items():
            if event_type not in filter_events:
                continue
            sub_events = events_df[events_df["event"] == event_type]
            if sub_events.empty:
                continue

            custom_info = np.column_stack([
                sub_events["user_id"].astype(str),
                sub_events["event"].astype(str),
                sub_events["match_time_sec"].round(1),
                sub_events["y"].round(1),
                sub_events["x"].round(1),
                sub_events["z"].round(1),
            ])

            fig.add_trace(
                go.Scatter(
                    x=sub_events["pixel_x"],
                    y=sub_events["pixel_y"],
                    mode="markers",
                    name=style["name"],
                    marker=dict(
                        size=style["size"],
                        color=style["color"],
                        symbol=style["symbol"],
                        line=dict(color="#000000", width=1.2),
                        opacity=0.95,
                    ),
                    customdata=custom_info,
                    hovertemplate=(
                        f"<b>{style['desc']}</b><br>"
                        "Player: %{customdata[0]}<br>"
                        "Match Time: %{customdata[2]}s<br>"
                        "Elevation: %{customdata[3]}m<br>"
                        "World Pos: (%{customdata[4]}, %{customdata[5]})<extra></extra>"
                    ),
                    showlegend=True,
                )
            )

    fig.update_layout(
        title=dict(
            text=f"Match Replay — T = {current_time_sec:.0f}s",
            font=dict(color="#00D2FF", size=16),
            x=0.01,
            y=0.98,
        )
    )
    return fig


def render_aggregate_heatmap(
    df: pd.DataFrame,
    map_id: str,
    heatmap_type: str = "movement",
    opacity: float = 0.65,
    colorscale: str = "Inferno",
    show_humans: bool = True,
    show_bots: bool = True,
) -> go.Figure:
    """
    Render 2D density heatmap overlay on the minimap for aggregated insights.
    Supported types: 'movement', 'combat', 'deaths', 'storm', 'loot'.
    """
    fig = create_base_minimap_figure(map_id)

    # Filter by user category
    mask = df["map_id"] == map_id
    if not show_humans and not show_bots:
        return fig
    elif not show_humans:
        mask = mask & df["is_bot"]
    elif not show_bots:
        mask = mask & (~df["is_bot"])

    map_df = df[mask]
    if map_df.empty:
        return fig

    # Filter by heatmap target
    title_text = "Aggregate Heatmap"
    if heatmap_type == "movement":
        title_text = f"High-Traffic Movement Density ({len(map_df):,} Points)"
        heat_data = map_df[map_df["event"].isin(["Position", "BotPosition"])]
    elif heatmap_type == "combat":
        title_text = "Combat & Kill Hotspots"
        heat_data = map_df[map_df["event"].isin(["Kill", "BotKill"])]
    elif heatmap_type == "deaths":
        title_text = "Player & Bot Elimination Zones"
        heat_data = map_df[map_df["event"].isin(["Killed", "BotKilled", "KilledByStorm"])]
    elif heatmap_type == "storm":
        title_text = "Storm / Ring Death Clusters"
        heat_data = map_df[map_df["event"] == "KilledByStorm"]
    elif heatmap_type == "loot":
        title_text = "Loot Pickup Density"
        heat_data = map_df[map_df["event"] == "Loot"]
    else:
        heat_data = map_df

    if heat_data.empty:
        fig.add_annotation(
            text="No events found for this filter combination.",
            x=512,
            y=512,
            showarrow=False,
            font=dict(color="#FF9E00", size=16),
        )
        return fig

    # Add 2D Contour Heatmap
    fig.add_trace(
        go.Histogram2dContour(
            x=heat_data["pixel_x"],
            y=heat_data["pixel_y"],
            colorscale=colorscale,
            reversescale=False,
            showscale=True,
            ncontours=30,
            contours=dict(coloring="heatmap", showlines=False),
            opacity=opacity,
            colorbar=dict(
                title=dict(text="Density", font=dict(color="#E0E0E0", size=12)),
                tickfont=dict(color="#C0C0C0", size=10),
                len=0.7,
                y=0.5,
                thickness=16,
            ),
            hoverinfo="skip",
        )
    )

    # For rare/critical events (like Storm Deaths or PvP Kills), overlay individual scatter pins
    if heatmap_type in ["storm", "deaths", "combat"]:
        sample_pins = heat_data.head(500)  # Pin up to 500 for crisp visual reference
        fig.add_trace(
            go.Scatter(
                x=sample_pins["pixel_x"],
                y=sample_pins["pixel_y"],
                mode="markers",
                marker=dict(
                    size=7,
                    color="#00FFFF" if heatmap_type == "storm" else "#FF2A2A",
                    line=dict(color="#000000", width=1),
                    opacity=0.85,
                ),
                name="Incident Pins",
                customdata=np.column_stack([
                    sample_pins["event"].astype(str),
                    sample_pins["clean_match_id"].astype(str),
                    sample_pins["date"].astype(str),
                    sample_pins["match_time_sec"].round(1),
                ]),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Date: %{customdata[2]}<br>"
                    "Match: %{customdata[1]}<br>"
                    "Time: %{customdata[3]}s<extra></extra>"
                ),
                showlegend=True,
            )
        )

    fig.update_layout(
        title=dict(
            text=f"{title_text} — {map_id}",
            font=dict(color="#00D2FF", size=16),
            x=0.01,
            y=0.98,
        )
    )
    return fig
