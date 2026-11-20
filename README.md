# ZOLA Elite

Pronósticos de fútbol con datos reales de API-Football, en Streamlit.

## Qué hace

- **Modelo real:** Poisson con corrección Dixon-Coles. La fuerza de cada equipo sale de sus goles a favor y en contra de la temporada (como local y como visita) y de su forma reciente. Si un equipo tiene pocos partidos, el modelo lo acerca al promedio de la liga.
- **En vivo:** calcula solo los goles que faltan. Usa los minutos restantes, el ritmo del partido (xG o tiros al arco), el marcador (quien pierde ataca más) y las tarjetas rojas.
- **Datos reales del partido:** eventos (goles, tarjetas, cambios), estadísticas y cuotas de API-Football (Bet365 por defecto). Ya no se inventa nada. Sin API key, la app muestra datos de demo marcados como **DEMO**.
- **Apuestas de valor:** compara la probabilidad del modelo con la cuota y calcula la ventaja. Descarta los mercados que ya están decididos.
- **Simulador:** valor esperado y stake sugerido con ¼ de Kelly según tu bankroll.
- **Historial con aciertos:** guardas una predicción con un botón y no se duplica. Cuando el partido termina, la app marca ✅ o ❌ y calcula el porcentaje de acierto y las unidades ganadas.

## Estructura

```
app.py            interfaz
zola/model.py     modelo (Poisson + Dixon-Coles + ajuste en vivo + valor/Kelly)
zola/api.py       cliente de API-Football con caché (cuida las 100 consultas/día del plan gratis)
zola/data.py      une API/demo con el modelo, filtros y cierre del historial
zola/db.py        historial SQLite
zola/status.py    estados de partido y grupos de ligas (por ID)
zola/demo.py      datos de demo
tests/            pruebas (pytest)
```

## Uso local

```bash
pip install -r requirements-dev.txt
streamlit run app.py
pytest -q
```

La API key se toma, en este orden, de `.streamlit/secrets.toml`, de la variable de entorno `API_FOOTBALL_KEY` o del panel ⚙️ Configuración.

## Render

`render.yaml` ya está listo. En Render, agrega `API_FOOTBALL_KEY` en *Environment*.
Ojo: en el plan gratis el disco se borra en cada deploy o reinicio, así que el historial no se conserva. Si quieres conservarlo, agrega un disco y apunta `ZOLA_DB_PATH` a él.

> Las probabilidades son estimaciones, no garantías. +18.
