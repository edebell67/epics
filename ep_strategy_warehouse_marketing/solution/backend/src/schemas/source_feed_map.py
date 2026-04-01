from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


logger = logging.getLogger(__name__)


class NetPoint(BaseModel):
    """
    Individual data point within _summary_net.json for a specific strategy-product pair.
    """
    model_config = ConfigDict(populate_by_name=True)

    timestamp: datetime = Field(alias="t")
    net: float = 0.0
    buy_net: float = Field(default=0.0, alias="buy_net")
    sell_net: float = Field(default=0.0, alias="sell_net")
    buy_alt: float = Field(default=0.0, alias="buy_alt")
    sell_alt: float = Field(default=0.0, alias="sell_alt")
    live_buy: float = Field(default=0.0, alias="live_buy")
    live_sell: float = Field(default=0.0, alias="live_sell")
    buys_count: int = Field(default=0, alias="b_c")
    sells_count: int = Field(default=0, alias="s_c")
    buy_percent: float = Field(default=0.0, alias="buyPercent")
    sell_percent: float = Field(default=0.0, alias="sellPercent")

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime:
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                logger.warning(f"Could not parse timestamp: {v}, using current time as fallback.")
                return datetime.now()
        return v


class SummaryNetFeed(BaseModel):
    """
    Structure of _summary_net.json.
    Mapping: strategies -> products -> List[NetPoint]
    """
    last_update: datetime = Field(default_factory=datetime.now)
    session_max_net: float = 0.0
    strategies: Dict[str, Dict[str, List[NetPoint]]] = Field(default_factory=dict)

    @field_validator("last_update", mode="before")
    @classmethod
    def parse_last_update(cls, v: Any) -> datetime:
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                return datetime.now()
        return v


class Leader(BaseModel):
    """
    A single leader entry in a frequency snapshot.
    """
    rank: int = 0
    score_rank: Optional[int] = None
    score: Optional[float] = None
    product: str = "Unknown"
    strategy: str = "Unknown"
    net: float = 0.0


class FrequencySnapshot(BaseModel):
    """
    A timed snapshot containing a list of leaders.
    """
    time: datetime
    leaders: List[Leader] = Field(default_factory=list)

    @field_validator("time", mode="before")
    @classmethod
    def parse_time(cls, v: Any) -> datetime:
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                return datetime.now()
        return v


class FrequencyFeed(BaseModel):
    """
    Structure of _frequency.json, _dna_frequency.json, and _dna_alt_frequency.json.
    """
    date: str = ""
    run_mode: str = "unknown"
    frequency_minutes: int = 5
    snapshot_count: int = 0
    snapshots: List[FrequencySnapshot] = Field(default_factory=list)


class WarehouseSnapshot(BaseModel):
    """
    Canonical mapping of a complete Strategy Warehouse snapshot directory.
    Combines the four main JSON feed files into a single normalized object.
    """
    summary_net: SummaryNetFeed
    frequency: FrequencyFeed
    dna_frequency: FrequencyFeed
    dna_alt_frequency: Optional[FrequencyFeed] = None

    # Fallback Logic Documentation (Procedural):
    # 1. Missing files: The consumer should handle cases where feed files are 
    #    absent by using default instances (e.g., empty dicts/lists).
    # 2. Stale data: 'last_update' and 'date' fields should be checked against 
    #    the current system time to identify staleness.
    # 3. Missing fields: Pydantic 'default' and 'default_factory' provide 
    #    automatic fallback for missing JSON keys.
    # 4. Parsing errors: Custom validators (parse_timestamp, etc.) catch 
    #    malformed ISO strings and fallback to current datetime.
