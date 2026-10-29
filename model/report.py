"""Create evaluation charts with Matplotlib: python model/report.py  (writes PNGs to model/reports/)."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from .features import FEATURES, TARGET, build_features
    from .train import DATA_PATH, METRICS_PATH, MODEL_PATH, TEST_START, build_estimator, mean_absolute_percentage_error
except ImportError:  # run as a script
    from features import FEATURES, TARGET, build_features
    from train import DATA_PATH, METRICS_PATH, MODEL_PATH, TEST_START, build_estimator, mean_absolute_percentage_error

OUT = Path(__file__).resolve().parent / "reports"
YELLOW, INK, TEAL, GREY, RED = "#e9ee3a", "#20231e", "#0f7b8a", "#c9cdd6", "#c2332f"


def style(ax, title: str, ylabel: str = "") -> None:
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color=INK)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=150)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    data = pd.read_csv(DATA_PATH, parse_dates=["Date"]).sort_values(["ATM_ID", "Date"]).reset_index(drop=True)
    features = build_features(data)
    usable = data[TARGET].notna() & data.groupby("ATM_ID").cumcount().ge(7)
    model = joblib.load(MODEL_PATH)

    test = usable & (data["Date"] >= TEST_START)
    frame = data.loc[test, ["Date", TARGET]].assign(prediction=np.maximum(0, model.predict(features.loc[test, FEATURES])))
    daily = frame.groupby("Date")[[TARGET, "prediction"]].sum() / 1e5
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(daily.index, daily[TARGET], color=INK, lw=1.8, label="Actual next-day demand")
    ax.plot(daily.index, daily["prediction"], color=TEAL, lw=1.8, ls="--", label="Model forecast")
    style(ax, f"Network demand, test period (accuracy {metrics['accuracy_percent']:.1f}%)", "Rupees (lakh)")
    ax.legend(frameon=False, loc="upper right")
    fig.autofmt_xdate()
    save(fig, "01_actual_vs_forecast.png")

    acc = pd.Series(metrics["atm_accuracy"]).sort_index()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(acc.index, acc.values, color=YELLOW, edgecolor=INK)
    ax.axhline(85, color=RED, ls="--", lw=1.4, label="Target 85%")
    ax.set_ylim(80, 100)
    style(ax, "Forecast accuracy by ATM (100 - MAPE)", "Accuracy %")
    ax.legend(frameon=False)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    save(fig, "02_accuracy_by_atm.png")

    bt = metrics["backtest"]
    fixed, forecast = bt["fixed_threshold"], bt["forecast_threshold"]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.6))
    for ax, key, label in zip(axes, ("cashouts", "refill_trips"), ("Cash-outs", "Refill trips")):
        ax.bar(["Fixed 25% rule", "Forecast rule"], [fixed[key], forecast[key]], color=[GREY, YELLOW], edgecolor=INK)
        for x, value in enumerate([fixed[key], forecast[key]]):
            ax.text(x, value, str(value), ha="center", va="bottom", fontweight="bold")
        style(ax, label)
    fig.suptitle("Simulated refill policies on the test period", x=0.02, ha="left", fontsize=12, fontweight="bold")
    save(fig, "03_policy_backtest.png")

    weekday = data.assign(day=data["Date"].dt.day_name()).groupby("day")["Total_Withdraw_Cash"].mean() / 1e3
    weekday = weekday.reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
    festival = data.groupby("Festival_Flag")["Total_Withdraw_Cash"].mean() / 1e3
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), gridspec_kw={"width_ratios": [3, 1.2]})
    axes[0].bar([d[:3] for d in weekday.index], weekday.values, color=YELLOW, edgecolor=INK)
    style(axes[0], "Average withdrawals by weekday", "Rupees (thousand)")
    axes[1].bar(["Regular", "Festival"], festival.values, color=[GREY, YELLOW], edgecolor=INK)
    style(axes[1], f"Festival effect {festival[1] / festival[0] * 100 - 100:+.0f}%")
    save(fig, "04_demand_patterns.png")

    rows = []
    for month_start in pd.date_range("2025-05-01", "2025-08-01", freq="MS"):
        month_end = month_start + pd.offsets.MonthEnd(0)
        train_mask = usable & (data["Date"] < month_start)
        fold_mask = usable & (data["Date"] >= month_start) & (data["Date"] <= month_end)
        estimator = build_estimator().fit(features.loc[train_mask, FEATURES], data.loc[train_mask, TARGET])
        prediction = np.maximum(0, estimator.predict(features.loc[fold_mask, FEATURES]))
        mape = mean_absolute_percentage_error(data.loc[fold_mask, TARGET].to_numpy(dtype=float), prediction)
        rows.append({"test_month": month_start.strftime("%Y-%m"), "train_rows": int(train_mask.sum()), "test_rows": int(fold_mask.sum()), "accuracy_percent": round(100 - mape, 2)})
    walk = pd.DataFrame(rows)
    walk.to_csv(OUT / "walk_forward_validation.csv", index=False)
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.bar(walk["test_month"], walk["accuracy_percent"], color=YELLOW, edgecolor=INK)
    ax.axhline(85, color=RED, ls="--", lw=1.4, label="Target 85%")
    ax.set_ylim(80, 100)
    style(ax, "Walk-forward validation by month", "Accuracy %")
    ax.legend(frameon=False)
    save(fig, "05_walk_forward.png")
    print(walk.to_string(index=False))
    print(f"Charts written to {OUT}")


if __name__ == "__main__":
    main()
