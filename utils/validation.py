"""
EcoTrack Input Validation
Validates all user inputs before they reach the calculation engine.

Supports two modes:
  individual  -- monthly activity values (higher limits)
  industry    -- daily activity values (daily limits)
"""

from datetime import datetime

VALID_TRANSPORT_MODES = [
    "petrol_car", "diesel_car", "motorcycle", "bus",
    "auto_rickshaw", "metro_rail", "electric_car", "bicycle", "walking"
]

VALID_USER_TYPES = ["individual", "industry"]

# ---- Individual / Household monthly limits ----
MAX_DISTANCE_KM_MONTHLY    = 10000   # km/month (long-distance commuters)
MAX_ELECTRICITY_KWH_MONTHLY = 5000   # kWh/month (large household)
MAX_LPG_CYLINDERS_MONTHLY  = 10.0    # cylinders/month
MAX_WASTE_KG_MONTHLY       = 500     # kg/month

# ---- Industry / Factory daily limits ----
MAX_DISTANCE_KM_DAILY      = 10000   # km/day (logistics/freight)
MAX_ELECTRICITY_KWH_DAY    = 100000  # kWh/day (factory)
MAX_LPG_CYLINDERS_DAY      = 100.0   # cylinders/day (industrial)
MAX_WASTE_KG_DAY           = 50000   # kg/day (industrial)


# ============================================================
# SHARED VALIDATORS
# ============================================================

def validate_number(value, field_name, min_val=0, max_val=None):
    """
    Validate that a value is a non-negative number within range.
    Returns (is_valid: bool, error_message: str or None)
    """
    try:
        num = float(value)
    except (TypeError, ValueError):
        return False, f"{field_name} must be a valid number."

    if num < min_val:
        return False, f"{field_name} cannot be negative."

    if max_val is not None and num > max_val:
        return False, f"{field_name} exceeds the maximum allowed value ({max_val})."

    return True, None


def validate_transport_mode(mode):
    """Validate that the transport mode is a known option."""
    if mode not in VALID_TRANSPORT_MODES:
        return False, (
            f"Unknown transport mode '{mode}'. "
            f"Valid options: {', '.join(VALID_TRANSPORT_MODES)}"
        )
    return True, None


def validate_user_type(user_type):
    """Validate that user_type is 'individual' or 'industry'."""
    if user_type not in VALID_USER_TYPES:
        return False, f"user_type must be 'individual' or 'industry', got '{user_type}'."
    return True, None


def validate_date(date_str):
    """
    Validate YYYY-MM-DD date.
    - Must not be in the future.
    - Must not be older than 5 years.
    """
    if not date_str:
        return False, "Date is required."
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return False, "Date must be in YYYY-MM-DD format (e.g. 2026-09-29)."

    if parsed.date() > datetime.now().date():
        return False, "Date cannot be in the future."

    if parsed.year < datetime.now().year - 5:
        return False, "Date is too far in the past (maximum 5 years)."

    return True, None


def validate_month(month_str):
    """
    Validate YYYY-MM month string.
    - Must not be in the future.
    - Must not be older than 5 years.
    """
    if not month_str:
        return False, "Month is required."
    try:
        parsed = datetime.strptime(month_str, "%Y-%m")
    except ValueError:
        return False, "Month must be in YYYY-MM format (e.g. 2026-09)."

    now = datetime.now()
    if parsed.year > now.year or (parsed.year == now.year and parsed.month > now.month):
        return False, "Month cannot be in the future."

    if parsed.year < now.year - 5:
        return False, "Month is too far in the past (maximum 5 years)."

    return True, None


# ============================================================
# MODE 1 — INDIVIDUAL / HOUSEHOLD (monthly inputs)
# ============================================================

