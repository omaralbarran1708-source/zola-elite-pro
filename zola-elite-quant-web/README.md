# ZOLA Elite Quant Web

Versión web ampliada con:
- partido principal arriba desde el inicio
- lectura de fixtures y odds reales cuando configuras APIs
- motor propio de evaluación de mercados
- análisis de:
  - 1X2
  - Over/Under
  - Ambos marcan
  - Doble oportunidad
  - Resultado HT
  - Próximo gol
  - marcador correcto demo/estimado
- detección de value por diferencia entre probabilidad del modelo y probabilidad implícita
- proxy serverless seguro para Vercel

## Ejecutar
```bash
npm install
npm run dev
```

## Deploy Vercel
1. Subir repo a GitHub
2. Importar en Vercel
3. Variables:
   - API_FOOTBALL_KEY
   - THE_ODDS_API_KEY
   - API_FOOTBALL_BASE_URL
   - THE_ODDS_BASE_URL

## Nota honesta
Esta versión sí aplica una inferencia propia en la web, pero no reemplaza un pipeline real de entrenamiento histórico con modelos avanzados. Ya queda preparada para crecer hacia eso.
