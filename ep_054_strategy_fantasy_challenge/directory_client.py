"""EP051 Strategy Directory public-data adapter.

Version history:
v1.1.0 · 2026-08-31 · Restricts selectable strategies to the current UTC trading date.
v1.0.0 · 2026-08-31 · Connects EP054 to EP051 catalogue and equity evidence.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class DirectoryUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class EvidencePoint:
    strategy_id: str
    equity: float
    net_return: float
    trade_number: int
    observed_at: str
    opened_at: str | None
    basis: str

    @property
    def evidence_ref(self) -> str:
        return f"{self.strategy_id}:{self.observed_at}:{self.trade_number}"


class StrategyDirectoryClient:
    def __init__(self, base_url: str | None = None, timeout: int = 30):
        self.base_url = (base_url or os.environ.get("STRATEGY_DIRECTORY_URL") or "https://ep051-directory.onrender.com").rstrip("/")
        self.timeout = timeout

    @staticmethod
    def current_trading_date() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def _current_period_query(self) -> dict:
        activity_date = self.current_trading_date()
        return {"date_from": activity_date, "date_to": activity_date}

    def _get(self, path: str, query: dict | None = None) -> dict:
        url = self.base_url + path
        if query:
            url += "?" + urlencode(query)
        try:
            request = Request(url, headers={"Accept": "application/json", "User-Agent": "EP054-Strategy-Challenge/1.0"})
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise DirectoryUnavailable(f"Strategy Directory unavailable: {exc}") from exc

    def catalogue(self, page_size: int = 100) -> dict:
        activity_date = self.current_trading_date()
        payload = self._get("/api/dna/strategies", {"page": 1, "page_size": page_size, "minimum_trades": 1, "sort": "strategy_id", "direction": "asc", **self._current_period_query()})
        items = payload.get("data", {}).get("items", [])
        if not items:
            raise DirectoryUnavailable(f"No EP051 strategies have traded on {activity_date}; entry is disabled until current-date evidence is available")
        return {
            "items": items,
            "as_of": payload["as_of"],
            "methodology_version": payload["methodology_version"],
            "basis": payload["basis"],
            "total": payload["data"]["total"],
            "activity_date": activity_date,
        }

    def strategy(self, strategy_id: str) -> dict:
        activity_date = self.current_trading_date()
        payload = self._get("/api/dna/strategies", {"page": 1, "page_size": 1, "minimum_trades": 1, "search": strategy_id, **self._current_period_query()})
        items = payload.get("data", {}).get("items", [])
        if len(items) != 1 or items[0].get("strategy_id") != strategy_id:
            raise DirectoryUnavailable(f"{strategy_id} has no EP051 trade evidence on {activity_date} and is not eligible for a new entry")
        return {"item": items[0], "as_of": payload["as_of"], "methodology_version": payload["methodology_version"], "basis": payload["basis"], "activity_date": activity_date}

    def evidence(self, strategy_id: str) -> EvidencePoint:
        payload = self._get(f"/api/dna/strategies/{strategy_id}/equity-curve")
        points = payload.get("points", [])
        if not points:
            raise DirectoryUnavailable(f"{strategy_id} has no closed-trade evidence")
        latest = points[-1]
        return EvidencePoint(
            strategy_id=strategy_id,
            equity=float(latest["equity"]),
            net_return=float(latest["net_return"]),
            trade_number=int(latest["trade_number"]),
            observed_at=latest["closed_at"],
            opened_at=latest.get("opened_at"),
            basis=payload["basis"],
        )
