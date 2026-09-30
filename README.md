# 🌿 EcoTrack — AI-Assisted Carbon Footprint Monitor

> **Environmental Science for Engineers (ESE) — Software Project**
> Estimate, monitor, and reduce your carbon footprint with AI-powered insights.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render-46e891?style=for-the-badge&logo=render)](https://eco-track-6tck.onrender.com)
[![GitHub](https://img.shields.io/badge/GitHub-AkhileshYadav117-181717?style=for-the-badge&logo=github)](https://github.com/AkhileshYadav117/ECO-TRACK)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com)

---

## 📌 Project Overview

**EcoTrack** is a full-stack web application that enables individuals and industries to estimate, track, and analyse their carbon footprint. It uses documented emission factors to calculate CO₂e (carbon dioxide equivalent) emissions from daily or monthly activities — including transportation, electricity consumption, LPG usage, and waste generation.

The application features an AI-powered prediction engine (Scikit-learn Linear Regression) that forecasts next month's estimated footprint based on historical data, and a what-if simulator that models the impact of lifestyle or operational changes.

> ⚠️ All results are **estimates** based on published emission factors. They are not direct physical measurements of emissions.

---

## 🌐 Live Demo

```
https://eco-track-6tck.onrender.com
```

> **Note:** The application is hosted on Render's free tier. The first request may take up to 60 seconds to wake the service. SQLite data may reset on restart — this is expected for a free-tier demo deployment.

---

## ✨ Features

### 🧮 Dual-Mode Carbon Calculator

| Mode | Input Type | Frequency | Best For |
|---|---|---|---|
| 🏠 Individual / Household | Monthly totals | One record per month | Personal & home use |
| 🏭 Industry / Factory | Daily totals | One record per day | Industrial operations |

- Industry daily records are automatically **aggregated into monthly totals** for dashboard, comparison, and ML prediction.
- Both modes share the same calculation engine and emission factors.

### 📊 Dashboard
- Monthly footprint trend (line chart)
- Category breakdown (donut chart — transport, electricity, fuel, waste)
- Industry daily trend (bar chart — current month)
- Month-over-month comparison (absolute + percentage change)
- Daily average and days recorded (Industry mode)
- ML-powered next-month prediction

### 💡 Personalized Recommendations
- Category-specific reduction tips based on the dominant emission source
- Tailored for both individual and industrial contexts

### 🎯 Monthly Goal Tracking
- Set a monthly CO₂e reduction target
- Visual progress bar comparing actual vs target
- Status message (on track / over target)

### 🔬 What-If Carbon Simulator
- Simulate how activity changes would reduce your footprint
- Compares simulated scenario against current monthly baseline
- Industry mode: projects daily simulation to monthly scale (×30)

### 🤖 ML Prediction (Scikit-learn)
- Linear Regression on historical monthly totals
- Minimum 3 months of data required for reliable prediction
- Reports model MAE (Mean Absolute Error) for transparency
- Industry mode: aggregates daily records into monthly totals before ML

### 📋 History & Anomaly Detection
- Full record history with mode toggle (Individual / Industry)
- Anomaly flag: records deviating >75% from rolling 5-record average
- Data Quality indicator (High / Medium / Low) per record

### ⬇️ CSV Export
- Raw records CSV (daily for Industry, monthly for Individual)
- Monthly aggregated summary CSV (for both modes)

### 🌱 Eco Score (0–100)
- Deterministic score computed from real tracking data — no manual input needed
- Circular SVG gauge with animated fill displayed on the Dashboard
- Scoring formula:
  - **40 pts** base — for having any footprint data
  - **Up to 20 pts** consistency bonus — based on months of tracking history
  - **Up to 40 pts** improvement bonus — based on % reduction vs previous month
- Score label changes with progress: *Getting Started → Building Habits → Good Progress → Eco Champion*
- Updates automatically when new calculations are submitted

### 🏆 Achievement Badges
- 5 badges that unlock automatically based on real tracking history

| Badge | Unlock Condition |
|---|---|
| 🥇 Eco Starter | Complete your first footprint calculation |
| 🌱 Green Progress | Reduce footprint vs previous month |
| 📉 10% Reducer | Achieve ≥10% month-over-month reduction |
| 📅 3-Month Tracker | Track for 3 or more months |
| 🏆 Carbon Champion | Achieve an Eco Score of 80 or higher |

- Locked badges are visually dimmed; unlocked badges glow green
- Displayed alongside Eco Score on the Dashboard

### 🔍 Emission Factor Explorer
- Dedicated page (`/emission-factors`) explaining the carbon calculation methodology
- Accordion-style expandable cards for each emission category
- Shows the **exact same factors used by the calculator** — single source of truth from `utils/calculator.py`
- Displays: factor value, unit, reference source, calculation formula, and a worked example
- Transport section includes a full table of all 9 vehicle modes
- Methodology statement explaining that results are estimates, not measurements

### 📱 Mobile Responsive
- Hamburger navigation menu on phones and tablets
- Responsive form layout and stat grids

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend                      │
│   HTML5  •  CSS3  •  JavaScript  •  Chart.js   │
└──────────────────────┬──────────────────────────┘
                       │ HTTP (REST API)
┌──────────────────────▼──────────────────────────┐
│               Flask Backend (Python)            │
│                                                 │
│  ┌──────────────┐  ┌────────────────────────┐   │
│  │  Calculator  │  │  Validation Engine     │   │
│  │  Engine      │  │  (Individual/Industry) │   │
│  └──────────────┘  └────────────────────────┘   │
│                                                 │
│  ┌──────────────┐  ┌────────────────────────┐   │
│  │  Recommender │  │  What-If Simulator     │   │
│  └──────────────┘  └────────────────────────┘   │
│                                                 │
│  ┌──────────────────────────────────────────┐   │
│  │  ML Predictor (Scikit-learn LR)          │   │
│  └──────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              SQLite Database                    │
│                                                 │
│  footprint_records  │  goals  │  users          │
│  ─────────────────────────────────────────      │
│  Individual: user_type='individual'             │
│              frequency='monthly'                │
│              date = first day of month          │
│                                                 │
│  Industry:   user_type='industry'               │
│              frequency='daily'                  │
│              date = actual activity date        │
│                                                 │
│  Monthly aggregation: SQL SUM GROUP BY month    │
└─────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
ECOTRACK/
│
├── app.py                      # Flask application — all API routes
│
├── database/
│   └── init_db.py              # SQLite schema + migrations + seeding
│
├── utils/
│   ├── calculator.py           # CO₂e calculation engine (emission factors)
│   ├── validation.py           # Input validation (Individual + Industry)
│   ├── simulator.py            # What-if scenario engine
│   ├── recommendations.py      # Category-based recommendation generator
│   └── data_quality.py         # Data quality scoring (High/Medium/Low)
│
├── ml/
│   └── predictor.py            # Scikit-learn Linear Regression predictor
│
├── templates/
│   ├── index.html              # Homepage
│   ├── calculator.html         # Dual-mode calculator
│   ├── dashboard.html          # Dashboard + charts + Eco Score + Badges
│   ├── history.html            # History + export
│   └── factors.html            # Emission Factor Explorer
│
├── static/
│   ├── css/style.css           # Global design system (dark mode, glassmorphism)
│   └── js/
│       ├── main.js             # Global utilities + hamburger menu
│       ├── calculator.js       # Calculator form + result display
│       ├── dashboard.js        # Dashboard data loading + charts
│       ├── reports.js          # History table + CSV export
│       └── simulator.js        # What-if simulator
│
├── data/
│   └── emission_factors.csv    # Documented emission factors reference
│
├── requirements.txt            # Python dependencies
├── render.yaml                 # Render deployment configuration
└── .gitignore
```

---

## 🔬 Emission Factors

All calculations use peer-reviewed, documented emission factors:

| Category | Factor | Unit | Source |
|---|---|---|---|
| Petrol Car | 0.210 | kg CO₂e / km | DEFRA 2023 |
| Diesel Car / Truck | 0.170 | kg CO₂e / km | DEFRA 2023 |
| Motorcycle | 0.110 | kg CO₂e / km | DEFRA 2023 |
| Bus | 0.089 | kg CO₂e / km | IPCC AR6 |
| Auto Rickshaw | 0.075 | kg CO₂e / km | MoEFCC India |
| Metro / Rail | 0.031 | kg CO₂e / km | CEA India |
| Electric Vehicle | 0.050 | kg CO₂e / km | CEA India 2023 |
| Bicycle / Walking | 0.000 | — | — |
| Electricity (India Grid) | 0.716 | kg CO₂e / kWh | CEA India 2023 |
| LPG Cylinder (14.2 kg) | 14.200 | kg CO₂e / cylinder | IPCC AR6 |
| Mixed Waste | 0.450 | kg CO₂e / kg | DEFRA 2023 |

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Charts** | Chart.js 4.4 |
| **Fonts** | Google Fonts — Inter |
| **Backend** | Python 3.11, Flask 3.1 |
| **Database** | SQLite 3 |
| **ML** | Scikit-learn, NumPy, Pandas |
| **Production Server** | Gunicorn |
| **Deployment** | Render (cloud) |
| **Version Control** | Git, GitHub |

---

## 🚀 Running Locally

### Prerequisites
- Python 3.10+ installed
- Git installed

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/AkhileshYadav117/ECO-TRACK.git
cd ECO-TRACK

# 2. Create a virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the application
python app.py
```

### Access
Open your browser at:
```
http://127.0.0.1:5000
```

The database is created automatically on first run at `database/ecotrack.db`.

---

## ☁️ Deployment (Render)

EcoTrack is deployed on Render as a Python Web Service.

| Setting | Value |
|---|---|
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |
| **Environment Variable** | `FLASK_ENV=production` |

The `render.yaml` in the repository root contains the complete deployment configuration.

> **SQLite on Render Free Tier:** Data may reset when the service spins down due to inactivity. This is acceptable for demonstration purposes. For persistent production storage, migrate to PostgreSQL.

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/calculate` | Submit activity data, calculate CO₂e, save record |
| `GET` | `/api/history?user_type=` | Fetch all records for given user type |
| `GET` | `/api/monthly-summary?user_type=` | Monthly aggregated totals |
| `GET` | `/api/daily-summary` | Daily records for current month (Industry) |
| `GET` | `/api/recommendations?user_type=` | Category-specific recommendations |
| `GET` | `/api/predict?user_type=` | ML prediction for next month |
| `POST` | `/api/simulate?user_type=` | What-if scenario simulation |
| `GET` | `/api/goals?user_type=` | Fetch current month's goal |
| `POST` | `/api/goals?user_type=` | Set a new monthly goal |
| `GET` | `/api/report?user_type=` | Export raw records as CSV |
| `GET` | `/api/report/monthly?user_type=` | Export monthly summary as CSV |

All API endpoints accept `?user_type=individual` or `?user_type=industry`.

### Page Routes

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Homepage |
| `GET` | `/calculator` | Carbon calculator |
| `GET` | `/dashboard` | Dashboard with Eco Score + Badges |
| `GET` | `/history` | History and CSV export |
| `GET` | `/emission-factors` | Emission Factor Explorer |

---

## ⚠️ Disclaimer

> All carbon footprint values produced by EcoTrack are **estimates** calculated using published emission factors from DEFRA, IPCC AR6, CEA India, and MoEFCC.
>
> These values are **not** direct physical measurements of greenhouse gas emissions.
>
> Results are intended for educational awareness and approximate personal or industrial carbon accounting only.
>
> EcoTrack should not be used as the sole basis for regulatory reporting or commercial carbon offsetting.

---

## 📚 References

- DEFRA (2023). *UK Government Greenhouse Gas Conversion Factors for Company Reporting.*
- IPCC (2022). *Sixth Assessment Report (AR6).*
- Central Electricity Authority (2023). *CO₂ Baseline Database for the Indian Power Sector.*
- Ministry of Environment, Forest and Climate Change, India. *Emission Factor Database.*

---

