"""
LILA BLACK — Player Journey Visualization Tool
Web-based interactive telemetry visualizer for Level Designers.
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from src.data_loader import (
    load_data,
    get_available_maps,
    get_available_dates,
    get_matches_for_selection,
    get_match_info,
    get_aggregate_stats,
    MAP_CONFIGS,
    ALL_EVENT_TYPES,
)
from src.map_renderer import (
    render_match_replay,
    render_aggregate_heatmap,
    EVENT_STYLES,
)

# Set page config
st.set_page_config(
    page_title="LILA BLACK — Player Journey Tool",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for Dark UI & Game Dev Dashboard
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }
        .main-header {
            font-size: 1.8rem;
            font-weight: 700;
            color: #00D2FF;
            margin-bottom: 0.2rem;
        }
        .sub-header {
            font-size: 0.95rem;
            color: #A0AAB8;
            margin-bottom: 1rem;
        }
        .kpi-card {
            background-color: #161B22;
            border: 1px solid #30363D;
            border-radius: 8px;
            padding: 12px 16px;
            text-align: center;
        }
        .kpi-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #00D2FF;
        }
        .kpi-label {
            font-size: 0.8rem;
            color: #8B949E;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .stSlider [data-baseweb="slider"] {
            margin-top: -10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def get_cached_dataset():
    return load_data()


def main():
    # Load data
    try:
        df = get_cached_dataset()
    except Exception as e:
        st.error(f"Failed to load dataset: {e}")
        st.info("Run `python scripts/preprocess.py` to bake the dataset first.")
        return

    # Sidebar Header
    st.sidebar.markdown("## 🎯 LILA BLACK")
    st.sidebar.markdown(
        "<div style='margin-top: -12px; margin-bottom: 12px; color: #8B949E; font-size: 0.85rem;'>"
        "Level Design Telemetry Suite</div>",
        unsafe_allow_html=True,
    )

    # 1. Map Filter
    maps = get_available_maps(df)
    map_labels = {
        m: f"{m} ({MAP_CONFIGS.get(m, {}).get('display_name', m)})" for m in maps
    }
    selected_map = st.sidebar.selectbox(
        "Select Map",
        options=maps,
        format_func=lambda m: map_labels.get(m, m),
        index=0,
    )

    # 2. Date Filter
    dates = ["All Dates"] + get_available_dates(df, selected_map)
    selected_date = st.sidebar.selectbox("Filter by Date", options=dates, index=0)

    if selected_date == "2026-02-14":
        st.sidebar.caption("⚠️ **Note:** Feb 14 is a partial telemetry collection day.")

    st.sidebar.markdown("---")

    # 3. View Mode
    view_mode = st.sidebar.radio(
        "View Mode",
        options=["🎬 Match Journey Replay", "🔥 Aggregate Heatmaps"],
        index=0,
    )

    st.sidebar.markdown("---")

    # 4. Entity Visibility
    st.sidebar.markdown("### Entity & Event Visibility")
    show_humans = st.sidebar.checkbox("Show Human Players (UUID)", value=True)
    show_bots = st.sidebar.checkbox("Show AI Bots (Numeric ID)", value=True)

    # Discrete events filter
    event_options = list(EVENT_STYLES.keys())
    selected_events = st.sidebar.multiselect(
        "Display Event Markers",
        options=event_options,
        default=event_options,
        format_func=lambda ev: EVENT_STYLES[ev]["name"],
    )

    # Main Area Header
    map_info = MAP_CONFIGS.get(selected_map, {})
    st.markdown(
        f"<div class='main-header'>🗺️ {selected_map} — Level Design Analytics</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='sub-header'>Scale: <b>{map_info.get('scale')}</b> | "
        f"Origin: <b>({map_info.get('origin_x')}, {map_info.get('origin_z')})</b> | "
        f"Selected Date: <b>{selected_date}</b></div>",
        unsafe_allow_html=True,
    )

    # =========================================================================
    # VIEW MODE 1: MATCH REPLAY
    # =========================================================================
    if view_mode == "🎬 Match Journey Replay":
        matches = get_matches_for_selection(df, selected_map, selected_date)
        if not matches:
            st.warning("No matches found for the current filter criteria.")
            return

        # Sidebar match picker
        col_m1, col_m2 = st.sidebar.columns([3, 1])
        selected_match = col_m1.selectbox(
            "Select Match ID",
            options=matches,
            index=0,
            help="Unique match instance identifier",
        )
        col_m2.metric("Matches", len(matches))

        match_df = df[df["clean_match_id"] == selected_match]
        match_meta = get_match_info(df, selected_match)

        # Top KPI Metric Strip for selected match
        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        with kpi1:
            st.markdown(
                f"<div class='kpi-card'><div class='kpi-value'>{match_meta.get('duration_sec', 0):.0f}s</div>"
                f"<div class='kpi-label'>Duration</div></div>",
                unsafe_allow_html=True,
            )
        with kpi2:
            st.markdown(
                f"<div class='kpi-card'><div class='kpi-value'>{match_meta.get('human_count', 0)} / {match_meta.get('bot_count', 0)}</div>"
                f"<div class='kpi-label'>Humans / Bots</div></div>",
                unsafe_allow_html=True,
            )
        with kpi3:
            st.markdown(
                f"<div class='kpi-card'><div class='kpi-value'>{match_meta.get('player_kills', 0) + match_meta.get('bot_kills', 0)}</div>"
                f"<div class='kpi-label'>Total Kills</div></div>",
                unsafe_allow_html=True,
            )
        with kpi4:
            st.markdown(
                f"<div class='kpi-card'><div class='kpi-value'>{match_meta.get('storm_deaths', 0)}</div>"
                f"<div class='kpi-label'>Storm Deaths</div></div>",
                unsafe_allow_html=True,
            )
        with kpi5:
            st.markdown(
                f"<div class='kpi-card'><div class='kpi-value'>{match_meta.get('loot_events', 0)}</div>"
                f"<div class='kpi-label'>Loot Pickups</div></div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

        # Timeline Scrubber Controls
        max_duration = float(match_meta.get("duration_sec", 10.0))
        if max_duration <= 0.0:
            max_duration = 1.0

        col_time, col_opt = st.columns([3, 1])
        with col_time:
            current_time = st.slider(
                "⏱️ Timeline Scrubber (Seconds Elapsed from Match Start):",
                min_value=0.0,
                max_value=max_duration,
                value=max_duration,
                step=1.0 if max_duration > 10 else 0.1,
                help="Scrub to watch players traverse the map and events unfold over time",
            )
        with col_opt:
            show_paths = st.checkbox("Show Trajectory Lines", value=True)
            show_events = st.checkbox("Show Event Markers", value=True)

        # Render Map Figure
        replay_fig = render_match_replay(
            match_df=match_df,
            map_id=selected_map,
            current_time_sec=current_time,
            show_humans=show_humans,
            show_bots=show_bots,
            show_paths=show_paths,
            show_events=show_events,
            selected_events=selected_events,
        )

        st.plotly_chart(
            replay_fig,
            use_container_width=True,
            config={"scrollZoom": True, "displayModeBar": True},
        )

        # Match Event Feed / Chronological Combat Log
        with st.expander("📜 Chronological Match Combat & Event Log", expanded=False):
            combat_df = match_df[
                match_df["event"].isin(
                    ["Kill", "Killed", "BotKill", "BotKilled", "KilledByStorm", "Loot"]
                )
                & (match_df["match_time_sec"] <= current_time)
            ][["match_time_sec", "event", "user_id", "is_bot", "x", "y", "z"]]
            if not combat_df.empty:
                st.dataframe(
                    combat_df.sort_values(by="match_time_sec"),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("No combat or loot events up to this timestamp.")

    # =========================================================================
    # VIEW MODE 2: AGGREGATE HEATMAPS
    # =========================================================================
    else:
        # Filter master dataset
        agg_mask = df["map_id"] == selected_map
        if selected_date != "All Dates":
            agg_mask = agg_mask & (df["date"] == selected_date)
        filtered_agg_df = df[agg_mask]

        stats = get_aggregate_stats(filtered_agg_df)

        # Top KPI Metric Strip for Aggregates
        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            st.markdown(
                f"<div class='kpi-card'><div class='kpi-value'>{stats['total_matches']:,}</div>"
                f"<div class='kpi-label'>Total Matches</div></div>",
                unsafe_allow_html=True,
            )
        with k2:
            st.markdown(
                f"<div class='kpi-card'><div class='kpi-value'>{stats['human_players']:,} / {stats['bot_players']:,}</div>"
                f"<div class='kpi-label'>Humans / Bots</div></div>",
                unsafe_allow_html=True,
            )
        with k3:
            st.markdown(
                f"<div class='kpi-card'><div class='kpi-value'>{stats['pvp_kills'] + stats['bot_kills']:,}</div>"
                f"<div class='kpi-label'>Total Kills</div></div>",
                unsafe_allow_html=True,
            )
        with k4:
            st.markdown(
                f"<div class='kpi-card'><div class='kpi-value'>{stats['storm_deaths']:,}</div>"
                f"<div class='kpi-label'>Storm Deaths</div></div>",
                unsafe_allow_html=True,
            )
        with k5:
            st.markdown(
                f"<div class='kpi-card'><div class='kpi-value'>{stats['loot_pickups']:,}</div>"
                f"<div class='kpi-label'>Loot Pickups</div></div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

        # Heatmap Configuration Toolbar
        col_type, col_cmap, col_opac = st.columns([2, 1, 1])
        with col_type:
            heatmap_target = st.selectbox(
                "🔥 Heatmap Overlay Target:",
                options=[
                    ("movement", "🚶 High-Traffic Movement Density"),
                    ("combat", "⚔️ Combat & Kill Hotspots"),
                    ("deaths", "💀 Player & Bot Death Locations"),
                    ("storm", "⚡ Storm Ring Deaths"),
                    ("loot", "📦 Loot Pickup Hotspots"),
                ],
                format_func=lambda x: x[1],
                index=0,
            )[0]
        with col_cmap:
            colorscale = st.selectbox(
                "Color Palette:",
                options=["Inferno", "Hot", "Turbo", "Viridis", "Plasma", "YlOrRd"],
                index=0,
            )
        with col_opac:
            opacity = st.slider("Overlay Opacity:", min_value=0.2, max_value=1.0, value=0.65, step=0.05)

        # Render Aggregate Heatmap
        heat_fig = render_aggregate_heatmap(
            df=filtered_agg_df,
            map_id=selected_map,
            heatmap_type=heatmap_target,
            opacity=opacity,
            colorscale=colorscale,
            show_humans=show_humans,
            show_bots=show_bots,
        )

        st.plotly_chart(
            heat_fig,
            use_container_width=True,
            config={"scrollZoom": True, "displayModeBar": True},
        )

        # Quick Insights Callout
        st.info(
            "💡 **Level Designer Tip:** Compare 'High-Traffic Movement' with 'Loot Pickups' to spot ignored map quadrants, "
            "or review 'Storm Ring Deaths' to see bottlenecks where players get caught by the storm before extracting."
        )


if __name__ == "__main__":
    main()
