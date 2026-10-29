from __future__ import annotations

import hashlib
import hmac
import json
import logging
import math
import os
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import joblib
import jwt
import pandas as pd
import mysql.connector
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

try:
    from model.features import FEATURES, build_features
except ImportError:
    from ..model.features import FEATURES, build_features

logger = logging.getLogger("cashcast")
ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = Path(os.getenv("CASHCAST_DATASET", ROOT / "Dataset" / "ATM_Cash_Demand.csv"))
MODEL_PATH = Path(os.getenv("CASHCAST_MODEL", ROOT / "model" / "cashcast_model.joblib"))
METRICS_PATH = Path(os.getenv("CASHCAST_METRICS", ROOT / "model" / "metrics.json"))
TOKEN_TTL_SECONDS = 8 * 60 * 60
ALLOWED_ROLES = {"Admin", "Cash Ops Officer", "Viewer"}
DEMO_ACCOUNTS = {
    "admin@bankmuscat.demo": "Admin",
    "ops@bankmuscat.demo": "Cash Ops Officer",
    "viewer@bankmuscat.demo": "Viewer",
}

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    JWT_SECRET = secrets.token_urlsafe(48)
    logger.warning("JWT_SECRET is not set; using a random process-local secret. Set JWT_SECRET in .env for stable sessions.")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
router = APIRouter()
_auth_lock = threading.Lock()
_password_hashes: dict[str, tuple[bytes, bytes]] = {}
_failed_logins: dict[str, tuple[int, float]] = {}
_runtime_model: Any = None
_runtime_data: pd.DataFrame | None = None
_runtime_features: pd.DataFrame | None = None
_runtime_predictions: pd.Series | None = None
_runtime_error: str | None = None
_acked_in_memory: set[str] = set()
SQLITE_PATH = Path(os.getenv("CASHCAST_SQLITE_PATH", ROOT / "data" / "cashcast.sqlite3"))
COVER_RISK_DAYS = 3.0
CRITICAL_COVER_DAYS = 1.5


def initialize_auth() -> None:
    """Derive demo password hashes once for this process."""
    if _password_hashes:
        return
    password = os.getenv("CASHCAST_DEMO_PASSWORD", "demo123").encode("utf-8")
    with _auth_lock:
        if _password_hashes:
            return
        for email in DEMO_ACCOUNTS:
            salt = secrets.token_bytes(16)
            digest = hashlib.pbkdf2_hmac("sha256", password, salt, 310_000)
            _password_hashes[email] = (salt, digest)


def _verify_password(email: str, password: str) -> bool:
    stored = _password_hashes.get(email)
    if stored is None:
        # Keep unknown-user comparisons close to the same cost.
        hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), b"cashcast-unknown", 310_000)
        return False
    salt, expected = stored
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return hmac.compare_digest(actual, expected)


def initialize_runtime() -> None:
    global _runtime_model, _runtime_data, _runtime_features, _runtime_predictions, _runtime_error
    try:
        if not DATASET_PATH.is_file():
            raise FileNotFoundError(f"Dataset file not found: {DATASET_PATH}")
        frame = pd.read_csv(DATASET_PATH, parse_dates=["Date"])
        required = {"ATM_ID", "Date", "ATM_Capacity", "Total_Current_Cash", "Cash_Demand_Next_Day"}
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")
        frame = frame.sort_values(["ATM_ID", "Date"]).reset_index(drop=True)
        if not MODEL_PATH.is_file():
            raise FileNotFoundError(f"Trained model not found: {MODEL_PATH}; run python model/train.py")
        estimator = joblib.load(MODEL_PATH)
        features = build_features(frame)
        predictions = pd.Series(
            estimator.predict(features[FEATURES]),
            index=frame.index,
            dtype="float64",
        ).clip(lower=0)
        _runtime_data = frame
        _runtime_features = features
        _runtime_predictions = predictions
        _runtime_model = estimator
        _runtime_error = None
        logger.info("Loaded %d dataset rows and the HistGradientBoosting forecast model.", len(frame))
    except Exception as exc:
        _runtime_model = None
        _runtime_data = None
        _runtime_features = None
        _runtime_predictions = None
        _runtime_error = str(exc)
        logger.exception("CashCast model/data initialization failed")


