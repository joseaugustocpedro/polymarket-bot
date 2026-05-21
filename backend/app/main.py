from __future__ import annotations

import asyncio
from typing import List
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, func
from .database import create_db_and_tables, get_session, engine
from .models import MonitoredWallet, Activity, SimulatedOrder
from .schemas import WalletCreate, WalletUpdate, WalletUsernameCreate
from .monitor import MonitorService
from .simulator import simulate_copy_trade
from .config import get_settings
from .polymarket_client import PolymarketClient

app = FastAPI(title="Polymarket Alert Bot", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

monitor = MonitorService()
resolver_client = PolymarketClient()
settings = get_settings()
_monitor_task: asyncio.Task | None = None


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        disconnected = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)


manager = ConnectionManager()


def seed_default_wallets() -> None:
    """Cadastra carteiras padrão no primeiro startup.

    O projeto já nasce com @fullpicks1 monitorado. Para adicionar outros seeds,
    ajuste DEFAULT_WALLETS no .env no formato: "Alias:0xEndereco,Outro:0xEndereco".
    """
    if not settings.default_wallets:
        return
    with Session(engine) as db:
        for item in settings.default_wallets.split(','):
            if ':' not in item:
                continue
            alias, address = item.split(':', 1)
            alias = alias.strip()
            address = address.strip().lower()
            if not alias or not address.startswith('0x'):
                continue
            existing = db.exec(select(MonitoredWallet).where(MonitoredWallet.address == address)).first()
            if existing:
                continue
            wallet = MonitoredWallet(
                alias=alias,
                address=address,
                notes='Carteira padrão carregada automaticamente no startup.',
            )
            db.add(wallet)
        db.commit()


async def broadcast_activity(activity: Activity) -> None:
    await manager.broadcast({
        "type": "activity",
        "data": activity.model_dump(mode="json"),
    })


@app.on_event("startup")
async def startup() -> None:
    global _monitor_task
    create_db_and_tables()
    seed_default_wallets()
    monitor.on_new_activity = broadcast_activity
    _monitor_task = asyncio.create_task(monitor.run_forever())


@app.on_event("shutdown")
async def shutdown() -> None:
    monitor.stop()
    if _monitor_task:
        _monitor_task.cancel()


@app.get("/health")
def health():
    return {"ok": True, "monitor_running": monitor.running}


@app.post("/wallets", response_model=MonitoredWallet)
def create_wallet(payload: WalletCreate, db: Session = Depends(get_session)):
    address = payload.address.lower()
    existing = db.exec(select(MonitoredWallet).where(MonitoredWallet.address == address)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Carteira já cadastrada")
    wallet = MonitoredWallet(alias=payload.alias, address=address, notes=payload.notes)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


@app.get("/profiles/resolve/{username}")
async def resolve_profile(username: str):
    resolved = await resolver_client.resolve_username_to_wallet(username)
    if not resolved:
        raise HTTPException(status_code=404, detail="Não consegui resolver esse username para uma proxy wallet pública")
    return resolved


@app.post("/wallets/by-username", response_model=MonitoredWallet)
async def create_wallet_by_username(payload: WalletUsernameCreate, db: Session = Depends(get_session)):
    resolved = await resolver_client.resolve_username_to_wallet(payload.username)
    if not resolved or not resolved.get("proxyWallet"):
        raise HTTPException(status_code=404, detail="Não consegui resolver esse username para uma proxy wallet pública")

    address = str(resolved["proxyWallet"]).lower()
    alias = payload.alias or str(resolved.get("username") or payload.username).lstrip("@")
    existing = db.exec(select(MonitoredWallet).where(MonitoredWallet.address == address)).first()
    if existing:
        return existing

    wallet = MonitoredWallet(
        alias=alias,
        address=address,
        notes=payload.notes or f"Adicionada via username @{payload.username.lstrip('@')}; source={resolved.get('source')}",
    )
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


@app.get("/wallets", response_model=List[MonitoredWallet])
def list_wallets(db: Session = Depends(get_session)):
    return db.exec(select(MonitoredWallet).order_by(MonitoredWallet.created_at.desc())).all()


@app.patch("/wallets/{wallet_id}", response_model=MonitoredWallet)
def update_wallet(wallet_id: int, payload: WalletUpdate, db: Session = Depends(get_session)):
    wallet = db.get(MonitoredWallet, wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Carteira não encontrada")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(wallet, key, value)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


@app.delete("/wallets/{wallet_id}")
def delete_wallet(wallet_id: int, db: Session = Depends(get_session)):
    wallet = db.get(MonitoredWallet, wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Carteira não encontrada")
    db.delete(wallet)
    db.commit()
    return {"deleted": True}


@app.get("/activities", response_model=List[Activity])
def list_activities(limit: int = 100, db: Session = Depends(get_session)):
    limit = min(max(limit, 1), 500)
    return db.exec(select(Activity).order_by(Activity.timestamp.desc()).limit(limit)).all()


@app.post("/monitor/poll")
async def manual_poll():
    created = await monitor.poll_once()
    return {"created": created}


@app.get("/ranking")
def ranking(db: Session = Depends(get_session)):
    rows = db.exec(
        select(
            Activity.trader_alias,
            Activity.wallet_address,
            func.count(Activity.id),
            func.sum(Activity.usdc_size),
        )
        .group_by(Activity.trader_alias, Activity.wallet_address)
        .order_by(func.sum(Activity.usdc_size).desc())
    ).all()
    return [
        {
            "trader_alias": r[0],
            "wallet_address": r[1],
            "trades": r[2],
            "volume_usdc": float(r[3] or 0),
        }
        for r in rows
    ]


@app.get("/performance")
def performance(db: Session = Depends(get_session)):
    rows = db.exec(
        select(Activity.timestamp, Activity.trader_alias, Activity.usdc_size, Activity.side)
        .order_by(Activity.timestamp.asc())
    ).all()
    cumulative = 0.0
    data = []
    for ts, alias, usdc, side in rows:
        # MVP: desempenho aqui é volume acumulado, não P&L real.
        cumulative += float(usdc or 0)
        data.append({"timestamp": ts, "trader_alias": alias, "volume": float(usdc or 0), "cumulative_volume": cumulative, "side": side})
    return data


@app.post("/simulate/copy/{activity_id}", response_model=SimulatedOrder)
def simulate_copy(activity_id: int, db: Session = Depends(get_session)):
    activity = db.get(Activity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    return simulate_copy_trade(db, activity, reason="manual_dashboard")


@app.get("/simulated-orders", response_model=List[SimulatedOrder])
def simulated_orders(db: Session = Depends(get_session)):
    return db.exec(select(SimulatedOrder).order_by(SimulatedOrder.created_at.desc()).limit(100)).all()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
