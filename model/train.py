from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

try:  # Support both `python model/train.py` and package imports in tests.
    from .features import CATEGORICAL_FEATURES, FEATURES, NUMERIC_FEATURES, TARGET, build_features
except ImportError:  # pragma: no cover - exercised by the script entry point
    from features import CATEGORICAL_FEATURES, FEATURES, NUMERIC_FEATURES, TARGET, build_features

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "Dataset" / "ATM_Cash_Demand.csv"
MODEL_PATH = Path(__file__).resolve().parent / "cashcast_model.joblib"
METRICS_PATH = Path(__file__).resolve().parent / "metrics.json"
TEST_START = pd.Timestamp("2025-05-01")


def mean_absolute_percentage_error(actual: np.ndarray, predicted: np.ndarray) -> float:
    valid = actual != 0
    return float(np.mean(np.abs((actual[valid] - predicted[valid]) / actual[valid])) * 100)


def replay_daily_policy(rows: pd.DataFrame, forecast_driven: bool) -> dict[str, int]:
    """Replay cash balances one day at a time per ATM using historical deposits/withdrawals."""
    cashouts = 0
    refill_trips = 0
    for _, atm_rows in rows.sort_values(["ATM_ID", "Date"]).groupby("ATM_ID", sort=True):
        ordered_atm = atm_rows.reset_index(drop=True)
        if ordered_atm.empty:
            continue
        balance = float(ordered_atm.loc[0, "Total_Current_Cash"])
        for row in ordered_atm.itertuples(index=False):
            capacity = float(row.ATM_Capacity)
            forecast = float(row.forecast)
            trigger = balance < (1.2 * forecast + capacity * 0.05) if forecast_driven else balance < capacity * 0.25
            if trigger:
                refill = min(max(0.0, capacity * 0.85 - balance), max(0.0, capacity - balance))
                if refill > 0:
                    balance += refill
                    refill_trips += 1
            demand = max(0.0, float(getattr(row, TARGET)))
            if balance < demand:
                cashouts += 1
            balance = min(capacity, max(0.0, balance - demand) + max(0.0, float(row.Total_deposite_Cash)))
    return {"cashouts": cashouts, "refill_trips": refill_trips}


def build_estimator():
    preprocessing = ColumnTransformer(
        [
            ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
            ("numeric", "passthrough", NUMERIC_FEATURES),
        ],
        verbose_feature_names_out=False,
    )
    return make_pipeline(
        preprocessing,
        HistGradientBoostingRegressor(max_iter=220, learning_rate=0.08, max_leaf_nodes=15, l2_regularization=1.0, random_state=136),
    )


def main() -> None:
    data = pd.read_csv(DATA_PATH, parse_dates=["Date"])
    ordered = data.sort_values(["ATM_ID", "Date"]).reset_index(drop=True)
    features = build_features(ordered)
    history_days = ordered.groupby("ATM_ID").cumcount()
    usable = ordered[TARGET].notna() & history_days.ge(7)
    train_mask = (ordered["Date"] < TEST_START) & usable
    test_mask = (ordered["Date"] >= TEST_START) & usable
    if not train_mask.any() or not test_mask.any():
        raise ValueError("The chronological split must contain both training and test rows.")

    estimator = build_estimator()
    estimator.fit(features.loc[train_mask, FEATURES], ordered.loc[train_mask, TARGET])
    actual = ordered.loc[test_mask, TARGET].to_numpy(dtype=float)
    prediction = np.maximum(0, estimator.predict(features.loc[test_mask, FEATURES]))
    baseline = features.loc[test_mask, "withdrawals_rolling_7"].to_numpy(dtype=float)
    mape = mean_absolute_percentage_error(actual, prediction)
    baseline_mape = mean_absolute_percentage_error(actual, baseline)

    test_rows = ordered.loc[test_mask].copy()
    test_rows["forecast"] = prediction
    policy_a = replay_daily_policy(test_rows, forecast_driven=False)
    policy_b = replay_daily_policy(test_rows, forecast_driven=True)
    reduction = (policy_a["cashouts"] - policy_b["cashouts"]) / max(policy_a["cashouts"], 1) * 100
    test_rows["actual"] = actual
    test_rows["prediction"] = prediction
    atm_accuracy = {
        str(atm_id): 100 - mean_absolute_percentage_error(rows["actual"].to_numpy(), rows["prediction"].to_numpy())
        for atm_id, rows in test_rows.groupby("ATM_ID")
    }

    metrics = {
        "test_start": TEST_START.date().isoformat(),
        "test_rows": int(test_mask.sum()),
        "mape_percent": mape,
        "accuracy_percent": 100 - mape,
        "mae": float(mean_absolute_error(actual, prediction)),
        "r2": float(r2_score(actual, prediction)),
        "baseline_mape_percent": baseline_mape,
        "atm_accuracy": atm_accuracy,
        "model_trained": True,
        "backtest": {
            "simulation": True,
            "method": "day-by-day replay per ATM; balances carry forward after simulated refills, withdrawals, and recorded deposits",
            "fixed_threshold": policy_a,
            "forecast_threshold": policy_b,
            "cashout_reduction_percent": reduction,
        },
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(estimator, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
