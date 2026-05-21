from sqlmodel import Session
from .config import get_settings
from .models import Activity
from .simulator import simulate_copy_trade

settings = get_settings()


class CopyTrader:
    """Camada segura para copy trading.

    Por padrão, só simula. Para execução real, integre com o SDK oficial da Polymarket
    e mantenha ENABLE_LIVE_TRADING=false até testar em produção com valores pequenos.
    """

    def allowed_market(self, activity: Activity) -> bool:
        keywords = [k.strip().lower() for k in (settings.allowed_market_keywords or "").split(",") if k.strip()]
        if not keywords:
            return True
        title = (activity.title or "").lower()
        return any(k in title for k in keywords)

    def handle_signal(self, db: Session, activity: Activity):
        if activity.type != "TRADE":
            return None
        if not self.allowed_market(activity):
            return None
        if settings.paper_trading or not settings.enable_live_trading:
            return simulate_copy_trade(db, activity, reason="paper_trading_enabled")

        raise RuntimeError(
            "Live trading bloqueado no MVP. Implemente confirmação manual e SDK oficial antes de ativar."
        )