def get_model():
    return _runtime_model


def get_data():
    return _runtime_data


def database_settings() -> dict[str, Any]:
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "database": os.getenv("MYSQL_DATABASE", "cashcast"),
        "user": os.getenv("MYSQL_USER", "cashcast"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "connection_timeout": int(os.getenv("MYSQL_CONNECT_TIMEOUT", "3")),
    }


_schema_ready = False


@contextmanager
def _db():
    """Yield a dict cursor; commit on success, roll back on any error, always close.

    The first successful connection also creates the tables and stores tomorrow's forecasts, so the
    API still works when MySQL was not ready at start-up (for example while its container boots).
    """
    global _schema_ready
    settings = database_settings()
    if not settings["password"]:
        raise RuntimeError("MYSQL_PASSWORD is not configured")
    connection = mysql.connector.connect(**settings, charset="utf8mb4", use_pure=True)
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            if not _schema_ready:
                _prepare(cursor)
                _schema_ready = True
            yield cursor
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
    finally:
        connection.close()


SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _prepare(cursor) -> None:
    """Create the MySQL tables (idempotent) and upsert tomorrow's forecast for every ATM."""
    for statement in (part.strip() for part in SCHEMA_PATH.read_text(encoding="utf-8").split(";")):
        if statement:
            cursor.execute(statement)
    try:
        items = _forecast_items()
    except HTTPException:
        return  # model or dataset not loaded yet; forecasts are stored on the next start
    cursor.executemany(
        """INSERT INTO forecasts (atm_id, forecast_date, predicted_amount, cash_on_hand)
           VALUES (%s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE predicted_amount = VALUES(predicted_amount), cash_on_hand = VALUES(cash_on_hand), created_at = CURRENT_TIMESTAMP""",
        [(item["ATM_ID"], item["forecast_date"], round(item["forecast"], 2), round(item["current_cash"], 2)) for item in items],
    )


def initialize_database() -> None:
    """Called at start-up: connect, create the tables and store tomorrow's forecasts."""
    global _schema_ready
    _schema_ready = False
    try:
        with _db():
            pass
        logger.info("Using MySQL persistence.")
    except Exception as exc:
        logger.warning("MySQL is unavailable; using local SQLite persistence: %s", exc)
        _ensure_sqlite()


