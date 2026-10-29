"""Create a local .env with random secrets (does nothing if .env already exists)."""
import secrets
from pathlib import Path

root = Path(__file__).resolve().parent
target = root / ".env"
if target.exists():
    raise SystemExit(".env already exists; leaving it untouched.")
text = (root / ".env.example").read_text(encoding="utf-8")
for key, size in (("JWT_SECRET", 48), ("MYSQL_PASSWORD", 24), ("MYSQL_ROOT_PASSWORD", 24)):
    text = text.replace(f"{key}=\n", f"{key}={secrets.token_urlsafe(size)}\n")
target.write_text(text, encoding="utf-8")
print("Created .env with random JWT_SECRET, MYSQL_PASSWORD and MYSQL_ROOT_PASSWORD.")
