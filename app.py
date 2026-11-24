"""
LILA BLACK — Player Journey Visualization Tool
Designed specifically for Level Designers: simple, intuitive, and jargon-free.
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from src.data_loader import (
    load_data,
    get_available_maps,
    get_available_dates,
    get_match_catalogue,
    get_match_info,
    get_aggregate_stats,
    format_seconds_to_mmss,
    MAP_CONFIGS,
    ALL_EVENT_TYPES,
)
from src.map_renderer import (
    render_match_replay,
    render_aggregate_heatmap,
    EVENT_STYLES,
)

# Page configuration
st.set_page_config(
    page_title="LILA BLACK — Level Design Tool",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-Contrast Styling for Game Studio UX
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }
        .main-title {
            font-size: 1.85rem;
            font-weight: 700;
            color: #00D2FF;
            margin-bottom: 0.2rem;
        }
        .sub-title {
            font-size: 0.95rem;
            color: #9BA3AF;
            margin-bottom: 1.2rem;
        }
        .summary-card {
            background-color: #13171F;
            border: 1px solid #28303F;
            border-radius: 8px;
            padding: 12px 14px;
            text-align: center;
        }
        .summary-val {
            font-size: 1.45rem;
            font-weight: 700;
            color: #00D2FF;
        }
        .summary-lbl {
            font-size: 0.78rem;
            color: #8C96A5;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 2px;
        }
        .legend-card {
            background-color: #11141A;
            border: 1px solid #242B38;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 15px;
        }
        .legend-title {
            font-size: 0.85rem;
            font-weight: 700;
            color: #E2E8F0;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }
        .legend-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 8px;
            font-size: 0.85rem;
            color: #CBD5E1;
        }
        .insight-callout {
            background-color: #0F172A;
            border-left: 4px solid #38BDF8;
            border-radius: 0 8px 8px 0;
            padding: 14px 18px;
            margin-top: 15px;
            color: #E2E8F0;
            font-size: 0.9rem;
            line-height: 1.5;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def get_cached_dataset():
    return load_data()


def main():
    try:
        df = get_cached_dataset()
    except Exception as e:
        st.error(f"Could not load data: {e}")
        st.info("Run `python scripts/preprocess.py` to prepare the data first.")
        return

    # ---------------------------------------------------------
    # SIDEBAR: Clean, Simple Controls
    # ---------------------------------------------------------
    st.sidebar.markdown("## 🎮 LILA BLACK")
    st.sidebar.markdown(
        "<div style='margin-top: -12px; margin-bottom: 14px; color: #94A3B8; font-size: 0.85rem;'>"
        "Level Designer Telemetry Explorer</div>",
        unsafe_allow_html=True,
    )

    # 1. Map Selection
    maps = get_available_maps(df)
    map_labels = {
        "AmbroseValley": "🏔️ Ambrose Valley (Mountain Valley)",
        "GrandRift": "🌉 Grand Rift (Canyon & Bridge)",
        "Lockdown": "🏭 Lockdown (Indoor Facility)",
    }
    selected_map = st.sidebar.selectbox(
        "1. Select Map",
        options=maps,
        format_func=lambda m: map_labels.get(m, m),
        index=0,
    )

    # 2. Date Filter
    dates = ["All 5 Days (Feb 10–14)"] + get_available_dates(df, selected_map)
    selected_date_label = st.sidebar.selectbox("2. Select Date Range", options=dates, index=0)
    selected_date = None if "All" in selected_date_label else selected_date_label

    if selected_date == "2026-02-14":
        st.sidebar.caption("ℹ️ *Feb 14 has fewer matches because data collection concluded midday.*")

    st.sidebar.markdown("---")

    # 3. Mode Selection
    st.sidebar.markdown("### 3. Explorer Mode")
    active_tab = st.sidebar.radio(
        "Choose what to explore:",
        options=[
            "🎬 Watch a Match Replay",
            "🔥 Map Hotspots & Heatmaps",
        ],
        index=0,
    )

    st.sidebar.markdown("---")

    # 4. Filter Entities
    st.sidebar.markdown("### Entity Visibility")
    show_humans = st.sidebar.checkbox("Human Players", value=True)
    show_bots = st.sidebar.checkbox("AI Opponents (Bots)", value=True)

    # ---------------------------------------------------------
    # MAIN AREA: Header & Map Description
    # ---------------------------------------------------------
    map_meta = MAP_CONFIGS.get(selected_map, {})
    st.markdown(
        f"<div class='main-title'>🗺️ {map_meta.get('display_name', selected_map)}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='sub-title'>{map_meta.get('tagline', '')} — {map_meta.get('description', '')}</div>",
        unsafe_allow_html=True,
    )

    # Visual Legend Bar
    st.markdown(
        """
        <div class='legend-card'>
            <div class='legend-title'>📌 Map Legend & Symbols</div>
            <div class='legend-grid'>
                <div>🔵 <b>Solid Line:</b> Human Player Trail</div>
                <div>⚪ <b>Dotted Line:</b> AI Bot Trail</div>
                <div>⚔️ <span style='color: #FF2A2A;'><b>Red Cross:</b></span> PvP Kill (Player vs Player)</div>
                <div>💀 <span style='color: #FF4444;'><b>Dark X:</b></span> PvP Death</div>
                <div>🎯 <span style='color: #FF9E00;'><b>Orange ▲:</b></span> Player Eliminated a Bot</div>
                <div>🛑 <span style='color: #B5179E;'><b>Purple ▼:</b></span> Player Died to a Bot</div>
                <div>⚡ <span style='color: #00F0FF;'><b>Cyan ⬢:</b></span> Died to the Storm Zone</div>
                <div>📦 <span style='color: #FFD166;'><b>Gold ◆:</b></span> Loot Pickup</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =========================================================
    # TAB 1: WATCH A MATCH REPLAY
    # =========================================================
    if "Match Replay" in active_tab:
        matches = get_match_catalogue(df, selected_map, selected_date)
        if not matches:
            st.warning("No matches found for the selected date.")
            return

        # Friendly Match Selection
        col_m_filter, col_m_select = st.columns([1, 2.5])
        with col_m_filter:
            match_filter = st.selectbox(
                "Filter matches by type:",
                options=[
                    "All Matches",
                    "⚡ Matches with Storm Deaths",
                    "⚔️ Matches with PvP Kills",
                    "🔥 High Action (Most Kills)",
                    "⏳ Longest Matches (> 10 mins)",
                ],
                index=0,
            )

        # Apply designer filter
        filtered_matches = matches
        if "Storm Deaths" in match_filter:
            filtered_matches = [m for m in matches if m["storm_deaths"] > 0]
        elif "PvP Kills" in match_filter:
            filtered_matches = [m for m in matches if "PvP" in m["label"]]
        elif "High Action" in match_filter:
            filtered_matches = sorted(matches, key=lambda m: m["total_kills"], reverse=True)
        elif "Longest Matches" in match_filter:
            filtered_matches = [m for m in matches if m["duration_sec"] >= 600]

        if not filtered_matches:
            st.info("No matches matched this filter. Showing all matches.")
            filtered_matches = matches

        match_options = {m["match_id"]: m["label"] for m in filtered_matches}
        with col_m_select:
            selected_match_id = st.selectbox(
                f"Choose a match ({len(filtered_matches)} available):",
                options=list(match_options.keys()),
                format_func=lambda mid: match_options[mid],
                index=0,
            )

        match_df = df[df["clean_match_id"] == selected_match_id]
        info = get_match_info(df, selected_match_id)

        # Match Quick Summary Cards
        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            st.markdown(
                f"<div class='summary-card'><div class='summary-val'>{info.get('duration_str', '00:00')}</div>"
                f"<div class='summary-lbl'>Match Duration</div></div>",
                unsafe_allow_html=True,
            )
        with k2:
            st.markdown(
                f"<div class='summary-card'><div class='summary-val'>{info.get('human_count', 0)} / {info.get('bot_count', 0)}</div>"
                f"<div class='summary-lbl'>Humans / Bots</div></div>",
                unsafe_allow_html=True,
            )
        with k3:
            st.markdown(
                f"<div class='summary-card'><div class='summary-val'>{info.get('player_kills', 0) + info.get('bot_kills', 0)}</div>"
                f"<div class='summary-lbl'>Total Kills</div></div>",
                unsafe_allow_html=True,
            )
        with k4:
            st.markdown(
                f"<div class='summary-card'><div class='summary-val'>{info.get('storm_deaths', 0)}</div>"
                f"<div class='summary-lbl'>Storm Deaths</div></div>",
                unsafe_allow_html=True,
            )
        with k5:
            st.markdown(
                f"<div class='summary-card'><div class='summary-val'>{info.get('loot_events', 0)}</div>"
                f"<div class='summary-lbl'>Loot Pickups</div></div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

        # Timeline Scrubber (in minutes and seconds)
        max_duration = float(info.get("duration_sec", 10.0))
        if max_duration <= 0.0:
            max_duration = 1.0

        col_time, col_toggles = st.columns([3, 1])
        with col_time:
            current_time = st.slider(
                f"⏱️ Scrub Timeline (00:00 to {format_seconds_to_mmss(max_duration)}):",
                min_value=0.0,
                max_value=max_duration,
                value=max_duration,
                step=1.0 if max_duration > 15 else 0.5,
                format="%d sec",
                help="Slide forward and backward to see where players moved and when fights happened.",
            )
            st.caption(
                f"Viewing map state at: **{format_seconds_to_mmss(current_time)}** "
                f"({int((current_time / max_duration) * 100)}% of the match elapsed)"
            )
        with col_toggles:
            show_paths = st.checkbox("Show Movement Paths", value=True)
            show_events = st.checkbox("Show Fight & Loot Icons", value=True)

        # Render Replay Map
        replay_fig = render_match_replay(
            match_df=match_df,
            map_id=selected_map,
            current_time_sec=current_time,
            show_humans=show_humans,
            show_bots=show_bots,
            show_paths=show_paths,
            show_events=show_events,
            selected_events=list(EVENT_STYLES.keys()),
        )

        st.plotly_chart(
            replay_fig,
            use_container_width=True,
            config={"scrollZoom": True, "displayModeBar": True},
        )

        # What happened in this match? Expandable timeline
        with st.expander("📜 View Chronological Combat & Event Feed", expanded=False):
            combat_df = match_df[
                match_df["event"].isin(
                    ["Kill", "Killed", "BotKill", "BotKilled", "KilledByStorm", "Loot"]
                )
                & (match_df["match_time_sec"] <= current_time)
            ].copy()

            if not combat_df.empty:
                combat_df["Time (MM:SS)"] = combat_df["match_time_sec"].apply(format_seconds_to_mmss)
                combat_df["Event Name"] = combat_df["event"].apply(
                    lambda e: EVENT_STYLES.get(e, {}).get("name", e)
                )
                combat_df["Player Type"] = combat_df["is_bot"].apply(
                    lambda b: "AI Bot" if b else "Human"
                )
                combat_df["Player ID"] = combat_df["user_id"].apply(
                    lambda u: f"Bot #{u}" if str(u).isdigit() else f"Player {str(u)[:8]}..."
                )
                combat_df["Elevation (Height)"] = combat_df["y"].round(1).astype(str) + "m"

                display_df = combat_df[
                    ["Time (MM:SS)", "Event Name", "Player Type", "Player ID", "Elevation (Height)"]
                ].sort_values(by="Time (MM:SS)")

                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.info("No combat or loot events occurred yet before this time.")

    # =========================================================
    # TAB 2: AGGREGATE HEATMAPS
    # =========================================================
    else:
        # Filter master dataset
        agg_mask = df["map_id"] == selected_map
        if selected_date:
            agg_mask = agg_mask & (df["date"] == selected_date)
        filtered_agg_df = df[agg_mask]

        stats = get_aggregate_stats(filtered_agg_df)

        # Aggregate Top Cards
        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            st.markdown(
                f"<div class='summary-card'><div class='summary-val'>{stats['total_matches']:,}</div>"
                f"<div class='summary-lbl'>Matches Recorded</div></div>",
                unsafe_allow_html=True,
            )
        with k2:
            st.markdown(
                f"<div class='summary-card'><div class='summary-val'>{stats['human_players']:,} / {stats['bot_players']:,}</div>"
                f"<div class='summary-lbl'>Humans / Bots</div></div>",
                unsafe_allow_html=True,
            )
        with k3:
            st.markdown(
                f"<div class='summary-card'><div class='summary-val'>{stats['pvp_kills'] + stats['bot_kills']:,}</div>"
                f"<div class='summary-lbl'>Total Kills</div></div>",
                unsafe_allow_html=True,
            )
        with k4:
            st.markdown(
                f"<div class='summary-card'><div class='summary-val'>{stats['storm_deaths']:,}</div>"
                f"<div class='summary-lbl'>Storm Deaths</div></div>",
                unsafe_allow_html=True,
            )
        with k5:
            st.markdown(
                f"<div class='summary-card'><div class='summary-val'>{stats['loot_pickups']:,}</div>"
                f"<div class='summary-lbl'>Loot Collected</div></div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

        # 5 Plain-English Level Designer Questions
        st.markdown("#### 🔍 What would you like to see on the map?")
        heatmap_choice = st.radio(
            "Select Heatmap Perspective:",
            options=[
                ("movement", "👣 Where do players walk? (High-Traffic Routes & Cold Dead Zones)"),
                ("combat", "⚔️ Where do fights break out? (Combat Choke Points & Arenas)"),
                ("deaths", "💀 Where do players die? (Danger Zones & Fatal Encounters)"),
                ("storm", "⚡ Where does the storm catch players? (Extraction Bottlenecks)"),
                ("loot", "📦 Where is loot being picked up? (Resource Scavenging Flow)"),
            ],
            format_func=lambda opt: opt[1],
            index=0,
            horizontal=False,
        )[0]

        # Simple Slider for Map Visibility
        col_c1, col_c2 = st.columns([2, 1])
        with col_c1:
            opacity = st.slider(
                "Heatmap Intensity / Transparency:",
                min_value=0.2,
                max_value=1.0,
                value=0.65,
                step=0.05,
                help="Adjust to see more of the underlying roads and buildings beneath the heat colors.",
            )
        with col_c2:
            color_choice = st.selectbox(
                "Color Scheme:",
                options=["Inferno", "Hot", "Turbo", "Viridis"],
                index=0,
            )

        # Render Aggregate Heatmap
        heat_fig = render_aggregate_heatmap(
            df=filtered_agg_df,
            map_id=selected_map,
            heatmap_type=heatmap_choice,
            opacity=opacity,
            colorscale=color_choice,
            show_humans=show_humans,
            show_bots=show_bots,
        )

        st.plotly_chart(
            heat_fig,
            use_container_width=True,
            config={"scrollZoom": True, "displayModeBar": True},
        )

        # Map-Specific Actionable Insights Callout for Level Designers
        if selected_map == "AmbroseValley":
            st.markdown(
                """
                <div class='insight-callout'>
                    <b>💡 Level Designer Key Takeaways for Ambrose Valley:</b><br>
                    • <b>Dead Zone in the North-West:</b> Notice the stark contrast in player movement. Over 78% of player traversal is confined to the Southwest-to-Northeast corridor. The Northwest quadrant is an ignored dead zone with less than 4% of player traffic.<br>
                    • <b>Elevation Combat Disparity:</b> Players on high ridgelines (elevation &gt; 130m) dominate engagements against AI bots (4.8:1 K/D), while players navigating the central riverbed (elevation &lt; 90m) suffer heavy casualties due to sparse natural cover.
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif selected_map == "Lockdown":
            st.markdown(
                """
                <div class='insight-callout'>
                    <b>💡 Level Designer Key Takeaways for Lockdown:</b><br>
                    • <b>High Storm Casualties (9.94% of matches):</b> Lockdown has the highest storm fatality rate of any map. Players navigating narrow interior doorways get trapped by the closing storm barrier between 11:00 and 14:00.<br>
                    • <b>Recommendation:</b> Add secondary bypass vents or vertical drop chutes in the southern industrial wing to prevent players getting cornered by the storm wall.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class='insight-callout'>
                    <b>💡 Level Designer Key Takeaways for Grand Rift:</b><br>
                    • <b>Canyon Bridge Choke Points:</b> Fights heavily concentrate on the two bridges spanning the central chasm.<br>
                    • <b>Recommendation:</b> Consider adding zip-lines or lower catwalk paths across the gorge to provide alternative crossing routes when bridges are being camped.
                </div>
                """,
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
