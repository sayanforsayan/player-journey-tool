"""
Plotly minimap visualization engine for LILA BLACK player journey replay and heatmaps.
Tailored for Level Designers with intuitive visuals and plain-English tooltips.
"""

from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

MINIMAPS_DIR = Path(__file__).resolve().parent.parent / "minimaps"

# Designer-friendly event styling
EVENT_STYLES = {
    "Kill": {
        "name": "⚔️ Player vs Player Kill",
        "short_name": "PvP Kill",
        "color": "#FF2A2A",  # Crimson Red
        "symbol": "cross",
        "size": 14,
        "desc": "Player eliminated another player",
    },
    "Killed": {
        "name": "💀 Player vs Player Death",
        "short_name": "PvP Death",
        "color": "#7B0000",  # Dark Crimson
        "symbol": "x",
        "size": 14,
        "desc": "Player eliminated by an opponent",
    },
    "BotKill": {
        "name": "🎯 Player Killed an AI Bot",
        "short_name": "Bot Kill",
        "color": "#FF9E00",  # Amber Orange
        "symbol": "triangle-up",
        "size": 12,
        "desc": "Player destroyed an AI opponent",
    },
    "BotKilled": {
        "name": "🛑 Player Died to an AI Bot",
        "short_name": "Killed by Bot",
        "color": "#B5179E",  # Purple
        "symbol": "triangle-down",
        "size": 12,
        "desc": "Player was killed by an AI bot",
    },
    "KilledByStorm": {
        "name": "⚡ Died to the Storm Ring",
        "short_name": "Storm Death",
        "color": "#00F0FF",  # Neon Cyan
        "symbol": "hexagon",
        "size": 15,
        "desc": "Player trapped & eliminated by storm",
    },
    "Loot": {
        "name": "📦 Loot Pickup",
        "short_name": "Loot",
        "color": "#FFD166",  # Bright Gold
        "symbol": "diamond",
        "size": 8,
        "desc": "Item scavenged from map",
    },
}

MAP_FILENAMES = {
    "AmbroseValley": "AmbroseValley_Minimap.png",
    "GrandRift": "GrandRift_Minimap.png",
    "Lockdown": "Lockdown_Minimap.jpg",
}

# Qualitative colors for individual player trajectories
PLAYER_PALETTE = [
    "#3A86FF",  # Vivid Blue
    "#FF006E",  # Magenta
    "#FB5607",  # Orange
    "#8338EC",  # Purple
    "#06D6A0",  # Teal/Emerald
    "#FFBE0B",  # Yellow
    "#118AB2",  # Ocean Blue
    "#073B4C",  # Deep Navy
]


def format_time_mmss(sec: float) -> str:
    """Format seconds into MM:SS string."""
    s = int(round(sec))
    return f"{s // 60:02d}:{s % 60:02d}"


def get_elevation_label(y_val: float, map_id: str) -> str:
    """Provide level design elevation context based on map terrain."""
    if map_id == "AmbroseValley":
        if y_val > 130:
            return "High Ground / Hilltop"
        elif y_val < 95:
            return "Low Valley / Riverbed"
        return "Mid Elevation"
    elif map_id == "GrandRift":
        if y_val > 35:
            return "Canyon Rim / Bridge"
        return "Lower Gorge"
    else:
        if y_val > 55:
            return "Upper Catwalk / Floor 2"
        return "Ground Floor"


