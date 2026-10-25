# Datos reales y previsión de demanda

## Fuente

El módulo de demanda real utiliza **FreshRetailNet-50K**, publicado por Dingdong Inc.:

- fuente oficial: <https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K>;
- licencia declarada por el proveedor: **CC BY 4.0**;
- particiones usadas: `train.parquet` y `eval.parquet`;
- fecha de descarga: 20 de octubre de 2026.

Los datos contienen ventas de productos perecederos, tienda, producto, descuentos, promociones, festivos, variables meteorológicas y anotaciones de rotura de stock. No contienen los costes internos, precios finales, caducidades ni mermas de una empresa usuaria.

Las particiones locales cubren del **28 de marzo al 2 de julio de 2024**: 4.500.000 filas de entrenamiento y 350.000 de evaluación en la fuente completa. Son suficientes para demostrar y comparar métodos de previsión con un corte temporal, pero son datos históricos y no representan la demanda actual de una empresa en 2026.

Eurostat `cei_pc035` se utiliza como contexto nacional del desperdicio alimentario. Además, el proyecto incorpora el índice mensual `sts_trtu_m` para ventas minoristas de alimentos, bebidas y tabaco en España. La consulta oficial se guarda en `data/external/eurostat_food_retail_volume_spain.json` y se puede actualizar con `python -m src.fetch_eurostat_retail_context`; el último dato disponible en la descarga del 24 de octubre de 2026 es agosto de 2026 (índice 109,9; 2021=100).

Estos indicadores nacionales aportan actualidad y contexto, pero no tienen el detalle tienda-producto-día necesario para unirlos a FreshRetailNet o usarlos como predictores. Se mantienen como referencias separadas. La previsión por producto sigue siendo una evaluación histórica, no una previsión actual de una empresa.

## Preparación

`src.real_demand` selecciona de manera determinista hasta 100 combinaciones de tienda y producto con historial suficiente. Compara dos métodos sobre los mismos siete días posteriores al entrenamiento:

1. **Referencia estacional ingenua:** predice la venta observada siete días antes.
2. **Media móvil de 7 días:** promedia los últimos siete días de entrenamiento y mantiene esa estimación constante durante el horizonte de siete días.

Ambos métodos se comparan en una separación temporal; las ventas del periodo de evaluación no se usan para calcular la media móvil.

El conjunto bruto no se incluye en el repositorio por su tamaño. La plataforma conserva los resultados derivados y documenta cómo regenerarlos:

```powershell
python -m src.real_demand
```

Para regenerar la evaluación:

1. Abre la [fuente oficial de FreshRetailNet-50K](https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K) y descarga `train.parquet` y `eval.parquet` de la misma versión.
2. Guarda ambos archivos en `data/external/freshretailnet/`, con esos nombres exactos. La carpeta se crea automáticamente si hace falta.
3. Instala dependencias con `python -m pip install -r requirements.txt`.
4. Ejecuta `python -m src.real_demand`.

Los archivos Parquet brutos no se versionan por su tamaño. La demo reproducible usa el CSV de ventas derivado incluido en `data/demo/`; el inventario, los costes y los lotes de esa demo son supuestos sintéticos.

El contexto Eurostat se obtiene con `python -m src.fetch_eurostat_context`; el resultado registra fuente, licencia y fecha de descarga UTC. Su reutilización requiere atribuir a Eurostat (Unión Europea), conforme a su [política de reutilización](https://ec.europa.eu/eurostat/help/copyright-notice).

## Evaluación

La comparación usa 100 series de tienda-producto y el mismo conjunto de 700 observaciones de evaluación:

| Métrica | Resultado |
|---|---:|
| Observaciones de evaluación | 700 |
| MAE — referencia estacional | 0,5109 |
| RMSE — referencia estacional | 0,8352 |
| MAE — media móvil de 7 días | 0,4813 |
| RMSE — media móvil de 7 días | 0,7847 |

En este conjunto la media móvil obtiene menor MAE y RMSE que la referencia estacional. La evaluación es temporal: el entrenamiento termina antes de las fechas de evaluación. Estos resultados describen este subconjunto público y no garantizan el rendimiento en otra tienda o empresa.

## Limitaciones

1. El resultado demuestra previsión de demanda con ventas reales, no predicción de merma.
2. El subconjunto de 100 series es una demostración reproducible; no representa todos los comercios.
3. Una empresa usuaria debe entrenar y evaluar sus propios modelos con su historial antes de operar con sus decisiones.
4. El módulo de escenarios no infiere la elasticidad de precios de FreshRetailNet; el usuario declara ese supuesto de forma explícita.
