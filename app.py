"""
EcoTrack — Flask Application
AI-Assisted Personal Carbon Footprint Monitoring and Prediction Platform

Supports two calculation modes:
  Individual / Household  -- monthly activity inputs, direct monthly CO2e
  Industry   / Factory    -- daily activity inputs, aggregated to monthly CO2e

Both modes feed into a common monthly data layer for:
  dashboard, comparison, recommendations, goals, simulator, ML prediction, CSV.

All CO2e values are ESTIMATES based on documented emission factors.
They are not direct physical measurements.
"""

import io
import csv
import sys
import os
import numpy as np

from datetime import datetime
from flask import Flask, request, jsonify, render_template, Response

sys.path.insert(0, os.path.dirname(__file__))

from database.init_db      import init_db, get_connection
from utils.calculator      import (calculate, calculate_daily_total,
                                   TRANSPORT_FACTORS, ELECTRICITY_FACTOR,
                                   LPG_FACTOR, WASTE_FACTOR)

from utils.validation      import validate_calculator_input
from utils.data_quality    import assess_data_quality
from utils.recommendations import get_recommendations
from utils.simulator       import run_simulation
from ml.predictor          import predict_next_month

# ============================================================
app = Flask(__name__)
# ============================================================

DEFAULT_USER_ID    = 1
ANOMALY_THRESHOLD  = 0.75   # 75% deviation from rolling average

with app.app_context():
    init_db()


# ============================================================
# PAGE ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculator')
def calculator():
    return render_template('calculator.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/emission-factors')
def emission_factors_page():
    """Emission Factor Explorer — displays the factors used by the calculator."""
    transport_data = [
        {"mode": "Petrol Car",        "factor": TRANSPORT_FACTORS["petrol_car"],    "source": "DEFRA 2023"},
        {"mode": "Diesel Car / Truck","factor": TRANSPORT_FACTORS["diesel_car"],    "source": "DEFRA 2023"},
        {"mode": "Motorcycle",        "factor": TRANSPORT_FACTORS["motorcycle"],    "source": "DEFRA 2023"},
        {"mode": "Bus",               "factor": TRANSPORT_FACTORS["bus"],           "source": "IPCC AR6"},
        {"mode": "Auto Rickshaw",     "factor": TRANSPORT_FACTORS["auto_rickshaw"], "source": "MoEFCC India"},
        {"mode": "Metro / Rail",      "factor": TRANSPORT_FACTORS["metro_rail"],    "source": "CEA India"},
        {"mode": "Electric Car",      "factor": TRANSPORT_FACTORS["electric_car"],  "source": "CEA India 2023"},
        {"mode": "Bicycle",           "factor": TRANSPORT_FACTORS["bicycle"],       "source": "Zero emission"},
        {"mode": "Walking",           "factor": TRANSPORT_FACTORS["walking"],       "source": "Zero emission"},
    ]
    return render_template('factors.html',
        transport_factors   = transport_data,
        electricity_factor  = ELECTRICITY_FACTOR,
        lpg_factor          = LPG_FACTOR,
        waste_factor        = WASTE_FACTOR
    )


@app.route('/history')
def history():
    return render_template('history.html')


# ============================================================
# HELPERS — MONTHLY AGGREGATION
# ============================================================

