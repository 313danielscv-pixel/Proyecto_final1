# Datos reales y previsión de demanda

## Fuente

El módulo de demanda real utiliza **FreshRetailNet-50K**, publicado por Dingdong Inc.:

- fuente oficial: <https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K>;
- licencia declarada por el proveedor: **CC BY 4.0**;
- particiones usadas: `train.parquet` y `eval.parquet`;
- fecha de descarga: 20 de octubre de 2026.

Los datos contienen ventas de productos perecederos, tienda, producto, descuentos, promociones, festivos, variables meteorológicas y anotaciones de rotura de stock. No contienen los costes internos, precios finales, caducidades ni mermas de una empresa usuaria.

## Preparación

`src.real_demand` selecciona de manera determinista hasta 100 combinaciones de tienda y producto con historial suficiente. Compara dos métodos sobre los mismos siete días posteriores al entrenamiento:

1. **Referencia estacional ingenua:** predice la venta observada siete días antes.
2. **Media móvil de 7 días:** promedia los últimos siete días de entrenamiento y mantiene esa estimación constante durante el horizonte de siete días.

Ambos métodos se comparan en una separación temporal; las ventas del periodo de evaluación no se usan para calcular la media móvil.

El conjunto bruto no se incluye en el repositorio por su tamaño. La plataforma conserva los resultados derivados y documenta cómo regenerarlos:

```powershell
python -m src.real_demand
```

Antes de ejecutar el comando deben descargarse las particiones oficiales en `data/external/freshretailnet/`. La instalación con `python -m pip install -r requirements.txt` incluye `pyarrow`, necesario para leer Parquet.

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
