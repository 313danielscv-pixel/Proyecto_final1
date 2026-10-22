# Datos, preparación y análisis exploratorio

## Fuentes y uso

| Fuente | Uso en el proyecto | Naturaleza y límite |
|---|---|---|
| Archivos CSV/Excel de empresa | Análisis de ventas, inventario, costes, lotes y EDA libre | Datos aportados por el usuario; se conservan en la sesión de Streamlit, no en el repositorio. |
| FreshRetailNet-50K | Demostración y evaluación de una referencia de demanda | Ventas reales publicadas por Dingdong Inc.; licencia declarada CC BY 4.0. No contiene los costes ni las caducidades de la empresa usuaria. |
| Piloto FreshMarket | Desarrollo y demostración histórica del caso de merma | Datos sintéticos; no describen una empresa real ni se usan como datos de clientes. |
| Eurostat `cei_pc035` | Contexto agregado del desperdicio alimentario | Estadística pública de toda la cadena de valor; no mide la merma de una tienda concreta ni alimenta el cálculo de riesgo por lote. |

Los detalles de FreshRetailNet, sus filtros, evaluación y licencia están en [Datos reales y previsión](07_datos_reales_y_demanda.md).

## Ingesta y calidad

La app tiene dos rutas de carga:

- **Carga por contrato:** normaliza alias conocidos y valida los campos requeridos por ventas, inventario, costes, proveedores o lotes.
- **Carga libre para EDA:** conserva las columnas originales de un CSV o Excel, aunque no coincidan con un contrato empresarial.

La validación informa de campos requeridos ausentes, conversiones inválidas, valores que requieren revisión y duplicados. Los duplicados no se eliminan automáticamente. Un valor negativo se comunica como advertencia: su validez depende del significado de esa columna y de las reglas de negocio.

## Preparación de demanda e inventario

Para calcular demanda media por producto y día:

1. Se normaliza la fecha a día.
2. Se suman las transacciones del mismo producto en el mismo día.
3. Se calcula la media de los días observados.

Los días sin transacciones no se rellenan automáticamente con cero: un extracto puede estar incompleto. La métrica es una media descriptiva de días observados, no una previsión.

## EDA empresarial de ventas

El **Resumen empresarial** permite filtrar por periodo y producto y organiza el análisis en seis vistas:

- **Resumen:** unidades, fechas registradas, productos, filas aptas, evolución diaria y medias móviles de 7 y 30 días.
- **Productos:** unidades, participación, días con registros y facturación calculada cuando hay precios válidos.
- **Distribución:** media, mediana, dispersión, percentiles, histograma, caja y candidatos a valores atípicos por IQR.
- **Temporal:** agregados semanales y comparación descriptiva por día de la semana, indicando cuántas fechas respaldan cada resultado.
- **Calidad:** fechas y cantidades inválidas, productos vacíos, duplicados, nulos, cobertura de fechas y perfil de columnas.
- **Hallazgos:** observaciones y cálculos basados en los filtros activos, con limitaciones y asuntos pendientes de validar.

Las medias móviles se calculan sobre las fechas con registros dentro de cada ventana; las fechas ausentes se mantienen desconocidas, no se convierten en cero. El análisis de demanda excluye temporalmente filas sin fecha o producto válido, con cantidades no numéricas o negativas; estas filas permanecen en el archivo cargado y se contabilizan en Calidad. Las filas duplicadas se informan, pero no se eliminan. Los atípicos IQR son candidatos para revisar, no errores confirmados. La comparación por semana o día de la semana no demuestra estacionalidad.

## EDA reutilizable

La pestaña **EDA avanzado** adapta los análisis a las columnas disponibles:

- **Perfil y calidad:** tipos, valores nulos, cardinalidad, ejemplos, duplicados y alertas genéricas.
- **Distribución:** media, mediana, desviación estándar, cuartiles, asimetría, histogramas, diagramas de caja y posibles atípicos por IQR.
- **Relaciones:** correlaciones de variables numéricas, dispersión y contraste Mann–Whitney para una variable numérica entre dos grupos.
- **Tiempo:** agregación diaria, evolución, perfil exploratorio por día de la semana y anomalías mediante z-score cuando hay suficientes fechas.
- **Deriva:** PSI para comparar dos periodos con muestras suficientes; señala cambios que merecen revisión, no su causa.
- **Robustez exploratoria:** intervalo bootstrap del 95 % para la media y segmentación K-Means de variables numéricas.

Cada técnica tiene requisitos de muestra y avisos. Bootstrap requiere al menos 10 valores válidos y supone observaciones independientes; no cuantifica correctamente la incertidumbre de una serie autocorrelacionada. PSI exige al menos 20 observaciones por periodo. K-Means necesita un mínimo de cinco filas válidas por segmento solicitado y no admite valores infinitos. La heurística de posible fuga de información se basa en nombres de columna y no confirma una fuga real.

El perfil por día de semana es descriptivo, no una prueba de estacionalidad. Los gráficos de relación no demuestran causalidad. SHAP/LIME, inferencia causal y predicción conformal no se ejecutan sin un modelo de negocio evaluado, una hipótesis causal adecuada o un diseño de validación que los respalde.

## Riesgo por lote empresarial

Este módulo es opcional y requiere ventas con fecha, producto y unidades, además de lotes con identificador, producto, stock disponible, fecha límite y coste unitario. Exige al menos 30 días distintos de ventas por producto.

La lógica compara el stock del lote con las ventas medias por día observado hasta su fecha límite. El indicador `estimated_unsold_stock_ratio` es la proporción estimada de stock que no se vendería según esa aproximación. No es una probabilidad calibrada ni una merma confirmada. Si falta historial suficiente, la app no presenta una estimación para ese producto.

## Transparencia de la demo

El botón de demostración combina ventas reales derivadas de FreshRetailNet-50K con inventario, costes y lotes de escenario. Estos últimos son supuestos didácticos, no información incluida en el conjunto de datos real. El margen y el coste expuesto son estimaciones, no ahorros ni pérdidas realizadas.
