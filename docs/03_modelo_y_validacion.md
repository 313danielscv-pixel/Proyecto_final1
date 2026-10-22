# Métodos, evaluación y límites

ResQ Intelligence combina análisis descriptivo, cálculos operativos y escenarios. No todos los resultados son predicciones y la app identifica la naturaleza de cada uno.

## Referencia de demanda con datos reales

La pestaña **Demanda real** compara dos métodos sobre FreshRetailNet-50K y el mismo holdout temporal. La referencia estacional predice la venta observada siete días antes. La media móvil usa la media de los últimos siete días de entrenamiento, constante durante los siete días de evaluación. Se seleccionan de manera determinista hasta 100 series.

| Métrica | Resultado documentado |
|---|---:|
| Observaciones evaluadas | 700 |
| MAE — referencia estacional | 0,5109 |
| RMSE — referencia estacional | 0,8352 |
| MAE — media móvil de 7 días | 0,4813 |
| RMSE — media móvil de 7 días | 0,7847 |

La separación es temporal: ambos métodos se ajustan con datos anteriores y se comparan con el mismo periodo posterior. En esta evaluación la media móvil reduce el error frente a la referencia, pero el resultado no garantiza la misma precisión en otro comercio. La fuente, licencia, preparación y límites se detallan en [07_datos_reales_y_demanda.md](07_datos_reales_y_demanda.md).

## Cálculos de inventario y lotes

La vista de inventario calcula cobertura a partir de unidades disponibles y demanda media por producto-día natural desde el primer registro del producto hasta el final del extracto, solo después de confirmar que este cubre todos los días del periodo. Sin confirmación, la media usa fechas con registro y las señales de inventario se identifican como provisionales. Un stock positivo con demanda registrada igual a cero se marca como sobrestock, no equilibrado. También estima capital expuesto como unidades en stock por coste unitario, y marca señales de rotura o sobrestock con los campos de plazo de reposición y stock mínimo cuando existen.

El módulo empresarial de lotes no es un clasificador entrenado: es una estimación determinista basada en demanda diaria de calendario, stock disponible y días hasta la fecha límite. El resultado se expresa como proporción estimada de stock no vendido. Requiere 30 días naturales de historial por producto y no debe confundirse con una probabilidad de merma. Las bandas y recomendaciones usan la misma proporción redondeada a una décima porcentual que se muestra en pantalla para evitar discrepancias en los límites.

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