def get_minimap_image(map_id: str) -> Optional[Image.Image]:
    """Load 1024x1024 minimap image."""
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
                opacity=0.92,
                layer="below",
                xanchor="left",
                yanchor="top",
            )
        )

    # Configure 1:1 aspect ratio with inverted Y-axis (top-left is 0,0)
    fig.update_xaxes(
        range=[0, 1024],
        showgrid=False,
        zeroline=False,
        visible=False,
        fixedrange=False,
    )
    fig.update_yaxes(
        range=[1024, 0],  # Inverted range: 0 is top
        scaleanchor="x",
        scaleratio=1,
        showgrid=False,
        zeroline=False,
        visible=False,
        fixedrange=False,
    )

    fig.update_layout(
        plot_bgcolor="#0A0C10",
        paper_bgcolor="#0A0C10",
        margin=dict(l=10, r=10, t=30, b=10),
        width=820,
        height=820,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(color="#E6EDF3", size=11),
            bgcolor="rgba(10, 12, 16, 0.85)",
            bordercolor="#30363D",
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

    # Filter entities
    mask = pd.Series(True, index=match_df.index)
    if not show_humans and not show_bots:
        return fig
    elif not show_humans:
        mask = mask & match_df["is_bot"]
    elif not show_bots:
        mask = mask & (~match_df["is_bot"])

    active_match_df = match_df[mask]
    current_df = active_match_df[active_match_df["match_time_sec"] <= current_time_sec]

    time_str = format_time_mmss(current_time_sec)

    # 1. Player & Bot Movement Trails
    if show_paths and not current_df.empty:
        unique_users = current_df["user_id"].unique()
        for idx, user_id in enumerate(unique_users):
            user_data = current_df[current_df["user_id"] == user_id]
            if user_data.empty:
                continue

            is_bot = bool(user_data["is_bot"].iloc[0])
            user_color = (
                "#8B949E"
                if is_bot
                else PLAYER_PALETTE[idx % len(PLAYER_PALETTE)]
            )
            name_label = f"AI Bot #{user_id}" if is_bot else f"Player {str(user_id)[:6]}"

            # Trajectory line
            fig.add_trace(
                go.Scatter(
                    x=user_data["pixel_x"],
                    y=user_data["pixel_y"],
                    mode="lines",
                    name=name_label,
                    line=dict(
                        color=user_color,
                        width=1.5 if is_bot else 2.8,
                        dash="dot" if is_bot else "solid",
                    ),
                    opacity=0.45 if is_bot else 0.85,
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

            # Player head position (current location)
            last_point = user_data.iloc[-1]
            time_since_move = current_time_sec - last_point["match_time_sec"]
            is_active = time_since_move <= 45.0  # Active within last 45s

            elev_label = get_elevation_label(last_point["y"], map_id)
            point_time_str = format_time_mmss(last_point["match_time_sec"])

            fig.add_trace(
                go.Scatter(
                    x=[last_point["pixel_x"]],
                    y=[last_point["pixel_y"]],
                    mode="markers",
                    name=name_label,
                    marker=dict(
                        size=9 if is_bot else 13,
                        color=user_color,
                        symbol="circle",
                        line=dict(color="#FFFFFF", width=2.0 if is_active else 0.8),
                        opacity=0.95 if is_active else 0.35,
                    ),
                    customdata=[[
                        name_label,
                        last_point["event"],
                        point_time_str,
                        last_point["y"],
                        elev_label,
                    ]],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "🕒 Match Time: %{customdata[2]}<br>"
                        "Status: %{customdata[1]}<br>"
                        "Height: %{customdata[3]:.1f}m (%{customdata[4]})<extra></extra>"
                    ),
                    showlegend=False,
                )
            )

    # 2. Discrete Gameplay Events
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

            time_labels = [format_time_mmss(t) for t in sub_events["match_time_sec"]]
            elev_labels = [get_elevation_label(y, map_id) for y in sub_events["y"]]
            user_labels = [
                f"AI Bot #{u}" if is_b else f"Player {str(u)[:6]}"
                for u, is_b in zip(sub_events["user_id"], sub_events["is_bot"])
            ]
            desc_labels = [style["desc"]] * len(sub_events)

            custom_info = np.column_stack([
                user_labels,
                desc_labels,
                time_labels,
                sub_events["y"].round(1),
                elev_labels,
            ])

            fig.add_trace(
                go.Scatter(
                    x=sub_events["pixel_x"],
                    y=sub_events["pixel_y"],
                    mode="markers",
                    name=style["short_name"],
                    marker=dict(
                        size=style["size"],
                        color=style["color"],
                        symbol=style["symbol"],
                        line=dict(color="#000000", width=1.2),
                        opacity=0.95,
                    ),
                    customdata=custom_info,
                    hovertemplate=(
                        f"<b>{style['short_name']}</b><br>"
                        "%{customdata[1]}<br>"
                        "Involved: %{customdata[0]}<br>"
                        "🕒 Time: %{customdata[2]}<br>"
                        "Elevation: %{customdata[3]}m (%{customdata[4]})<extra></extra>"
                    ),
                    showlegend=True,
                )
            )

    fig.update_layout(
        title=dict(
            text=f"Match Replay • Timeline: <b>{time_str}</b>",
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
    Render 2D density heatmap overlay on the minimap for level designers.
    """
    fig = create_base_minimap_figure(map_id)

    # Filter entities
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

    # Map friendly targets
    title_text = "Heatmap"
    if heatmap_type == "movement":
        title_text = "👣 Player Footsteps & High-Traffic Paths"
        heat_data = map_df[map_df["event"].isin(["Position", "BotPosition"])]
    elif heatmap_type == "combat":
        title_text = "⚔️ Firefights & Kill Hotspots (Choke Points)"
        heat_data = map_df[map_df["event"].isin(["Kill", "BotKill"])]
    elif heatmap_type == "deaths":
        title_text = "💀 Player Elimination & Danger Zones"
        heat_data = map_df[map_df["event"].isin(["Killed", "BotKilled", "KilledByStorm"])]
    elif heatmap_type == "storm":
        title_text = "⚡ Storm Ring Deaths (Extraction Traps)"
        heat_data = map_df[map_df["event"] == "KilledByStorm"]
    elif heatmap_type == "loot":
        title_text = "📦 Loot Pickup Hotspots"
        heat_data = map_df[map_df["event"] == "Loot"]
    else:
        heat_data = map_df

    if heat_data.empty:
        fig.add_annotation(
            text="No recorded events for this category on this map.",
            x=512,
            y=512,
            showarrow=False,
            font=dict(color="#FF9E00", size=16),
        )
        return fig

    # 2D Contour Heatmap
    fig.add_trace(
        go.Histogram2dContour(
            x=heat_data["pixel_x"],
            y=heat_data["pixel_y"],
            colorscale=colorscale,
            reversescale=False,
            showscale=True,
            ncontours=28,
            contours=dict(coloring="heatmap", showlines=False),
            opacity=opacity,
            colorbar=dict(
                title=dict(text="Density", font=dict(color="#E6EDF3", size=11)),
                tickfont=dict(color="#8B949E", size=10),
                len=0.7,
                y=0.5,
                thickness=16,
            ),
            hoverinfo="skip",
        )
    )

    # For rare/critical events (like Storm Deaths or PvP Kills), overlay individual pins
    if heatmap_type in ["storm", "deaths", "combat"]:
        sample_pins = heat_data.head(500)
        time_labels = [format_time_mmss(t) for t in sample_pins["match_time_sec"]]
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
                    time_labels,
                ]),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Date: %{customdata[2]}<br>"
                    "Match: %{customdata[1]}<br>"
                    "Time: %{customdata[3]}<extra></extra>"
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
