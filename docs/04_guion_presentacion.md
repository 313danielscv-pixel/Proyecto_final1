# Guion para la presentación

## Idea principal

ResQ Intelligence ayuda a responsables de operaciones, compras y finanzas a entender sus datos y priorizar decisiones sobre demanda, inventario y perecederos. Es una herramienta de apoyo: muestra cálculos, supuestos y límites, pero no ejecuta cambios en los sistemas de la empresa.

## Recorrido de 10 diapositivas

1. **ResQ Intelligence:** presenta el nombre y la pregunta de negocio: cómo priorizar decisiones para proteger el margen.
2. **El problema:** ventas, inventario y costes suelen estar separados; decidir con extractos incompletos puede ocultar riesgos.
3. **Usuario y decisión:** compras, operaciones o finanzas necesitan identificar cambios de demanda, exceso de stock y lotes que requieren revisión.
4. **Propuesta:** cargar, validar, explorar, priorizar y comparar escenarios en una misma app Streamlit.
5. **Datos y calidad:** muestra los contratos de carga y las validaciones; distingue datos empresariales, datos públicos y supuestos sintéticos.
6. **Análisis exploratorio:** enseña evolución, productos, distribución, temporalidad y calidad. Aclara que una relación no demuestra causalidad.
7. **Inventario y perecederos:** explica la demanda diaria de calendario y el cálculo de stock estimado sin vender. Un stock positivo sin demanda registrada se marca como sobrestock.
8. **Comparación de previsiones:** sobre 700 observaciones de 100 series FreshRetailNet-50K, compara la referencia estacional (MAE 0,5109; RMSE 0,8352) con la media móvil de siete días (MAE 0,4813; RMSE 0,7847).
9. **Escenarios y límites:** muestra cómo cambian los resultados bajo supuestos explícitos. La media móvil se evaluó en datos públicos; no se garantiza el mismo resultado en una empresa.
10. **Cierre:** resume qué decisión facilita la app y qué debe validar una empresa antes de usarla operativamente.

## Demostración de 3:30

| Tiempo | Acción | Qué explicar |
|---|---|---|
| 0:00–0:25 | Abrir **Datos y calidad** y cargar la demostración. | Las ventas derivan de FreshRetailNet-50K; inventario, costes y lotes son supuestos de escenario. |
| 0:25–0:55 | Revisar calidad y campos disponibles. | Los módulos dependen de los datos; ResQ informa si falta historial o algún campo. |
| 0:55–1:25 | Abrir **Análisis exploratorio**. | Mostrar un hallazgo y una gráfica; describirlo como evidencia observada, no como causalidad. |
| 1:25–2:10 | Revisar **Inventario y rentabilidad** y **Riesgo por lote**. | Explicar demanda por día natural, stock sin ventas y porcentajes estimados antes de la fecha límite. |
| 2:10–2:45 | Abrir **Demanda real**. | Comparar el baseline estacional con la media móvil en el mismo holdout temporal. |
| 2:45–3:15 | Abrir **Escenarios** y variar un supuesto. | El resultado cambia según entradas explícitas; no es una predicción ni un ahorro realizado. |
| 3:15–3:30 | Cerrar con **Informe** o volver a Inicio. | La decisión final corresponde a la empresa y requiere validar sus datos. |

## Preguntas previsibles

**¿Los lotes y costes de la demo proceden de FreshRetailNet?**  
No. FreshRetailNet aporta ventas públicas. El inventario, los costes y los lotes son supuestos didácticos.

**¿El porcentaje de stock no vendido es una probabilidad de merma?**  
No. Es una estimación determinista basada en demanda histórica, stock y días hasta la fecha límite; no es una probabilidad calibrada.

**¿La media móvil predice lo que venderá cualquier empresa?**  
No. Se evaluó como referencia sobre un subconjunto temporal público. Cada empresa debe contrastarla con sus propios datos y otros métodos.

**¿Una correlación o una gráfica demuestra la causa de un cambio?**  
No. El análisis es descriptivo y exploratorio; no establece causalidad.
