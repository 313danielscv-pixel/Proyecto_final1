# ResQ Intelligence

ResQ Intelligence es una plataforma B2B para convertir datos empresariales en decisiones de demanda, inventario y rentabilidad. Una empresa puede cargar sus CSV, revisar su calidad, detectar riesgos operativos y comparar escenarios económicos con supuestos visibles.

## Pregunta de negocio

> ¿Qué decisiones debe priorizar una empresa para proteger su margen a partir de su demanda, inventario y costes?

## Capacidades

- Carga de CSV y Excel de ventas, inventario, costes y proveedores, además de una carga libre que conserva todas las columnas para EDA.
- Mapeo de alias como `fecha`, `sku`, `producto`, `unidades` o `coste`.
- Detección de campos ausentes, fechas o números inválidos, negativos y duplicados.
- EDA empresarial con filtros por periodo y producto, medias móviles, ranking de productos, distribución, patrones temporales, calidad y hallazgos con límites explícitos.
- Chat contextual sobre ResQ y los datos de sesión, ejecutado exclusivamente mediante Ollama local.
- EDA avanzado reutilizable: perfilado, nulos, duplicados, valores negativos, distribuciones, atípicos, anomalías temporales, bootstrap, deriva y segmentación exploratoria.
- Cobertura de inventario, riesgo de rotura, sobrestock y capital expuesto.
- Riesgo por lote opcional para empresas con stock por lote y fecha límite, con demanda media por día natural y proporción estimada de stock sin vender.
- Análisis Naive Bayes de riesgo de merma para snapshots históricos etiquetados, validando siempre por lotes separados.
- Simulador de escenarios de precio, volumen y coste de almacenamiento.
- Comparación de una media móvil de 7 días con una referencia estacional sobre datos reales de FreshRetailNet-50K.

## Contratos de datos

La plataforma no exige un esquema único ni datos de caducidad. Cada módulo se activa solo cuando los datos cargados lo permiten:

- [Plantillas y contratos](docs/06_contratos_de_datos.md).
- [Plantillas CSV](data/templates/).
- [Lista de comprobación](docs/05_lista_de_comprobacion.md).

## Datos y transparencia

| Fuente | Uso | Naturaleza |
|---|---|---|
| FreshRetailNet-50K | Evaluación de previsión de demanda. | Datos reales, licencia CC BY 4.0. |
| Eurostat `cei_pc035` | Contexto del caso alimentario. | Indicador público agregado. |
| Eurostat `sts_trtu_m` | Contexto reciente del comercio alimentario en España. | Índice mensual agregado; última observación disponible: agosto de 2026. |

La documentación de la fuente real, el método temporal, métricas y límites está en [07_datos_reales_y_demanda.md](docs/07_datos_reales_y_demanda.md).

No se afirma que FreshRetailNet-50K incluya costes internos, caducidades o mermas de una empresa usuaria. Los cálculos de escenarios son estimaciones y nunca ahorros realizados.

### Preparación y resultados demostrables

Para el análisis empresarial, las ventas se agregan por producto y día. Las filas con fecha, producto o unidades no válidas se excluyen de los cálculos de demanda y siguen contabilizadas en la vista de calidad; los duplicados se informan, pero no se eliminan automáticamente. Las fechas sin registros se consideran desconocidas salvo que se confirme que el extracto cubre todo el periodo.

En la demo, el producto FRN-300 registra una media de 16,20 unidades/día en los últimos 7 días frente a 12,51 en 30 días (+3,69; +29,5 %) hasta el 25/06/2024. Es una señal histórica para revisar, no una predicción ni evidencia de rotura; inventario, costes y lotes de la demo son supuestos sintéticos.

La evaluación de demanda selecciona de forma determinista 100 series de FreshRetailNet-50K y compara dos métodos sobre el mismo holdout temporal de 7 días (700 observaciones):

| Método | MAE | RMSE |
|---|---:|---:|
| Referencia estacional (venta de hace 7 días) | 0,5109 | 0,8352 |
| Media móvil de 7 días | 0,4813 | 0,7847 |

MAE y RMSE resumen el tamaño medio del error, en las unidades de venta del conjunto; valores menores son mejores en esta comparación. La media móvil obtiene menor error en estas series, pero el resultado no garantiza precisión en otra empresa. El método, la licencia y las limitaciones están desarrollados en [Datos reales y previsión](docs/07_datos_reales_y_demanda.md).

