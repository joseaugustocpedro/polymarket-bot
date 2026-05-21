import React, { useEffect, useMemo, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Bell, Wallet, Activity, BarChart3, Search } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function money(value) {
  return Number(value || 0).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
}

function App() {
  const [wallets, setWallets] = useState([]);
  const [activities, setActivities] = useState([]);
  const [ranking, setRanking] = useState([]);
  const [performance, setPerformance] = useState([]);
  const [alias, setAlias] = useState('');
  const [address, setAddress] = useState('');
  const [username, setUsername] = useState('@fullpicks1');
  const [usernameAlias, setUsernameAlias] = useState('FullPicks1');
  const [filter, setFilter] = useState('');
  const [resolveInfo, setResolveInfo] = useState('');

  async function load() {
    const [w, a, r, p] = await Promise.all([
      fetch(`${API}/wallets`).then(x => x.json()),
      fetch(`${API}/activities?limit=200`).then(x => x.json()),
      fetch(`${API}/ranking`).then(x => x.json()),
      fetch(`${API}/performance`).then(x => x.json()),
    ]);
    setWallets(w);
    setActivities(a);
    setRanking(r);
    setPerformance(p);
  }

  useEffect(() => {
    load();
    const timer = setInterval(load, 15000);
    const ws = new WebSocket(API.replace('http', 'ws') + '/ws');
    ws.onmessage = () => load();
    return () => {
      clearInterval(timer);
      ws.close();
    };
  }, []);

  const filtered = useMemo(() => {
    const f = filter.toLowerCase();
    return activities.filter(a =>
      !f ||
      String(a.trader_alias).toLowerCase().includes(f) ||
      String(a.title).toLowerCase().includes(f) ||
      String(a.side).toLowerCase().includes(f)
    );
  }, [activities, filter]);

  async function addWallet(e) {
    e.preventDefault();
    const res = await fetch(`${API}/wallets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ alias, address }),
    });
    if (!res.ok) {
      alert('Erro cadastrando carteira. Confira se é um endereço 0x válido.');
      return;
    }
    setAlias('');
    setAddress('');
    load();
  }

  async function addByUsername(e) {
    e.preventDefault();
    setResolveInfo('Resolvendo username...');
    const res = await fetch(`${API}/wallets/by-username`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, alias: usernameAlias || undefined }),
    });
    if (!res.ok) {
      setResolveInfo('Não consegui resolver esse username. Tente cadastrar pela wallet 0x.');
      return;
    }
    const wallet = await res.json();
    setResolveInfo(`Adicionado: ${wallet.alias} → ${wallet.address}`);
    load();
  }

  async function resolveOnly() {
    setResolveInfo('Consultando perfil público...');
    const clean = username.replace('@', '');
    const res = await fetch(`${API}/profiles/resolve/${encodeURIComponent(clean)}`);
    if (!res.ok) {
      setResolveInfo('Não encontrei proxy wallet pública para esse username.');
      return;
    }
    const data = await res.json();
    setResolveInfo(`${data.username} → ${data.proxyWallet} | source: ${data.source}`);
  }

  async function pollNow() {
    await fetch(`${API}/monitor/poll`, { method: 'POST' });
    load();
  }

  async function simulate(id) {
    await fetch(`${API}/simulate/copy/${id}`, { method: 'POST' });
    alert('Ordem simulada registrada.');
  }

  return (
    <main style={{ padding: 24, fontFamily: 'Inter, Arial, sans-serif', background: '#f7f8fb', minHeight: '100vh' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0 }}>Polymarket Alert Bot</h1>
          <p style={{ margin: '6px 0', color: '#64748b' }}>Já vem com @fullpicks1 monitorado. Use usernames ou wallets 0x.</p>
        </div>
        <button onClick={pollNow} style={buttonStyle}><Bell size={16} /> Verificar agora</button>
      </header>

      <section style={gridStyle}>
        <Card icon={<Wallet />} title="Carteiras monitoradas" value={wallets.length} />
        <Card icon={<Activity />} title="Atividades salvas" value={activities.length} />
        <Card icon={<BarChart3 />} title="Volume rastreado" value={money(activities.reduce((s, a) => s + Number(a.usdc_size || 0), 0))} />
      </section>

      <section style={gridTwoStyle}>
        <div style={panelStyle}>
          <h2>Cadastrar por username</h2>
          <form onSubmit={addByUsername} style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <input placeholder="@username" value={username} onChange={e => setUsername(e.target.value)} style={inputStyle} />
            <input placeholder="Apelido opcional" value={usernameAlias} onChange={e => setUsernameAlias(e.target.value)} style={inputStyle} />
            <button style={buttonStyle}>Resolver e adicionar</button>
            <button type="button" onClick={resolveOnly} style={secondaryButtonStyle}><Search size={16} /> Apenas resolver</button>
          </form>
          {resolveInfo && <p style={{ color: '#475569', wordBreak: 'break-all' }}>{resolveInfo}</p>}
        </div>

        <div style={panelStyle}>
          <h2>Cadastrar carteira manual</h2>
          <form onSubmit={addWallet} style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <input placeholder="Apelido do trader" value={alias} onChange={e => setAlias(e.target.value)} style={inputStyle} />
            <input placeholder="0x... proxy wallet" value={address} onChange={e => setAddress(e.target.value)} style={{ ...inputStyle, minWidth: 360 }} />
            <button style={buttonStyle}>Adicionar</button>
          </form>
        </div>
      </section>

      <section style={panelStyle}>
        <h2>Carteiras monitoradas</h2>
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead><tr><th>Apelido</th><th>Wallet</th><th>Status</th><th>Notas</th></tr></thead>
            <tbody>
              {wallets.map(w => (
                <tr key={w.address}><td>{w.alias}</td><td style={{ fontFamily: 'monospace' }}>{w.address}</td><td>{w.enabled ? 'ativo' : 'pausado'}</td><td>{w.notes}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section style={gridTwoStyle}>
        <div style={panelStyle}>
          <h2>Ranking de traders</h2>
          <table style={tableStyle}>
            <thead><tr><th>Trader</th><th>Trades</th><th>Volume</th></tr></thead>
            <tbody>
              {ranking.map((r, i) => (
                <tr key={r.wallet_address}><td>{i + 1}. {r.trader_alias}</td><td>{r.trades}</td><td>{money(r.volume_usdc)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={panelStyle}>
          <h2>Gráfico de volume acumulado</h2>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={performance}>
              <XAxis dataKey="timestamp" hide />
              <YAxis />
              <Tooltip formatter={(v) => money(v)} />
              <Line type="monotone" dataKey="cumulative_volume" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section style={panelStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
          <h2>Histórico de operações</h2>
          <input placeholder="Filtrar por trader, mercado ou ação" value={filter} onChange={e => setFilter(e.target.value)} style={inputStyle} />
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead>
              <tr><th>Trader</th><th>Ação</th><th>Mercado</th><th>Opção</th><th>Valor</th><th>Preço</th><th>Qtd.</th><th>Links</th><th>Simulação</th></tr>
            </thead>
            <tbody>
              {filtered.map(a => (
                <tr key={a.unique_key}>
                  <td>{a.trader_alias}</td>
                  <td>{a.side}</td>
                  <td>{a.title}</td>
                  <td>{a.outcome}</td>
                  <td>{money(a.usdc_size)}</td>
                  <td>{Number(a.price || 0).toFixed(4)}</td>
                  <td>{Number(a.size || 0).toLocaleString()}</td>
                  <td>
                    {a.market_url && <a href={a.market_url} target="_blank">mercado</a>} {' '}
                    {a.tx_url && <a href={a.tx_url} target="_blank">tx</a>}
                  </td>
                  <td><button onClick={() => simulate(a.id)} style={smallButtonStyle}>simular</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

function Card({ icon, title, value }) {
  return (
    <div style={panelStyle}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#2563eb' }}>{icon}<strong>{title}</strong></div>
      <div style={{ fontSize: 28, fontWeight: 800, marginTop: 10 }}>{value}</div>
    </div>
  );
}

const panelStyle = { background: '#fff', borderRadius: 18, padding: 18, boxShadow: '0 10px 30px rgba(15,23,42,.06)', marginBottom: 18 };
const gridStyle = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 18 };
const gridTwoStyle = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 18 };
const inputStyle = { padding: '12px 14px', border: '1px solid #dbe2ea', borderRadius: 12, fontSize: 14 };
const buttonStyle = { padding: '12px 16px', border: 0, borderRadius: 12, background: '#2563eb', color: '#fff', display: 'inline-flex', gap: 8, alignItems: 'center', cursor: 'pointer', fontWeight: 700 };
const secondaryButtonStyle = { ...buttonStyle, background: '#0f172a' };
const smallButtonStyle = { padding: '8px 10px', border: 0, borderRadius: 10, background: '#0f172a', color: '#fff', cursor: 'pointer' };
const tableStyle = { width: '100%', borderCollapse: 'collapse' };

export default App;
