from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from Backend import cashcast, main
from model.features import build_features


class FakeModel:
    def predict(self, features):
        return np.full(len(features), 8_000.0)


class FakeMySQL:
    """In-memory stand-in for the MySQL cursor that Backend.cashcast._db() yields."""

    def __init__(self):
        self.dispatch_rows = []
        self.ack_rows = set()
        self.next_id = 1
        self.lastrowid = None
        self._one = None
        self._many = []

    def execute(self, query, params=None):
        query, params = " ".join(query.split()), params or ()
        if query.startswith("INSERT INTO dispatches"):
            row = {"id": self.next_id, "atm_id": params[0], "amount": params[1], "scheduled_by": params[2],
                   "status": "scheduled", "created_at": datetime(2025, 8, 22)}
            self.lastrowid = self.next_id
            self.next_id += 1
            self.dispatch_rows.append(row)
        elif query.startswith("SELECT id, atm_id") and "WHERE id" in query:
            self._one = next(row for row in self.dispatch_rows if row["id"] == params[0])
        elif query.startswith("SELECT id, atm_id"):
            self._many = list(reversed(self.dispatch_rows))[: params[0]]
        elif query.startswith("SELECT alert_id"):
            self._many = [{"alert_id": alert_id} for alert_id in self.ack_rows]
        elif query.startswith("INSERT INTO alert_acknowledgements"):
            self.ack_rows.add(params[0])

    def executemany(self, query, rows):
        pass

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._many


def sample_frame():
    rows = []
    start = date(2025, 4, 25)
    for atm_id, city in (("ATM001", "Mumbai"), ("ATM002", "Delhi")):
        for offset in range(10):
            current_day = start + timedelta(days=offset)
            rows.append({
                "ATM_ID": atm_id,
                "Date": current_day,
                "Day_of_week": current_day.strftime("%A"),
                "Location": "Branch",
                "City": city,
                "Day": current_day.day,
                "Month": current_day.month,
                "Year": current_day.year,
                "ATM_Capacity": 10_000.0,
                "Total_Current_Cash": 4_000.0,
                "Total_Withdraw_Cash": 1_000.0,
                "Total_deposite_Cash": 100.0,
                "No_of_Deposits": 2,
                "No_of_Withdraws": 8,
                "Temperature": 25.0,
                "Weather_Condition": "Sunny",
                "Holiday_Flag": int(current_day.weekday() == 6),
                "Festival_Flag": 0,
                "Previous_Day_Cash_Level": 5_000.0,
                "Cash_Demand_Next_Day": 1_200.0,
            })
    return pd.DataFrame(rows).sort_values(["ATM_ID", "Date"]).reset_index(drop=True)


@pytest.fixture
def client(monkeypatch, tmp_path):
    frame = sample_frame()
    features = build_features(frame)
    monkeypatch.setattr(cashcast, "_runtime_data", frame)
    monkeypatch.setattr(cashcast, "_runtime_features", features)
    monkeypatch.setattr(cashcast, "_runtime_predictions", pd.Series(np.full(len(frame), 8_000.0)))
    monkeypatch.setattr(cashcast, "_runtime_model", FakeModel())
    monkeypatch.setattr(cashcast, "_runtime_error", None)
    monkeypatch.setattr(cashcast, "initialize_runtime", lambda: None)
    monkeypatch.setattr(main, "initialize_runtime", lambda: None)
    monkeypatch.setattr(main, "initialize_database", lambda: None)
    monkeypatch.setattr(cashcast, "_password_hashes", {})
    monkeypatch.setattr(cashcast, "_failed_logins", {})
    monkeypatch.setattr(cashcast, "_acked_in_memory", set())
    fake_pg = FakeMySQL()

    @contextmanager
    def fake_db():
        yield fake_pg

    monkeypatch.setattr(cashcast, "_db", fake_db)
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(json.dumps({
        "test_start": "2025-05-01",
        "test_rows": 10,
        "mape_percent": 10.0,
        "accuracy_percent": 90.0,
        "mae": 50.0,
        "r2": 0.8,
        "baseline_mape_percent": 12.0,
        "atm_accuracy": {"ATM001": 90.0, "ATM002": 91.0},
        "backtest": {"simulation": True, "fixed_threshold": {"cashouts": 2}, "forecast_threshold": {"cashouts": 1}, "cashout_reduction_percent": 50.0},
    }), encoding="utf-8")
    monkeypatch.setattr(cashcast, "METRICS_PATH", metrics_path)
    with TestClient(main.app) as test_client:
        yield test_client, fake_pg


