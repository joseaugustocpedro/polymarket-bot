from typing import Optional
from pydantic import BaseModel, Field


class WalletCreate(BaseModel):
    alias: str = Field(min_length=2, max_length=80)
    address: str = Field(pattern=r"^0x[a-fA-F0-9]{40}$")
    notes: Optional[str] = None


class WalletUsernameCreate(BaseModel):
    username: str = Field(min_length=2, max_length=80, description="Username público da Polymarket, com ou sem @")
    alias: Optional[str] = Field(default=None, max_length=80)
    notes: Optional[str] = None


class WalletUpdate(BaseModel):
    alias: Optional[str] = None
    enabled: Optional[bool] = None
    notes: Optional[str] = None


class CopyRules(BaseModel):
    enabled: bool = False
    manual_confirmation: bool = True
    max_trade_usd: float = 25.0
    proportional_percent: float = 0.0
    daily_loss_limit_usd: float = 50.0
    allowed_market_keywords: list[str] = []
