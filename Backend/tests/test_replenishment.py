import pytest

from Backend.cashcast import _replenishment_item


def atm(cash, forecast, capacity=1_000):
    return {"ATM_ID": "ATM001", "Location": "Branch", "City": "Mumbai", "current_cash": cash, "forecast": forecast, "capacity": capacity}


def test_cash_above_safety_buffer_does_not_trigger_refill():
    result = _replenishment_item(atm(600, 100))
    assert result["refill_required"] is False
    assert result["recommended_refill"] == 0
    assert result["urgency"] == "LOW"


def test_replenishment_is_capped_by_physical_vault_space():
    result = _replenishment_item(atm(900, 800))
    assert result["refill_required"] is True
    assert result["recommended_refill"] == 100
    assert result["capacity_limited"] is True


def test_cashout_risk_is_critical_when_demand_exceeds_cash():
    result = _replenishment_item(atm(100, 200))
    assert result["urgency"] == "CRITICAL"
    assert result["expected_cash_remaining"] == -100
    assert result["days_of_cover"] == 0.5


@pytest.mark.parametrize("cash,forecast,capacity", [(0, 0, 0), (-1, 0, 100), (101, 0, 100)])
def test_source_data_invalid_vault_values_are_not_silently_used(cash, forecast, capacity):
    with pytest.raises((ValueError, ZeroDivisionError)):
        _replenishment_item(atm(cash, forecast, capacity))
