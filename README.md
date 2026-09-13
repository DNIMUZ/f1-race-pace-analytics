# 🏎️ Box-Box Analytics: F1 Race Pace Dashboard

> **Interactive dashboard** for analyzing Formula 1 race pace, tyre degradation, and pit stop strategies using **official FIA timing data**.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31-red?logo=streamlit&logoColor=white)
![FastF1](https://img.shields.io/badge/FastF1-3.3-darkred?logo=formula1&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

---

## 🚀 Live Demo

**[View on Streamlit Cloud](https://f1-race-pace-analytics-2qxyxwwxl798wejx3y3xxt.streamlit.app/)** ← Click to explore live!

*(Opens in your browser — no installation needed)*

---

## 📊 Features

### 📈 Race Pace Analysis
- **Lap Time Evolution:** Track each driver's pace throughout the race
- **Multi-driver Comparison:** Compare pace curves side-by-side
- **Interactive Charts:** Hover for detailed info (lap number, tyre compound, tyre age)

### 🛞 Tyre Degradation
- **Compound Performance:** Visualize SOFT vs MEDIUM vs HARD tyre behavior
- **Tyre Life Analysis:** See how lap time changes with tyre age
- **Driver-Specific Stats:** Best lap, average lap, consistency (std dev)

### ⛽ Pit Stop Strategy
- **Timeline Table:** When did each driver pit? What compounds?
- **Pit Stop Count:** Visual breakdown of pit stops per driver
- **Strategy Insights:** Identify undercuts, overcuts, and recovery strategies

### 📊 Driver Performance Summary
- **Best Lap:** Fastest single lap
- **Consistency:** Standard deviation of lap times
- **Median Lap:** Middle-ground performance
- **Total Laps:** Completed laps in race

---

## 🛠️ Tech Stack

| Component | Tool | Version |
|-----------|------|---------|
| **Language** | Python | 3.12+ |
| **Data Ingestion** | FastF1 | 3.3.7 |
| **Data Processing** | Pandas | 2.2.0 |
| **Visualization** | Plotly | 5.18.0 |
| **Web App** | Streamlit | 1.31.0 |
| **Deployment** | Streamlit Cloud | Free Tier |
| **Version Control** | Git / GitHub | Latest |

---

## 📥 Installation & Setup

### Prerequisites
- Python 3.12 or higher
- `pip` (Python package manager)
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/diniemuzaffar/f1-race-pace-analytics.git
cd f1-race-pace-analytics
```

### 2. Create Virtual Environment

```bash
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Locally

```bash
streamlit run app.py
```

This opens the app in your browser at `http://localhost:8501`

---

## 🎮 How to Use

1. **Select Race:** Choose year and Grand Prix from the sidebar
2. **Pick Drivers:** Select drivers you want to compare (or leave empty for all)
3. **Explore Tabs:**
   - 📊 **Race Pace** — Lap time evolution across the race
   - 🛞 **Tyre Degradation** — How tyres age and lap times increase
   - ⛽ **Pit Stops** — When drivers pitted and tyre strategies
   - 📈 **Driver Stats** — Summary metrics (best lap, consistency, etc.)

---

## 📁 Project Structure

```
f1-race-pace-analytics/
├── app.py                      # Streamlit dashboard (main app)
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
├── README.md                   # This file
│
├── src/
│   ├── __init__.py            # Package initialization
│   └── analytics.py           # Core analytics functions
│                               # (load_race_data, plot_pace_analysis, etc.)
│
├── data/
│   └── cache/                 # FastF1 cached race data (auto-generated)
│
├── notebooks/
│   └── 01_explore_fastf1.ipynb # Data exploration & prototyping
│
└── assets/
    └── (screenshots, diagrams)
```

---

## 💡 Key Functions (src/analytics.py)

### `load_race_data(year, race)`
Loads F1 race session data from FastF1 API
- **Returns:** DataFrame with lap telemetry
- **Example:** `laps = load_race_data(2024, 'Monaco')`

### `plot_pace_analysis(laps, drivers)`
Creates interactive lap time vs lap number chart
- **Use:** Compare pace curves across multiple drivers
- **Returns:** Plotly Figure

### `plot_tyre_degradation(laps, driver)`
Visualizes tyre degradation (lap time vs tyre age)
- **Use:** Understand which compound performs best when
- **Returns:** Plotly Figure with separate traces per compound

### `get_pit_stops(laps)`
Extracts pit stop events from race data
- **Returns:** DataFrame with pit stop details
- **Use:** Strategy analysis, undercut/overcut detection

### `get_driver_stats(laps, driver)`
Calculate performance metrics (best lap, avg, consistency)
- **Returns:** Dictionary with key stats
- **Use:** Quick driver comparison

---

## 📊 Sample Analysis Output

### Race Pace Chart
```
Max Verstappen (VER):  1:45.234 → 1:46.123 → 1:46.891 (consistent, slight degradation)
Charles Leclerc (LEC): 1:45.678 → 1:45.456 → 1:45.789 (strong consistency)
Lewis Hamilton (HAM):  1:46.012 → 1:45.234 → 1:46.567 (high variance, pit stop recovery)
```

### Tyre Degradation
- **SOFT:** Quick pace, high degradation (3-7 lap stint)
- **MEDIUM:** Balanced (10-20 lap stint)
- **HARD:** Slow warm-up, lower degradation (20+ lap stint)

---

## 📊 Power BI Version

The same race data is available as a **Power BI dashboard** backed by a **Supabase Postgres** warehouse.

- **ETL:** [`ingest/ingest_to_supabase.py`](/ingest/ingest_to_supabase.py) pulls the season from the
  FastF1 API, transforms it into a star schema (`races`, `drivers`, `laps`), and upserts into
  Supabase (or falls back to local CSVs with `--csv`).
- **Schema:** [`powerbi/supabase_schema.sql`](/powerbi/supabase_schema.sql)
- **Build guide:** [`powerbi/POWERBI_STEPBYSTEP.md`](/powerbi/POWERBI_STEPBYSTEP.md) — connect Power BI
  Desktop to Supabase via the native PostgreSQL connector, model the star schema, write DAX measures
  and publish with scheduled refresh.

```powershell
python ingest/ingest_to_supabase.py --year 2026          # -> Supabase
python ingest/ingest_to_supabase.py --year 2026 --csv    # -> powerbi/*.csv
```

---

## 🚀 Deployment (Streamlit Cloud)

### Option 1: Deploy Your Own Fork (Recommended)

1. **Fork this repo** on GitHub
2. Go to [Streamlit Cloud](https://share.streamlit.io)
3. Click "New app"
4. Select your forked repo
5. Set **Main file path:** `app.py`
6. Click "Deploy"
7. Your app is live! Share the URL.

### Option 2: Run Locally for Offline Use

```bash
streamlit run app.py --logger.level=debug
```

---

## 📈 Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Startup Time** | ~5-10s | First load caches FastF1 data |
| **Page Load** | ~1-2s | Subsequent loads use cache |
| **Data Points** | 50-300 laps | Depends on race |
| **Responsiveness** | Real-time | Interactive Plotly charts |

---

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'fastf1'"
**Solution:** Ensure virtual environment is activated and dependencies installed
```bash
pip install -r requirements.txt
```

### Issue: "Race not found" error
**Solution:** Check if the race name is correct (e.g., 'Silverstone' not 'Britain')
- See [FastF1 docs](https://theoehrly.github.io/Fast-F1/) for valid race names

### Issue: Very slow data loading
**Solution:** First load downloads data (~5-10 min). Subsequent loads are instant (cached).
- Cache is stored in `data/cache/`

---

## 🤝 Contributing

Contributions welcome! Areas to improve:
- [ ] Sector-by-sector analysis (S1, S2, S3)
- [ ] Weather data integration (rain, wind, temperature)
- [ ] Weather-adjusted pace comparison
- [ ] Head-to-head driver comparison (same fuel load)
- [ ] Fuel consumption analysis
- [ ] DRS detection and impact

### How to Contribute

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m "Add feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📚 Learning Resources

- **FastF1 Docs:** [theoehrly.github.io/Fast-F1/](https://theoehrly.github.io/Fast-F1/)
- **Streamlit Docs:** [docs.streamlit.io](https://docs.streamlit.io)
- **Plotly Docs:** [plotly.com/python](https://plotly.com/python/)
- **F1 Strategy Podcast:** Great for understanding pit stop strategies

---

## 📜 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Muhamad Dinie Bin Muzaffar**

- 🔗 **LinkedIn:** [linkedin.com/in/diniemuzaffar](https://linkedin.com/in/diniemuzaffar)
- 📧 **Email:** diniemuzaffar@gmail.com
- 🐙 **GitHub:** [@diniemuzaffar](https://github.com/diniemuzaffar)

---

## ⭐ Show Your Support

If you found this helpful, please:
- ⭐ **Star this repo** on GitHub
- 🔗 **Share the live link** with friends
- 💬 **Open an issue** if you find bugs
- 🤝 **Contribute** improvements!

---

## 📝 Changelog

### v1.0.0 (2026-08-20)
- ✅ Initial release
- ✅ Lap time evolution chart
- ✅ Tyre degradation analysis
- ✅ Pit stop detection & timeline
- ✅ Driver performance stats
- ✅ Deployed on Streamlit Cloud

---

## 🏁 What's Next?

- Sector-by-sector pace breakdown (S1, S2, S3)
- Qualifying session analysis
- Season-long trend analysis
- Team radio / commentary integration
- Mobile-responsive design improvements

---

<div align="center">

**Built with ❤️ for F1 fans and data enthusiasts**

[⬆ back to top](#-box-box-analytics-f1-race-pace-dashboard)

</div>
