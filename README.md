# ZOLA Elite

Marcadores en vivo, tablas de posiciones y pronósticos de fútbol con modelo estadístico.

## Qué incluye

- **Partidos:** días para elegir, filtros (en vivo, próximos, terminados, favoritos), región, ligas fijadas arriba, barra de partidos en vivo y aviso cuando hay gol.
- **Detalle del partido:**
  - **Resumen:** quién gana, cuotas 1X2, apuesta de valor y análisis.
  - **Pronóstico:** mapa de marcadores y mercados.
  - **Estadísticas:** del partido y de la temporada.
  - **Eventos:** línea de tiempo del partido.
  - **Cara a cara.**
  - **Clasificación.**
  - **Cuotas.**
  - **Simulador:** con criterio Kelly.
- **Ligas:** competiciones del día con su tabla y sus partidos.
- **Mis pronósticos:** se guardan en el navegador y se cierran solos al terminar el partido (acierto %, unidades y evolución).
- **Temas:** claro y oscuro. La página se adapta a celular, con navegación inferior.
- **Actualización:** se refresca sola (lista cada 60 s, partido en vivo cada 45 s).

## Modelo (v2)

- **Ratings Dixon-Coles con decaimiento temporal:** con los resultados de la temporada (1 consulta por liga) estima el ataque y la defensa de cada equipo, la ventaja de local y rho. Los partidos recientes pesan más (vida media de 120 días). Si un equipo tiene pocos partidos, se acerca al promedio.
- **Respaldo:** si no hay resultados suficientes, usa los promedios de goles de la temporada (`/teams/statistics`).
- **Mezcla con el mercado:** la probabilidad final combina el modelo con la cuota sin margen (35 % por defecto). Las apuestas de valor se miden contra esa probabilidad combinada.
- **En vivo:** calcula solo los goles que faltan, con una tasa que sube a lo largo del partido. Usa el ritmo real (xG o tiros al arco), el marcador y las tarjetas rojas.
- **Probar modelo:** prueba walk-forward con temporadas reales de football-data.co.uk (gratis, con cuotas de cierre). Mide acierto, log-loss y Brier, y los compara con la casa y con una base de frecuencias. También mide la calibración y el ROI de las apuestas de valor.

## APIs recomendadas

| Para qué | API | Plan gratis |
|---|---|---|
| Partidos en vivo, eventos, estadísticas, cuotas, tablas | API-Football (api-sports.io) | 100 consultas/día; Pro 7.500/día |
| Probar el modelo con historia y cuotas de cierre | football-data.co.uk (CSV) | Gratis, sin key |
| Más casas y cuotas en vivo | The Odds API | 500 créditos/mes |

## Modelo (v1, notas)

Poisson con corrección Dixon-Coles. Usa los promedios reales de goles de la temporada (local/visita) y la forma reciente. En vivo, se ajusta según el tiempo restante, el ritmo del partido (xG o tiros al arco), el marcador y las tarjetas rojas. Compara la probabilidad del modelo con la cuota para encontrar apuestas de valor.

## Estructura

```
server.py         servidor (FastAPI): API JSON + logos en caché + interfaz
static/           interfaz (HTML, CSS, JS)
zola/model.py     modelo
zola/api.py       cliente de API-Football con caché
zola/data.py      datos (API real o demo)
zola/demo.py      datos de demostración
tests/            pruebas
```

## Uso local

```bash
pip install -r requirements-dev.txt
API_FOOTBALL_KEY=tu_key uvicorn server:app --reload
pytest -q
```

Sin `API_FOOTBALL_KEY` la página funciona en modo demo.

## Render

`render.yaml` ya está listo. El comando de arranque es `uvicorn server:app --host 0.0.0.0 --port $PORT`. Pon `API_FOOTBALL_KEY` en *Environment*.
