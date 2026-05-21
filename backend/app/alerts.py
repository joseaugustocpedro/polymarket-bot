from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Tuple
import httpx
from sqlmodel import Session
from .config import get_settings
from .models import Activity, AlertLog

settings = get_settings()


def format_alert(activity: Activity) -> str:
    side = activity.side or "N/A"
    outcome = activity.outcome or "N/A"
    title = activity.title or "Mercado sem título"
    return (
        f"🚨 Nova atividade na Polymarket\n\n"
        f"Trader: {activity.trader_alias}\n"
        f"Ação: {side}\n"
        f"Mercado: {title}\n"
        f"Opção: {outcome}\n"
        f"Valor: ${activity.usdc_size:,.2f}\n"
        f"Preço: {activity.price:.4f}\n"
        f"Quantidade: {activity.size:,.4f}\n"
        f"Horário Unix: {activity.timestamp}\n"
        f"Mercado: {activity.market_url or 'N/A'}\n"
        f"Transação: {activity.tx_url or 'N/A'}"
    )


class AlertDispatcher:
    async def send_all(self, db: Session, activity: Activity) -> None:
        message = format_alert(activity)
        for channel, sender in [
            ("telegram", self.send_telegram),
            ("discord", self.send_discord),
            ("email", self.send_email),
        ]:
            ok, response = await sender(message)
            if ok or response != "not_configured":
                db.add(AlertLog(
                    activity_unique_key=activity.unique_key,
                    channel=channel,
                    ok=ok,
                    response=response[:500] if response else None,
                ))
        db.commit()

    async def send_telegram(self, message: str) -> Tuple[bool, str]:
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            return False, "not_configured"
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        payload = {"chat_id": settings.telegram_chat_id, "text": message, "disable_web_page_preview": False}
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=payload)
        return r.is_success, r.text

    async def send_discord(self, message: str) -> Tuple[bool, str]:
        if not settings.discord_webhook_url:
            return False, "not_configured"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(settings.discord_webhook_url, json={"content": message})
        return r.is_success, r.text

    async def send_email(self, message: str) -> Tuple[bool, str]:
        required = [settings.smtp_host, settings.smtp_user, settings.smtp_password, settings.email_from, settings.email_to]
        if not all(required):
            return False, "not_configured"
        try:
            email = EmailMessage()
            email["Subject"] = "Nova atividade monitorada na Polymarket"
            email["From"] = settings.email_from
            email["To"] = settings.email_to
            email.set_content(message)
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                smtp.starttls()
                smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(email)
            return True, "sent"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
