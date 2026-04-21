function send(res, body, code = 200) {
  res.statusCode = code
  res.setHeader('Content-Type', 'application/json')
  res.end(JSON.stringify(body))
}

export default async function handler(req, res) {
  try {
    const key = process.env.API_FOOTBALL_KEY
    const baseUrl = process.env.API_FOOTBALL_BASE_URL || 'https://v3.football.api-sports.io'
    if (!key) return send(res, { ok: false, reason: 'missing_api_key' })

    const response = await fetch(`${baseUrl}/fixtures?live=all`, {
      headers: { 'x-apisports-key': key }
    })
    if (!response.ok) return send(res, { ok: false, status: response.status }, response.status)

    const data = await response.json()
    return send(res, { ok: true, data })
  } catch (error) {
    return send(res, { ok: false, reason: String(error?.message || error) }, 500)
  }
}
