# Polymarket Alert Bot — MVP seguro

Bot para monitorar carteiras públicas da Polymarket, salvar histórico, enviar alertas e exibir um dashboard web.

> Aviso: este projeto é para alertas, análise e simulação. Não promete lucro e não é aconselhamento financeiro. O modo de copy trading real não vem ativado por padrão.

## Estrutura

```text
polymarket-alert-bot/
  backend/
    app/
      main.py
      config.py
      database.py
      models.py
      schemas.py
      polymarket_client.py
      alerts.py
      monitor.py
      simulator.py
      copy_trader.py
    requirements.txt
    .env.example
  frontend/
    src/
      App.jsx
      main.jsx
    index.html
    package.json
    vite.config.js
  docker-compose.yml
```

## Rodar localmente

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Abra: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Abra: http://localhost:5173

## Variáveis de ambiente importantes

Veja `backend/.env.example`.

- `DATABASE_URL`: SQLite local ou PostgreSQL em produção.
- `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`: alertas no Telegram.
- `DISCORD_WEBHOOK_URL`: alertas no Discord.
- `SMTP_*`: alertas por e-mail.
- `PAPER_TRADING=true`: mantém o bot em simulação.
- `ENABLE_LIVE_TRADING=false`: proteção contra operação real acidental.
- `ALERT_ON_BACKFILL=false`: salva histórico inicial sem disparar vários alertas antigos.

## Fluxo

1. Você cadastra uma carteira/proxy wallet da Polymarket.
2. O monitor consulta `https://data-api.polymarket.com/activity`.
3. Se aparecer uma atividade nova, o bot grava no banco.
4. O alerta é enviado via Telegram/Discord/e-mail.
5. O dashboard atualiza histórico, ranking e estimativas.
6. O modo simulação registra o que teria sido copiado, sem gastar dinheiro.

## @fullpicks1 já vem embutido

O projeto já cadastra automaticamente a carteira pública do perfil `@fullpicks1` no primeiro startup:

```text
FullPicks1:0x9b1e0334569aa1768a07705a859686aad58e82c9
```

Você pode alterar ou adicionar seeds no `.env`:

```env
DEFAULT_WALLETS=FullPicks1:0x9b1e0334569aa1768a07705a859686aad58e82c9,OutroTrader:0x...
```

## Resolver username para wallet

O backend agora tem duas rotas para resolver perfis públicos:

```text
GET  /profiles/resolve/{username}
POST /wallets/by-username
```

O resolvedor tenta a Gamma API `public-search` com `search_profiles=true` e lê o campo `proxyWallet`. Se não encontrar, usa um fallback local para seeds conhecidos, incluindo `@fullpicks1`.

No dashboard, use a seção **Cadastrar por username** para adicionar perfis como `@fullpicks1`.
