from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MonitoredWallet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    alias: str
    address: str = Field(index=True, unique=True)
    enabled: bool = True
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class Activity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    unique_key: str = Field(index=True, unique=True)
    wallet_address: str = Field(index=True)
    trader_alias: str = Field(index=True)

    timestamp: int = Field(index=True)
    type: str = Field(index=True, default="TRADE")
    side: Optional[str] = Field(default=None, index=True)
    title: Optional[str] = None
    outcome: Optional[str] = None
    condition_id: Optional[str] = Field(default=None, index=True)
    asset: Optional[str] = Field(default=None, index=True)
    slug: Optional[str] = None
    event_slug: Optional[str] = None

    size: float = 0.0
    usdc_size: float = 0.0
    price: float = 0.0
    transaction_hash: Optional[str] = Field(default=None, index=True)
    market_url: Optional[str] = None
    tx_url: Optional[str] = None

    created_at: datetime = Field(default_factory=utcnow)


class AlertLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    activity_unique_key: str = Field(index=True)
    channel: str
    ok: bool = False
    response: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class SimulatedOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_activity_key: str = Field(index=True)
    wallet_address: str = Field(index=True)
    market_title: str
    side: str
    outcome: str
    reference_price: float
    simulated_amount_usd: float
    simulated_size: float
    status: str = "SIMULATED"
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
