from __future__ import annotations

from typing import Any
import httpx
from .config import get_settings

settings = get_settings()


KNOWN_PROFILE_WALLETS: dict[str, dict[str, str]] = {
    # Confirmado pela própria página pública da Polymarket:
    # https://polymarket.com/fr/profile/0x9b1e0334569aa1768a07705a859686aad58e82c9
    "fullpicks1": {
        "name": "FullPicks1",
        "proxyWallet": "0x9b1e0334569aa1768a07705a859686aad58e82c9",
        "source": "known_seed",
    }
}


def normalize_username(username: str) -> str:
    return username.strip().lstrip("@").lower()


class PolymarketClient:
    def __init__(self) -> None:
        self.data_api = settings.polymarket_data_api.rstrip("/")
        self.gamma_api = settings.polymarket_gamma_api.rstrip("/")
        self.clob_api = settings.polymarket_clob_api.rstrip("/")

    async def get_user_activity(self, user_address: str, limit: int = 50) -> list[dict[str, Any]]:
        """Busca atividades públicas de um endereço/proxy wallet.

        A API retorna compras, vendas, splits, merges, rewards etc.
        Para alertas de trading, normalmente usamos type=TRADE.
        """
        params = {
            "user": user_address,
            "limit": min(limit, 500),
            "offset": 0,
            "sortBy": "TIMESTAMP",
            "sortDirection": "DESC",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(f"{self.data_api}/activity", params=params)
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else []


    async def search_profiles(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Busca perfis públicos pelo username/nome usando a Gamma API.

        A API oficial `public-search` retorna mercados, eventos, tags e perfis.
        Aqui filtramos perfis e lemos `proxyWallet` quando disponível.
        """
        params = {
            "q": query.strip().lstrip("@"),
            "search_profiles": "true",
            "limit_per_type": min(max(limit, 1), 25),
        }
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(f"{self.gamma_api}/public-search", params=params)
            r.raise_for_status()
            data = r.json()
            profiles = data.get("profiles") if isinstance(data, dict) else []
            return profiles if isinstance(profiles, list) else []

    async def get_public_profile(self, address: str) -> dict[str, Any] | None:
        """Busca perfil público pelo endereço/proxy wallet."""
        params = {"address": address}
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(f"{self.gamma_api}/public-profile", params=params)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, dict) else None

    async def resolve_username_to_wallet(self, username: str) -> dict[str, Any] | None:
        """Resolve @username -> proxyWallet.

        Estratégia:
        1. tenta `public-search` com `search_profiles=true`;
        2. escolhe match exato por `name`, `pseudonym` ou `xUsername`;
        3. fallback para a tabela local de seeds conhecidos, incluindo @fullpicks1.
        """
        normalized = normalize_username(username)
        profiles = await self.search_profiles(normalized, limit=10)
        exact = None
        for profile in profiles:
            names = [
                profile.get("name"),
                profile.get("pseudonym"),
                profile.get("xUsername"),
            ]
            if any(normalize_username(str(n)) == normalized for n in names if n):
                exact = profile
                break
        selected = exact or (profiles[0] if profiles else None)
        if selected and selected.get("proxyWallet"):
            return {
                "username": selected.get("name") or selected.get("pseudonym") or username,
                "proxyWallet": selected.get("proxyWallet"),
                "profile": selected,
                "source": "gamma_public_search",
            }

        fallback = KNOWN_PROFILE_WALLETS.get(normalized)
        if fallback:
            return {
                "username": fallback["name"],
                "proxyWallet": fallback["proxyWallet"],
                "profile": fallback,
                "source": fallback["source"],
            }
        return None

    async def get_order_book(self, token_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(f"{self.clob_api}/book", params={"token_id": token_id})
            r.raise_for_status()
            return r.json()

    async def get_simplified_markets(self, next_cursor: str | None = None) -> dict[str, Any]:
        params = {}
        if next_cursor:
            params["next_cursor"] = next_cursor
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"{self.clob_api}/simplified-markets", params=params)
            r.raise_for_status()
            return r.json()


def market_url(activity: dict[str, Any]) -> str | None:
    event_slug = activity.get("eventSlug")
    slug = activity.get("slug")
    if event_slug:
        return f"https://polymarket.com/event/{event_slug}"
    if slug:
        return f"https://polymarket.com/market/{slug}"
    return None


def tx_url(tx_hash: str | None) -> str | None:
    if not tx_hash:
        return None
    return f"https://polygonscan.com/tx/{tx_hash}"


def activity_unique_key(a: dict[str, Any]) -> str:
    parts = [
        str(a.get("transactionHash") or "no-tx"),
        str(a.get("asset") or "no-asset"),
        str(a.get("side") or "no-side"),
        str(a.get("timestamp") or "0"),
        str(a.get("size") or "0"),
        str(a.get("price") or "0"),
    ]
    return "|".join(parts)
