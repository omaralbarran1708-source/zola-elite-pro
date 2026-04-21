const VITE_API_FOOTBALL_KEY = import.meta.env.VITE_API_FOOTBALL_KEY
const VITE_THE_ODDS_API_KEY = import.meta.env.VITE_THE_ODDS_API_KEY
const API_FOOTBALL_BASE_URL = import.meta.env.VITE_API_FOOTBALL_BASE_URL || 'https://v3.football.api-sports.io'
const THE_ODDS_BASE_URL = import.meta.env.VITE_THE_ODDS_BASE_URL || 'https://api.the-odds-api.com/v4'

async function getJson(url, options = {}, timeoutMs = 12000) {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(url, { ...options, signal: controller.signal })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    return await response.json()
  } finally {
    clearTimeout(id)
  }
}

export async function fetchLiveMatches() {
  try {
    const proxy = await getJson('/api/live-matches')
    if (proxy?.ok && proxy?.data) return proxy.data
  } catch {}

  if (VITE_API_FOOTBALL_KEY) {
    return getJson(`${API_FOOTBALL_BASE_URL}/fixtures?live=all`, {
      headers: { 'x-apisports-key': VITE_API_FOOTBALL_KEY }
    })
  }
  return null
}

export async function fetchOdds() {
  try {
    const proxy = await getJson('/api/odds')
    if (proxy?.ok && proxy?.data) return proxy.data
  } catch {}

  if (VITE_THE_ODDS_API_KEY) {
    return getJson(`${THE_ODDS_BASE_URL}/sports/soccer/odds/?apiKey=${VITE_THE_ODDS_API_KEY}&regions=eu&markets=h2h,totals,btts`)
  }
  return null
}