def _ensure_sqlite() -> None:
    """Create the local persistence store used when MySQL is unavailable."""
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(SQLITE_PATH) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS dispatches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                atm_id TEXT NOT NULL,
                amount REAL NOT NULL,
                scheduled_by TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'scheduled',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS alert_acknowledgements (
                alert_id TEXT PRIMARY KEY,
                acknowledged_by TEXT NOT NULL,
                acknowledged_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def _sqlite_rows(query: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    _ensure_sqlite()
    with sqlite3.connect(SQLITE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(query, parameters).fetchall()]


def database_is_up() -> bool:
    try:
        with _db() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchall()
        return True
    except Exception:
        try:
            _ensure_sqlite()
            return True
        except Exception:
            return False


def _require_runtime() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, Any]:
    if _runtime_data is None or _runtime_features is None or _runtime_predictions is None or _runtime_model is None:
        initialize_runtime()
    if _runtime_data is None or _runtime_features is None or _runtime_predictions is None or _runtime_model is None:
        raise HTTPException(status_code=503, detail=f"Model or dataset unavailable: {_runtime_error or 'initialization failed'}")
    return _runtime_data, _runtime_features, _runtime_predictions, _runtime_model


def _latest_records() -> list[tuple[int, pd.Series]]:
    frame, _, _, _ = _require_runtime()
    indexes = frame.groupby("ATM_ID", sort=True)["Date"].idxmax().tolist()
    return [(int(index), frame.loc[index]) for index in indexes]


def _forecast_items() -> list[dict[str, Any]]:
    frame, _, predictions, _ = _require_runtime()
    output = []
    for index, row in _latest_records():
        amount = float(predictions.loc[index])
        cash = float(row["Total_Current_Cash"])
        capacity = float(row["ATM_Capacity"])
        output.append({
            "ATM_ID": str(row["ATM_ID"]),
            "Location": str(row["Location"]),
            "City": str(row["City"]),
            "forecast": amount,
            "current_cash": cash,
            "capacity": capacity,
            "cash_level_percent": round(cash / capacity * 100, 2) if capacity > 0 else None,
            "last_record_date": pd.Timestamp(row["Date"]).date().isoformat(),
            "forecast_date": (pd.Timestamp(row["Date"]) + pd.Timedelta(days=1)).date().isoformat(),
        })
    return output


def _replenishment_item(atm: dict[str, Any], forecast: float | None = None) -> dict[str, Any]:
    cash = float(atm["current_cash"])
    capacity = float(atm["capacity"])
    demand = max(0.0, float(atm["forecast"] if forecast is None else forecast))
    if not all(math.isfinite(value) for value in (cash, capacity, demand)) or capacity <= 0 or cash < 0 or cash > capacity:
        raise ValueError("ATM capacity and cash values must be finite and within the vault capacity.")
    expected = cash - demand
    target = capacity * 0.85
    days_of_cover = cash / demand if demand > 0 else None
    required = days_of_cover is not None and days_of_cover < COVER_RISK_DAYS
    refill_target = max(0.0, target - expected) if required else 0.0
    refill = round(min(refill_target, max(0.0, capacity - cash)), 2)
    if days_of_cover is not None and days_of_cover < CRITICAL_COVER_DAYS:
        urgency, label = "CRITICAL", "Stockout Risk Imminent"
    elif days_of_cover is not None and days_of_cover < COVER_RISK_DAYS:
        urgency, label = "HIGH", "Urgent Refill Required"
    else:
        urgency, label = "LOW", "Optimal Cash Vault"
    return {
        **atm,
        "forecast": demand,
        "expected_cash_remaining": round(expected, 2),
        "days_of_cover": round(days_of_cover, 2) if days_of_cover is not None else None,
        "risk_level": urgency,
        "at_risk": required,
        "critical_risk": urgency == "CRITICAL",
        "refill_required": required,
        "recommended_refill": refill,
        "capacity_limited": refill_target > max(0.0, capacity - cash),
        "urgency": urgency,
        "status": label,
    }


def _user_role(user: dict[str, Any], roles: set[str]) -> None:
    if user.get("role") not in roles:
        raise HTTPException(status_code=403, detail="Your role cannot perform this action.")


async def current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        subject = str(payload["sub"])
        role = str(payload["role"])
        if subject not in DEMO_ACCOUNTS or role not in ALLOWED_ROLES or DEMO_ACCOUNTS[subject] != role:
            raise credentials_error
        return {"email": subject, "role": role}
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise credentials_error


@router.post("/auth/login", tags=["Authentication"])
def login(request: Request, form: OAuth2PasswordRequestForm = Depends()):
    initialize_auth()
    username = form.username.strip().lower()
    # OAuth2PasswordRequestForm exposes the space-delimited `scope` field as
    # `scopes`; joining it preserves this app's multi-word role names.
    role = " ".join(form.scopes).strip()
    remote = request.client.host if request and request.client else "unknown"
    lock_key = f"{remote}:{username}"
    now = time.monotonic()
    with _auth_lock:
        failed, until = _failed_logins.get(lock_key, (0, 0.0))
        if until > now:
            raise HTTPException(status_code=429, detail="Too many failed sign-in attempts. Try again after 10 seconds.")
        if until:
            _failed_logins.pop(lock_key, None)
    valid_role = role in ALLOWED_ROLES and DEMO_ACCOUNTS.get(username) == role
    valid_password = _verify_password(username, form.password)
    if not (valid_role and valid_password):
        with _auth_lock:
            failures, _ = _failed_logins.get(lock_key, (0, 0.0))
            failures += 1
            if failures >= 3:
                _failed_logins[lock_key] = (failures, now + 10)
                raise HTTPException(status_code=429, detail="Too many failed sign-in attempts. Try again after 10 seconds.")
            _failed_logins[lock_key] = (failures, 0.0)
        raise HTTPException(status_code=401, detail="Incorrect email, password, or selected role.", headers={"WWW-Authenticate": "Bearer"})
    with _auth_lock:
        _failed_logins.pop(lock_key, None)
    issued_at = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": username, "role": role, "iat": issued_at, "exp": issued_at + timedelta(seconds=TOKEN_TTL_SECONDS)},
        JWT_SECRET,
        algorithm="HS256",
    )
    return {"access_token": token, "token_type": "bearer", "role": role, "email": username, "expires_in": TOKEN_TTL_SECONDS}


