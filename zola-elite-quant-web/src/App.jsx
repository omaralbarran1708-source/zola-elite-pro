import React, { useEffect, useMemo, useState } from 'react'
import { fetchLiveMatches, fetchOdds } from './api'
import { demoFixtures, demoUpcoming, demoHistory } from './demo'
import { buildOddsMap, deriveQuantModel, normalizeFixture } from './engine'

const NAV = ['Partidos en vivo', 'Mercados', 'Watchlist', 'Historial', 'Bankroll', 'Alertas', 'Configuración']

function formatMoney(v) {
  return `USD ${Number(v).toFixed(2)}`
}

function TrafficLight({ active }) {
  const label = active === 'green' ? 'Alta' : active === 'yellow' ? 'Media' : 'Baja'
  return (
    <div className="traffic-light">
      <span className={active === 'red' ? 'on red' : 'red'} />
      <span className={active === 'yellow' ? 'on yellow' : 'yellow'} />
      <span className={active === 'green' ? 'on green' : 'green'} />
      <small>Decisión {label}</small>
    </div>
  )
}

function Logo({ src, alt, className = '', fallback = '•' }) {
  const [failed, setFailed] = useState(false)
  if (!src || failed) return <span className={`logo-fallback ${className}`}>{fallback}</span>
  return <img src={src} alt={alt} className={className} onError={() => setFailed(true)} />
}

function TeamCard({ team }) {
  return (
    <div className="team-card">
      <Logo src={team.logo} alt={team.name} className="team-logo" fallback={team.name?.[0] || 'T'} />
      <h2>{team.name}</h2>
    </div>
  )
}

function TeamInline({ team }) {
  return (
    <span className="team-inline">
      <Logo src={team.logo} alt={team.name} className="team-inline-logo" fallback={team.name?.[0] || 'T'} />
      <strong>{team.name}</strong>
    </span>
  )
}

function MetricBar({ label, left, right, decimal = false }) {
  const total = Number(left) + Number(right)
  const leftPercent = total ? (Number(left) / total) * 100 : 50
  return (
    <div className="metric-bar">
      <div className="metric-head">
        <strong>{decimal ? Number(left).toFixed(2) : left}</strong>
        <span>{label}</span>
        <strong>{decimal ? Number(right).toFixed(2) : right}</strong>
      </div>
      <div className="dual-track">
        <div className="dual-left" style={{ width: `${leftPercent}%` }} />
        <div className="dual-right" style={{ width: `${100-leftPercent}%` }} />
      </div>
    </div>
  )
}

function MomentumChart({ values }) {
  const width = 100
  const height = 24
  const step = width / Math.max(values.length - 1, 1)
  const max = 10
  const points = values.map((value, index) => {
    const x = index * step
    const y = height / 2 - (value / max) * (height / 2 - 1)
    return `${x},${y}`
  }).join(' ')
  const area = `0,${height/2} ${points} ${width},${height/2} ${width},${height} 0,${height}`
  return (
    <div className="momentum-chart">
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <line x1="0" y1={height/2} x2={width} y2={height/2} className="mid-line" />
        <polygon points={area} className="momentum-area" />
        <polyline points={points} className="momentum-line" />
      </svg>
      <div className="axis-row"><span>0'</span><span>15'</span><span>30'</span><span>HT</span><span>60'</span><span>75'</span><span>90'</span></div>
    </div>
  )
}

function Sparkline({ values }) {
  const width = 100
  const height = 26
  const min = Math.min(...values)
  const max = Math.max(...values)
  const normalized = values.map((value, index) => {
    const x = (index / (values.length - 1)) * width
    const y = height - ((value - min) / (max - min || 1)) * (height - 2) - 1
    return `${x},${y}`
  }).join(' ')
  return (
    <div className="sparkline-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <polyline points={normalized} className="sparkline" />
      </svg>
      <div className="axis-row small"><span>20 Mar</span><span>27 Mar</span><span>3 Abr</span><span>10 Abr</span><span>20 Abr</span></div>
    </div>
  )
}

function InfoPanel({ title, children }) {
  return <div className="panel simple-panel"><h2>{title}</h2>{children}</div>
}