## Aplicación

La app usa una navegación lateral y una portada con indicadores condicionales: cada cifra aparece solo si hay datos suficientes para calcularla.

1. **Inicio**: resume ventas, margen estimado, capital y lotes prioritarios cuando los datos permiten calcularlos.
2. **Datos y calidad**: importa CSV o Excel por contrato o conserva todas las columnas mediante la carga libre para EDA.
3. **Análisis exploratorio**: alterna entre el EDA empresarial y el EDA avanzado, que incluye distribuciones, temporalidad, robustez y análisis bayesiano.
4. **Demanda**: muestra la evaluación reproducible sobre FreshRetailNet-50K.
5. **Inventario y rentabilidad**, **Riesgo por lote** y **Escenarios**: muestran indicadores o estimaciones con requisitos y límites visibles.
6. **Informe**: descarga un resumen Markdown de calidad, resultados disponibles, fuentes, supuestos y limitaciones; no exporta filas originales.

El EDA avanzado solo activa cada técnica si la muestra y los tipos de datos la justifican. El bootstrap exige 10 observaciones y asume independencia; no debe usarse como incertidumbre temporal cuando existe autocorrelación. La deriva requiere 20 observaciones en cada periodo; la segmentación exige dos variables numéricas y una muestra suficiente. Las fechas se agregan a día y los valores extremos se incluyen en el PSI. Sus resultados describen patrones y limitaciones: no demuestran causalidad ni sustituyen un modelo predictivo evaluado.

El análisis Naive Bayes requiere snapshots de lotes con las columnas de la plantilla descargable desde **EDA avanzado → Riesgo bayesiano**. `hubo_merma` debe indicar el resultado final (1/0) para al menos 20 lotes y cuatro lotes de cada clase; puede dejarse vacío en snapshots de lotes todavía sin resultado. La validación mantiene todas las filas de cada lote en una sola partición. Las probabilidades son orientativas, no están calibradas y no prueban causalidad ni rendimiento en producción.

Para la demanda de inventario y lotes, ResQ divide las unidades por los días naturales desde la primera fecha registrada de cada producto hasta el final del extracto, solo cuando se confirma que este cubre todos los días del periodo. Sin esa confirmación, la media usa fechas con registro y el módulo de riesgo por lote no calcula estimaciones. Un producto con stock positivo y demanda registrada igual a cero se marca como sobrestock.

### Estructura del repositorio

- `app.py`: punto de entrada de Streamlit.
- `src/`: ingesta, análisis, interfaz, informes y conectores.
- `data/demo/`: datos reproducibles de demostración, con procedencia y unidades.
- `data/processed/`: métricas y resultados derivados versionados.
- `data/external/`: contexto público y ubicación documentada para datos descargados; los Parquet brutos no se versionan.
- `docs/`: caso de uso, datos, metodología y contratos.
- `tests/`: pruebas automatizadas de lógica e interfaz.

### Mejoras siguientes

Antes de operar con datos de una empresa, habría que validar los contratos y las unidades con responsables del negocio, comparar métodos de demanda con su histórico mediante cortes temporales, calibrar cualquier probabilidad con resultados representativos y medir las decisiones en un piloto controlado. También conviene vigilar cambios de calidad y distribución. Estas tareas son una hoja de ruta, no capacidades ya validadas en producción.

### Conectar una base de datos

En **Datos y calidad** puedes elegir **Base de datos** para conectar MySQL, PostgreSQL o Microsoft SQL Server, listar tablas y vistas, previsualizar una tabla y cargarla en la sesión para el análisis correspondiente. **Actualizar datos** vuelve a consultar la fuente; ResQ no escribe cambios en la base conectada. El conector solo construye consultas de lectura y la cuenta debe tener permisos `SELECT` únicamente. SQL Server requiere `pyodbc` y el controlador ODBC 18 de Microsoft; habilita TCP/IP y utiliza el puerto del servidor (por defecto, 1433). Puedes usar autenticación de Windows —con los permisos de la cuenta que ejecuta ResQ— o una cuenta SQL. La conexión cifra el tráfico y valida el certificado; confía en un certificado autofirmado solo para una prueba local. SQL Server Management Studio (SSMS) es el cliente de administración; también debe existir un servicio de SQL Server activo.

