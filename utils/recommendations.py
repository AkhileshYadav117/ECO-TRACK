"""
EcoTrack Recommendations Engine
Rule-based (NOT ML) personalized recommendations.
Identifies the dominant emission category and returns targeted suggestions.
"""

RECOMMENDATIONS = {
    "transport": [
        "Consider switching from a petrol car to public transport (bus/metro) for your daily commute.",
        "Carpooling with colleagues can reduce your transport emissions by up to 50%.",
        "For short distances under 3 km, consider walking or cycling — zero emissions.",
        "If feasible, switching to a CNG or electric vehicle significantly reduces transport CO₂e.",
        "Combine multiple errands into one trip to reduce total distance driven.",
        "Work from home even 2 days per week can reduce monthly transport emissions by ~40%.",
    ],
    "electricity": [
        "Switch to LED lighting throughout your home — they use 75% less energy than incandescent bulbs.",
        "Set your AC thermostat to 24°C instead of 18°C — each degree saves ~6% electricity.",
        "Unplug devices on standby — phantom loads can account for 5–10% of household electricity.",
        "Consider rooftop solar panels — they can significantly reduce grid electricity dependence.",
        "Use energy-efficient appliances (BEE 5-star rated) when replacing old equipment.",
        "Run washing machines and dishwashers with full loads only.",
    ],
    "fuel": [
        "Reduce LPG use by using a pressure cooker — it cuts cooking time and gas consumption by 50–70%.",
        "Keep burner flames low and match pan size to burner size for efficient cooking.",
        "Cover pots while cooking to retain heat and reduce cooking time.",
        "Consider an induction cooktop for occasional cooking — more energy-efficient than LPG.",
        "Ensure your LPG burners are clean and maintained — blocked jets waste fuel.",
    ],
    "waste": [
        "Compost organic kitchen waste — it diverts waste from landfill and reduces methane emissions.",
        "Follow Reduce → Reuse → Recycle to minimise waste generation.",
        "Buy products with minimal packaging to reduce packaging waste.",
        "Separate dry and wet waste at source for more effective recycling.",
        "Avoid single-use plastics — carry reusable bags and bottles.",
        "Donate usable items instead of discarding them.",
    ],
}

GENERAL_RECOMMENDATIONS = [
    "Track your footprint every month to identify trends and stay accountable.",
    "Set a monthly CO₂e reduction goal — even a 5% reduction per month adds up significantly.",
    "Share your progress with family or friends to encourage collective action.",
]


def get_dominant_category(record):
    """
    Identify the category with the highest CO₂e contribution.
    record: dict with keys transport, electricity, fuel, waste
    """
    categories = {
        "transport":   float(record.get("transport",   0)),
        "electricity": float(record.get("electricity", 0)),
        "fuel":        float(record.get("fuel",        0)),
        "waste":       float(record.get("waste",       0)),
    }
    if all(v == 0 for v in categories.values()):
        return None
    return max(categories, key=categories.get)


def get_recommendations(record, max_tips=5):
    """
    Return personalized recommendations based on the dominant category.
    Returns a dict with 'dominant_category' and 'recommendations' list.
    """
    dominant = get_dominant_category(record)

    if dominant is None:
        return {
            "dominant_category": None,
            "recommendations":   GENERAL_RECOMMENDATIONS
        }

    tips = RECOMMENDATIONS.get(dominant, [])[:max_tips]

    return {
        "dominant_category": dominant,
        "recommendations":   tips
    }