export default function App() {
  const [nav, setNav] = useState('Partidos en vivo')
  const [fixtures, setFixtures] = useState(demoFixtures)
  const [oddsMap, setOddsMap] = useState({})
  const [status, setStatus] = useState('Modo demo premium')
  const [selectedId, setSelectedId] = useState(demoFixtures[0].id)
  const [coupon, setCoupon] = useState([{ id:'demo-1', match:'Flamengo vs Boca Juniors', market:'Over 2.5', odds:1.72, stake:10 }])
  const [watchlist, setWatchlist] = useState([2])
  const [search, setSearch] = useState('')
  const [marketCategory, setMarketCategory] = useState('Todos')
  const [alerts, setAlerts] = useState([
    { id:'a1', type:'market', text:'Value detectado en Over 2.5' },
    { id:'a2', type:'goal', text:"GOL 21' Flamengo 2-1 Boca Juniors" },
    { id:'a3', type:'market', text:'Modelo recalculado con edge positivo' },
  ])

  useEffect(() => {
    let mounted = true
    async function load() {
      try {
        const [live, odds] = await Promise.all([fetchLiveMatches(), fetchOdds()])
        if (!mounted) return

        const apiRows = live?.response || live?.data?.response
        if (Array.isArray(apiRows) && apiRows.length) {
          const normalized = apiRows.map(normalizeFixture)
          setFixtures(normalized)
          setSelectedId(normalized[0].id)
          setStatus('Datos reales activos')
        }

        const oddsRows = odds?.data || odds
        if (Array.isArray(oddsRows) && oddsRows.length) {
          setOddsMap(buildOddsMap(oddsRows))
          setStatus((prev) => prev === 'Datos reales activos' ? 'Datos reales + odds activas' : 'Odds activas')
        }
      } catch {}
    }
    load()
    return () => { mounted = false }
  }, [])

  const selected = useMemo(() => fixtures.find((f) => f.id === selectedId) || fixtures[0], [fixtures, selectedId])

  const model = useMemo(() => {
    if (!selected) return null
    const key = `${selected.home.name}__${selected.away.name}`
    return deriveQuantModel(selected, oddsMap[key] || {})
  }, [selected, oddsMap])

  const filteredFixtures = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return fixtures
    return fixtures.filter((f) => [f.home.name, f.away.name, f.competition.name].join(' ').toLowerCase().includes(q))
  }, [fixtures, search])

  const visibleMarkets = useMemo(() => {
    if (!model) return []
    if (marketCategory === 'Todos') return model.markets
    if (marketCategory === 'Resultado') return model.markets.filter((m) => ['homeWin','draw','awayWin','homeOrDraw','awayOrDraw','eitherWins'].includes(m.key))
    if (marketCategory === 'Goles') return model.markets.filter((m) => ['over25','under25','bttsYes','bttsNo','nextGoalHome','nextGoalAway','noNextGoal'].includes(m.key))
    if (marketCategory === 'HT') return model.markets.filter((m) => ['htDraw'].includes(m.key))
    return model.markets
  }, [model, marketCategory])

  const couponSummary = useMemo(() => {
    const stake = coupon.reduce((a,b) => a + b.stake, 0)
    const totalOdds = coupon.reduce((a,b) => a * b.odds, 1)
    return { stake, totalOdds, potential: stake * totalOdds }
  }, [coupon])

  const analytics = useMemo(() => {
    const totalStake = demoHistory.reduce((a,b) => a + b.stake, 0)
    const totalProfit = demoHistory.reduce((a,b) => a + b.profit, 0)
    const wins = demoHistory.filter((x) => x.result === 'WIN').length
    return {
      roi: totalStake ? (totalProfit / totalStake) * 100 : 0,
      accuracy: demoHistory.length ? (wins / demoHistory.length) * 100 : 0,
      yield: 12.3,
      bankroll: 7248.5,
      points: [0,35,60,150,90,120,30,75,95,200,140,180,155,245,190,230,170,310],
    }
  }, [])

  function addPick(label, odds) {
    const id = `${selected.id}-${label}`
    if (coupon.some((c) => c.id === id)) return
    setCoupon((prev) => [...prev, {
      id,
      match: `${selected.home.name} vs ${selected.away.name}`,
      market: label,
      odds: Number(odds),
      stake: 10,
    }])
  }

  function removePick(id) {
    setCoupon((prev) => prev.filter((p) => p.id !== id))
  }

  function toggleWatch(id) {
    setWatchlist((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [id, ...prev])
  }

  if (!selected || !model) return null

  return (
    <div className="app-shell">
      <aside className="sidebar panel">
        <div className="brand">
          <img src="/logos/zola-mark.svg" alt="ZOLA Elite" className="brand-logo" />
          <div>
            <h1>ZOLA Elite</h1>
            <p>Inteligencia aplicada al fútbol en tiempo real.</p>
          </div>
        </div>

        <div className="brand-mini-grid">
          <div className="mini-stat"><span>Live</span><strong>{fixtures.length} partidos</strong></div>
          <div className="mini-stat"><span>Estado</span><strong>{status}</strong></div>
        </div>

        <nav className="nav-list">
          {NAV.map((item) => (
            <button key={item} className={`nav-item ${nav === item ? 'active' : ''}`} onClick={() => setNav(item)}>
              <span>{item}</span>
              {item === 'Partidos en vivo' ? <span className="tag-live">LIVE</span> : null}
            </button>
          ))}
        </nav>

        <div className="panel stats-card">
          <h3>Estadísticas generales</h3>
          <div className="stat-line"><span>ROI</span><strong className="positive">+{analytics.roi.toFixed(1)}%</strong></div>
          <div className="stat-line"><span>Acierto</span><strong>{analytics.accuracy.toFixed(1)}%</strong></div>
          <div className="stat-line"><span>Yield</span><strong className="positive">+{analytics.yield}%</strong></div>
          <div className="stat-line"><span>Bankroll</span><strong>{formatMoney(analytics.bankroll)}</strong></div>
        </div>
      </aside>

      <main className="main-content">
        <div className="topbar panel">
          <input className="search-input" placeholder="Buscar partidos, ligas..." value={search} onChange={(e) => setSearch(e.target.value)} />
          <div className="topbar-right">
            <span className="api-pill">{status}</span>
            <span className="simple-link">Alertas {alerts.length}</span>
            <div className="avatar-pill">OA <span>Pro</span></div>
          </div>
        </div>

        {nav === 'Partidos en vivo' && (
          <>
            <div className="hero panel hero-first">
              <div className="hero-header">
                <div className="league-row">
                  <Logo src={selected.competition.logo} alt={selected.competition.name} className="competition-logo" fallback="🏆" />
                  <span>{selected.competition.name}</span>
                </div>
                <button className="ghost-icon" onClick={() => toggleWatch(selected.id)}>{watchlist.includes(selected.id) ? '★' : '☆'}</button>
              </div>

              <div className="match-hero">
                <TeamCard team={selected.home} />
                <div className="score-center">
                  <div className="status-row">
                    <span className="live-badge">{selected.status.short === 'NS' ? 'PRÓXIMO' : 'EN VIVO'}</span>
                    <span className="minute-badge">{selected.status.short === 'NS' ? '0' : `${selected.status.elapsed || 0}'`}</span>
                  </div>
                  <div className="score-big">{selected.goals.home} <span>-</span> {selected.goals.away}</div>
                  <div className="half-badges"><span>{selected.status.long}</span></div>
                  {selected.scorers?.length ? <div className="scorers-row">{selected.scorers.map((s) => <span key={s}>{s}</span>)}</div> : null}
                </div>
                <TeamCard team={selected.away} />
              </div>

              <div className="hero-stats">
                <MetricBar label="Posesión" left={selected.stats.possession[0]} right={selected.stats.possession[1]} />
                <MetricBar label="Tiros" left={selected.stats.shots[0]} right={selected.stats.shots[1]} />
                <MetricBar label="Tiros al arco" left={selected.stats.shotsOnTarget[0]} right={selected.stats.shotsOnTarget[1]} />
                <MetricBar label="Corners" left={selected.stats.corners[0]} right={selected.stats.corners[1]} />
                <MetricBar label="xG" left={selected.stats.xg[0]} right={selected.stats.xg[1]} decimal />
              </div>

              <div className="hero-tabs">
                {['Resumen', 'Estadísticas', 'Eventos', 'Enfrentamientos'].map((tab) => <button key={tab} className={`hero-tab ${tab === 'Resumen' ? 'active' : ''}`}>{tab}</button>)}
              </div>
            </div>

            <div className="alert-strip panel">
              {alerts.map((alert) => (
                <div key={alert.id} className={`alert-chip ${alert.type}`}>
                  <strong>{alert.type === 'goal' ? 'GOL' : 'MERCADO'}</strong>
                  <span>{alert.text}</span>
                </div>
              ))}
            </div>

            <div className="dashboard-grid">
              <section className="center-column">
                <div className="middle-grid">
                  <div className="panel section-pad">
                    <div className="row-between"><h3>Momentum del partido</h3><span className="muted">ⓘ</span></div>
                    <div className="legend-row">
                      <span><i className="dot red"></i>{selected.home.name}</span>
                      <span><i className="dot yellow"></i>{selected.away.name}</span>
                    </div>
                    <MomentumChart values={selected.momentum} />
                    <div className="row-between timeline-head"><h3>Línea de tiempo</h3></div>
                    <div className="timeline">
                      {(selected.timeline.length ? selected.timeline : [{ minute:"--", type:'info', title:'Sin eventos cargados', detail:'La API no envió eventos detallados en este momento.' }]).map((item) => (
                        <div className="timeline-item" key={`${item.minute}-${item.title}`}>
                          <span className="timeline-icon">{item.type === 'goal' ? '⚽' : item.type === 'red' ? '🟥' : '•'}</span>
                          <div><strong>{item.minute} {item.title}</strong><p>{item.detail}</p></div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="panel section-pad">
                    <div className="row-between"><h3>Predicción del modelo</h3><span className="trend-tag">Tendencia: ↑ {model.trend}</span></div>
                    <div className="prediction-main">
                      <div><span className="muted">Mercado principal</span><div className="prediction-score" style={{fontSize:'2.2rem'}}>{model.recommendation}</div></div>
                      <div className="prob-card"><span>Probabilidad</span><strong>{model.probability}%</strong></div>
                    </div>
                    <div className="alternative-grid">
                      {model.scoreScenarios.map((alt) => (
                        <div className="alternative-card" key={alt.label}><strong>{alt.label}</strong><span>Prob. {alt.prob}%</span></div>
                      ))}
                    </div>
                    <div className="panel section-note">
                      <h4>Lectura del modelo</h4>
                      <ul>{model.notes.map((n) => <li key={n}>{n}</li>)}</ul>
                    </div>
                  </div>
                </div>

                <div className="panel markets-panel">
                  <div className="row-between">
                    <div>
                      <h3>Motor de mercados</h3>
                      <div className="market-tabs">
                        {['Todos','Resultado','Goles','HT'].map((tab) => (
                          <button key={tab} className={`market-tab ${marketCategory === tab ? 'active' : ''}`} onClick={() => setMarketCategory(tab)}>{tab}</button>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="quant-market-table">
                    <div className="quant-head">
                      <span>Mercado</span>
                      <span>Prob. modelo</span>
                      <span>Cuota</span>
                      <span>Cuota justa</span>
                      <span>Edge</span>
                      <span>Estado</span>
                      <span></span>
                    </div>
                    {visibleMarkets.map((m) => (
                      <div key={m.key} className="quant-row">
                        <span>{m.label}</span>
                        <span>{m.probability}%</span>
                        <span>{Number(m.odds).toFixed(2)}</span>
                        <span>{m.fairOdds ? Number(m.fairOdds).toFixed(2) : '--'}</span>
                        <span className={m.edgePct > 0 ? 'positive' : m.edgePct < 0 ? 'negative' : ''}>
                          {m.edgePct > 0 ? '+' : ''}{m.edgePct.toFixed(1)}%
                        </span>
                        <span className={m.edgePct > 2 ? 'positive' : m.edgePct < -3 ? 'negative' : 'muted'}>{m.rating}</span>
                        <button className="primary-mini" onClick={() => addPick(m.label, m.odds)}>Añadir</button>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="panel list-panel">
                  <div className="row-between"><h3>Partidos en vivo</h3><span className="small-pill">{filteredFixtures.length}</span></div>
                  <div className="match-list">
                    {filteredFixtures.map((f) => (
                      <button key={f.id} className={`match-row ${selected.id === f.id ? 'active' : ''}`} onClick={() => setSelectedId(f.id)}>
                        <div>
                          <span className="muted">{f.competition.name}</span>
                          <div className="teams-inline">
                            <TeamInline team={f.home} />
                            <span>vs</span>
                            <TeamInline team={f.away} />
                          </div>
                        </div>
                        <div className="match-row-right">
                          <span>{f.status.short === 'NS' ? 'Próximo' : `${f.status.elapsed || 0}'`}</span>
                          <strong>{f.goals.home} - {f.goals.away}</strong>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </section>

              <aside className="right-column">
                <div className="panel ia-panel">
                  <div className="row-between"><h3>IA ZOLA</h3><span className="value-pill">Quant</span></div>
                  <div className="decision-box">
                    <TrafficLight active={model.traffic} />
                    <div>
                      <span className="muted">Decisión recomendada</span>
                      <h2>{model.recommendation}</h2>
                      <span className="green-chip">{model.topValue?.rating || 'VALUE'}</span>
                    </div>
                  </div>
                  <div className="confidence-box">
                    <div className="row-between"><span>Confianza del modelo</span><strong>{model.confidence}%</strong></div>
                    <div className="progress-track"><div className="progress-fill" style={{ width: `${model.confidence}%` }} /></div>
                  </div>
                  <div className="triple-metrics">
                    <div><span>Cuota justa</span><strong>{Number(model.fairOdds).toFixed(2)}</strong></div>
                    <div><span>Cuota actual</span><strong>{Number(model.currentOdds).toFixed(2)}</strong></div>
                    <div><span>Edge</span><strong className={model.edgePct > 0 ? 'positive' : ''}>{model.edgePct > 0 ? '+' : ''}{Number(model.edgePct).toFixed(1)}%</strong></div>
                  </div>
                </div>

                <div className="panel coupon-panel">
                  <div className="row-between"><h3>Cupón activo</h3><span className="small-pill green">{coupon.length} picks</span></div>
                  <div className="coupon-list">
                    {coupon.map((c) => (
                      <div className="coupon-item" key={c.id}>
                        <div><strong>{c.market}</strong><p>{c.match}</p></div>
                        <div className="coupon-side"><strong>{Number(c.odds).toFixed(2)}</strong><button className="remove-btn" onClick={() => removePick(c.id)}>✕</button></div>
                      </div>
                    ))}
                  </div>
                  <div className="summary-list">
                    <div><span>Cuota total</span><strong>{couponSummary.totalOdds.toFixed(2)}</strong></div>
                    <div><span>Stake total</span><strong>{formatMoney(couponSummary.stake)}</strong></div>
                    <div><span>Retorno potencial</span><strong className="positive">{formatMoney(couponSummary.potential)}</strong></div>
                  </div>
                </div>

                <div className="panel opportunity-panel">
                  <div className="row-between"><h3>Mejor oportunidad</h3><span className="top-value-pill">TOP VALUE</span></div>
                  <p className="muted">{selected.home.name} vs {selected.away.name} · {selected.competition.name}</p>
                  <h2>{model.topValue?.label || model.recommendation}</h2>
                  <div className="triple-metrics">
                    <div><span>Cuota</span><strong>{Number(model.topValue?.odds || model.currentOdds).toFixed(2)}</strong></div>
                    <div><span>Confianza</span><strong>{model.confidence}%</strong></div>
                    <div><span>Edge</span><strong className="positive">+{Number(model.topValue?.edgePct || 0).toFixed(1)}%</strong></div>
                  </div>
                  <div className="progress-track"><div className="progress-fill greenish" style={{ width: `${model.confidence}%` }} /></div>
                  <div className="row-actions">
                    <button className="primary-btn" onClick={() => addPick(model.topValue?.label || model.recommendation, model.topValue?.odds || model.currentOdds)}>Añadir al cupón</button>
                  </div>
                </div>
              </aside>
            </div>
          </>
        )}

        {nav === 'Mercados' && (
          <InfoPanel title="Mercados">
            <div className="quant-market-table">
              <div className="quant-head">
                <span>Mercado</span><span>Prob. modelo</span><span>Cuota</span><span>Cuota justa</span><span>Edge</span><span>Estado</span><span></span>
              </div>
              {model.markets.map((m) => (
                <div key={m.key} className="quant-row">
                  <span>{m.label}</span><span>{m.probability}%</span><span>{Number(m.odds).toFixed(2)}</span><span>{m.fairOdds ? Number(m.fairOdds).toFixed(2) : '--'}</span>
                  <span className={m.edgePct > 0 ? 'positive' : m.edgePct < 0 ? 'negative' : ''}>{m.edgePct > 0 ? '+' : ''}{m.edgePct.toFixed(1)}%</span>
                  <span>{m.rating}</span>
                  <button className="primary-mini" onClick={() => addPick(m.label, m.odds)}>Añadir</button>
                </div>
              ))}
            </div>
          </InfoPanel>
        )}

        {nav === 'Watchlist' && (
          <InfoPanel title="Watchlist">
            <div className="simple-list">
              {watchlist.map((id) => {
                const f = fixtures.find((x) => x.id === id)
                if (!f) return null
                return <div className="simple-row" key={id}><strong>{f.home.name} vs {f.away.name}</strong><span>{f.competition.name}</span></div>
              })}
            </div>
          </InfoPanel>
        )}

        {nav === 'Historial' && (
          <InfoPanel title="Historial">
            <div className="history-table">
              <div className="history-head"><span>Fecha</span><span>Apuesta</span><span>Cuota</span><span>Stake</span><span>Resultado</span><span>Profit</span></div>
              {demoHistory.map((h) => <div className="history-row" key={h.date+h.market}><span>{h.date}</span><span>{h.market}</span><span>{h.odds}</span><span>{formatMoney(h.stake)}</span><span className={h.result==='WIN'?'positive':'negative'}>{h.result}</span><span className={h.profit>0?'positive':'negative'}>{h.profit>0?'+':''}${h.profit.toFixed(2)}</span></div>)}
            </div>
          </InfoPanel>
        )}

        {nav === 'Bankroll' && (
          <InfoPanel title="Bankroll">
            <div className="analytics-grid">
              <div className="analytics-card"><span>ROI</span><strong className="positive">+{analytics.roi.toFixed(1)}%</strong></div>
              <div className="analytics-card"><span>Acierto</span><strong>{analytics.accuracy.toFixed(1)}%</strong></div>
              <div className="analytics-card"><span>Yield</span><strong className="positive">+{analytics.yield}%</strong></div>
              <div className="analytics-card"><span>Bankroll</span><strong>{formatMoney(analytics.bankroll)}</strong></div>
            </div>
            <Sparkline values={analytics.points} />
          </InfoPanel>
        )}

        {nav === 'Alertas' && (
          <InfoPanel title="Alertas">
            <div className="simple-list">
              {alerts.map((a) => <div className="simple-row" key={a.id}><strong>{a.type.toUpperCase()}</strong><span>{a.text}</span></div>)}
            </div>
          </InfoPanel>
        )}

        {nav === 'Configuración' && (
          <InfoPanel title="Configuración">
            <div className="simple-list">
              <div className="simple-row"><strong>Estado API</strong><span>{status}</span></div>
              <div className="simple-row"><strong>Seguridad</strong><span>Usa proxy serverless y no expone keys en producción.</span></div>
              <div className="simple-row"><strong>Modelo</strong><span>Motor cuantitativo web basado en score-probability + edge detection.</span></div>
              <div className="simple-row"><strong>Advertencia honesta</strong><span>No existe precisión 100% garantizada en predicción deportiva real.</span></div>
            </div>
          </InfoPanel>
        )}
      </main>
    </div>
  )
}
