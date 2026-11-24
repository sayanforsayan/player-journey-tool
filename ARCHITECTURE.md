# System Architecture & Technical Design Document
**Project:** Player Journey Visualization Tool  
**Target User:** Level Designers & Gameplay Engineers  
**Author:** Game Systems Developer  

---

## 1. High-Level System Architecture

The Player Journey Visualization Tool is designed to give Level Designers an intuitive, responsive, and visual way to inspect telemetry data from gameplay sessions without requiring database queries or complex data tools.

```
┌────────────────────────────────┐
│   Raw Telemetry Data           │
│   1,243 Parquet files (~8 MB)  │
│   5 days (Feb 10 - Feb 14)     │
└───────────────┬────────────────┘
                │ One-time offline "Bake"
                ▼
┌────────────────────────────────┐
│   scripts/preprocess.py        │
│   - Decodes binary event bytes │
│   - Bot vs Human detection     │
│   - True epoch & elapsed time  │
│   - Vectorized UV/Pixel math   │
└───────────────┬────────────────┘
                │ Generates master parquet (~4 MB)
                ▼
┌────────────────────────────────┐
│ data/processed_events.parquet  │
│ (Committed to Git for hosting) │
└───────────────┬────────────────┘
                │
        ┌───────┴───────┐
        ▼               ▼
┌──────────────┐ ┌──────────────┐
│data_loader.py│ │map_renderer  │
│(@st.cache)   │ │(Plotly/PIL)  │
└───────┬──────┘ └──────┬───────┘
        │               │
        ▼               ▼
┌────────────────────────────────┐
│   app.py (Streamlit Web App)   │
│   - Match Playback Replay      │
│   - Aggregate 2D Heatmaps      │
│   - KPI Summary Strip          │
└────────────────────────────────┘
```

---

## 2. Data Pipeline & Optimization Strategy

### 2.1 The One-Time "Bake" Architecture
- **Problem:** Booting a web app that reads 1,243 individual files on startup causes memory bloat, high disk I/O, and slow response times on cloud hosting.
- **Solution:** A standalone preprocessing script (`scripts/preprocess.py`) bakes all files into a single, compact master Parquet file (`data/processed_events.parquet`, 4.05 MB).
- **Hosting Suitability:** By committing the baked Parquet file directly to GitHub, the deployed app on Streamlit Community Cloud boots in **< 1.5 seconds** and runs comfortably within free-tier resource limits.

### 2.2 Minimap Image Downscaling (Web Optimization)
- Raw minimap images in `minimaps/` were up to **9000x9000 pixels (11.8 MB)**. Transferring these uncompressed over web sockets for every filter change degrades browser framerate.
- The repository maintains web-optimized $1024 \times 1024$ minimap images in `minimaps/`, reducing payload size by **~90%** (down to 124 KB–750 KB) while preserving 1:1 pixel parity with the coordinate math.

---

## 3. Coordinate System & Mathematical Derivations

In-game world coordinates $(x, y, z)$ are mapped to a $1024 \times 1024$ 2D minimap canvas:

| Map | Scale | Origin X | Origin Z | Minimap File |
| :--- | :--- | :--- | :--- | :--- |
| **AmbroseValley** | $900$ | $-370$ | $-473$ | `AmbroseValley_Minimap.png` |
| **GrandRift** | $581$ | $-290$ | $-290$ | `GrandRift_Minimap.png` |
| **Lockdown** | $1000$ | $-500$ | $-500$ | `Lockdown_Minimap.jpg` |

### 3.1 Normalization & Projection Math
1. **World Coordinates to UV space ($[0, 1]$ interval):**
   $$u = \frac{x - \text{origin}_x}{\text{scale}}, \quad v = \frac{z - \text{origin}_z}{\text{scale}}$$
2. **UV Space to Pixel Coordinates ($1024 \times 1024$ Image):**
   $$\text{pixel}_x = u \times 1024$$
   $$\text{pixel}_y = (1 - v) \times 1024$$
3. **Elevation ($y$):** In the 3D game engine, $y$ represents vertical elevation/height (e.g. altitude from $20\text{m}$ to $165\text{m}$). It is displayed in hover tooltips and metric cards for elevation advantage analysis, but excluded from 2D plane projection.

---

## 4. Key Data Traps & Engineering Edge Cases Handled

### 4.1 The Timestamp / Elapsed Time Nuance
- **The Trap:** The Parquet schema marks `ts` as `timestamp[ms]`. When read directly, PyArrow interprets the raw integers as milliseconds after 1970 (`1970-01-21 11:52...`), making match duration differences appear as fractional milliseconds ($0.7\text{s}$–$0.9\text{s}$).
- **The Discovery & Fix:** The integer values (e.g., `1770760465`) are actually **Unix epoch timestamps in SECONDS** corresponding to Feb 10, 2026 21:54:25 UTC.
- By extracting raw integer seconds, we reconstruct true wall-clock time and derive match-elapsed time:
  $$\text{match\_time\_sec} = \text{ts}_{\text{row}} - \min(\text{ts}_{\text{match}})$$
  This produces real, intuitive match durations ($200\text{s}$–$890\text{s}$, or $\sim 3$ to $15$ minutes), properly aligning timeline playback.

### 4.2 The Plotly Y-Axis Inversion Trap
- Standard Cartesian coordinates place $(0, 0)$ at the bottom-left, whereas 2D image coordinates place $(0, 0)$ at the top-left.
- The formula $\text{pixel}_y = (1 - v) \times 1024$ produces image-space coordinates.
- To prevent inverted map overlays, Plotly's Y-axis range is configured as `range=[1024, 0]`, with `scaleanchor="x"` and `scaleratio=1` to guarantee undistorted 1:1 aspect ratio.

### 4.3 Combat Semantics
- Telemetry events follow strict actor definitions:
  - `Kill`: Human player eliminated another human player.
  - `Killed`: Human player was eliminated by another human player.
  - `BotKill`: Human player eliminated an AI bot.
  - `BotKilled`: Human player was eliminated by an AI bot.
- Distinct color-coded visual markers and tooltips prevent level designers from misinterpreting AI deaths as PvP encounters.

### 4.4 Partial Day Telemetry (Feb 14)
- Feb 14 contains 79 files (partial recording day). The UI surfaces a callout banner when Feb 14 is selected so designers do not mistake reduced sample count for player attrition.

---

## 5. Security & Deployment

- Built strictly on open-source libraries: `streamlit`, `pandas`, `pyarrow`, `plotly`, `pillow`.
- Hosted on Streamlit Community Cloud with automatic GitHub CI synchronization.
- Memory usage is capped below 150 MB at runtime through `@st.cache_data`.
