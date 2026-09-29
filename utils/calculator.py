"""
EcoTrack Calculation Engine
Computes estimated CO2e emissions from user activity data.
Formula: CO2e = Activity Quantity x Emission Factor

Supports two calculation modes:
  Individual / Household  -- monthly activity inputs
  Industry / Factory      -- daily activity inputs (aggregated monthly)

All results are ESTIMATES based on documented emission factors.
They are not direct physical measurements.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.init_db import get_connection


# ============================================================
# EMISSION FACTORS (kg CO2e per unit)
# Loaded from DB at runtime; fallback constants used if DB unavailable.
# ============================================================

TRANSPORT_FACTORS = {
    "petrol_car":    0.21,   # DEFRA 2023
    "diesel_car":    0.17,   # DEFRA 2023
    "motorcycle":    0.11,   # DEFRA 2023
    "bus":           0.089,  # IPCC AR6
    "auto_rickshaw": 0.075,  # MoEFCC India
    "metro_rail":    0.031,  # CEA India
    "electric_car":  0.05,   # CEA India 2023
    "bicycle":       0.0,
    "walking":       0.0,
}

ELECTRICITY_FACTOR = 0.716   # CEA India 2023 (kg CO2e per kWh)
LPG_FACTOR         = 14.2    # kg CO2e per standard 14.2 kg cylinder
WASTE_FACTOR       = 0.45    # kg CO2e per kg mixed municipal waste


def get_emission_factor(category, activity):
    """
    Fetch the emission factor from the database.
    Falls back to in-memory constants if DB lookup fails.
    """
    try:
        conn = get_connection()
        row  = conn.execute(
            "SELECT factor FROM emission_factors WHERE category=? AND activity=?",
            (category, activity)
        ).fetchone()
        conn.close()
        if row:
            return float(row["factor"])
    except Exception:
        pass
    return None


# ============================================================
# BASE CATEGORY CALCULATORS
# These work for any quantity (daily or monthly).
# The caller is responsible for passing the correct quantity.
# ============================================================

def calculate_transport(mode, distance_km):
    """
    Calculate transport CO2e for a given total distance.

    Args:
        mode        (str):   vehicle type key
        distance_km (float): total km travelled (daily OR monthly)

    Returns:
        float: kg CO2e
    """
    factor = get_emission_factor("transport", mode)
    if factor is None:
        factor = TRANSPORT_FACTORS.get(mode, 0.21)

    co2e = float(distance_km) * factor
    return round(co2e, 4)


def calculate_electricity(units_kwh):
    """
    Calculate electricity CO2e using India grid emission factor.

    Args:
        units_kwh (float): kWh consumed (daily OR monthly)

    Returns:
        float: kg CO2e
    """
    factor = get_emission_factor("electricity", "grid_india")
    if factor is None:
        factor = ELECTRICITY_FACTOR

    co2e = float(units_kwh) * factor
    return round(co2e, 4)


def calculate_fuel(cylinders):
    """
    Calculate LPG / cooking fuel CO2e.

    Args:
        cylinders (float): number of 14.2 kg LPG cylinders (daily fraction OR monthly count)

    Returns:
        float: kg CO2e
    """
    factor = get_emission_factor("fuel", "lpg_cylinder")
    if factor is None:
        factor = LPG_FACTOR

    co2e = float(cylinders) * factor
    return round(co2e, 4)


def calculate_waste(waste_kg):
    """
    Calculate mixed municipal waste CO2e.

    Args:
        waste_kg (float): kg of waste (daily OR monthly)

    Returns:
        float: kg CO2e
    """
    factor = get_emission_factor("waste", "mixed_waste")
    if factor is None:
        factor = WASTE_FACTOR

    co2e = float(waste_kg) * factor
    return round(co2e, 4)


# ============================================================
# MODE 1 — INDIVIDUAL / HOUSEHOLD
# Monthly inputs --> Monthly CO2e
# ============================================================

def calculate_monthly_total(transport_mode, monthly_distance_km,
                            monthly_electricity_kwh, monthly_lpg_cylinders,
                            monthly_waste_kg):
    """
    Calculate total MONTHLY carbon footprint for an Individual / Household.

    The user enters monthly quantities directly:
      - monthly_distance_km     : total km travelled this month
      - monthly_electricity_kwh : kWh from monthly electricity bill
      - monthly_lpg_cylinders   : number of LPG cylinders used this month
      - monthly_waste_kg        : total kg of waste generated this month

    Returns a dict with category breakdown and monthly total.
    """
    transport_co2e   = calculate_transport(transport_mode, monthly_distance_km)
    electricity_co2e = calculate_electricity(monthly_electricity_kwh)
    fuel_co2e        = calculate_fuel(monthly_lpg_cylinders)
    waste_co2e       = calculate_waste(monthly_waste_kg)

    total = round(transport_co2e + electricity_co2e + fuel_co2e + waste_co2e, 4)

    return {
        "transport":   transport_co2e,
        "electricity": electricity_co2e,
        "fuel":        fuel_co2e,
        "waste":       waste_co2e,
        "total":       total
    }


# ============================================================
# MODE 2 — INDUSTRY / FACTORY
# Daily inputs --> Daily CO2e --> Monthly aggregation via SQL
# ============================================================

def calculate_daily_total(transport_mode, distance_km,
                          electricity_kwh, lpg_cylinders, waste_kg):
    """
    Calculate total DAILY carbon footprint for an Industry / Factory.

    The user enters daily activity quantities:
      - distance_km     : km travelled or transported today
      - electricity_kwh : kWh consumed today
      - lpg_cylinders   : fraction of LPG cylinder used today
      - waste_kg        : kg of waste generated today

    Returns a dict with category breakdown and daily total.
    """
    transport_co2e   = calculate_transport(transport_mode, distance_km)
    electricity_co2e = calculate_electricity(electricity_kwh)
    fuel_co2e        = calculate_fuel(lpg_cylinders)
    waste_co2e       = calculate_waste(waste_kg)

    total = round(transport_co2e + electricity_co2e + fuel_co2e + waste_co2e, 4)

    return {
        "transport":   transport_co2e,
        "electricity": electricity_co2e,
        "fuel":        fuel_co2e,
        "waste":       waste_co2e,
        "total":       total
    }


# ============================================================
# UNIFIED DISPATCHER
# ============================================================

def calculate(user_type, **kwargs):
    """
    Dispatch to the correct calculation function based on user_type.

    For 'individual':
        Required kwargs: transport_mode, monthly_distance_km,
                         monthly_electricity_kwh, monthly_lpg_cylinders,
                         monthly_waste_kg

    For 'industry':
        Required kwargs: transport_mode, distance_km,
                         electricity_kwh, lpg_cylinders, waste_kg

    Returns a category breakdown dict with 'total'.
    """
    if user_type == "individual":
        return calculate_monthly_total(
            transport_mode        = kwargs["transport_mode"],
            monthly_distance_km   = float(kwargs.get("distance_km", 0)),
            monthly_electricity_kwh = float(kwargs.get("electricity_kwh", 0)),
            monthly_lpg_cylinders = float(kwargs.get("lpg_cylinders", 0)),
            monthly_waste_kg      = float(kwargs.get("waste_kg", 0))
        )
    else:  # industry (default)
        return calculate_daily_total(
            transport_mode  = kwargs["transport_mode"],
            distance_km     = float(kwargs.get("distance_km", 0)),
            electricity_kwh = float(kwargs.get("electricity_kwh", 0)),
            lpg_cylinders   = float(kwargs.get("lpg_cylinders", 0)),
            waste_kg        = float(kwargs.get("waste_kg", 0))
        )


# --- Backward-compatibility alias ---
def calculate_total(transport_mode, distance_km, trips_per_month=1,
                    electricity_kwh=0, lpg_cylinders=0, waste_kg=0):
    """DEPRECATED: use calculate_daily_total() or calculate() instead."""
    return calculate_daily_total(
        transport_mode  = transport_mode,
        distance_km     = distance_km,
        electricity_kwh = electricity_kwh,
        lpg_cylinders   = lpg_cylinders,
        waste_kg        = waste_kg
    )
