# Datos, preparación y análisis exploratorio

## Origen

El proyecto usa dos fuentes con objetivos distintos:

| Fuente | Uso | Naturaleza |
|---|---|---|
| `data/raw/food_waste_pilot.db` | Entrenamiento y demostración de la aplicación | Piloto sintético reproducible |
| Eurostat `cei_pc035` | Contextualizar el problema de desperdicio alimentario | Fuente pública oficial |

La descarga de Eurostat está automatizada con `python -m src.fetch_eurostat_context`. La consulta solicita España, 2022, unidad `KG_HAB`. La respuesta descargada informa de **65 kg por habitante**. El indicador incluye desperdicio de toda la cadena de valor, por lo que no se utiliza como una medida de merma de supermercado ni como una variable del modelo.

## Modelo de datos del piloto

La base SQLite contiene seis entidades:

- `tiendas`: ubicación y tipología de cinco tiendas.
- `productos`: categoría, vida útil, precio y coste.
- `lotes`: entrada, unidades y caducidad de cada lote.
- `ventas`: transacciones por lote.
- `mermas`: unidades retiradas y coste asociado.
- `donaciones`: unidades y valor donado.

La base contiene 3.610 lotes, 16.300 ventas, 1.149 registros de merma y 724 donaciones.

## Preparación

`src.data_pipeline` genera una instantánea por lote y día de vida. Para cada fecha disponible solo usa ventas anteriores a esa fecha para calcular el stock estimado y la velocidad de venta; de este modo no incorpora ventas futuras en las variables de entrada.

Variables de entrada:

- tienda y tipo de ubicación;
- categoría;
- vida útil y días restantes;
- unidades recibidas y stock estimado;
- velocidad de venta diaria;
- precio, coste y día de la semana.

La variable objetivo es `hubo_merma`: toma valor 1 si el lote termina con una merma registrada.

Se verifican nulos y duplicados. El informe reproducible se genera en `data/processed/data_quality_report.json`.

## Hallazgos del piloto

Los importes siguientes se calculan desde `food_waste_pilot.db`:

| Hallazgo | Evidencia | Implicación |
|---|---:|---|
| Coste de merma acumulado | 17.422,10 EUR | Priorizar por impacto económico, no solo por unidades. |
| Mayor categoría expuesta | Platos preparados: 8.397,10 EUR | Revisar primero productos de vida corta como sushi y comida preparada. |
| Tres tiendas más expuestas | Eixample, Vallecas y Ruzafa: 16.196,60 EUR | Concentrar un piloto operativo en estas ubicaciones. |
| Tiendas con menor merma | Sarrià y Centro Madrid: 1.225,50 EUR | Comparar sus prácticas con las tiendas de mayor exposición. |
| Valor donado | 3.069,20 EUR | La donación es una alternativa que debe activarse antes de la retirada. |

Estas conclusiones describen el escenario simulado. Son útiles para probar el flujo analítico, no para atribuir pérdidas a un supermercado real.
