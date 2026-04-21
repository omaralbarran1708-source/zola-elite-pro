function send(res, body, code = 200) {
  res.statusCode = code
  res.setHeader('Content-Type', 'application/json')
  res.end(JSON.stringify(body))
}

export default async function handler(req, res) {
  try {
    const key = process.env.THE_ODDS_API_KEY
    const baseUrl = process.env.THE_ODDS_BASE_URL || 'https://api.the-odds-api.com/v4'
    if (!key) return send(res, { ok: false, reason: 'missing_api_key' })

    const response = await fetch(`${baseUrl}/sports/soccer/odds/?apiKey=${key}&regions=eu&markets=h2h,totals,btts`)
    if (!response.ok) return send(res, { ok: false, status: response.status }, response.status)

    const data = await response.json()
    return send(res, { ok: true, data })
  } catch (error) {
    return send(res, { ok: false, reason: String(error?.message || error) }, 500)
  }
}
