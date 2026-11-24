"""
LILA BLACK — Player Journey Visualization Tool
All controls & functions in the left sidebar.
Main screen displays only the Map Title, Playback Timeline, and the Minimap Canvas.
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

# Responsive Page Configuration
st.set_page_config(
    page_title="LILA BLACK — Level Design Telemetry",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling: Prevents any title cutoff and keeps main screen focused on map
st.markdown(
    """
    <style>
        /* Main page layout */
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1.5rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }
        @media (min-width: 768px) {
            .block-container {
                padding-left: 1.8rem !important;
                padding-right: 1.8rem !important;
            }
        }

        /* Prominent Map Title (Never cut off) */
        .map-header-box {
            padding-top: 0.5rem;
            padding-bottom: 0.6rem;
            margin-bottom: 0.5rem;
            border-bottom: 1px solid #1E293B;
        }
        .map-title {
            font-size: 1.85rem !important;
            font-weight: 700 !important;
            color: #38BDF8 !important;
            margin: 0 0 4px 0 !important;
            line-height: 1.25 !important;
        }
        .map-subtitle {
            font-size: 0.92rem !important;
            color: #94A3B8 !important;
            margin: 0 !important;
            line-height: 1.4 !important;
        }

        /* Timeline badge */
        .timeline-badge {
            display: inline-block;
            background-color: #0F172A;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 4px 12px;
            font-size: 0.88rem;
            color: #E2E8F0;
            margin-bottom: 6px;
        }
        .timeline-badge b {
            color: #38BDF8;
        }

        /* Sidebar Legend Container */
        .sidebar-legend {
            background-color: #0F172A;
            border: 1px solid #1E293B;
            border-radius: 8px;
            padding: 10px 12px;
            margin-top: 14px;
            font-size: 0.8rem;
            color: #CBD5E1;
            line-height: 1.6;
        }
        .sidebar-legend-title {
            font-weight: 700;
            color: #F8FAFC;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 6px;
        }

        /* Sidebar Insights Box */
        .sidebar-insight {
            background-color: #0F172A;
            border-left: 3px solid #38BDF8;
            border-radius: 0 6px 6px 0;
            padding: 10px 12px;
            margin-top: 12px;
            font-size: 0.82rem;
            color: #E2E8F0;
            line-height: 1.45;
        }
        .sidebar-insight b {
            color: #38BDF8;
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
        st.error(f"Could not load telemetry data: {e}")
        st.info("Run 'python scripts/preprocess.py' to generate the dataset.")
        return

    # =========================================================================
    # LEFT SIDEBAR: ALL CONTROLS, FILTERS, METRICS & SETTINGS
    # =========================================================================
    st.sidebar.markdown("## LILA BLACK")
    st.sidebar.markdown(
        "<div style='margin-top: -8px; margin-bottom: 12px; color: #94A3B8; font-size: 0.82rem;'>"
        "Level Design Telemetry Suite</div>",
        unsafe_allow_html=True,
    )

    # 1. Map Selection
    maps = get_available_maps(df)
    map_labels = {
        "AmbroseValley": "Ambrose Valley (Mountain Valley)",
        "GrandRift": "Grand Rift (Canyon and Bridge)",
        "Lockdown": "Lockdown (Indoor CQB Facility)",
    }
    selected_map = st.sidebar.selectbox(
        "Select Map",
        options=maps,
        format_func=lambda m: map_labels.get(m, m),
        index=0,
    )
    map_meta = MAP_CONFIGS.get(selected_map, {})

    # 2. Date Selection
    dates = ["All 5 Days (Feb 10 - Feb 14)"] + get_available_dates(df, selected_map)
    selected_date_label = st.sidebar.selectbox("Filter Date", options=dates, index=0)
    selected_date = None if "All" in selected_date_label else selected_date_label

    if selected_date == "2026-02-14":
        st.sidebar.caption("Notice: Feb 14 is a partial collection day.")

    st.sidebar.markdown("---")

    # 3. View Mode Selection
    view_mode = st.sidebar.radio(
        "Explorer Mode",
        options=["Match Replay", "Map Heatmaps", "Level Design Insights"],
        index=0,
    )

    st.sidebar.markdown("---")

    # State variables initialized for main screen rendering
    current_time_sec = 0.0
    max_duration_sec = 1.0
    show_paths = True
    show_events = True
    show_humans = True
    show_bots = True
    heatmap_choice = "movement"
    opacity = 0.65
    color_choice = "Inferno"
    selected_match_id = None
    match_df = None
    match_info = {}

    # ---------------------------------------------------------
    # SIDEBAR CONTROLS: MATCH REPLAY MODE
    # ---------------------------------------------------------
    if view_mode == "Match Replay":
        st.sidebar.markdown("### Match Controls")
        matches = get_match_catalogue(df, selected_map, selected_date)

        if not matches:
            st.sidebar.warning("No matches found for selected date.")
        else:
            # Match Filter Preset
            match_filter = st.sidebar.selectbox(
                "Filter Match Type",
                options=[
                    "All Matches",
                    "Matches with Storm Deaths",
                    "Matches with PvP Kills",
                    "High Action (Most Kills)",
                    "Longest Matches (> 10 mins)",
                ],
                index=0,
            )

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
                st.sidebar.info("No matches matched this filter. Showing all matches.")
                filtered_matches = matches

            match_options = {m["match_id"]: m["label"] for m in filtered_matches}
            selected_match_id = st.sidebar.selectbox(
                f"Select Match ({len(filtered_matches)} matches)",
                options=list(match_options.keys()),
                format_func=lambda mid: match_options[mid],
                index=0,
            )

            match_df = df[df["clean_match_id"] == selected_match_id]
            match_info = get_match_info(df, selected_match_id)
            max_duration_sec = float(match_info.get("duration_sec", 10.0))
            if max_duration_sec <= 0:
                max_duration_sec = 1.0

            # Match Entity Toggles
            st.sidebar.markdown("### Display Options")
            show_humans = st.sidebar.checkbox("Human Players", value=True)
            show_bots = st.sidebar.checkbox("AI Bots", value=True)
            show_paths = st.sidebar.checkbox("Show Movement Trails", value=True)
            show_events = st.sidebar.checkbox("Show Combat & Loot Icons", value=True)

            # Match Summary Metrics inside sidebar
            st.sidebar.markdown("### Match Summary")
            sm1, sm2 = st.sidebar.columns(2)
            sm1.metric("Duration", match_info.get("duration_str", "00:00"))
            sm2.metric("Total Kills", match_info.get("player_kills", 0) + match_info.get("bot_kills", 0))

            sm3, sm4 = st.sidebar.columns(2)
            sm3.metric("Humans / Bots", f"{match_info.get('human_count', 0)} / {match_info.get('bot_count', 0)}")
            sm4.metric("Storm Deaths", match_info.get("storm_deaths", 0))

            # Chronological Combat Feed expander inside sidebar
            with st.sidebar.expander("Chronological Combat Feed", expanded=False):
                combat_df = match_df[
                    match_df["event"].isin(
                        ["Kill", "Killed", "BotKill", "BotKilled", "KilledByStorm", "Loot"]
                    )
                ].copy()
                if not combat_df.empty:
                    combat_df["Time"] = combat_df["match_time_sec"].apply(format_seconds_to_mmss)
                    combat_df["Event"] = combat_df["event"].apply(
                        lambda e: EVENT_STYLES.get(e, {}).get("name", e)
                    )
                    combat_df["Actor"] = combat_df["user_id"].apply(
                        lambda u: f"Bot #{u}" if str(u).isdigit() else f"Player {str(u)[:6]}"
                    )
                    st.dataframe(
                        combat_df[["Time", "Event", "Actor"]].sort_values(by="Time"),
                        hide_index=True,
                        use_container_width=True,
                    )
                else:
                    st.caption("No combat events recorded in this match.")

    # ---------------------------------------------------------
    # SIDEBAR CONTROLS: MAP HEATMAPS MODE
    # ---------------------------------------------------------
    elif view_mode == "Map Heatmaps":
        st.sidebar.markdown("### Heatmap Perspective")
        heatmap_choice = st.sidebar.radio(
            "Select Heatmap View:",
            options=[
                ("movement", "High-Traffic Movement Paths"),
                ("combat", "Firefights & Kill Hotspots (Choke Points)"),
                ("deaths", "Player Elimination Hotspots"),
                ("storm", "Storm Ring Eliminations (Zone Traps)"),
                ("loot", "Loot Pickup Density"),
            ],
            format_func=lambda opt: opt[1],
            index=0,
        )[0]

        st.sidebar.markdown("### Heatmap Settings")
        opacity = st.sidebar.slider("Overlay Transparency", 0.2, 1.0, 0.65, 0.05)
        color_choice = st.sidebar.selectbox("Color Scheme", ["Inferno", "Hot", "Turbo", "Viridis"], index=0)

        show_humans = st.sidebar.checkbox("Human Players", value=True)
        show_bots = st.sidebar.checkbox("AI Bots", value=True)

        # Aggregate Metrics in sidebar
        agg_mask = df["map_id"] == selected_map
        if selected_date:
            agg_mask = agg_mask & (df["date"] == selected_date)
        filtered_agg_df = df[agg_mask]
        stats = get_aggregate_stats(filtered_agg_df)

        st.sidebar.markdown("### Map Telemetry Summary")
        hm1, hm2 = st.sidebar.columns(2)
        hm1.metric("Matches", f"{stats['total_matches']:,}")
        hm2.metric("Total Kills", f"{stats['pvp_kills'] + stats['bot_kills']:,}")

        hm3, hm4 = st.sidebar.columns(2)
        hm3.metric("Humans / Bots", f"{stats['human_players']:,} / {stats['bot_players']:,}")
        hm4.metric("Storm Deaths", f"{stats['storm_deaths']:,}")

    # ---------------------------------------------------------
    # SIDEBAR CONTROLS: LEVEL DESIGN INSIGHTS MODE
    # ---------------------------------------------------------
    else:
        st.sidebar.markdown("### Level Design Notes")
        st.sidebar.info("Review key spatial observations and balance takeaways for the selected map below.")

    # ---------------------------------------------------------
    # SIDEBAR MAP LEGEND (Always visible on left side)
    # ---------------------------------------------------------
    st.sidebar.markdown(
        """
        <div class='sidebar-legend'>
            <div class='sidebar-legend-title'>Map Legend & Symbols</div>
            <div><span style='color: #38BDF8;'>―</span> Solid Line: Human Player Trail</div>
            <div><span style='color: #94A3B8;'>┄</span> Dotted Line: AI Bot Trail</div>
            <div><span style='color: #E63946;'>+</span> Red Cross: Player vs Player Kill</div>
            <div><span style='color: #8B0000;'>x</span> Dark X: Player vs Player Death</div>
            <div><span style='color: #F77F00;'>▲</span> Orange ▲: Player Eliminated a Bot</div>
            <div><span style='color: #9D4EDD;'>▼</span> Purple ▼: Player Died to a Bot</div>
            <div><span style='color: #00F0FF;'>⬢</span> Cyan ⬢: Eliminated by Storm Zone</div>
            <div><span style='color: #FFD166;'>◆</span> Gold ◆: Loot Pickup</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =========================================================================
    # MAIN SCREEN: ONLY MAP TITLE, PLAYBACK TIMELINE & MAP CANVAS
    # =========================================================================

    # 1. Map Title (Crisp, Never Cut Off)
    st.markdown(
        f"""
        <div class='map-header-box'>
            <div class='map-title'>{map_meta.get('display_name', selected_map)}</div>
            <div class='map-subtitle'>{map_meta.get('tagline', '')} | {map_meta.get('description', '')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Main Screen Content Based on Mode
    if view_mode == "Match Replay":
        if match_df is not None and not match_df.empty:
            # Playback Timeline Slider directly on Main Screen
            current_time_sec = st.slider(
                "Match Playback Timeline (Seconds):",
                min_value=0.0,
                max_value=max_duration_sec,
                value=max_duration_sec,
                step=1.0 if max_duration_sec > 15 else 0.5,
                help="Slide forward and backward to watch player movement and combat unfold.",
            )

            time_badge_str = (
                f"<div class='timeline-badge'>"
                f"Timeline Playback: <b>{format_seconds_to_mmss(current_time_sec)} / {format_seconds_to_mmss(max_duration_sec)}</b> "
                f"({int((current_time_sec / max_duration_sec) * 100)}% of match elapsed)"
                f"</div>"
            )
            st.markdown(time_badge_str, unsafe_allow_html=True)

            # Responsive Map Canvas
            replay_fig = render_match_replay(
                match_df=match_df,
                map_id=selected_map,
                current_time_sec=current_time_sec,
                show_humans=show_humans,
                show_bots=show_bots,
                show_paths=show_paths,
                show_events=show_events,
                selected_events=list(EVENT_STYLES.keys()),
            )

            st.plotly_chart(
                replay_fig,
                use_container_width=True,
                config={"responsive": True, "scrollZoom": True, "displayModeBar": True},
            )
        else:
            st.info("Please select a valid match from the left sidebar to start playback.")

    elif view_mode == "Map Heatmaps":
        agg_mask = df["map_id"] == selected_map
        if selected_date:
            agg_mask = agg_mask & (df["date"] == selected_date)
        filtered_agg_df = df[agg_mask]

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
            config={"responsive": True, "scrollZoom": True, "displayModeBar": True},
        )

    else:
        # Level Design Insights Mode on Main Screen
        st.markdown("### Actionable Level Design Takeaways")
        if selected_map == "AmbroseValley":
            st.markdown(
                """
                <div class='sidebar-insight'>
                    <b>1. Dead Zone in the North-West Quadrant:</b><br>
                    Over <b>78.4%</b> of player traversal is confined to a diagonal Southwest-to-Northeast corridor 
                    connecting the main landing zones to the primary central extraction point. 
                    The entire Northwest quadrant accounts for less than <b>4%</b> of total player movement.<br>
                    <i>Recommendation:</i> Introduce high-value extraction beacons or dedicated infiltration spawns 
                    in the Northwest corner to incentivize peripheral exploration before late-game ring collapse.
                </div>
                <div class='sidebar-insight' style='margin-top: 14px;'>
                    <b>2. Elevation Combat Disparity:</b><br>
                    Ambrose Valley elevation ranges from 68m (river valley) to 163m (hilltop fortresses). 
                    Players engaging AI bots from high ground (elevation &gt; 130m) have a <b>4.8 : 1</b> kill-to-death ratio. 
                    Conversely, players in low-lying riverbeds (elevation &lt; 90m) suffer nearly 3x higher mortality.<br>
                    <i>Recommendation:</i> Add natural rock outcroppings and sightline blockers along the lower riverbed 
                    to break downward lines of sight from elevated ridges.
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif selected_map == "Lockdown":
            st.markdown(
                """
                <div class='sidebar-insight'>
                    <b>1. High Storm Ring Mortality (9.94% of matches):</b><br>
                    Lockdown has the highest storm fatality rate of any map in LILA BLACK. 
                    Storm casualties tightly cluster around interior choke points in the southern industrial wing.<br>
                    <i>Recommendation:</i> Add secondary egress vents or vertical drop chutes in the southern wing 
                    to prevent players getting cornered by the closing storm wall between 11:00 and 14:00.
                </div>
                <div class='sidebar-insight' style='margin-top: 14px;'>
                    <b>2. Close-Quarters AI Lethality:</b><br>
                    Due to tight indoor rooms and doorway bottlenecks, AI bots achieve their highest lethality on Lockdown 
                    (player-to-bot K/D drops to 2.54 : 1, compared to &gt; 4.1 : 1 on open maps).
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class='sidebar-insight'>
                    <b>1. Central Gorge Bridge Choke Points:</b><br>
                    Player traversal and combat on Grand Rift are heavily funneled through the two bridges spanning the central chasm.<br>
                    <i>Recommendation:</i> Add lower catwalks or zip-line crossing points across the gorge to give players 
                    viable flanking alternatives when bridges are camped by snipers.
                </div>
                <div class='sidebar-insight' style='margin-top: 14px;'>
                    <b>2. Fast Lane Rotations:</b><br>
                    Grand Rift has the shortest average match duration of all 3 maps (mean duration 6.2 minutes), 
                    suggesting players encounter one another much faster due to the linear two-lane map layout.
                </div>
                """,
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
