from sqlmodel import Session
from .config import get_settings
from .models import Activity, SimulatedOrder

settings = get_settings()


def simulate_copy_trade(db: Session, activity: Activity, reason: str = "auto-simulation") -> SimulatedOrder:
    """Registra uma cópia simulada de trade, sem enviar ordem real.

    Regra simples do MVP: copiar no máximo MAX_TRADE_USD ou o valor original, o que for menor.
    """
    amount = min(settings.max_trade_usd, max(activity.usdc_size, 0.0))
    simulated_size = amount / activity.price if activity.price > 0 else 0.0
    order = SimulatedOrder(
        source_activity_key=activity.unique_key,
        wallet_address=activity.wallet_address,
        market_title=activity.title or "N/A",
        side=activity.side or "BUY",
        outcome=activity.outcome or "N/A",
        reference_price=activity.price,
        simulated_amount_usd=amount,
        simulated_size=simulated_size,
        reason=reason,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order
