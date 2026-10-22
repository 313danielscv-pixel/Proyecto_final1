# Guion de exposición — ResQ Intelligence (15 minutos)

Usa diez diapositivas y una demo independiente. El texto entre comillas es una guía para explicar el proyecto con tus palabras.

| Parte | Tiempo |
|---|---:|
| Diapositivas 1 a 7 | 7 minutos |
| Demo de la aplicación | 3 minutos y 30 segundos |
| Diapositivas 8 a 10 | 4 minutos y 30 segundos |

## Diapositiva 1 de 10 — Problema y propuesta

**Título:** `ResQ Intelligence: decisiones para proteger el margen`

**Muestra:** demanda, inventario y rentabilidad como tres áreas conectadas.

> “ResQ Intelligence es una plataforma B2B que convierte datos operativos en decisiones económicas explicables. Una empresa no pierde margen por una sola causa: la demanda cambia, el inventario se desequilibra y los costes afectan a cada decisión.”

> “La pregunta que responde el proyecto es: ¿qué decisiones debe priorizar una empresa para proteger su margen a partir de su demanda, inventario y costes?”

## Diapositiva 2 de 10 — Usuario y recorrido

**Título:** `De CSV dispersos a una decisión priorizada`

**Muestra:** navegación lateral y flujo: cargar CSV/Excel → validar → explorar → priorizar → comparar escenarios.

> “El usuario puede ser un responsable de operaciones, compras o finanzas. Carga los datos que tiene: ventas, inventario, costes y, si existen, proveedores.”

> “La plataforma valida la información antes de calcular nada. Después muestra evidencia, riesgos y escenarios. La previsión real se presenta aparte como demostración metodológica, no como previsión de la empresa usuaria.”

## Diapositiva 3 de 10 — Contratos de datos

**Título:** `Un núcleo reutilizable, no una plantilla rígida`

**Muestra:** tabla con `ventas.csv`, `inventario.csv`, `costes.csv` y `proveedores.csv`.

> “Definí contratos de datos con campos mínimos por módulo. Para demanda se necesita fecha, producto y cantidad. Para inventario, producto y stock; la fecha es opcional. Para rentabilidad se necesitan costes y, si se quiere calcular margen, precio.”

> “La fecha de caducidad es opcional. Si existe, activa el caso de perecederos; si no existe, la plataforma sigue funcionando para otros sectores.”

## Diapositiva 4 de 10 — Calidad de datos

**Título:** `No hay recomendaciones sin datos fiables`

**Muestra:** reglas de validación y ejemplos de mensajes claros.

> “La carga reconoce alias como fecha, SKU, producto, unidades o coste. Detecta campos ausentes, conversiones inválidas, negativos que deben revisarse y duplicados. No borra filas automáticamente. También hay una carga libre para EDA que conserva las columnas originales.”

> “Si no hay datos suficientes, el sistema no inventa una predicción. Explica qué módulo no puede activarse y qué campo falta.”

## Diapositiva 5 de 10 — Análisis exploratorio

**Título:** `Primero evidencias, después recomendaciones`

**Muestra:** resumen empresarial de la demo con filtros, tendencia y productos; después, el EDA avanzado.

> “El EDA empresarial permite investigar la evolución de ventas, medias móviles, productos, distribución diaria, patrones semanales y calidad. Los días sin datos no se convierten en cero y las filas inválidas o duplicadas se señalan sin borrarlas. El EDA avanzado añade perfilado, relaciones, comparación entre grupos, deriva, intervalos bootstrap y segmentos.”

> “Los filtros afectan a la exploración, mientras que la vista de calidad conserva el contexto del archivo completo. Un valor extremo es un candidato a revisar, no un error confirmado. Los gráficos describen los registros; no prueban causalidad ni predicen ventas.”

## Diapositiva 6 de 10 — Datos reales y previsión de demanda

**Título:** `Demanda real con evaluación temporal`

**Muestra:** FreshRetailNet-50K, licencia CC BY 4.0, 4,5 millones de filas de entrenamiento y métricas.

> “Para demostrar previsión sobre datos reales uso FreshRetailNet-50K, un conjunto de ventas reales de productos perecederos con descuentos, promociones, clima y roturas de stock.”

> “La evaluación separa el tiempo: la referencia usa ventas de siete días antes y se evalúa sobre siete días posteriores. En un subconjunto reproducible de cien series, obtiene MAE 0,5109 y RMSE 0,8352. Es una línea base, no un modelo de producción.”

> “Estos datos demuestran previsión de demanda. No afirmo que contengan costes internos, caducidades o mermas de la empresa usuaria.”

## Diapositiva 7 de 10 — Inventario y rentabilidad

**Título:** `De la demanda al riesgo económico`

**Muestra:** fórmula de cobertura, capital expuesto, rotura y sobrestock.

