# Datos reales y previsión de demanda

## Fuente

El módulo de demanda real utiliza **FreshRetailNet-50K**, publicado por Dingdong Inc.:

- fuente oficial: <https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K>;
- licencia declarada por el proveedor: **CC BY 4.0**;
- particiones usadas: `train.parquet` y `eval.parquet`;
- fecha de descarga: 20 de octubre de 2026.

Los datos contienen ventas de productos perecederos, tienda, producto, descuentos, promociones, festivos, variables meteorológicas y anotaciones de rotura de stock. No contienen los costes internos, precios finales, caducidades ni mermas de una empresa usuaria.

## Preparación

`src.real_demand` selecciona de manera determinista las primeras 100 combinaciones ordenadas de tienda y producto. Usa las observaciones anteriores de entrenamiento para producir una previsión de referencia sobre los siete días posteriores de evaluación.

El conjunto bruto no se incluye en el repositorio por su tamaño. La plataforma conserva los resultados derivados y documenta cómo regenerarlos:

```powershell
python -m src.real_demand
```

Antes de ejecutar el comando deben descargarse las particiones oficiales en `data/external/freshretailnet/`. La instalación con `python -m pip install -r requirements.txt` incluye `pyarrow`, necesario para leer Parquet.

## Evaluación

Se usa una referencia estacional ingenua: la predicción de cada día es la venta observada siete días antes del mismo producto-tienda. Es una línea base deliberadamente simple, no un modelo de producción.

| Métrica | Resultado |
|---|---:|
| Observaciones de evaluación | 700 |
| MAE | 0,5109 |
| RMSE | 0,8352 |

La evaluación es temporal: el entrenamiento termina antes de las fechas de evaluación. No se usan ventas futuras para generar la previsión.

## Limitaciones

1. El resultado demuestra previsión de demanda con ventas reales, no predicción de merma.
2. El subconjunto de 100 series es una demostración reproducible; no representa todos los comercios.
3. Una empresa usuaria debe entrenar y evaluar sus propios modelos con su historial antes de operar con sus decisiones.
4. El módulo de escenarios no infiere la elasticidad de precios de FreshRetailNet; el usuario declara ese supuesto de forma explícita.