Por seguridad, el servidor solo acepta por defecto conexiones a `localhost`, `127.0.0.1` y `::1`. Para autorizar otro host de confianza, configura `RESQ_DB_ALLOWED_HOSTS` en el entorno del proceso Streamlit. Las credenciales se mantienen solo en memoria durante la sesión; no las añadas al repositorio. El conector limita las importaciones a 100.000 filas y rechaza una tabla que supere el límite elegido.

Para iniciar la base PostgreSQL sintética de demostración, copia `.env.example` a `.env`, cambia las dos contraseñas locales y ejecuta:

```powershell
docker compose up -d
streamlit run app.py
```

En la app, conecta con PostgreSQL en `localhost:5433`, base `resq_demo`, usuario `resq_reader` y la contraseña de solo lectura configurada en `.env`. La base solo contiene filas sintéticas y el puerto se publica en loopback. El archivo `.env` está excluido de Git.

### Asistente local de ResQ

El panel lateral **Chat sobre ResQ** responde preguntas sobre la aplicación, su metodología documentada y los datos cargados en la sesión. Usa Ollama en `localhost`; el código rechaza hosts remotos para que el contexto no salga del equipo. El modelo debe estar instalado localmente:

```powershell
ollama serve
ollama pull qwen3.6:latest
```

Si Ollama ya está ejecutándose, no hace falta iniciar otro servicio. La app detecta los modelos al pulsar **Conectar con Ollama**. Puede seleccionarse otro modelo con `OLLAMA_MODEL`. El contexto incluye el README y todos los documentos Markdown disponibles en `docs/`. Para tablas pequeñas incluye las filas completas (hasta 20 filas, 15 columnas y 2.500 caracteres); para tablas grandes usa perfiles y una muestra de hasta 8 filas. Si hay ventas y lotes, también aporta el cálculo exacto del riesgo por lote para hasta 20 lotes prioritarios y sus agregados, sin depender de la muestra de ventas.

### Demostración lista para ejecutar

En **Cargar datos empresa**, pulsa **“Cargar demostración con demanda real”**. El botón activa automáticamente:

- ventas reales derivadas de FreshRetailNet-50K;
- un inventario, costes y lote de escenario para mostrar todas las vistas de la app;
- EDA empresarial, inventario, escenarios y riesgo por lote.

Las ventas proceden de la fuente real documentada. El inventario, los costes y la fecha límite se etiquetan como supuestos de escenario porque FreshRetailNet-50K no publica esos datos internos.

Las dos capturas siguientes corresponden al prototipo histórico ResQData AI/FreshMarket y usan datos sintéticos del piloto. Se incluyen para explicar la evolución del proyecto, no como pantallas de ResQ Intelligence. La segunda captura muestra el clasificador antiguo y su probabilidad estimada; el módulo actual de riesgo por lote calcula una proporción estimada de stock no vendido y no presenta una probabilidad calibrada.

![Panel histórico de análisis de FreshMarket con datos sintéticos; no es la interfaz actual](docs/eda_dashboard.png)

![Flujo histórico del clasificador por lote del piloto sintético; no representa el cálculo actual](docs/prediction_workflow.png)

## Ejecución local

Requiere Python 3.11 o superior. Desde la carpeta raíz del repositorio:

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

El primer comando instala las dependencias declaradas; el segundo inicia la aplicación en el navegador. Para arrancar la app en sesiones posteriores basta con `streamlit run app.py`.

El caso FreshMarket genera sus artefactos locales si faltan. La app no almacena los CSV cargados por una empresa fuera de la sesión del navegador.

## Regenerar evidencias

```powershell
python -m src.fetch_eurostat_context
python -m src.data_pipeline
python -m src.train_model
python -m src.real_demand
```

Para regenerar la evaluación real, descarga antes las dos particiones oficiales de FreshRetailNet-50K en `data/external/freshretailnet/`, tal como se explica en [07_datos_reales_y_demanda.md](docs/07_datos_reales_y_demanda.md).
La lectura de esos archivos Parquet requiere `pyarrow`, incluido en `requirements.txt`.

## Verificación

```powershell
python -m pytest -q
```

## Despliegue

La aplicación está preparada para Streamlit Community Cloud con Python 3.11 y `app.py` como archivo principal. La publicación permanece pendiente de autorización expresa.
