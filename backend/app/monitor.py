from __future__ import annotations

import asyncio
from typing import Callable, Awaitable
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from .config import get_settings
from .database import engine
from .models import MonitoredWallet, Activity
from .polymarket_client import PolymarketClient, activity_unique_key, market_url, tx_url
from .alerts import AlertDispatcher
from .copy_trader import CopyTrader

settings = get_settings()


class MonitorService:
    def __init__(self) -> None:
        self.client = PolymarketClient()
        self.alerts = AlertDispatcher()
        self.copy_trader = CopyTrader()
        self.running = False
        self.on_new_activity: Callable[[Activity], Awaitable[None]] | None = None

    async def poll_once(self) -> int:
        created = 0
        with Session(engine) as db:
            wallets = db.exec(select(MonitoredWallet).where(MonitoredWallet.enabled == True)).all()  # noqa: E712
            for wallet in wallets:
                is_first_sync = db.exec(select(Activity).where(Activity.wallet_address == wallet.address)).first() is None
                try:
                    activities = await self.client.get_user_activity(wallet.address, limit=30)
                except Exception as exc:  # noqa: BLE001
                    print(f"Erro buscando {wallet.alias}/{wallet.address}: {exc}")
                    continue

                for raw in reversed(activities):
                    key = activity_unique_key(raw)
                    if db.exec(select(Activity).where(Activity.unique_key == key)).first():
                        continue

                    activity = Activity(
                        unique_key=key,
                        wallet_address=wallet.address,
                        trader_alias=wallet.alias,
                        timestamp=int(raw.get("timestamp") or 0),
                        type=str(raw.get("type") or "TRADE"),
                        side=raw.get("side"),
                        title=raw.get("title"),
                        outcome=raw.get("outcome"),
                        condition_id=raw.get("conditionId"),
                        asset=raw.get("asset"),
                        slug=raw.get("slug"),
                        event_slug=raw.get("eventSlug"),
                        size=float(raw.get("size") or 0),
                        usdc_size=float(raw.get("usdcSize") or 0),
                        price=float(raw.get("price") or 0),
                        transaction_hash=raw.get("transactionHash"),
                        market_url=market_url(raw),
                        tx_url=tx_url(raw.get("transactionHash")),
                    )
                    db.add(activity)
                    try:
                        db.commit()
                        db.refresh(activity)
                    except IntegrityError:
                        db.rollback()
                        continue

                    created += 1

                    # Evita disparar 30 alertas antigos quando uma carteira é adicionada
                    # pela primeira vez. O histórico é salvo, mas os alertas começam
                    # apenas nas próximas atividades novas. Para alertar também no
                    # backfill, configure ALERT_ON_BACKFILL=true no .env.
                    should_alert = (not is_first_sync) or settings.alert_on_backfill
                    if should_alert:
                        await self.alerts.send_all(db, activity)
                        self.copy_trader.handle_signal(db, activity)
                        if self.on_new_activity:
                            await self.on_new_activity(activity)
        return created

    async def run_forever(self) -> None:
        self.running = True
        while self.running:
            await self.poll_once()
            await asyncio.sleep(settings.poll_interval_seconds)

    def stop(self) -> None:
        self.running = False
