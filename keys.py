"""Reads Alpaca keys from environment variables or a local .env file."""
import os
from pathlib import Path


def _load_dotenv():
    env = Path(__file__).with_name(".env")
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def alpaca_keys():
    _load_dotenv()
    key, secret = os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY")
    if not key or not secret:
        raise SystemExit(
            "Missing Alpaca keys. Copy .env.example to .env and paste your PAPER keys "
            "from https://app.alpaca.markets (Paper Trading > API Keys)."
        )
    return key, secret
