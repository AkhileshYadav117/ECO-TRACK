"""
EcoTrack ML Predictor
Uses Scikit-learn Linear Regression to predict next month's
estimated carbon footprint from historical records.

Requires a minimum of 3 historical months for a meaningful prediction.
Results are trend-based estimates, not guaranteed forecasts.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error


MIN_RECORDS_REQUIRED = 3


def predict_next_month(records):
    """
    Predict next month's total CO₂e from historical footprint records.

    Parameters:
        records (list of dict): Each dict must have 'month' (YYYY-MM) and 'total' (float).

    Returns:
        dict: status, predicted_co2e, model, data_points, mae (if available), message
    """
    if len(records) < MIN_RECORDS_REQUIRED:
        return {
            "status":  "insufficient_data",
            "message": (
                f"At least {MIN_RECORDS_REQUIRED} months of footprint history are required "
                f"for a reliable ML prediction. You currently have {len(records)} record(s). "
                "Keep tracking your footprint each month!"
            )
        }

    # Build DataFrame
    df = pd.DataFrame(records)
    df = df.sort_values("month").reset_index(drop=True)
    df["month_index"] = np.arange(len(df))  # 0, 1, 2, ... as numeric time feature

    X = df[["month_index"]].values
    y = df["total"].values

    # Train Linear Regression
    model = LinearRegression()
    model.fit(X, y)

    # Predict next month (index = last + 1)
    next_index = np.array([[len(df)]])
    predicted  = model.predict(next_index)[0]

    # Clamp to non-negative (CO₂e cannot be negative)
    predicted = max(0.0, predicted)

    # Evaluate model on training data (indicative MAE)
    y_pred = model.predict(X)
    mae    = mean_absolute_error(y, y_pred)

    return {
        "status":          "success",
        "predicted_co2e":  round(predicted, 2),
        "model":           "Linear Regression",
        "data_points":     len(records),
        "mae":             round(mae, 2),
        "message":         (
            "Prediction based on your historical trend using Scikit-learn Linear Regression. "
            "This is an estimate — actual emissions depend on future behaviour."
        )
    }
