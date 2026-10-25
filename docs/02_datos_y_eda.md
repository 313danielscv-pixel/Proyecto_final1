# Datos, preparación y análisis exploratorio

## Fuentes y uso

| Fuente | Uso en el proyecto | Naturaleza y límite |
|---|---|---|
| Archivos CSV/Excel de empresa | Análisis de ventas, inventario, costes, lotes y EDA libre | Datos aportados por el usuario; se conservan en la sesión de Streamlit, no en el repositorio. |
| FreshRetailNet-50K | Demostración y evaluación de una referencia de demanda | Ventas reales publicadas por Dingdong Inc.; licencia declarada CC BY 4.0; particiones descargadas el 20/10/2026. No contiene los costes ni las caducidades de la empresa usuaria. |
| Piloto FreshMarket | Desarrollo y demostración histórica del caso de merma | Datos sintéticos; no describen una empresa real ni se usan como datos de clientes. |
| Eurostat `cei_pc035` | Contexto agregado del desperdicio alimentario | Indicador público de España para 2022, descargado el 24/10/2026 y reutilizado con atribución a Eurostat bajo CC BY 4.0. Cubre toda la cadena de valor; no mide la merma de una tienda concreta ni alimenta el cálculo de riesgo por lote. |
| Eurostat `sts_trtu_m` | Contexto reciente de la actividad minorista de alimentos | Índice mensual de volumen para España, alimentos/bebidas/tabaco, con ajuste de calendario; última observación disponible: agosto de 2026. Es contexto agregado, no ventas por tienda o producto ni entrada al modelo. |

El piloto FreshMarket y los datos operativos de la demo se generan dentro del proyecto con supuestos sintéticos; no proceden de empresas reales ni de una fuente externa.

El contexto Eurostat se mantiene separado de FreshRetailNet: el índice mensual tiene granularidad nacional y sectorial, no la clave tienda-producto-día necesaria para unirlo a las ventas ni para usarlo como predictor.

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
3. Si el periodo completo está confirmado, se divide el total de unidades por los días naturales desde la primera fecha del producto hasta la última fecha del extracto.

La app solo cuenta como cero las fechas sin filas dentro de ese periodo si la persona confirma que el extracto cubre todos los días. Sin confirmación, la media usa únicamente fechas con registro y las señales de inventario se muestran como provisionales; el riesgo por lote no se calcula. Las fechas anteriores al primer registro del producto no se imputan. Esta métrica es descriptiva, no una previsión.

## EDA empresarial de ventas

El **Resumen empresarial** permite filtrar por periodo y producto y organiza el análisis en seis vistas:

- **Resumen:** unidades, fechas registradas, productos, filas aptas, evolución diaria y medias móviles de 7 y 30 días.
- **Productos:** unidades, participación, días con registros y facturación calculada cuando hay precios válidos.
- **Distribución:** media, mediana, dispersión, percentiles, histograma, caja y candidatos a valores atípicos por IQR.
- **Temporal:** agregados semanales y comparación descriptiva por día de la semana, indicando cuántas fechas respaldan cada resultado.
- **Calidad:** fechas y cantidades inválidas, productos vacíos, duplicados, nulos, cobertura de fechas y perfil de columnas.
- **Hallazgos:** observaciones y cálculos basados en los filtros activos, con limitaciones y asuntos pendientes de validar.

Las medias móviles del EDA se calculan sobre las fechas con registros dentro de cada ventana; las fechas ausentes se mantienen desconocidas, no se convierten en cero. Esta regla de visualización descriptiva es distinta de la demanda diaria usada por inventario y lotes. El análisis de demanda del EDA excluye temporalmente filas sin fecha o producto válido, con cantidades no numéricas o negativas; estas filas permanecen en el archivo cargado y se contabilizan en Calidad. Las filas duplicadas se informan, pero no se eliminan. Los atípicos IQR son candidatos para revisar, no errores confirmados. La comparación por semana o día de la semana no demuestra estacionalidad.

## EDA reutilizable

La pestaña **EDA avanzado** adapta los análisis a las columnas disponibles:

- **Perfil y calidad:** tipos, valores nulos, cardinalidad, ejemplos, duplicados y alertas genéricas.
- **Distribución:** media, mediana, desviación estándar, cuartiles, asimetría, histogramas, diagramas de caja y posibles atípicos por IQR.
- **Relaciones:** correlaciones de variables numéricas, dispersión y contraste Mann–Whitney para una variable numérica entre dos grupos.
- **Tiempo:** agregación diaria, evolución, perfil exploratorio por día de la semana y anomalías mediante z-score cuando hay suficientes fechas.
- **Deriva:** PSI para comparar dos periodos con muestras suficientes; señala cambios que merecen revisión, no su causa.
- **Robustez exploratoria:** intervalo bootstrap del 95 % para la media y segmentación K-Means de variables numéricas.

En EDA avanzado se pueden declarar las unidades de las columnas numéricas. Los cuatro conjuntos de demostración precargan las unidades documentadas en [`README_DEMO.json`](../data/demo/README_DEMO.json). Las etiquetas se aplican a los ejes sin convertir los valores; si una unidad no se especifica, el gráfico lo indica como «unidad no especificada». Para archivos empresariales hay que contrastar las unidades introducidas con la documentación del archivo antes de interpretar o presentar los gráficos.

Cada técnica tiene requisitos de muestra y avisos. Bootstrap requiere al menos 10 valores válidos y supone observaciones independientes; no cuantifica correctamente la incertidumbre de una serie autocorrelacionada. PSI exige al menos 20 observaciones por periodo. K-Means necesita un mínimo de cinco filas válidas por segmento solicitado y no admite valores infinitos. La heurística de posible fuga de información se basa en nombres de columna y no confirma una fuga real.

El perfil por día de semana es descriptivo, no una prueba de estacionalidad. Los gráficos de relación no demuestran causalidad. SHAP/LIME, inferencia causal y predicción conformal no se ejecutan sin un modelo de negocio evaluado, una hipótesis causal adecuada o un diseño de validación que los respalde.

## Riesgo por lote empresarial

Este módulo es opcional y requiere ventas con fecha, producto y unidades, además de lotes con identificador, producto, stock disponible, fecha límite y coste unitario. Exige confirmar la cobertura del periodo y al menos 30 días naturales desde el primer registro de cada producto hasta el final del extracto; no exige 30 fechas con ventas.

La lógica compara el stock del lote con las ventas medias por día natural hasta su fecha límite y requiere confirmar que el extracto cubre todos los días. Por ejemplo, vender 10 unidades cada cinco días en un periodo completo equivale aproximadamente a 2 unidades al día, no a 10. El indicador `estimated_unsold_stock_ratio` es la proporción estimada de stock que no se vendería según esa aproximación. No es una probabilidad calibrada ni una merma confirmada. Si no se confirma la cobertura o falta historial suficiente, la app no presenta una estimación para ese producto.

## Transparencia de la demo

El botón de demostración combina ventas reales derivadas de FreshRetailNet-50K con inventario, costes y lotes de escenario. Estos últimos son supuestos didácticos, no información incluida en el conjunto de datos real. El margen y el coste expuesto son estimaciones, no ahorros ni pérdidas realizadas.
