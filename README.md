# LILA BLACK — Player Journey Visualization Tool
> **Product Engineer Written Test Deliverable for LILA Games**  
> A high-performance, web-based telemetry and level design analytics suite built for **LILA BLACK** (an extraction shooter).

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://player-journey-tool-sayanforsayan.streamlit.app)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Live Web Application
- **Live Streamlit App:** [https://player-journey-tool-sayanforsayan.streamlit.app](https://player-journey-tool-sayanforsayan.streamlit.app)
- **GitHub Repository:** [https://github.com/sayanforsayan/player-journey-tool](https://github.com/sayanforsayan/player-journey-tool)

---

## Deliverable Documents
1. **[ARCHITECTURE.md](ARCHITECTURE.md)**: 1-page system design document detailing data pipeline baking, coordinate projection math, and data nuances.
2. **[INSIGHTS.md](INSIGHTS.md)**: 3 actionable gameplay insights for Level Designers backed by empirical telemetry stats (Storm choke points, AI bot elevation combat, and map dead zones).

---

## Key Features

### 1. Match Journey Replay
- **Timeline Playback Scrubber:** Scrub match time from 00:00 to match end (up to ~15 mins) to observe player paths unfold in chronological order.
- **Human vs. AI Differentiation:** Human players render with solid, distinct color-coded lines; AI bots render with dashed paths.
- **Discrete Event Markers:** Real-time visual markers for PvP Kills, PvP Deaths, Bot Kills, Bot Deaths, Storm Eliminations, and Loot Pickups.
- **Combat Log:** Chronological, filterable match feed showing all combat and loot events with elevation context.

### 2. Aggregate Heatmaps
- **Multi-Match Density Overlays:** Aggregate across 5 days (Feb 10–14, 2026) and 796 matches.
- **5 Focused Heatmap Modes:**
  1. *High-Traffic Movement Paths* (Player and bot route volume)
  2. *Combat and Kill Hotspots* (Where firefights happen)
  3. *Elimination Hotspots* (Where players die)
  4. *Storm Ring Deaths* (Zone bottlenecks and failed extractions)
  5. *Loot Distribution* (Resource collection density)
- **Visual Controls:** Adjustable overlay transparency, custom color palettes, and incident pins.

### 3. Level Design Insights Tab
- Actionable map-specific observations and recommendations tailored for Level Designers.

---

## 📐 Map Configuration & Coordinate Conversion

All 3 in-game maps are mapped onto $1024 \times 1024$ pixel minimap images:

| Map | Scale | Origin X | Origin Z | Minimap Image |
| :--- | :--- | :--- | :--- | :--- |
| **Ambrose Valley** | 900 | -370 | -473 | `AmbroseValley_Minimap.png` |
| **Grand Rift** | 581 | -290 | -290 | `GrandRift_Minimap.png` |
| **Lockdown** | 1000 | -500 | -500 | `Lockdown_Minimap.jpg` |

### Coordinate Math:
$$u = \frac{x - \text{origin}_x}{\text{scale}}, \quad v = \frac{z - \text{origin}_z}{\text{scale}}$$
$$\text{pixel}_x = u \times 1024, \quad \text{pixel}_y = (1 - v) \times 1024$$

*Note: World $y$ represents 3D elevation (height), which is rendered in hover tooltips for altitude combat analysis.*

---

## 🛠️ Project Structure

```
player-journey-tool/
├── .gitignore                      # Ignores .venv, raw player_data, caches
├── requirements.txt                # Streamlit deployment dependencies
├── app.py                          # Main Streamlit dashboard application
├── scripts/
│   └── preprocess.py               # One-time baking script (1,243 files -> 1 Parquet)
├── src/
│   ├── data_loader.py              # Cached data loading and filtering logic
│   └── map_renderer.py             # Plotly 1:1 aspect minimap & heatmap engine
├── data/
│   └── processed_events.parquet    # Baked master telemetry dataset (4.05 MB)
├── minimaps/                       # 1024x1024 minimap images
│   ├── AmbroseValley_Minimap.png
│   ├── GrandRift_Minimap.png
│   └── Lockdown_Minimap.jpg
├── ARCHITECTURE.md                 # System design & coordinate projection doc
├── INSIGHTS.md                     # 3 telemetry-backed level design insights
└── README.md                       # Documentation & setup guide
```

---

## 🚀 Local Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/sayanforsayan/player-journey-tool.git
cd player-journey-tool
```

### 2. Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. (Optional) Run Preprocessing
The repository already includes the pre-baked `data/processed_events.parquet`. If you wish to re-bake from raw data:
```bash
python scripts/preprocess.py --input-dir /path/to/player_data
```

### 5. Launch the Web Application
```bash
streamlit run app.py
```
Open your browser to `http://localhost:8501`.

---

## ☁️ Deployment Instructions (Streamlit Community Cloud)

1. Push all committed changes to GitHub:
   ```bash
   git push origin main
   ```
2. Navigate to [share.streamlit.io](https://share.streamlit.io).
3. Click **"New app"**, select `sayanforsayan/player-journey-tool`, branch `main`, and main file path `app.py`.
4. Click **Deploy**. The app will be live within 2 minutes!

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
