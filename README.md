# Dashboard Urdido PH

Dashboard de análisis de producción, roturas, tiempos perdidos y comentarios.

## Estructura
- index.html — dashboard
- data/ — CSVs de datos
- netlify/functions/ — backend serverless

## Cómo agregar un día nuevo
1. Subir los 3 CSV a data/
2. Esperar 1 minuto
3. Recargar el dashboard

## Cómo funciona
- Auto-descubre fechas en data/
- Los comentarios se guardan vía Netlify Function en data/comentarios.csv

## URLs
- Dashboard: https://ph-urdido.netlify.app/
- Repo: https://github.com/fherross3-ops/PH_urdido