@router.get("/metrics", tags=["Dashboard"], dependencies=[Depends(current_user)])
def metrics():
    frame, _, _, _ = _require_runtime()
    if not METRICS_PATH.is_file():
        raise HTTPException(status_code=503, detail="Model evaluation metrics are unavailable; run model/train.py.")
    report = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    latest = frame.groupby("ATM_ID", sort=True).tail(1)
    return {
        "atm_count": int(frame["ATM_ID"].nunique()),
        "record_count": int(len(frame)),
        "data_start": pd.Timestamp(frame["Date"].min()).date().isoformat(),
        "data_end": pd.Timestamp(frame["Date"].max()).date().isoformat(),
        "currency": "INR",
        "accuracy_percent": report.get("accuracy_percent"),
        "mape_percent": report.get("mape_percent"),
        "mae": report.get("mae"),
        "r2": report.get("r2"),
        "baseline_mape_percent": report.get("baseline_mape_percent"),
        "atm_accuracy": report.get("atm_accuracy", {}),
        "cashout_reduction_percent": report.get("backtest", {}).get("cashout_reduction_percent"),
        "backtest": report.get("backtest"),
        "cash_on_hand": float(latest["Total_Current_Cash"].sum()),
        "capacity": float(latest["ATM_Capacity"].sum()),
        "source": "historical simulation",
        "simulation": True,
    }


@router.get("/atms", tags=["ATMs"], dependencies=[Depends(current_user)])
def atms():
    items = [_replenishment_item(item) for item in _forecast_items()]
    return {"items": items, "count": len(items), "source": "historical simulation", "currency": "INR"}


@router.get("/forecast/{atm_id}", tags=["Forecast"], dependencies=[Depends(current_user)])
def forecast(atm_id: str):
    frame, _, predictions, _ = _require_runtime()
    if atm_id.lower() == "network":
        selected = frame.copy()
        selected["predicted"] = predictions
        selected["actual"] = selected["Cash_Demand_Next_Day"]
        # The final row's "next day" is the forecast day itself, so it is not treated as known.
        selected = selected[selected["Date"] < selected["Date"].max()]
        selected["Date"] = selected["Date"] + pd.Timedelta(days=1)  # row d predicts demand on d+1
        grouped = selected.groupby("Date", sort=True)[["actual", "predicted"]].sum().tail(30)
        latest_forecasts = _forecast_items()
        result = [
            {"date": pd.Timestamp(day).date().isoformat(), "actual": float(row.actual), "predicted": float(row.predicted)}
            for day, row in grouped.iterrows()
        ]
        latest = latest_forecasts[0] if latest_forecasts else None
        if latest:
            result.append({"date": latest["forecast_date"], "actual": None, "predicted": sum(item["forecast"] for item in latest_forecasts), "tomorrow": True})
        return {
            "ATM_ID": "network",
            "items": result,
            "forecast": sum(item["forecast"] for item in latest_forecasts),
            "forecast_date": latest_forecasts[0]["forecast_date"] if latest_forecasts else None,
            "source": "historical simulation",
            "simulation": True,
            "currency": "INR",
        }
    rows = frame.loc[frame["ATM_ID"].astype(str) == atm_id].copy()
    if rows.empty:
        raise HTTPException(status_code=404, detail=f"ATM {atm_id} was not found in the dataset.")
    rows["predicted"] = predictions.loc[rows.index]
    latest = rows.iloc[-1]
    return {
        "ATM_ID": atm_id,
        "Location": str(latest["Location"]),
        "City": str(latest["City"]),
        "items": [
            {"date": pd.Timestamp(row.Date).date().isoformat(), "actual": float(row.Cash_Demand_Next_Day), "predicted": float(row.predicted)}
            for row in rows.iloc[-31:-1].assign(Date=lambda frame: frame["Date"] + pd.Timedelta(days=1)).itertuples()
        ] + [{"date": (pd.Timestamp(latest["Date"]) + pd.Timedelta(days=1)).date().isoformat(), "actual": None, "predicted": float(rows["predicted"].iloc[-1]), "tomorrow": True}],
        "forecast": float(rows["predicted"].iloc[-1]),
        "forecast_date": (pd.Timestamp(latest["Date"]) + pd.Timedelta(days=1)).date().isoformat(),
        "source": "historical simulation",
        "simulation": True,
        "currency": "INR",
    }


