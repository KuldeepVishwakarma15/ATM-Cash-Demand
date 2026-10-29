from datetime import date, timedelta

import pandas as pd

from model.features import FEATURES, build_features
from model.train import TEST_START, replay_daily_policy


def history(days=10):
    rows = []
    start = date(2025, 4, 25)
    for atm_id, city in (("ATM001", "Mumbai"), ("ATM002", "Delhi")):
        for offset in range(days):
            current = start + timedelta(days=offset)
            rows.append({
                "ATM_ID": atm_id,
                "Date": current,
                "Day_of_week": current.strftime("%A"),
                "Location": "Branch",
                "City": city,
                "Day": current.day,
                "Month": current.month,
                "Year": current.year,
                "ATM_Capacity": 100_000,
                "Total_Current_Cash": 50_000,
                "Total_Withdraw_Cash": (offset + 1) * 100,
                "Total_deposite_Cash": 0,
                "No_of_Deposits": 0,
                "No_of_Withdraws": 10,
                "Temperature": 25,
                "Weather_Condition": "Sunny",
                "Holiday_Flag": 0,
                "Festival_Flag": 0,
                "Previous_Day_Cash_Level": 50_000,
                "Cash_Demand_Next_Day": 1_000 + offset,
            })
    return pd.DataFrame(rows).sort_values(["ATM_ID", "Date"]).reset_index(drop=True)


def test_features_include_lags_and_only_declared_model_inputs():
    frame = history()
    features = build_features(frame)
    atm_rows = features.loc[frame["ATM_ID"] == "ATM001"].reset_index(drop=True)
    assert list(features.columns) == FEATURES
    assert atm_rows.loc[7, "withdrawals_lag_1"] == 700
    assert atm_rows.loc[7, "withdrawals_lag_7"] == 100
    assert atm_rows.loc[7, "withdrawals_rolling_7"] == 400
    assert "Cash_Demand_Next_Day" not in features.columns


def test_model_split_is_chronological_before_may_first_2025():
    assert TEST_START == pd.Timestamp("2025-05-01")
    rows = history(10)
    dates = pd.to_datetime(rows["Date"])
    train = rows[dates < TEST_START]
    test = rows[dates >= TEST_START]
    assert not train.empty and not test.empty
    assert pd.Timestamp(train["Date"].max()) < TEST_START <= pd.Timestamp(test["Date"].min())


def test_simulation_replays_daily_cash_balance_and_policy_refills():
    rows = pd.DataFrame([
        {"ATM_ID": "ATM001", "Date": "2025-05-01", "ATM_Capacity": 100, "Total_Current_Cash": 20, "forecast": 40, "Cash_Demand_Next_Day": 30, "Total_deposite_Cash": 0},
        {"ATM_ID": "ATM001", "Date": "2025-05-02", "ATM_Capacity": 100, "Total_Current_Cash": 99, "forecast": 50, "Cash_Demand_Next_Day": 60, "Total_deposite_Cash": 0},
    ])
    fixed = replay_daily_policy(rows, forecast_driven=False)
    forecast_policy = replay_daily_policy(rows, forecast_driven=True)
    assert fixed == {"cashouts": 1, "refill_trips": 1}
    assert forecast_policy == {"cashouts": 0, "refill_trips": 2}


def test_replay_policy_counts_cashouts_and_refills():
    import pandas as pd
    from model.train import replay_daily_policy

    rows = pd.DataFrame({
        "ATM_ID": ["A"] * 3, "Date": pd.date_range("2025-05-01", periods=3),
        "ATM_Capacity": [1000.0] * 3, "Total_Current_Cash": [300.0] * 3, "Total_deposite_Cash": [0.0] * 3,
        "Cash_Demand_Next_Day": [350.0, 350.0, 350.0], "forecast": [350.0, 350.0, 350.0],
    })
    fixed = replay_daily_policy(rows, forecast_driven=False)
    forecast = replay_daily_policy(rows, forecast_driven=True)
    assert fixed["cashouts"] == 1            # 300 is above the 25% trigger but below the 350 demand
    assert forecast["cashouts"] == 0         # 300 < 1.2 * 350 + 50, so it refills first
    assert forecast["refill_trips"] >= 1
