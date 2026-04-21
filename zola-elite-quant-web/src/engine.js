export function normalizeFixture(raw, index = 0) {
  return {
    id: raw?.fixture?.id || raw?.id || index + 1,
    competition: {
      name: raw?.league?.name || raw?.competition?.name || 'Competición',
      logo: raw?.league?.logo || raw?.competition?.logo || '',
    },
    status: {
      short: raw?.fixture?.status?.short || raw?.status?.short || 'LIVE',
      elapsed: raw?.fixture?.status?.elapsed || raw?.status?.elapsed || 0,
      long: raw?.fixture?.status?.long || raw?.status?.long || 'In play',
    },
    home: {
      name: raw?.teams?.home?.name || raw?.home?.name || `Local ${index + 1}`,
      logo: raw?.teams?.home?.logo || raw?.home?.logo || '',
    },
    away: {
      name: raw?.teams?.away?.name || raw?.away?.name || `Visita ${index + 1}`,
      logo: raw?.teams?.away?.logo || raw?.away?.logo || '',
    },
    goals: {
      home: raw?.goals?.home ?? 0,
      away: raw?.goals?.away ?? 0,
    },
    stats: raw?.stats || raw?.statistics || { possession:[50,50], shots:[0,0], shotsOnTarget:[0,0], corners:[0,0], xg:[1.0,1.0] },
    momentum: raw?.momentum || [0,1,0,1,2,1,0,-1,0,1],
    timeline: raw?.timeline || [],
    scorers: raw?.scorers || [],
  }
}

export function buildOddsMap(oddsArray) {
  const map = {}
  if (!Array.isArray(oddsArray)) return map
  for (const item of oddsArray) {
    const key = `${item?.home_team}__${item?.away_team}`
    if (!item?.home_team || !item?.away_team) continue
    const row = {}
    for (const bookmaker of item?.bookmakers || []) {
      for (const market of bookmaker?.markets || []) {
        const mk = market?.key
        if (mk === 'h2h') {
          for (const outcome of market?.outcomes || []) {
            if (outcome?.name === item.home_team) row.homeWin = Number(outcome?.price)
            if (outcome?.name === item.away_team) row.awayWin = Number(outcome?.price)
            if (String(outcome?.name).toLowerCase() === 'draw') row.draw = Number(outcome?.price)
          }
        }
        if (mk === 'totals') {
          const over = (market?.outcomes || []).find((o) => String(o?.name).toLowerCase().includes('over'))
          const under = (market?.outcomes || []).find((o) => String(o?.name).toLowerCase().includes('under'))
          if (over?.price) row.over25 = Number(over.price)
          if (under?.price) row.under25 = Number(under.price)
        }
        if (mk === 'btts') {
          const yes = (market?.outcomes || []).find((o) => String(o?.name).toLowerCase() === 'yes')
          const no = (market?.outcomes || []).find((o) => String(o?.name).toLowerCase() === 'no')
          if (yes?.price) row.bttsYes = Number(yes.price)
          if (no?.price) row.bttsNo = Number(no.price)
        }
      }
    }
    map[key] = row
  }
  return map
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}

function poisson(lambda, k) {
  if (lambda <= 0) return k === 0 ? 1 : 0
  return Math.exp(-lambda) * Math.pow(lambda, k) / factorial(k)
}

const factCache = {0:1,1:1}
function factorial(n) {
  if (factCache[n]) return factCache[n]
  let acc = 1
  for (let i = 2; i <= n; i += 1) acc *= i
  factCache[n] = acc
  return acc
}

function impliedProb(odds) {
  return odds ? 1 / Number(odds) : null
}

function fairOdds(prob) {
  return prob > 0 ? 1 / prob : null
}

function edgeFromProb(modelProb, odds) {
  const implied = impliedProb(odds)
  if (!implied) return null
  return modelProb - implied
}

