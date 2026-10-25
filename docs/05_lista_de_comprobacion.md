# Lista de comprobación de entrega

Esta matriz conecta el proyecto final con una evidencia concreta. La app que se presenta es **ResQ Intelligence**; FreshMarket/ResQData se conserva como caso histórico sintético y no debe describirse como si fuera el producto B2B completo.

| Requisito | Evidencia |
|---|---|
| Problema y usuario definidos | [Caso de uso](01_caso_de_uso.md): plataforma B2B para responsables de operaciones, compras o finanzas. |
| Ingesta flexible | [`src/ingestion.py`](../src/ingestion.py): CSV/Excel por contrato y carga libre que conserva columnas. |
| Calidad de datos | [`src/platform_ui.py`](../src/platform_ui.py): informes de campos requeridos, conversiones inválidas, negativos y duplicados. |
| EDA profesional explicable | [`src/platform_ui.py`](../src/platform_ui.py) y [`src/business_intelligence.py`](../src/business_intelligence.py): EDA empresarial filtrable con tendencia, productos, distribución, temporalidad, calidad y hallazgos; [`src/advanced_eda.py`](../src/advanced_eda.py): relaciones, Mann–Whitney, PSI, bootstrap y segmentación. |
| Inteligencia empresarial | [`src/business_intelligence.py`](../src/business_intelligence.py): demanda por producto-día, inventario, capital expuesto y escenarios. |
| Sensibilidad de escenarios | [`scenario_sensitivity`](../src/business_intelligence.py): tabla de supuestos de precio y demanda mostrada como mapa de calor. |
| Riesgo opcional por lote | [`src/lot_risk.py`](../src/lot_risk.py): estimación del stock no vendido con historial empresarial y límites visibles. |
| Evidencia con datos reales | [Datos reales y previsión](07_datos_reales_y_demanda.md): FreshRetailNet-50K, licencia, método temporal, métricas y limitaciones. |
| Diferencia entre real y sintético | [Datos, preparación y EDA](02_datos_y_eda.md): FreshRetailNet real; datos de escenario y FreshMarket sintéticos o supuestos. |
| App demostrable | [`app.py`](../app.py): navegación lateral, portada, carga, EDA, inventario, lote, escenarios, fuentes, informe y metodología. |
| Informe exportable | [`src/reporting.py`](../src/reporting.py): resumen Markdown de calidad, resultados disponibles, procedencia y supuestos; no exporta registros originales. |
| Dependencias y ejecución | [`requirements.txt`](../requirements.txt) y [README](../README.md). |
| Pruebas automatizadas | [`tests/`](../tests/): contratos, ingesta, inteligencia, demo, FreshMarket y EDA avanzado. |

## Antes de presentar

1. Ejecuta `python -m pytest -q` y confirma que todas las pruebas pasan.
2. Si vas a usar la demo, genera sus archivos con `python -m src.demo_data`; las ventas derivan de FreshRetailNet y los otros CSV son supuestos.
3. Arranca `streamlit run app.py` y recorre la navegación lateral, especialmente **Inicio**, **Datos y calidad**, **Análisis exploratorio**, **Riesgo por lote**, **Escenarios** e **Informe**.
4. Explica que el análisis temporal y estadístico es exploratorio, la matriz de sensibilidad no predice respuestas reales y los resultados de lote son estimaciones.
5. Comprueba que puedes distinguir los datos reales de FreshRetailNet, los datos sintéticos de FreshMarket y los supuestos de la demo.
6. Publicar o desplegar requiere autorización expresa; no forma parte de esta comprobación.
