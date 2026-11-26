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

## Modelo

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