def validate_individual_input(data):
    """
    Validate monthly inputs for Individual / Household mode.

    Expected keys:
        month           - YYYY-MM  (the billing/reporting month)
        transport_mode  - string key
        distance_km     - total km travelled this month
        electricity_kwh - kWh from monthly electricity bill
        lpg_cylinders   - number of LPG cylinders used this month
        waste_kg        - total kg of waste this month

    Returns (is_valid: bool, errors: list of str)
    """
    errors = []

    # Month
    valid, msg = validate_month(data.get("month", ""))
    if not valid:
        errors.append(msg)

    # Transport mode
    valid, msg = validate_transport_mode(data.get("transport_mode", ""))
    if not valid:
        errors.append(msg)

    # Monthly distance
    valid, msg = validate_number(
        data.get("distance_km"), "Monthly Distance (km)",
        min_val=0, max_val=MAX_DISTANCE_KM_MONTHLY
    )
    if not valid:
        errors.append(msg)

    # Monthly electricity
    valid, msg = validate_number(
        data.get("electricity_kwh"), "Monthly Electricity (kWh)",
        min_val=0, max_val=MAX_ELECTRICITY_KWH_MONTHLY
    )
    if not valid:
        errors.append(msg)

    # Monthly LPG
    valid, msg = validate_number(
        data.get("lpg_cylinders"), "Monthly LPG Cylinders",
        min_val=0, max_val=MAX_LPG_CYLINDERS_MONTHLY
    )
    if not valid:
        errors.append(msg)

    # Monthly waste
    valid, msg = validate_number(
        data.get("waste_kg"), "Monthly Waste (kg)",
        min_val=0, max_val=MAX_WASTE_KG_MONTHLY
    )
    if not valid:
        errors.append(msg)

    return len(errors) == 0, errors


# ============================================================
# MODE 2 — INDUSTRY / FACTORY (daily inputs)
# ============================================================

def validate_industry_input(data):
    """
    Validate daily inputs for Industry / Factory mode.

    Expected keys:
        date            - YYYY-MM-DD
        transport_mode  - string key
        distance_km     - km travelled / transported today
        electricity_kwh - kWh consumed today
        lpg_cylinders   - fraction or count of LPG cylinders used today
        waste_kg        - kg of waste generated today

    Returns (is_valid: bool, errors: list of str)
    """
    errors = []

    # Date
    valid, msg = validate_date(data.get("date", ""))
    if not valid:
        errors.append(msg)

    # Transport mode
    valid, msg = validate_transport_mode(data.get("transport_mode", ""))
    if not valid:
        errors.append(msg)

    # Daily distance
    valid, msg = validate_number(
        data.get("distance_km"), "Daily Distance (km)",
        min_val=0, max_val=MAX_DISTANCE_KM_DAILY
    )
    if not valid:
        errors.append(msg)

    # Daily electricity
    valid, msg = validate_number(
        data.get("electricity_kwh"), "Daily Electricity (kWh)",
        min_val=0, max_val=MAX_ELECTRICITY_KWH_DAY
    )
    if not valid:
        errors.append(msg)

    # Daily LPG
    valid, msg = validate_number(
        data.get("lpg_cylinders"), "Daily LPG (cylinders)",
        min_val=0, max_val=MAX_LPG_CYLINDERS_DAY
    )
    if not valid:
        errors.append(msg)

    # Daily waste
    valid, msg = validate_number(
        data.get("waste_kg"), "Daily Waste (kg)",
        min_val=0, max_val=MAX_WASTE_KG_DAY
    )
    if not valid:
        errors.append(msg)

    return len(errors) == 0, errors


# ============================================================
# UNIFIED DISPATCHER
# ============================================================

def validate_calculator_input(data):
    """
    Dispatch to the correct validator based on user_type.
    Validates user_type first, then delegates.

    Returns (is_valid: bool, errors: list of str)
    """
    user_type = data.get("user_type", "")

    # Validate user_type first
    valid, msg = validate_user_type(user_type)
    if not valid:
        return False, [msg]

    if user_type == "individual":
        return validate_individual_input(data)
    else:
        return validate_industry_input(data)
