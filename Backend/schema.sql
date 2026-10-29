-- CashCast MySQL schema (MySQL 8). Executed idempotently at API start-up.
CREATE TABLE IF NOT EXISTS dispatches (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    atm_id VARCHAR(20) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    scheduled_by VARCHAR(120) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_dispatches_amount CHECK (amount >= 0),
    INDEX idx_dispatches_created (created_at),
    INDEX idx_dispatches_atm (atm_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS alert_acknowledgements (
    alert_id VARCHAR(20) NOT NULL PRIMARY KEY,
    acknowledged_by VARCHAR(120) NOT NULL,
    acknowledged_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS forecasts (
    atm_id VARCHAR(20) NOT NULL,
    forecast_date DATE NOT NULL,
    predicted_amount DECIMAL(15, 2) NOT NULL,
    cash_on_hand DECIMAL(15, 2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (atm_id, forecast_date)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4
