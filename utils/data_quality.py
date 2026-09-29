"""
EcoTrack Data Quality Indicator
Assesses the reliability of a submitted carbon footprint calculation.
Quality is based on completeness and plausibility of inputs.
This is an indicative score, NOT a statistically certified measure.
"""


def assess_data_quality(data):
    """
    Assess input data quality and return a rating and notes.
    Returns: dict with 'rating' (High/Medium/Low) and 'notes' (list of str)
    """
    notes = []
    score = 100  # Start at 100 and deduct for quality issues

    transport_mode = data.get("transport_mode", "")
    distance_km    = float(data.get("distance_km", 0))
    trips          = float(data.get("trips_per_month", 0))
    electricity    = float(data.get("electricity_kwh", 0))
    lpg            = float(data.get("lpg_cylinders", 0))
    waste          = float(data.get("waste_kg", 0))

    # Check: all zero inputs
    if distance_km == 0 and electricity == 0 and lpg == 0 and waste == 0:
        score -= 40
        notes.append("All activity values are zero. Result may not reflect actual footprint.")

    # Check: transport entered but distance or trips is zero
    if transport_mode not in ("bicycle", "walking"):
        if distance_km == 0:
            score -= 15
            notes.append("Transport mode selected but distance is zero.")
        if trips == 0:
            score -= 15
            notes.append("Transport mode selected but number of trips is zero.")

    # Check: electricity is zero (unusual for most households)
    if electricity == 0:
        score -= 10
        notes.append("Electricity consumption is zero. If your home uses electricity, please enter units consumed.")

    # Check: waste is zero
    if waste == 0:
        score -= 5
        notes.append("Waste is zero. Consider estimating household waste generated per month.")

    # Check: unusually high electricity
    if electricity > 1000:
        score -= 10
        notes.append("Electricity value is unusually high (>1000 kWh/month). Please verify.")

    # Check: unusually high distance
    if distance_km > 500:
        score -= 5
        notes.append("Daily commute distance is very high (>500 km). Please verify.")

    # Determine rating
    if score >= 80:
        rating = "High"
    elif score >= 50:
        rating = "Medium"
    else:
        rating = "Low"

    if not notes:
        notes.append("All inputs appear complete and plausible.")

    return {
        "rating": rating,
        "score":  score,
        "notes":  notes
    }