@router.get("/whatif", tags=["Forecast"], dependencies=[Depends(current_user)])
def whatif(
    festival: bool = Query(default=False),
    holiday: bool = Query(default=False),
    adjust: float = Query(default=0, ge=-100, le=200),
):
    frame, features, _, estimator = _require_runtime()
    items = []
    for index, row in _latest_records():
        sample = features.loc[[index], FEATURES].copy()
        if "next_day_festival" in sample:
            sample.loc[:, "next_day_festival"] = int(festival)
        if "next_day_holiday" in sample:
            sample.loc[:, "next_day_holiday"] = int(holiday)
        raw = max(0.0, float(estimator.predict(sample)[0]))
        adjusted = max(0.0, raw * (1 + adjust / 100))
        atm = {
            "ATM_ID": str(row["ATM_ID"]), "Location": str(row["Location"]), "City": str(row["City"]),
            "current_cash": float(row["Total_Current_Cash"]), "capacity": float(row["ATM_Capacity"]),
            "base_forecast": raw, "forecast": adjusted,
        }
        items.append(_replenishment_item(atm, adjusted))
    return {
        "items": items,
        "assumptions": {"festival": festival, "holiday": holiday, "adjust_percent": adjust},
        "source": "model scenario simulation",
        "simulation": True,
        "currency": "INR",
    }


@router.get("/replenishment", tags=["Replenishment"], dependencies=[Depends(current_user)])
def replenishment():
    items = [_replenishment_item(item) for item in _forecast_items()]
    items.sort(key=lambda item: (item["refill_required"] is False, item["days_of_cover"] if item["days_of_cover"] is not None else float("inf")))
    return {
        "items": items,
        "total_atms": len(items),
        "refill_required_count": sum(item["refill_required"] for item in items),
        "total_recommended_refill_amount": sum(item["recommended_refill"] for item in items),
        "source": "historical simulation",
        "simulation": True,
        "currency": "INR",
    }


@router.get("/alerts", tags=["Alerts"], dependencies=[Depends(current_user)])
def alerts():
    items = [item for item in replenishment()["items"] if item["refill_required"]]
    try:
        with _db() as cursor:
            cursor.execute("SELECT alert_id FROM alert_acknowledgements")
            acknowledged = {row["alert_id"] for row in cursor.fetchall()}
    except Exception as exc:
        logger.warning("Unable to read alert acknowledgement state from MySQL: %s", exc)
        try:
            acknowledged = {row["alert_id"] for row in _sqlite_rows("SELECT alert_id FROM alert_acknowledgements")}
        except Exception:
            acknowledged = set(_acked_in_memory)
    for item in items:
        item["id"] = item["ATM_ID"]
        item["acknowledged"] = item["id"] in acknowledged
    return {"items": items, "count": len(items), "source": "historical simulation", "simulation": True}


@router.post("/alerts/{alert_id}/acknowledge", tags=["Alerts"], dependencies=[Depends(current_user)])
def acknowledge_alert(alert_id: str, user: dict[str, Any] = Depends(current_user)):
    known = {item["ATM_ID"] for item in replenishment()["items"] if item["refill_required"]}
    if alert_id not in known:
        raise HTTPException(status_code=404, detail="Active alert was not found.")
    try:
        with _db() as cursor:
            cursor.execute(
                """INSERT INTO alert_acknowledgements (alert_id, acknowledged_by)
                   VALUES (%s, %s)
                   ON DUPLICATE KEY UPDATE acknowledged_by = VALUES(acknowledged_by), acknowledged_at = CURRENT_TIMESTAMP""",
                (alert_id, user["email"]),
            )
    except Exception as exc:
        logger.warning("Saving alert acknowledgement to local SQLite: %s", exc)
        try:
            _ensure_sqlite()
            with sqlite3.connect(SQLITE_PATH) as connection:
                connection.execute(
                    "INSERT INTO alert_acknowledgements (alert_id, acknowledged_by) VALUES (?, ?) "
                    "ON CONFLICT(alert_id) DO UPDATE SET acknowledged_by = excluded.acknowledged_by, acknowledged_at = CURRENT_TIMESTAMP",
                    (alert_id, user["email"]),
                )
        except Exception as sqlite_exc:
            raise HTTPException(status_code=503, detail="Alert acknowledgement could not be saved.") from sqlite_exc
    _acked_in_memory.add(alert_id)
    return {"alert_id": alert_id, "acknowledged": True, "acknowledged_by": user["email"]}