def auth(client, role="Cash Ops Officer", password="demo123", email=None):
    email = email or {"Admin": "admin@bankmuscat.demo", "Cash Ops Officer": "ops@bankmuscat.demo", "Viewer": "viewer@bankmuscat.demo"}[role]
    response = client.post("/auth/login", data={"username": email, "password": password, "scope": role})
    if response.status_code == 200:
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    return response


def test_login_issues_role_scoped_eight_hour_bearer_token(client):
    test_client, _ = client
    response = test_client.post("/auth/login", data={"username": "ops@bankmuscat.demo", "password": "demo123", "scope": "Cash Ops Officer"})
    assert response.status_code == 200
    assert response.json()["role"] == "Cash Ops Officer"
    assert response.json()["token_type"] == "bearer"
    assert response.json()["expires_in"] == 8 * 60 * 60


def test_login_rejects_wrong_role_or_password(client):
    test_client, _ = client
    response = test_client.post("/auth/login", data={"username": "viewer@bankmuscat.demo", "password": "demo123", "scope": "Admin"})
    assert response.status_code == 401


def test_three_failed_logins_lock_account_for_ten_seconds(client, monkeypatch):
    test_client, _ = client
    monkeypatch.setattr(cashcast.time, "monotonic", lambda: 100.0)
    data = {"username": "lockout-test@bankmuscat.demo", "password": "bad", "scope": "Viewer"}
    assert test_client.post("/auth/login", data=data).status_code == 401
    assert test_client.post("/auth/login", data=data).status_code == 401
    assert test_client.post("/auth/login", data=data).status_code == 429
    assert test_client.post("/auth/login", data=data).status_code == 429
    monkeypatch.setattr(cashcast.time, "monotonic", lambda: 111.0)
    good = {"username": "viewer@bankmuscat.demo", "password": "demo123", "scope": "Viewer"}
    assert test_client.post("/auth/login", data=good).status_code == 200


def test_every_read_route_requires_a_bearer_token(client):
    test_client, _ = client
    for path in ("/metrics", "/atms", "/forecast/network", "/forecast/ATM001", "/whatif", "/replenishment", "/alerts", "/dispatches"):
        assert test_client.get(path).status_code == 401, path


def test_metrics_atms_and_network_forecasts_are_dataset_backed(client):
    test_client, _ = client
    headers = auth(test_client)
    metrics = test_client.get("/metrics", headers=headers).json()
    atms = test_client.get("/atms", headers=headers).json()
    forecast = test_client.get("/forecast/network", headers=headers).json()
    assert metrics["atm_count"] == 2
    assert metrics["accuracy_percent"] == 90
    assert metrics["simulation"] is True
    assert {row["ATM_ID"] for row in atms["items"]} == {"ATM001", "ATM002"}
    assert forecast["items"][-1]["tomorrow"] is True
    assert forecast["items"][-1]["predicted"] > 0


def test_individual_forecast_and_unknown_atm(client):
    test_client, _ = client
    headers = auth(test_client)
    assert len(test_client.get("/forecast/ATM001", headers=headers).json()["items"]) == 10
    assert test_client.get("/forecast/ATM999", headers=headers).status_code == 404