def _get_monthly_summaries(user_id, user_type):
    """
    Return monthly CO2e totals for the given user_type.

    Individual:
        Records are already monthly — return them directly.

    Industry:
        Aggregate daily records into monthly totals via SQL SUM.

    Both return the same shape:
        [{ month, transport, electricity, fuel, waste, total, day_count }, ...]
    """
    conn = get_connection()

    if user_type == "individual":
        # Individual records ARE monthly — one record per month per user
        rows = conn.execute(
            """
            SELECT
                month,
                transport,
                electricity,
                fuel,
                waste,
                total,
                1 AS day_count
            FROM footprint_records
            WHERE user_id = ? AND user_type = 'individual'
            ORDER BY month ASC
            """,
            (user_id,)
        ).fetchall()
    else:
        # Industry — aggregate daily records into monthly totals
        rows = conn.execute(
            """
            SELECT
                month,
                SUM(transport)   AS transport,
                SUM(electricity) AS electricity,
                SUM(fuel)        AS fuel,
                SUM(waste)       AS waste,
                SUM(total)       AS total,
                COUNT(*)         AS day_count
            FROM footprint_records
            WHERE user_id = ? AND user_type = 'industry'
            GROUP BY month
            ORDER BY month ASC
            """,
            (user_id,)
        ).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def _get_current_month_total(user_id, user_type):
    """
    Return the aggregated total for the current calendar month.
    Individual: direct record lookup.
    Industry:   SUM of daily records for this month.
    """
    current_month = datetime.now().strftime("%Y-%m")
    conn = get_connection()

    if user_type == "individual":
        row = conn.execute(
            """
            SELECT transport, electricity, fuel, waste, total, 1 AS day_count
            FROM footprint_records
            WHERE user_id = ? AND user_type = 'individual' AND month = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (user_id, current_month)
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT
                SUM(transport)   AS transport,
                SUM(electricity) AS electricity,
                SUM(fuel)        AS fuel,
                SUM(waste)       AS waste,
                SUM(total)       AS total,
                COUNT(*)         AS day_count
            FROM footprint_records
            WHERE user_id = ? AND user_type = 'industry' AND month = ?
            """,
            (user_id, current_month)
        ).fetchone()

    conn.close()

    if row and row["total"] is not None:
        return dict(row)
    return {"transport": 0, "electricity": 0, "fuel": 0,
            "waste": 0, "total": 0, "day_count": 0}


def _flag_anomalies(records, window=5):
    """
    Flag records whose total deviates more than ANOMALY_THRESHOLD
    from a rolling window average. Modifies list in-place.
    """
    for i, rec in enumerate(records):
        rec["is_anomaly"] = False
        if i >= window:
            recent_vals = [records[j]["total"] for j in range(i - window, i)]
            avg = float(np.mean(recent_vals))
            if avg > 0:
                deviation = abs(rec["total"] - avg) / avg
                if deviation > ANOMALY_THRESHOLD:
                    rec["is_anomaly"] = True


# ============================================================
# API — CALCULATE
# ============================================================