function normalizeScoreProbs(homeLambda, awayLambda, maxGoals = 6) {
  const matrix = []
  let total = 0
  for (let h = 0; h <= maxGoals; h += 1) {
    for (let a = 0; a <= maxGoals; a += 1) {
      const p = poisson(homeLambda, h) * poisson(awayLambda, a)
      matrix.push({ h, a, p })
      total += p
    }
  }
  return matrix.map((x) => ({ ...x, p: x.p / total }))
}

function probabilityFromMatrix(matrix, predicate) {
  return matrix.filter(predicate).reduce((acc, row) => acc + row.p, 0)
}

export function deriveQuantModel(match, oddsRow = {}) {
  const posHome = Number(match.stats?.possession?.[0] ?? 50)
  const posAway = Number(match.stats?.possession?.[1] ?? 50)
  const sotHome = Number(match.stats?.shotsOnTarget?.[0] ?? 0)
  const sotAway = Number(match.stats?.shotsOnTarget?.[1] ?? 0)
  const shotsHome = Number(match.stats?.shots?.[0] ?? 0)
  const shotsAway = Number(match.stats?.shots?.[1] ?? 0)
  const cornersHome = Number(match.stats?.corners?.[0] ?? 0)
  const cornersAway = Number(match.stats?.corners?.[1] ?? 0)
  const xgHome = Number(match.stats?.xg?.[0] ?? 1.0)
  const xgAway = Number(match.stats?.xg?.[1] ?? 1.0)
  const goalsHome = Number(match.goals?.home ?? 0)
  const goalsAway = Number(match.goals?.away ?? 0)
  const totalGoals = goalsHome + goalsAway
  const minute = Number(match.status?.elapsed ?? 0)

  const timeFactor = clamp((90 - minute) / 90, 0.08, 1)
  const momentumBias = ((posHome - posAway) / 100) + ((sotHome - sotAway) * 0.03)
  const homeLambda = clamp((xgHome * 0.72 + shotsHome * 0.035 + sotHome * 0.12 + cornersHome * 0.02 + Math.max(momentumBias, -0.2)) * timeFactor + goalsHome * 0.1, 0.15, 3.8)
  const awayLambda = clamp((xgAway * 0.72 + shotsAway * 0.035 + sotAway * 0.12 + cornersAway * 0.02 + Math.max(-momentumBias, -0.2)) * timeFactor + goalsAway * 0.1, 0.15, 3.8)

  const matrix = normalizeScoreProbs(homeLambda, awayLambda, 6)
  const pHomeWin = probabilityFromMatrix(matrix, (x) => x.h > x.a)
  const pDraw = probabilityFromMatrix(matrix, (x) => x.h === x.a)
  const pAwayWin = probabilityFromMatrix(matrix, (x) => x.h < x.a)
  const pOver25 = probabilityFromMatrix(matrix, (x) => x.h + x.a >= 3)
  const pUnder25 = 1 - pOver25
  const pBTTS = probabilityFromMatrix(matrix, (x) => x.h >= 1 && x.a >= 1)
  const pNoBTTS = 1 - pBTTS
  const pHomeOrDraw = pHomeWin + pDraw
  const pAwayOrDraw = pAwayWin + pDraw
  const pEitherWins = pHomeWin + pAwayWin
  const pHTDraw = clamp(0.28 + (Math.abs(posHome - posAway) < 8 ? 0.08 : -0.03) + (minute < 35 ? 0.05 : 0), 0.18, 0.55)

  let pNextGoalHome = clamp(0.5 + (xgHome - xgAway) * 0.18 + (sotHome - sotAway) * 0.03 + (posHome - posAway) * 0.004, 0.12, 0.78)
  let pNextGoalAway = clamp(1 - pNextGoalHome - 0.12, 0.08, 0.70)
  let pNoNextGoal = clamp(1 - pNextGoalHome - pNextGoalAway, 0.08, 0.55)
  const rebalance = pNextGoalHome + pNextGoalAway + pNoNextGoal
  pNextGoalHome /= rebalance
  pNextGoalAway /= rebalance
  pNoNextGoal /= rebalance

  const sortedScores = [...matrix].sort((a, b) => b.p - a.p).slice(0, 3).map((s) => ({
    label: `${s.h} - ${s.a}`,
    prob: Math.round(s.p * 100),
  }))

  const markets = [
    { key:'homeWin', label:`${match.home.name} gana`, prob:pHomeWin, odds: oddsRow.homeWin },
    { key:'draw', label:'Empate', prob:pDraw, odds: oddsRow.draw },
    { key:'awayWin', label:`${match.away.name} gana`, prob:pAwayWin, odds: oddsRow.awayWin },
    { key:'over25', label:'Over 2.5', prob:pOver25, odds: oddsRow.over25 || 1.88 },
    { key:'under25', label:'Under 2.5', prob:pUnder25, odds: oddsRow.under25 || 1.95 },
    { key:'bttsYes', label:'BTTS Sí', prob:pBTTS, odds: oddsRow.bttsYes || 1.80 },
    { key:'bttsNo', label:'BTTS No', prob:pNoBTTS, odds: oddsRow.bttsNo || 1.92 },
    { key:'homeOrDraw', label:'1X', prob:pHomeOrDraw, odds: oddsRow.homeOrDraw || 1.28 },
    { key:'awayOrDraw', label:'X2', prob:pAwayOrDraw, odds: oddsRow.awayOrDraw || 1.55 },
    { key:'eitherWins', label:'12', prob:pEitherWins, odds: oddsRow.eitherWins || 1.30 },
    { key:'htDraw', label:'Empate primer tiempo', prob:pHTDraw, odds: oddsRow.htDraw || 2.00 },
    { key:'nextGoalHome', label:`Próximo gol ${match.home.name}`, prob:pNextGoalHome, odds: oddsRow.nextGoalHome || 2.10 },
    { key:'nextGoalAway', label:`Próximo gol ${match.away.name}`, prob:pNextGoalAway, odds: oddsRow.nextGoalAway || 3.10 },
    { key:'noNextGoal', label:'No habrá más goles', prob:pNoNextGoal, odds: oddsRow.noNextGoal || 4.30 },
  ].map((m) => {
    const implied = impliedProb(m.odds)
    const edge = edgeFromProb(m.prob, m.odds)
    return {
      ...m,
      probability: Math.round(m.prob * 100),
      fairOdds: fairOdds(m.prob),
      impliedProbability: implied ? implied * 100 : null,
      edgePct: edge ? edge * 100 : 0,
      rating: edge && edge > 0.05 ? 'Top value' : edge && edge > 0.02 ? 'Value' : edge && edge < -0.03 ? 'Sobrepreciado' : 'Neutral',
    }
  })

  const topValue = [...markets].sort((a, b) => b.edgePct - a.edgePct)[0]
  const recommendation = topValue?.label || 'Over 2.5'
  const confidence = clamp(Math.round(58 + Math.abs(posHome - posAway) * 0.3 + (sotHome + sotAway) * 1.6 + totalGoals * 4), 52, 91)
  const traffic = confidence >= 79 ? 'green' : confidence >= 64 ? 'yellow' : 'red'
  const trend = posHome >= posAway ? `Favorable ${match.home.name}` : `Favorable ${match.away.name}`
  const notes = [
    `${match.home.name} vs ${match.away.name}: modelo cuantitativo ajustado por posesión, tiros, xG y tiempo restante.`,
    `La proyección principal favorece ${topValue?.label || 'mercado principal'} con edge estimado de ${(topValue?.edgePct || 0).toFixed(1)}%.`,
    `El motor usa una capa Poisson simplificada para score y una capa heurística para mercados live como próximo gol y HT.`,
  ]

  return {
    recommendation,
    confidence,
    traffic,
    trend,
    probability: topValue?.probability || 55,
    fairOdds: topValue?.fairOdds || 1.75,
    currentOdds: topValue?.odds || 1.90,
    edgePct: topValue?.edgePct || 0,
    topValue,
    scoreScenarios: sortedScores,
    markets,
    notes,
    pHomeWin, pDraw, pAwayWin, pOver25, pBTTS,
  }
}
