from __future__ import annotations

import pandas as pd

TARGET = "Cash_Demand_Next_Day"
CATEGORICAL_FEATURES = ["ATM_ID", "Location", "City", "Weather_Condition"]
NUMERIC_FEATURES = [
    "ATM_Capacity",
    "Total_Current_Cash",
    "Total_Withdraw_Cash",
    "Total_deposite_Cash",
    "No_of_Deposits",
    "No_of_Withdraws",
    "Temperature",
    "Holiday_Flag",
    "Festival_Flag",
    "Previous_Day_Cash_Level",
    "Day",
    "Month",
    "Year",
    "Day_of_week",
    "withdrawals_lag_1",
    "withdrawals_lag_7",
    "withdrawals_rolling_7",
    "next_day_holiday",
    "next_day_festival",
    "next_day_weekday",
    "payday_flag",
]
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    data["Date"] = pd.to_datetime(data["Date"])
    data = data.sort_values(["ATM_ID", "Date"]).reset_index(drop=True)
    grouped = data.groupby("ATM_ID", sort=False)
    data["withdrawals_lag_1"] = grouped["Total_Withdraw_Cash"].shift(1)
    data["withdrawals_lag_7"] = grouped["Total_Withdraw_Cash"].shift(7)
    data["withdrawals_rolling_7"] = grouped["Total_Withdraw_Cash"].transform(
        lambda values: values.shift(1).rolling(7, min_periods=1).mean()
    )
    data["next_day_holiday"] = grouped["Holiday_Flag"].shift(-1).fillna(0)
    data["next_day_festival"] = grouped["Festival_Flag"].shift(-1).fillna(0)
    next_dates = grouped["Date"].shift(-1).fillna(data["Date"] + pd.Timedelta(days=1))
    data["next_day_weekday"] = next_dates.dt.weekday
    data["payday_flag"] = next_dates.dt.day.map(lambda day: int(day >= 25 or day <= 2))
    data["Day_of_week"] = pd.to_numeric(data["Day_of_week"], errors="coerce").fillna(data["Date"].dt.weekday)
    data["Day"] = data["Date"].dt.day
    data["Month"] = data["Date"].dt.month
    data["Year"] = data["Date"].dt.year
    return data[FEATURES].fillna(0)