@app.route('/api/calculate', methods=['POST'])
def api_calculate():
    """
    Accept activity data, calculate CO2e, detect anomaly, save record.

    Individual:
        user_type = 'individual'
        month     = YYYY-MM   (from request)
        date      = first day of that month  (derived automatically)
        Values represent MONTHLY totals.

    Industry:
        user_type = 'industry'
        date      = YYYY-MM-DD  (from request)
        month     = YYYY-MM     (derived automatically)
        Values represent DAILY totals.

    One record per (user_id, user_type, date) — duplicate date updates existing.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received."}), 400

    # Validate inputs (routes to individual or industry validator)
    is_valid, errors = validate_calculator_input(data)
    if not is_valid:
        return jsonify({"error": " | ".join(errors)}), 400

    user_type = data["user_type"]

    # Determine date and month
    if user_type == "individual":
        month = data["month"]                          # e.g. "2026-09"
        date  = month + "-01"                          # e.g. "2026-09-01"
    else:
        date  = data["date"]                           # e.g. "2026-09-29"
        month = date[:7]                               # e.g. "2026-09"

    frequency = "monthly" if user_type == "individual" else "daily"

    # Calculate CO2e using the unified dispatcher
    result = calculate(
        user_type       = user_type,
        transport_mode  = data["transport_mode"],
        distance_km     = float(data.get("distance_km",     0)),
        electricity_kwh = float(data.get("electricity_kwh", 0)),
        lpg_cylinders   = float(data.get("lpg_cylinders",   0)),
        waste_kg        = float(data.get("waste_kg",        0))
    )

    # Data quality assessment
    quality = assess_data_quality(data)

    # Anomaly detection — compare against recent 5 records of same user_type
    is_anomaly      = False
    anomaly_message = ""
    conn = get_connection()
    recent = conn.execute(
        """SELECT total FROM footprint_records
           WHERE user_id = ? AND user_type = ?
           ORDER BY date DESC LIMIT 5""",
        (DEFAULT_USER_ID, user_type)
    ).fetchall()
    conn.close()

    if recent:
        recent_totals = [r["total"] for r in recent]
        avg = float(np.mean(recent_totals))
        if avg > 0:
            deviation = abs(result["total"] - avg) / avg
            if deviation > ANOMALY_THRESHOLD:
                is_anomaly = True
                if user_type == "individual":
                    anomaly_message = (
                        "This month's footprint is unusually different from "
                        "your recent monthly records. Please verify the input."
                    )
                else:
                    anomaly_message = (
                        "This day's footprint is unusually high or low "
                        "compared with your recent daily records. Please verify the input."
                    )

    # Save to database — UPSERT (one record per user_type per date)
    conn = get_connection()
    conn.execute(
        """INSERT INTO footprint_records
               (user_id, user_type, frequency, date, month,
                transport, electricity, fuel, waste, total,
                data_quality, quality_notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_id, user_type, date)
           DO UPDATE SET
               frequency     = excluded.frequency,
               month         = excluded.month,
               transport     = excluded.transport,
               electricity   = excluded.electricity,
               fuel          = excluded.fuel,
               waste         = excluded.waste,
               total         = excluded.total,
               data_quality  = excluded.data_quality,
               quality_notes = excluded.quality_notes,
               created_at    = datetime('now')
        """,
        (
            DEFAULT_USER_ID, user_type, frequency, date, month,
            result["transport"], result["electricity"],
            result["fuel"], result["waste"], result["total"],
            quality["rating"], " | ".join(quality["notes"])
        )
    )
    conn.commit()
    conn.close()

    return jsonify({
        "user_type":     user_type,
        "frequency":     frequency,
        "date":          date,
        "month":         month,
        "transport":     result["transport"],
        "electricity":   result["electricity"],
        "fuel":          result["fuel"],
        "waste":         result["waste"],
        "total":         result["total"],
        "data_quality":  quality["rating"],
        "quality_notes": quality["notes"],
        "is_anomaly":    is_anomaly,
        "anomaly_message": anomaly_message,
    }), 201


# ============================================================
# API — HISTORY
# ============================================================

@app.route('/api/history', methods=['GET'])
def api_history():
    """
    Return footprint records filtered by user_type.
    Query param: ?user_type=individual | industry (default: industry)

    Individual: sorted by month
    Industry:   sorted by date
    """
    user_type  = request.args.get("user_type", "industry")
    order_col  = "month" if user_type == "individual" else "date"

    conn = get_connection()
    rows = conn.execute(
        f"""SELECT id, user_id, user_type, frequency, date, month,
                  transport, electricity, fuel, waste, total,
                  data_quality, quality_notes, created_at
           FROM footprint_records
           WHERE user_id = ? AND user_type = ?
           ORDER BY {order_col} ASC""",
        (DEFAULT_USER_ID, user_type)
    ).fetchall()
    conn.close()

    records = [dict(r) for r in rows]
    _flag_anomalies(records)

    return jsonify({"records": records, "user_type": user_type})


# ============================================================
# API — MONTHLY SUMMARY
# ============================================================

@app.route('/api/monthly-summary', methods=['GET'])
def api_monthly_summary():
    """
    Return monthly CO2e summaries for the given user_type.
    Query param: ?user_type=individual | industry (default: industry)

    Individual: each record IS the monthly total
    Industry:   SQL SUM aggregation of daily records per month

    Both return the same shape:
        { summaries, current, previous, change }
    """
    user_type = request.args.get("user_type", "industry")
    summaries = _get_monthly_summaries(DEFAULT_USER_ID, user_type)

    current_month  = datetime.now().strftime("%Y-%m")
    current_data   = next((s for s in summaries if s["month"] == current_month), None)
    prev_months    = [s for s in summaries if s["month"] < current_month]
    previous_data  = prev_months[-1] if prev_months else None

    change = {}
    if current_data and previous_data and previous_data["total"] > 0:
        abs_change = round(current_data["total"] - previous_data["total"], 2)
        pct_change = round((abs_change / previous_data["total"]) * 100, 2)
        change = {
            "absolute":  abs_change,
            "percent":   pct_change,
            "direction": "down" if abs_change <= 0 else "up"
        }

    # Daily average for Industry
    if current_data and current_data.get("day_count", 0) > 0:
        current_data["daily_avg"] = round(
            current_data["total"] / current_data["day_count"], 2
        )
    if previous_data and previous_data.get("day_count", 0) > 0:
        previous_data["daily_avg"] = round(
            previous_data["total"] / previous_data["day_count"], 2
        )

    return jsonify({
        "user_type": user_type,
        "summaries": summaries,
        "current":   current_data,
        "previous":  previous_data,
        "change":    change
    })


# ============================================================
# API — RECOMMENDATIONS
# ============================================================

@app.route('/api/recommendations', methods=['GET'])
def api_recommendations():
    """
    Return recommendations based on current month's aggregated category totals.
    Query param: ?user_type=individual | industry (default: industry)
    """
    user_type = request.args.get("user_type", "industry")
    monthly   = _get_current_month_total(DEFAULT_USER_ID, user_type)

    if monthly["total"] == 0:
        return jsonify({
            "dominant_category": None,
            "recommendations": [
                "Add your first footprint entry to receive personalized recommendations."
            ]
        })

    result = get_recommendations(monthly)
    return jsonify(result)


# ============================================================
# API — PREDICT (ML)
# ============================================================

@app.route('/api/predict', methods=['GET'])
def api_predict():
    """
    Predict next month's carbon footprint using Scikit-learn.
    Query param: ?user_type=individual | industry (default: industry)

    Pipeline:
        Individual: monthly records     --> ML
        Industry:   daily records
                    --> monthly aggregation
                    --> ML
    """
    user_type = request.args.get("user_type", "industry")
    summaries = _get_monthly_summaries(DEFAULT_USER_ID, user_type)
    result    = predict_next_month(summaries)
    return jsonify({**result, "user_type": user_type})


# ============================================================
# API — SIMULATE
# ============================================================

@app.route('/api/simulate', methods=['POST'])
def api_simulate():
    """
    What-if simulation on monthly baseline.
    Query param: ?user_type=individual | industry (default: industry)

    Individual: monthly record is the baseline.
    Industry:   daily average x 30 is the projected monthly baseline.
    """
    user_type = request.args.get("user_type", "industry")
    data      = request.get_json()
    if not data:
        return jsonify({"error": "No simulation data received."}), 400

    monthly = _get_current_month_total(DEFAULT_USER_ID, user_type)

    if user_type == "individual":
        baseline = monthly  # already monthly values
    else:
        # Convert daily average to a monthly-scale baseline for fair comparison
        days = monthly.get("day_count", 1) or 1
        baseline = {
            "transport":   monthly["transport"] / days,
            "electricity": monthly["electricity"] / days,
            "fuel":        monthly["fuel"] / days,
            "waste":       monthly["waste"] / days,
            "total":       monthly["total"] / days
        }

    result = run_simulation(data, baseline)

    # Monthly projection for Industry
    if user_type == "industry":
        result["projected_monthly"] = round(result["simulated_total"] * 30, 2)
        result["current_monthly"]   = round(monthly["total"], 2)
        result["monthly_saving"]    = round(
            monthly["total"] - result["projected_monthly"], 2
        )

    return jsonify({**result, "user_type": user_type})


# ============================================================
# API — GOALS
# ============================================================

@app.route('/api/goals', methods=['GET'])
def api_get_goal():
    """
    Return current month's goal and actual progress.
    Query param: ?user_type=individual | industry (default: industry)
    """
    user_type     = request.args.get("user_type", "industry")
    current_month = datetime.now().strftime("%Y-%m")

    conn = get_connection()
    goal = conn.execute(
        """SELECT * FROM goals
           WHERE user_id = ? AND user_type = ? AND month = ?
           ORDER BY created_at DESC LIMIT 1""",
        (DEFAULT_USER_ID, user_type, current_month)
    ).fetchone()
    conn.close()

    if not goal:
        return jsonify({"goal": None, "current_footprint": 0, "user_type": user_type})

    monthly = _get_current_month_total(DEFAULT_USER_ID, user_type)

    return jsonify({
        "goal":              dict(goal),
        "current_footprint": round(monthly["total"], 2),
        "day_count":         monthly.get("day_count", 0),
        "user_type":         user_type
    })


@app.route('/api/goals', methods=['POST'])
def api_set_goal():
    """Save or update a monthly CO2e reduction goal."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received."}), 400

    user_type = data.get("user_type", "industry")
    month     = data.get("month", "")
    target    = data.get("target_co2e", 0)

    if not month:
        return jsonify({"error": "Month is required."}), 400
    if float(target) <= 0:
        return jsonify({"error": "Target must be a positive number."}), 400

    conn = get_connection()
    conn.execute(
        """INSERT INTO goals (user_id, user_type, month, target_co2e)
           VALUES (?, ?, ?, ?)""",
        (DEFAULT_USER_ID, user_type, month, float(target))
    )
    conn.commit()
    conn.close()

    return jsonify({
        "message":     "Goal saved successfully.",
        "user_type":   user_type,
        "month":       month,
        "target_co2e": float(target)
    }), 201


