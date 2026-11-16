# Polymarket Alert Bot — monitoramento e simulação (protótipo)

Protótipo de monitoramento de atividades públicas da Polymarket, armazenamento de histórico, emissão de alertas e dashboard web. O repositório demonstra integração de APIs, backend em FastAPI e interface React; não representa uma plataforma validada para produção.

> **Uso educacional:** este projeto é para monitoramento, análise e simulação. Não promete lucro e não constitui aconselhamento financeiro. A operação real fica desativada por padrão; não execute sem entender as configurações e os riscos.

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
source .venv/bin/activate  # Windows (PowerShell): .venv\Scripts\Activate.ps1
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

## Segurança e escopo

- Execute localmente e **não exponha a API publicamente** sem implementar autenticação, autorização, restrição de origem e revisão de segurança. As rotas administrativas deste protótipo não constituem um painel multiusuário protegido.
- Guarde `.env` e credenciais somente na sua máquina ou no gerenciador de segredos do ambiente de execução. Um [modelo sem credenciais](backend/.env.example) acompanha o repositório.
- As integrações de alertas exigem configuração externa; a presença do código não comprova testes em produção.
- Dependências e configurações devem ser revisadas antes de qualquer hospedagem aberta. Não há comprovação de implantação pública ou CI neste repositório.

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