> “La plataforma cruza el inventario con la demanda observada. Calcula días de cobertura, riesgo de rotura si el stock no cubre el plazo de reposición y sobrestock si hay cobertura excesiva.”

> “El capital expuesto es stock por coste unitario. No es una pérdida realizada; muestra dónde hay más dinero inmovilizado y dónde conviene analizar una decisión.”

# Demo independiente — 3 minutos y 30 segundos

## Paso 1 — Datos y calidad

Pulsa **Cargar demostración con demanda real** en **Datos y calidad**. Si los datos demo no están generados, ejecuta `python -m src.demo_data` antes de la exposición. Como alternativa, carga los CSV de `data/templates/`.

> “La empresa puede subir archivos independientes. El sistema detecta el mapeo de columnas y comunica cuántas filas son aptas, inválidas o duplicadas.”

## Paso 2 — Análisis exploratorio

Abre **Análisis exploratorio** y elige **Resumen empresarial**.

> “Aquí veo la demanda diaria, los productos de mayor volumen y, si existe precio, la facturación. La plataforma no muestra métricas que sus datos no puedan respaldar.”

## Paso 3 — Inventario y margen

Abre **Inventario y margen**.

> “Esta vista ordena los productos por capital expuesto y clasifica riesgo de rotura, sobrestock o equilibrio.”

## Paso 4 — Escenarios

Abre **Escenarios**.

> “Ahora comparo un escenario base con un cambio de precio o demanda. El cambio de demanda es una hipótesis declarada por el usuario y el resultado se etiqueta como estimación.”

## Paso 5 — Riesgo por lote y demanda real

Abre **Riesgo por lote** y después **Demanda**.

> “Riesgo por lote usa las ventas y los lotes cargados por la empresa y exige al menos treinta días de ventas por producto. El indicador es una proporción estimada de stock sin vender, no una probabilidad calibrada. Demanda demuestra la evaluación con una fuente externa. FreshMarket se conserva como caso sintético independiente.”

## Cierre de la demo — Fuentes e informe

Abre **Fuentes** para distinguir las ventas derivadas de FreshRetailNet de los supuestos sintéticos. Abre **Informe** y muestra el botón **Descargar informe Markdown**.

> “El informe resume las comprobaciones y resultados disponibles, deja visible la procedencia y no incluye filas originales. Así otra persona puede revisar los supuestos y las limitaciones.”

## Diapositiva 8 de 10 — Simulador económico

**Título:** `Comparar decisiones sin prometer ahorros`

**Muestra:** escenario base frente a descuento, reposición o cambio de coste.

> “La plataforma compara ingreso, coste de producto, coste de almacenamiento y margen estimado. El usuario ve todos los supuestos y puede modificar el escenario.”

> “No se presenta ninguna variación como ahorro conseguido. Es un cálculo de escenario que debe validarse con la operación real.”

## Diapositiva 9 de 10 — Caso FreshMarket

**Título:** `Un vertical especializado para perecederos`

**Muestra:** riesgo por lote, caducidad, descuento, donación y EDA de merma.

> “Conservo FreshMarket como origen y caso histórico especializado, sin confundirlo con los datos que aporta una empresa a ResQ Intelligence.”

> “En ese caso se priorizan lotes por riesgo de merma y coste expuesto. Es una demostración sintética y no la fuente de los resultados de demanda real.”

## Diapositiva 10 de 10 — Límites y siguiente paso

**Título:** `Implementar con datos propios y medir impacto`

**Muestra:** cuatro pasos: cargar, validar, piloto, medir.

> “El siguiente paso para una empresa es cargar su histórico real, validar la calidad, evaluar su propio modelo de demanda y ejecutar un piloto controlado.”

> “Se deben medir margen, stock, roturas, sobrestock y resultado de las decisiones antes de automatizar acciones.”

> “En conclusión, ResQ Intelligence no sustituye el criterio empresarial: hace visibles los riesgos, explica los cálculos y permite comparar decisiones de forma responsable.”

## Preguntas previsibles

**¿Por qué no predice siempre la demanda?**  
> “La app no genera una previsión empresarial automática con cualquier CSV. La pestaña de demanda real muestra una línea base evaluada sobre FreshRetailNet; una empresa necesita validar un modelo propio con su histórico. El módulo de lotes, por separado, exige al menos treinta días observados por producto.”

**¿La matriz de sensibilidad predice qué hará el cliente?**  
> “No. Muestra el efecto matemático de supuestos elegidos para precio y demanda. La respuesta real al precio debe medirse en un piloto.”

**¿Las estimaciones son ahorros reales?**  
> “No. Son comparaciones de escenarios basadas en supuestos visibles. El ahorro solo existe si se mide en la operación real.”

**¿Por qué usar datos reales de otra empresa?**  
> “Se usan para demostrar metodología de previsión con una fuente abierta y documentada. Cada cliente necesita evaluar su propio histórico antes de usar el modelo.”
