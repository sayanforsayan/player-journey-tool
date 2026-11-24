# Gameplay & Level Design Insights Report
**Game:** LILA BLACK (Extraction Shooter)  
**Dataset:** 5 Days of Telemetry Data (Feb 10–14, 2026 | 796 Matches | 89,104 Events)  
**Audience:** Level Design Team, Combat Balance Team, and Product Leadership  

---

## Executive Summary

Using the Player Journey Visualization Tool, we analyzed player traversal, combat lethality, loot distribution, and ring-closure casualties across **Ambrose Valley**, **Grand Rift**, and **Lockdown**. 

Below are three critical insights identified from the data, accompanied by concrete recommendations for the Level Design team.

---

## Insight 1: Storm Ring Bottlenecks Cause Severe Player Attrition on Lockdown

### The Data:
- **Total Storm Casualties:** 39 players were eliminated by the storm (`KilledByStorm`) across the 5-day dataset.
- **Map Breakdown:**
  - **Lockdown:** 17 storm deaths across 171 matches (**9.94% of matches** suffered a storm death).
  - **Ambrose Valley:** 17 storm deaths across 566 matches (**3.00% of matches**).
  - **Grand Rift:** 5 storm deaths across 59 matches (**8.47% of matches**).
- **Timing:** Across all maps, storm deaths occur exclusively between $t = 655\text{s}$ and $t = 887\text{s}$ (mean: $t = 750.2\text{s}$, or $\sim 12.5$ minutes into the match).
- **Spatial Clustering:** On Lockdown, storm deaths tightly cluster around the southern interior choke points at pixel coordinates $(510 \pm 45, 620 \pm 50)$.

### Level Design Takeaway:
Lockdown is a high-density, close-quarters combat map. As the storm pushes in late-game ($t > 11$ minutes), interior doorways and dead-end corridors trap extracting players who are either engaged in combat or disoriented by interior geometry.

### Actionable Recommendations:
1. **Add Secondary Flanking / Escape Vents:** Open up at least one additional egress path or vertical drop-down chute in the southern industrial wing to prevent players getting cornered by the storm wall.
2. **Audio/Visual Storm Pacing Cues:** Introduce directional klaxons or dynamic lighting shifts 60 seconds before the final zone collapses to alert players navigating claustrophobic corridors.

---

## Insight 2: Elevation Disparity Drives AI Bot Combat Lethality on Ambrose Valley

### The Data:
- **Combat Volume:**
  - **BotKill** (Player killed Bot): 2,415 events
  - **BotKilled** (Bot killed Player): 700 events
  - Overall Player-to-Bot Kill Ratio: **3.45 : 1**
- **Elevation Advantage Correlation ($y$ axis):**
  - Ambrose Valley terrain spans from $y = 68.2\text{m}$ (river valley floor) to $y = 162.7\text{m}$ (hilltop fortresses), with a mean of $114.5\text{m}$.
  - When players engage bots from high ground ($y > 130\text{m}$), the player-to-bot kill ratio surges to **4.82 : 1**.
  - Conversely, when players are in low-lying trenches ($y < 90\text{m}$), bot lethality spikes dramatically, with players dying to bots at a **1.71 : 1** ratio (nearly $3\times$ higher bot lethality).

### Level Design Takeaway:
Bots patrolling elevated ridgelines have excessive sightline dominance over players navigating the river basin. Players traversing low-elevation valleys have limited natural cover and struggle to retaliate against AI aiming downward.

### Actionable Recommendations:
1. **Natural Valley Cover:** Add rock outcroppings, shipping containers, or foliage clumps along the lowest riverbed paths ($y < 90\text{m}$) to break line-of-sight from elevated vantage points.
2. **Bot Patrol Anchor Restraints:** Lower the AI patrol boundary radius on cliff edges so bots do not fire continuously down into transit corridors.

---

## Insight 3: The North-West Quadrant of Ambrose Valley is an Ignored "Dead Zone"

### The Data:
- **Movement Concentration:**
  - Out of 36,189 `Position` samples on Ambrose Valley, **78.4%** occur along a diagonal south-west to north-east corridor connecting the main landing zones to the primary central extract point.
  - The entire North-West sector ($u < 0.28, v > 0.72$, or pixel $x \in [0, 280], y \in [0, 280]$) accounts for only **3.8%** of total movement events.
- **Loot Distribution Mismatch:**
  - Over 9,955 loot pickups were recorded on Ambrose Valley.
  - However, the North-West POIs hold high-tier loot caches that are scavenged in fewer than **1.5%** of matches because the initial storm vector consistently threatens that side of the map early in the match cycle.

### Level Design Takeaway:
A substantial portion of Ambrose Valley's playable footprint is effectively wasted space. Level designers invested development time into structures and assets in the North-West that the vast majority of players never experience.

### Actionable Recommendations:
1. **Shift Extraction / Infiltration Spawns:** Introduce dedicated infiltration spawn beacons and high-value extraction helipads in the North-West corner.
2. **Dynamic In-Match Event:** Trigger a mid-match objective (e.g. an orbital supply drop or boss encounter) in the North-West to pull players across the map before the storm contracts toward the center.

---

## Summary Matrix for Level Designers

| Metric / Dimension | Ambrose Valley | Grand Rift | Lockdown | Designer Action Item |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Choke Points** | River basin ($y < 90\text{m}$) | Central chasm bridge | South doorway corridors | Add sightline blockers & egress routes |
| **Storm Casualty Rate** | $3.00\%$ of matches | $8.47\%$ of matches | **$9.94\%$ of matches** | Increase late-game storm escape windows |
| **Human vs Bot K/D** | $3.70 : 1$ | $4.17 : 1$ | **$2.54 : 1$** (Bots most lethal) | Tune close-range AI reaction time |
| **Map Utilization** | SW $\rightarrow$ NE corridor bias | Balanced linear flow | High room-to-room variance | Reposition NW high-tier loot & objectives |
