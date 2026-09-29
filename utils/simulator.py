"""
EcoTrack What-If Carbon Reduction Simulator
Reuses the same verified calculation engine to project
a simulated footprint under different activity assumptions.
Results are estimates — not direct measurements.

Works for both modes:
  Individual: simulate vs monthly baseline
  Industry:   simulate vs daily average baseline
"""

from utils.calculator import calculate_daily_total


def run_simulation(sim_data, current_record=None):
    """
    Calculate a projected footprint from simulated activity inputs.
    Compares against current_record if provided.

    Parameters:
        sim_data (dict): Simulated activity values.
            Required keys: transport_mode, distance_km, electricity_kwh,
                           lpg_cylinders, waste_kg
        current_record (dict): The baseline record to compare against.
            Must have 'total' key.

    Returns:
        dict: current_total, simulated_total, saving, saving_pct, breakdown
    """
    # Calculate simulated footprint using the same emission-factor engine
    simulated = calculate_daily_total(
        transport_mode  = sim_data.get("transport_mode", "petrol_car"),
        distance_km     = float(sim_data.get("distance_km",     0)),
        electricity_kwh = float(sim_data.get("electricity_kwh", 0)),
        lpg_cylinders   = float(sim_data.get("lpg_cylinders",   0)),
        waste_kg        = float(sim_data.get("waste_kg",        0))
    )

    simulated_total = simulated["total"]

    # Current footprint baseline
    current_total = float(current_record.get("total", 0)) if current_record else 0.0

    saving     = round(current_total - simulated_total, 4)
    saving_pct = round((saving / current_total * 100), 2) if current_total > 0 else 0.0

    return {
        "current_total":   current_total,
        "simulated_total": simulated_total,
        "saving":          saving,
        "saving_pct":      saving_pct,
        "breakdown": {
            "transport":   simulated["transport"],
            "electricity": simulated["electricity"],
            "fuel":        simulated["fuel"],
            "waste":       simulated["waste"],
        }
    }
