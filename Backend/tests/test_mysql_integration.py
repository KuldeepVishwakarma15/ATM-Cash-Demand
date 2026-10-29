"""Runs against a REAL MySQL server. Skipped unless MYSQL_PASSWORD (and a reachable server) is configured."""
import os

import pytest

from Backend import cashcast

pytestmark = pytest.mark.skipif(not os.getenv("MYSQL_PASSWORD"), reason="MYSQL_* variables are not configured")


@pytest.fixture(scope="module", autouse=True)
def schema():
    cashcast.initialize_runtime()
    cashcast.initialize_database()
    with cashcast._db() as cursor:
        cursor.execute("DELETE FROM dispatches WHERE scheduled_by = 'pytest@bankmuscat.demo'")
        cursor.execute("DELETE FROM alert_acknowledgements WHERE acknowledged_by = 'pytest@bankmuscat.demo'")


def test_schema_creates_all_tables():
    with cashcast._db() as cursor:
        cursor.execute("SHOW TABLES")
        tables = {next(iter(row.values())) for row in cursor.fetchall()}
    assert {"dispatches", "alert_acknowledgements", "forecasts"} <= tables


def test_initialize_database_is_idempotent_and_stores_forecasts():
    cashcast.initialize_database()
    cashcast.initialize_database()
    with cashcast._db() as cursor:
        cursor.execute("SELECT COUNT(*) AS n, MIN(predicted_amount) AS low FROM forecasts WHERE forecast_date = (SELECT MAX(forecast_date) FROM forecasts)")
        row = cursor.fetchone()
    assert row["n"] == 10 and float(row["low"]) > 0


def test_dispatch_round_trip_with_decimal_amount_and_rollback():
    with cashcast._db() as cursor:
        cursor.execute("INSERT INTO dispatches (atm_id, amount, scheduled_by) VALUES (%s, %s, %s)", ("ATM001", 123456.78, "pytest@bankmuscat.demo"))
        new_id = cursor.lastrowid
    with cashcast._db() as cursor:
        cursor.execute("SELECT amount, status FROM dispatches WHERE id = %s", (new_id,))
        row = cursor.fetchone()
    assert float(row["amount"]) == 123456.78 and row["status"] == "scheduled"
    with pytest.raises(RuntimeError):
        with cashcast._db() as cursor:
            cursor.execute("INSERT INTO dispatches (atm_id, amount, scheduled_by) VALUES ('ATM002', 5, 'pytest@bankmuscat.demo')")
            raise RuntimeError("force a rollback")
    with cashcast._db() as cursor:
        cursor.execute("SELECT COUNT(*) AS n FROM dispatches WHERE atm_id = 'ATM002' AND scheduled_by = 'pytest@bankmuscat.demo'")
        assert cursor.fetchone()["n"] == 0


def test_negative_amount_is_rejected_by_check_constraint():
    with pytest.raises(Exception):
        with cashcast._db() as cursor:
            cursor.execute("INSERT INTO dispatches (atm_id, amount, scheduled_by) VALUES ('ATM001', -1, 'pytest@bankmuscat.demo')")


def test_acknowledgement_upsert_keeps_one_row():
    for _ in range(2):
        with cashcast._db() as cursor:
            cursor.execute(
                "INSERT INTO alert_acknowledgements (alert_id, acknowledged_by) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE acknowledged_by = VALUES(acknowledged_by)", ("ATM001", "pytest@bankmuscat.demo"))
    with cashcast._db() as cursor:
        cursor.execute("SELECT COUNT(*) AS n FROM alert_acknowledgements WHERE alert_id = 'ATM001'")
        assert cursor.fetchone()["n"] == 1


def test_tables_are_created_on_first_connection_even_if_startup_missed_it():
    """If MySQL was still booting at start-up, the first later request must create the tables itself."""
    with cashcast._db() as cursor:
        cursor.execute("DROP TABLE IF EXISTS forecasts")
    cashcast._schema_ready = False
    with cashcast._db() as cursor:
        cursor.execute("SELECT COUNT(*) AS n FROM forecasts")
        assert cursor.fetchone()["n"] == 10
