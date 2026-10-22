# Informe por fases — ResQ Intelligence

Este archivo está preparado para copiar y pegar en otra conversación. Resume el estado real de la evolución, sus pruebas y sus límites.

## Objetivo

ResQ Intelligence es una plataforma B2B que ayuda a empresas a revisar demanda, inventario y rentabilidad con sus propios CSV. No exige caducidades ni lotes. FreshMarket permanece como una vertical alimentaria sintética.

## Fase 0 — Rediseño y contratos de datos

**Estado: COMPLETADA**

- `src/contracts.py` define contratos para ventas, inventario, costes y proveedores.
- `data/templates/` contiene plantillas de ventas, inventario, costes, proveedores y lotes.
- Caducidad es opcional y solo habilita el módulo de perecederos.
- Las pruebas verifican que demanda e inventario generales no dependen de campos alimentarios.

## Fase 1 — Carga y calidad de datos

**Estado: COMPLETADA**

- `src/ingestion.py` lee CSV/Excel sin guardar los ficheros originales.
- Mapea alias empresariales y convierte fechas, números y booleanos.
- Informa de campos ausentes, negativos, conversiones inválidas, duplicados y filas aptas.
- La carga libre de EDA preserva todas las columnas del archivo, mientras que la carga por contrato mantiene la normalización necesaria para los módulos de negocio.
- La app guarda datos cargados solo dentro de la sesión del navegador.

## Fase 2 — Análisis exploratorio

**Estado: COMPLETADA**

- El EDA empresarial permite filtrar por fechas y producto y muestra evolución, medias móviles, ranking, participación, distribución, análisis semanal y por día de semana, calidad y hallazgos.
- Distingue días ausentes de días con cero ventas; los inválidos y duplicados se informan sin borrarse.
- Los resultados solo se muestran cuando los campos existen y explican su muestra, procedencia y límites.

## Mejora posterior — EDA profesional reutilizable

**Estado: COMPLETADA**

- La pestaña **EDA avanzado** funciona sobre un CSV o Excel de carga libre, sin perder columnas ajenas a los contratos, y sobre conjuntos empresariales normalizados.
- Perfilado: tipos, nulos, cardinalidad, ejemplos y duplicados.
- Calidad: valores negativos como advertencia para revisión con regla de negocio, sin declararlos automáticamente incorrectos.
- Exploración: estadística descriptiva, asimetría, histogramas, diagramas de caja y atípicos por IQR.
- Relaciones: correlaciones, dispersión y contraste Mann-Whitney cuando una categoría tiene exactamente dos grupos.
- Tiempo: agregación temporal diaria, anomalías por z-score y deriva PSI entre mitades de la serie si el tamaño muestral permite calcularlas; el PSI incluye valores fuera del rango histórico.
- Robustez: intervalo bootstrap del 95 % para la media con advertencia de independencia y segmentación K-Means exploratoria que excluye valores infinitos.
- Límites: el EDA genera hipótesis, no prueba causalidad. SHAP/LIME y explicabilidad de modelos no se muestran sin un modelo compatible evaluado. Cada cálculo informa cuando la muestra es insuficiente.

## Fase 3 — Predicción de demanda con datos reales

**Estado: COMPLETADA**

- Fuente: FreshRetailNet-50K de Dingdong Inc., CC BY 4.0.
- Datos descargados localmente: 4,5 millones de filas de entrenamiento y 350.000 de evaluación.
- Demostración reproducible: 100 series tienda-producto y 700 observaciones futuras.
- Referencia temporal estacional: MAE 0,5109 y RMSE 0,8352.
- No se afirma que esta fuente tenga costes empresariales, caducidades o mermas.
- Documentación: `docs/07_datos_reales_y_demanda.md`.

## Fase 4 — Inteligencia de inventario y rentabilidad

**Estado: COMPLETADA**

- Agrega transacciones por producto y día antes de calcular la demanda media observada, cobertura, riesgo de rotura, sobrestock y capital expuesto.
- Los días sin transacción no se imputan como cero porque una extracción empresarial puede no contener el calendario completo.
- Requiere ventas e inventario válidos; sin ellos no inventa resultados.

## Fase 5 — Simulador de escenarios económicos

**Estado: COMPLETADA**

- Compara margen base y escenario usando precio, unidades, coste y almacenamiento.
- Muestra variación estimada con los supuestos introducidos por el usuario.
- No presenta el resultado como ahorro realizado.

## Fase 6 — Caso FreshMarket

**Estado: COMPLETADA**

- Se conserva el modelo de riesgo de merma, cartera de lotes, EDA y recomendaciones.
- Se presenta como caso especializado sintético, separado de los módulos generales.

## Mejora posterior — Riesgo por lote empresarial

**Estado: COMPLETADA**

- `lotes.csv` permite a una empresa cargar `lot_id`, `product_id`, `stock_available`, `expiry_date` y `unit_cost`.
- La pestaña **Riesgo por lote** usa las ventas cargadas por la propia empresa, no FreshMarket.
- El indicador se llama `estimated_unsold_stock_ratio`: proporción estimada de stock que no se espera vender antes de la fecha límite; no se presenta como probabilidad calibrada.
- Requiere al menos 30 días de historial por producto; sin ese mínimo, devuelve un aviso en vez de una predicción inventada.
- La interfaz anterior de ResQData/FreshMarket se retiró de Streamlit. FreshMarket permanece solo como activo histórico y caso documentado.

## Mejora posterior — Demostración ejecutable

**Estado: COMPLETADA**

- La pestaña **Cargar datos empresa** incorpora el botón **“Cargar demostración con demanda real”**.
- `src.demo_data.py` construye cuatro CSV de demo:
  - ventas reales derivadas de FreshRetailNet-50K;
  - inventario, costes y lote como supuestos de escenario.
- La app identifica explícitamente qué parte es observada y qué parte es un supuesto, evitando presentar datos simulados como datos de la fuente.

## Mejora posterior — Experiencia de uso e informe

**Estado: IMPLEMENTADA**

- La navegación principal pasa a una barra lateral con portada y secciones por tarea.
- El inicio muestra métricas solo cuando los datos requeridos están disponibles y etiqueta los costes y lotes sintéticos de la demo.
- Las vistas identifican procedencia, filas y periodo cuando existen fechas; el EDA avanzado explica el orden recomendado de exploración.
- **Informe** genera un Markdown con calidad, resultados disponibles, procedencia, supuestos y limitaciones, sin exportar filas originales.
- Los cálculos siguen en módulos de negocio separados de la interfaz Streamlit.

## Fase 7 — Entrega final y pruebas

**Estado: COMPLETADA, EXCEPTO PUBLICACIÓN**

- README, contratos, fuente real, metodología, pruebas y guion quedan documentados.
- No hay remoto ni `push`; publicar sigue bloqueado hasta autorización del usuario.

## Validación disponible

- Contratos de CSV.
- Ingesta, mapeo y valores inválidos.
- Cálculos de inventario y escenarios.
- Caso FreshMarket.
- Perfilado, calidad, atípicos, incertidumbre, anomalías, deriva y segmentación del EDA avanzado.
- Validación de la iteración de EDA empresarial: `python -m pytest -q` — 36 pruebas aprobadas.

## Reglas no negociables

- No presentar estimaciones como ahorros realizados.
- No generar predicciones si el historial es insuficiente.
- No atribuir a una fuente datos que no contiene.
- Documentar procedencia, licencia, fecha y filtros de los datos reales.
- No publicar sin autorización explícita.
