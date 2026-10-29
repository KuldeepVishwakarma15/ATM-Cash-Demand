#!/usr/bin/env bash
# CashCast: first-time setup and start (macOS / Linux). Stop with Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")"

command -v python3 >/dev/null || { echo "Python 3.11+ is required."; exit 1; }
command -v node >/dev/null || { echo "Node.js 22 is required."; exit 1; }

[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
echo "Installing Python packages (first run takes a few minutes)..."
python -m pip install -q -r Backend/requirements-dev.txt

[ -f .env ] || python make_env.py
[ -f model/cashcast_model.joblib ] || { echo "Training the forecast model..."; python model/train.py > /dev/null; }

if command -v docker >/dev/null 2>&1; then
  echo "Starting MySQL in Docker..."
  docker compose up -d mysql
else
  echo "Docker not found: the dashboard works, but Dispatch and alert acknowledgements need MySQL (see README)."
fi

[ -d Frontend/node_modules ] || (cd Frontend && npm ci)

python -m uvicorn Backend.main:app --port 8000 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT
(cd Frontend && npm run dev -- --host 127.0.0.1) &
sleep 10
echo
echo "Open http://127.0.0.1:5173  and sign in with ops@bankmuscat.demo / demo123 (role: Cash Ops Officer)."
wait