# ============================================================
# API — REPORT (Daily CSV — Industry)
# ============================================================

@app.route('/api/report', methods=['GET'])
def api_report():
    """
    Export footprint records as CSV.
    Query param: ?user_type=individual | industry (default: industry)

    Individual: monthly records CSV
    Industry:   daily records CSV
    """
    user_type = request.args.get("user_type", "industry")
    order_col = "month" if user_type == "individual" else "date"

    conn = get_connection()
    rows = conn.execute(
        f"""SELECT user_type, frequency, date, month,
                  transport, electricity, fuel, waste, total,
                  data_quality, quality_notes, created_at
           FROM footprint_records
           WHERE user_id = ? AND user_type = ?
           ORDER BY {order_col} ASC""",
        (DEFAULT_USER_ID, user_type)
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    if user_type == "individual":
        writer.writerow([
            "User Type", "Frequency", "Month",
            "Transport (kg CO2e)", "Electricity (kg CO2e)",
            "Fuel (kg CO2e)", "Waste (kg CO2e)", "Total (kg CO2e)",
            "Data Quality", "Quality Notes", "Recorded At"
        ])
        for row in rows:
            writer.writerow([
                row["user_type"], row["frequency"], row["month"],
                row["transport"], row["electricity"], row["fuel"],
                row["waste"], row["total"],
                row["data_quality"], row["quality_notes"], row["created_at"]
            ])
        filename = "ecotrack_individual_monthly.csv"
    else:
        writer.writerow([
            "User Type", "Frequency", "Date", "Month",
            "Transport (kg CO2e)", "Electricity (kg CO2e)",
            "Fuel (kg CO2e)", "Waste (kg CO2e)", "Daily Total (kg CO2e)",
            "Data Quality", "Quality Notes", "Recorded At"
        ])
        for row in rows:
            writer.writerow([
                row["user_type"], row["frequency"], row["date"], row["month"],
                row["transport"], row["electricity"], row["fuel"],
                row["waste"], row["total"],
                row["data_quality"], row["quality_notes"], row["created_at"]
            ])
        filename = "ecotrack_industry_daily.csv"

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============================================================
# API — MONTHLY REPORT CSV (both modes)
# ============================================================

@app.route('/api/report/monthly', methods=['GET'])
def api_report_monthly():
    """Export monthly aggregated summary as CSV."""
    user_type = request.args.get("user_type", "industry")
    summaries = _get_monthly_summaries(DEFAULT_USER_ID, user_type)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "User Type", "Month", "Days Recorded",
        "Transport (kg CO2e)", "Electricity (kg CO2e)",
        "Fuel (kg CO2e)", "Waste (kg CO2e)",
        "Monthly Total (kg CO2e)", "Daily Average (kg CO2e)"
    ])

    for s in summaries:
        day_count = s.get("day_count", 1) or 1
        daily_avg = round(s["total"] / day_count, 2)
        writer.writerow([
            user_type, s["month"], day_count,
            round(s["transport"], 2), round(s["electricity"], 2),
            round(s["fuel"], 2), round(s["waste"], 2),
            round(s["total"], 2), daily_avg
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                f"attachment; filename=ecotrack_{user_type}_monthly_summary.csv"
        }
    )


# ============================================================
# API — DAILY SUMMARY (Industry only — for daily trend chart)
# ============================================================

@app.route('/api/daily-summary', methods=['GET'])
def api_daily_summary():
    """
    Return daily records for the current month (Industry only).
    Used by the dashboard daily trend chart.
    Query param: ?month=YYYY-MM (default: current month)
    """
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))

    conn = get_connection()
    rows = conn.execute(
        """SELECT date, transport, electricity, fuel, waste, total
           FROM footprint_records
           WHERE user_id = ? AND user_type = 'industry' AND month = ?
           ORDER BY date ASC""",
        (DEFAULT_USER_ID, month)
    ).fetchall()
    conn.close()

    records = [dict(r) for r in rows]
    return jsonify({"records": records, "month": month})


# ============================================================
# RUN
# ============================================================

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    # debug=False in production; locally still works with python app.py
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)
