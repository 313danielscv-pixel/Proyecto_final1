# ResQData AI

ResQData AI es una aplicación de apoyo a decisiones para supermercados que estima el riesgo de merma de un lote de producto fresco y propone una acción preventiva: mantener el precio, aplicar un descuento o preparar una donación/retiro seguro.

## Caso de uso

FreshMarket, una cadena piloto de cinco tiendas, necesita priorizar los lotes de vida corta antes de que caduquen. En vez de revisar todos los productos de forma manual, el responsable de tienda recibe una probabilidad de merma, una acción explicable y una estimación del coste expuesto.

El proyecto responde a una pregunta operativa concreta:

> ¿Qué lotes requieren una acción hoy para reducir el coste potencial de la merma?

Consulta el contexto, los datos y las decisiones de diseño en [docs/](docs/).

## Qué incluye

- Un modelo relacional de inventario, ventas, mermas y donaciones.
- Un pipeline reproducible que crea 27.475 instantáneas de riesgo por lote.
- Un `RandomForestClassifier` evaluado con separación por `lote_id`.
- Una aplicación Streamlit para evaluar un lote y priorizar una cartera.
- Una fuente pública oficial de contexto: Eurostat `cei_pc035`.
- Pruebas unitarias y documentación de metodología, resultados y limitaciones.

## Datos y transparencia

El histórico operativo de FreshMarket es un **piloto sintético reproducible** creado con semilla fija; no representa operaciones reales de una empresa. El proyecto no presenta sus resultados como desempeño de producción.

Para contextualizar el problema se descarga el indicador oficial Eurostat `cei_pc035`: España registró **65 kg de desperdicio alimentario recogido por habitante en 2022**. Es un indicador nacional de contexto y no se usa para entrenar el clasificador de lotes.

## Aplicación y despliegue

La aplicación está preparada para desplegarse en Streamlit Community Cloud seleccionando:

- repositorio: este repositorio;
- rama: `main`;
- archivo principal: `app.py`;
- versión de Python: 3.11.

No usa secretos ni variables de entorno; [`.env.example`](.env.example) documenta este contrato. En el primer arranque, la aplicación genera el modelo y las instantáneas que falten a partir de los datos del piloto incluidos.

## Instalación y ejecución local

Requiere Python 3.11 o superior. Después de instalar dependencias, el arranque es un único comando:

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

Abre la dirección local que Streamlit muestre en la terminal. La aplicación no requiere claves ni conecta con TPVs. Si quieres regenerar los artefactos manualmente para auditar el flujo, ejecuta:

```powershell
python -m src.fetch_eurostat_context
python -m src.data_pipeline
python -m src.train_model
```

## Verificación

```powershell
python -m pytest tests -q
```

Las pruebas verifican la generación de instantáneas y las reglas de recomendación.

## Estructura

```text
app.py                         Aplicación Streamlit
data/raw/food_waste_pilot.db   Base del piloto sintético
data/processed/                Instantáneas, calidad y métricas generadas
data/external/                 Respuesta descargada de Eurostat
docs/                          Memoria y guion de exposición
models/                        Modelo generado localmente
src/                           Pipeline, entrenamiento y política de negocio
tests/                         Pruebas unitarias
```

Los ficheros de `data/processed/` y `models/` se regeneran con los comandos anteriores. La respuesta de Eurostat incluida en `data/external/` es una captura reproducible del contexto público utilizado.
