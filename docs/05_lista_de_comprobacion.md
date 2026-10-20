# Lista de comprobación de entrega

Esta matriz relaciona los requisitos del enunciado con una evidencia concreta del repositorio.

| Requisito | Evidencia de cumplimiento |
|---|---|
| Caso de uso real, ligado a una trayectoria | [Caso de uso](01_caso_de_uso.md): responsable de frescos que prioriza lotes de vida corta. |
| Datos con origen documentado | [Datos y EDA](02_datos_y_eda.md): piloto sintético reproducible y API oficial de Eurostat. |
| Preprocesamiento visible | [`src/data_pipeline.py`](../src/data_pipeline.py): tipado de fechas, unión de tablas, control de nulos y duplicados. |
| EDA con preguntas y conclusiones | [Datos y EDA](02_datos_y_eda.md) y pestaña **Análisis exploratorio** de la aplicación. |
| Ciencia de datos integrada | [`src/train_model.py`](../src/train_model.py) entrena el modelo; [`app.py`](../app.py) lo usa para responder al usuario. |
| Evaluación y limitaciones | [Modelo y validación](03_modelo_y_validacion.md): separación por lote, métricas, umbral y límites. |
| Aplicación completa y comprensible | [`app.py`](../app.py): formulario, resultado, recomendación, cartera y panel EDA. |
| Panel de inteligencia | Pestañas **Cartera de riesgo** y **Análisis exploratorio** integradas en la aplicación. |
| Despliegue | README con configuración exacta para Streamlit Community Cloud y arranque local verificado. |
| README como puerta de entrada | [`README.md`](../README.md): problema, datos, EDA, modelo, uso, estructura y despliegue. |
| Dependencias con versiones | [`requirements.txt`](../requirements.txt). |
| Variables de entorno | [`.env.example`](../.env.example): no hay secretos requeridos. |
| Código legible y probado | Nombres explícitos, comentarios de decisión y pruebas en [`tests/`](../tests/). |
| Exposición final | [Guion de presentación](04_guion_presentacion.md), con evidencia, demo y límites. |

## Antes de enviar

1. Ejecuta `python -m pytest -q`.
2. Arranca con `streamlit run app.py`.
3. Comprueba que las cuatro pestañas abren y que el formulario calcula una recomendación.
4. Relee los documentos y el código que presentarás; debes poder explicar cada decisión y limitación.
5. Publica la rama `main` y crea la aplicación en Streamlit Community Cloud con `app.py`.