def test_whatif_changes_model_input_and_returns_scenario_values(client):
    test_client, _ = client
    headers = auth(test_client)
    response = test_client.get("/whatif?festival=true&holiday=true&adjust=10", headers=headers)
    assert response.status_code == 200
    assert response.json()["assumptions"] == {"festival": True, "holiday": True, "adjust_percent": 10.0}
    assert response.json()["items"][0]["forecast"] == 8_800


def test_replenishment_alerts_and_acknowledgement_route(client):
    test_client, pg = client
    headers = auth(test_client)
    repl = test_client.get("/replenishment", headers=headers)
    assert repl.status_code == 200 and repl.json()["refill_required_count"] == 2
    alerts = test_client.get("/alerts", headers=headers).json()
    assert alerts["count"] == 2
    ack = test_client.post("/alerts/ATM001/acknowledge", headers=headers)
    assert ack.status_code == 200 and ack.json()["acknowledged"] is True
    assert "ATM001" in pg.ack_rows
    assert next(row for row in test_client.get("/alerts", headers=headers).json()["items"] if row["id"] == "ATM001")["acknowledged"]


def test_viewer_cannot_dispatch_and_operations_role_saves_dispatches(client):
    test_client, pg = client
    viewer_headers = auth(test_client, "Viewer")
    denied = test_client.post("/dispatch", headers=viewer_headers, json={"atm_ids": ["ATM001"]})
    assert denied.status_code == 403
    ops_headers = auth(test_client)
    saved = test_client.post("/dispatch", headers=ops_headers, json={"atm_ids": ["ATM001"]})
    assert saved.status_code == 200
    assert saved.json()["items"][0]["atm_id"] == "ATM001"
    assert len(pg.dispatch_rows) == 1
    listed = test_client.get("/dispatches", headers=ops_headers)
    assert listed.status_code == 200 and listed.json()["count"] == 1


def test_admin_can_dispatch_and_unknown_atm_is_rejected(client):
    test_client, _ = client
    headers = auth(test_client, "Admin")
    assert test_client.post("/dispatch", headers=headers, json={"atm_ids": ["ATM002"]}).status_code == 200
    assert test_client.post("/dispatch", headers=headers, json={"atm_ids": ["ATM404"]}).status_code == 422


def test_dispatch_requires_database_and_reports_failure(client, monkeypatch):
    test_client, _ = client
    headers = auth(test_client)
    def unavailable():
        raise RuntimeError("mysql unavailable")
    monkeypatch.setattr(cashcast, "_db", unavailable)
    response = test_client.post("/dispatch", headers=headers, json={"atm_ids": ["ATM001"]})
    assert response.status_code == 503


def test_forecast_dates_are_the_day_being_predicted(client):
    test_client, _ = client
    items = test_client.get("/forecast/ATM001", headers=auth(test_client)).json()["items"]
    dates = [row["date"] for row in items]
    assert dates == sorted(dates) and len(set(dates)) == len(dates)
    assert items[0]["date"] == "2025-04-26"          # first row (04-25) predicts 04-26
    assert items[-1]["tomorrow"] is True and items[-1]["actual"] is None
    assert items[-1]["date"] == "2025-05-05"        # the day after the last row (05-04)


def test_health_reports_model_and_database(client):
    test_client, _ = client
    body = test_client.get("/health").json()
    assert body["model_loaded"] and body["dataset_loaded"] and body["database"] == "up"


def test_dispatch_history_limit_and_validation(client):
    test_client, _ = client
    headers = auth(test_client)
    test_client.post("/dispatch", headers=headers, json={"atm_ids": ["ATM001", "ATM002"]})
    assert test_client.get("/dispatches?limit=1", headers=headers).json()["count"] == 1
    assert test_client.get("/dispatches?limit=0", headers=headers).status_code == 422
    assert test_client.post("/dispatch", headers=headers, json={"atm_ids": []}).status_code == 422
