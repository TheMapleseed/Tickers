#!/usr/bin/env python3
"""Refresh readme.md with Alpaca Trading API active US equity symbols.

Uses GET /v2/assets (see https://docs.alpaca.markets/reference/get-v2-assets-1).

Environment (first match wins for each):
  Key: APCA_API_KEY_ID, ALPACA_API_KEY_ID, ALPACA_API_KEY
  Secret: APCA_API_SECRET_KEY, ALPACA_API_SECRET_KEY, ALPACA_SECRET_KEY
  Base URL (optional): ALPACA_API_URL, ALPACA_API_BASE_URL, APCA_API_BASE_URL,
    ALPACA_BASE_URL — default https://api.alpaca.markets (paper: https://paper-api.alpaca.markets)

Example:
  ALPACA_API_KEY=... ALPACA_SECRET_KEY=... ALPACA_API_URL=https://paper-api.alpaca.markets \\
    python3 fetch_alpaca_tickers.py

Each successful run appends one line to alpaca_tickers_fetch.log (next to this script)
with UTC time, symbol count, output file, and API base URL. Latest line = last update.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


def _append_fetch_log(log_path: str, line: str) -> None:
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)
        if not line.endswith("\n"):
            f.write("\n")


def main() -> int:
    key = (
        os.environ.get("APCA_API_KEY_ID")
        or os.environ.get("ALPACA_API_KEY_ID")
        or os.environ.get("ALPACA_API_KEY")
    )
    secret = (
        os.environ.get("APCA_API_SECRET_KEY")
        or os.environ.get("ALPACA_API_SECRET_KEY")
        or os.environ.get("ALPACA_SECRET_KEY")
    )
    base = (
        os.environ.get("ALPACA_API_URL")
        or os.environ.get("ALPACA_API_BASE_URL")
        or os.environ.get("APCA_API_BASE_URL")
        or os.environ.get("ALPACA_BASE_URL")
        or "https://api.alpaca.markets"
    ).rstrip("/")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(script_dir, "alpaca_tickers_fetch.log")

    if not key or not secret:
        print(
            "Missing Alpaca credentials: set APCA_API_KEY_ID + APCA_API_SECRET_KEY, "
            "or ALPACA_API_KEY_ID + ALPACA_API_SECRET_KEY, "
            "or ALPACA_API_KEY + ALPACA_SECRET_KEY.",
            file=sys.stderr,
        )
        return 1

    params = urllib.parse.urlencode(
        {
            "status": "active",
            "asset_class": "us_equity",
        }
    )
    url = f"{base}/v2/assets?{params}"

    req = urllib.request.Request(
        url,
        headers={
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        ts = datetime.now(timezone.utc).isoformat()
        _append_fetch_log(
            log_path,
            f"{ts}\tFAIL\thttp_status={e.code}\tapi={base}\n",
        )
        return 1

    assets = json.loads(raw)
    tradable_only = "--all-active" not in sys.argv
    symbols: list[str] = []
    for a in assets:
        if not isinstance(a, dict):
            continue
        sym = a.get("symbol")
        if not sym:
            continue
        if tradable_only and not a.get("tradable"):
            continue
        symbols.append(sym)

    symbols = sorted(set(symbols))

    # Pretty multi-column lines similar to existing readme.md (4 symbols per chunk on a line).
    per_chunk = 8
    indent = "    "
    lines: list[str] = ["["]
    for i in range(0, len(symbols), per_chunk):
        chunk = symbols[i : i + per_chunk]
        inner = ", ".join(json.dumps(s) for s in chunk)
        comma = "," if i + per_chunk < len(symbols) else ""
        lines.append(f"{indent}{inner}{comma}")
    lines.append("]")
    out = "\n".join(lines) + "\n"

    out_path = os.path.join(script_dir, "readme.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)

    ts = datetime.now(timezone.utc).isoformat()
    filt = "tradable" if tradable_only else "all_active"
    _append_fetch_log(
        log_path,
        f"{ts}\tOK\tsymbols={len(symbols)}\tout={os.path.basename(out_path)}\tapi={base}\tfilter={filt}\n",
    )

    print(f"Wrote {len(symbols)} symbols to {out_path}")
    print(f"Logged update at {ts} (UTC) -> {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
