# Caso de uso — ResQ Intelligence

## Problema

Las empresas suelen tener sus ventas, inventario y costes repartidos entre archivos. Antes de decidir cuánto reponer, qué producto revisar o qué escenario económico probar, necesitan comprobar que los datos son utilizables y entender sus límites.

## Usuario y decisión

El usuario principal es una persona responsable de operaciones, compras o finanzas. Con los datos disponibles debe poder responder:

1. ¿Qué productos muestran cambios de demanda o problemas de calidad de datos?
2. ¿Qué inventario está expuesto a rotura, sobrestock o capital inmovilizado?
3. ¿Qué cambiaría el margen bajo supuestos distintos de precio, demanda y almacenamiento?
4. Si hay lotes con fecha límite, ¿cuáles conviene revisar primero?

## Propuesta

ResQ Intelligence es una plataforma B2B de apoyo a decisiones. Permite cargar CSV o Excel, validar su estructura, explorar los datos y comparar escenarios. Los módulos se activan según los campos disponibles; la fecha de caducidad no es necesaria para el análisis empresarial general.

El recorrido es:

**Cargar → validar → explorar → priorizar → comparar escenarios.**

La plataforma informa de los datos y supuestos que respaldan cada resultado. No ejecuta cambios de precio, reposición ni acciones en sistemas externos.

## Caso vertical conservado

FreshMarket mantiene el caso especializado de perecederos que dio origen al proyecto: riesgo de merma por lote, fecha límite y posibles acciones. Sus datos operativos son sintéticos. El módulo empresarial de riesgo por lote es opcional y calcula una proporción estimada de stock sin vender a partir de los archivos de la empresa; no reutiliza los lotes sintéticos de FreshMarket.

## Criterio de éxito

Una persona puede cargar datos, identificar problemas de calidad, revisar métricas explicables y comparar escenarios sin confundir una estimación con un resultado real. Si faltan datos o historial, la plataforma informa de la limitación en vez de inventar una conclusión.

## Alcance y límites

ResQ Intelligence es un prototipo académico. La previsión con FreshRetailNet-50K demuestra una línea base sobre datos públicos, no el rendimiento para una empresa concreta. Antes de tomar decisiones operativas, cada organización debe validar sus datos, acordar sus reglas de negocio y evaluar las estimaciones con su propio histórico.
