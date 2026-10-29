# What was fixed in this version

## Requirements
- **PostgreSQL replaced by MySQL 8** (your prerequisite list says MySQL): new `Backend/schema.sql`, `mysql-connector-python`, `docker-compose.yml` with `mysql:8.0`, ECS template and CI updated. Tested against a real MySQL 8.0 server.
- **Matplotlib** is now used in `model/report.py` (5 charts and a walk-forward validation).

## Bugs fixed
- **Sign-in showed "Your session has expired" for a wrong password** (the API client treated every 401 as an expired session). It now shows "Incorrect email, password, or selected role."
- **Forecast chart dates were one day early**: each row predicts the NEXT day. Dates now show the day being predicted, and tomorrow's forecast is never mixed with a known value.
- `/health` also checks the database; `/dispatches` accepts a `limit`; dispatch requests are capped at 50 ATMs.
- CORS now allows only GET/POST, two headers and the origins in `CORS_ORIGINS`.

## Added
- `Notebook/Model_training.ipynb`: step-by-step training, evaluation, Random Forest comparison, feature importance, cash-out replay, and saving the model the API loads (already executed, no errors).
- `run_windows.bat` and `run_mac_linux.sh`: one-click setup and start. MySQL tables are now also created on the first request if MySQL was not ready at start-up.
- MySQL tables `forecasts` and `alert_acknowledgements` (besides `dispatches`), 5 real-MySQL tests, 6 UI end-to-end tests, a policy-replay test, `pytest.ini`, `requirements-dev.txt`, `make_env.py`, `.env.example`, non-root API container with health check, GitHub Actions CI.

## Removed
- `.env` with a real MySQL root password (not included; **change that password anywhere it is used**)
- `ML Model/atm_cash_demand_model.joblib` (22 MB old model, rewritten by `train.py` on every run) and the code that wrote it. The notebook that lived in that folder was **not** useless: it is back as `Notebook/Model_training.ipynb`, now a full 12-step notebook connected to the API's model code.
- `Frontend/README.md` text about PostgreSQL (rewritten), the notebook's hard-coded `D:\` path (relative path now), `Data_analysis.pynb.ipynb` renamed to `Data_analysis.ipynb`