class DispatchRequest(BaseModel):
    atm_ids: list[str] = Field(min_length=1, max_length=50)


@router.post("/dispatch", tags=["Replenishment"])
def dispatch(payload: DispatchRequest, user: dict[str, Any] = Depends(current_user)):
    _user_role(user, {"Admin", "Cash Ops Officer"})
    # Only use dataset ATM ids and model-derived refill amounts in the persisted plan.
    eligible = {item["ATM_ID"]: item for item in [_replenishment_item(row) for row in _forecast_items()]}
    unique_ids = list(dict.fromkeys(payload.atm_ids))
    unknown = [atm_id for atm_id in unique_ids if atm_id not in eligible]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown ATM IDs: {', '.join(unknown)}")
    try:
        saved = []
        with _db() as cursor:
            for atm_id in unique_ids:
                amount = eligible[atm_id]["recommended_refill"]
                cursor.execute(
                    "INSERT INTO dispatches (atm_id, amount, scheduled_by) VALUES (%s, %s, %s)",
                    (atm_id, amount, user["email"]),
                )
                cursor.execute(
                    "SELECT id, atm_id, amount, scheduled_by, status, created_at FROM dispatches WHERE id = %s",
                    (cursor.lastrowid,),
                )
                saved.append(_dispatch_row(cursor.fetchone()))
    except Exception as exc:
        logger.warning("Saving dispatch records to local SQLite: %s", exc)
        try:
            _ensure_sqlite()
            with sqlite3.connect(SQLITE_PATH) as connection:
                for atm_id in unique_ids:
                    amount = eligible[atm_id]["recommended_refill"]
                    cursor = connection.execute(
                        "INSERT INTO dispatches (atm_id, amount, scheduled_by) VALUES (?, ?, ?)",
                        (atm_id, amount, user["email"]),
                    )
                    row = _sqlite_rows(
                        "SELECT id, atm_id, amount, scheduled_by, status, created_at FROM dispatches WHERE id = ?",
                        (cursor.lastrowid,),
                    )[0]
                    saved.append(_dispatch_row(row))
        except Exception as sqlite_exc:
            raise HTTPException(status_code=503, detail="Dispatch could not be saved.") from sqlite_exc
        return {"items": saved, "count": len(saved), "simulation": True, "source": "sqlite-fallback"}
    return {"items": saved, "count": len(saved), "simulation": True, "source": "mysql"}


def _dispatch_row(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["amount"] = float(item["amount"])
    if isinstance(item.get("created_at"), (date, datetime)):
        item["created_at"] = item["created_at"].isoformat()
    return item


@router.get("/dispatches", tags=["Replenishment"], dependencies=[Depends(current_user)])
def dispatches(limit: int = Query(default=100, ge=1, le=500)):
    try:
        with _db() as cursor:
            cursor.execute(
                "SELECT id, atm_id, amount, scheduled_by, status, created_at FROM dispatches ORDER BY created_at DESC, id DESC LIMIT %s",
                (limit,),
            )
            items = [_dispatch_row(row) for row in cursor.fetchall()]
        return {"items": items, "count": len(items), "source": "mysql", "simulation": True, "currency": "INR"}
    except Exception as exc:
        logger.warning("Reading dispatch history from local SQLite: %s", exc)
        try:
            rows = _sqlite_rows(
                "SELECT id, atm_id, amount, scheduled_by, status, created_at FROM dispatches "
                "ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            )
            return {"items": [_dispatch_row(row) for row in rows], "count": len(rows), "source": "sqlite-fallback", "simulation": True, "currency": "INR"}
        except Exception as sqlite_exc:
            raise HTTPException(status_code=503, detail="Dispatch history could not be loaded.") from sqlite_exc
