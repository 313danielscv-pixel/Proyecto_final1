# Métodos, evaluación y límites

ResQ Intelligence combina análisis descriptivo, cálculos operativos y escenarios. No todos los resultados son predicciones y la app identifica la naturaleza de cada uno.

## Referencia de demanda con datos reales

La pestaña **Demanda real** evalúa una línea base estacional ingenua sobre FreshRetailNet-50K. Para cada producto-tienda, la predicción de un día es la venta observada siete días antes. El proceso selecciona de manera determinista hasta 100 series y evalúa los siete días disponibles en el periodo de evaluación.

| Métrica | Resultado documentado |
|---|---:|
| Observaciones evaluadas | 700 |
| MAE | 0,5109 |
| RMSE | 0,8352 |

La separación es temporal: la referencia usa observaciones anteriores y se compara con un periodo posterior. MAE y RMSE resumen el error de esa evaluación; no garantizan la misma precisión en otro comercio. La fuente, licencia, preparación y límites se detallan en [07_datos_reales_y_demanda.md](07_datos_reales_y_demanda.md).

## Cálculos de inventario y lotes

La vista de inventario calcula cobertura a partir de unidades disponibles y demanda media por producto-día observado. También estima capital expuesto como unidades en stock por coste unitario, y marca señales de rotura o sobrestock con los campos de plazo de reposición y stock mínimo cuando existen.

El módulo empresarial de lotes no es un clasificador entrenado: es una estimación determinista basada en demanda histórica, stock disponible y días hasta la fecha límite. El resultado se expresa como proporción estimada de stock no vendido. Requiere al menos 30 días de ventas observadas por producto y no debe confundirse con una probabilidad de merma.

## Escenarios y sensibilidad

El simulador compara margen base y margen bajo cambios introducidos por la persona usuaria en precio y demanda, descontando coste de producto y almacenamiento. La matriz de sensibilidad varía supuestos de precio y demanda en un rango ilustrativo de −20 % a +20 %.

La matriz responde a “¿qué pasaría si…?” bajo las fórmulas y valores introducidos. No predice la reacción real de la demanda ante el precio, no asigna probabilidades a los escenarios y no mide ahorros realizados.

## EDA y validación

Los análisis estadísticos son exploratorios: resumen distribuciones, diferencias entre dos grupos, relaciones, cambios temporales y estabilidad de distribuciones. El bootstrap estima un intervalo de la media bajo el supuesto de independencia. PSI compara distribuciones entre dos periodos. K-Means agrupa observaciones según las variables elegidas. Ninguno identifica por sí solo una causa ni valida una intervención empresarial.

## Continuidad del piloto ResQData/FreshMarket

El repositorio conserva el pipeline y el clasificador Random Forest del piloto histórico de merma. Se entrenaron con datos sintéticos y se dividieron los datos agrupando por lote para evitar que instantáneas del mismo lote aparezcan a ambos lados de la validación. Es una evidencia de desarrollo del caso original, no un modelo activo de ResQ Intelligence ni una métrica de rendimiento en producción. FreshMarket debe presentarse siempre como escenario sintético.

## Qué sería necesario antes de operar

1. Validar los contratos y las reglas con datos reales anonimizados de la empresa.
2. Comparar modelos de demanda con una separación temporal y métricas adecuadas al negocio.
3. Calibrar cualquier probabilidad con datos representativos antes de usarla como probabilidad.
4. Medir las decisiones mediante un piloto controlado; no atribuir causalidad a una comparación observacional.
5. Vigilar cambios de calidad y distribución, y revisar las recomendaciones con responsables humanos.
