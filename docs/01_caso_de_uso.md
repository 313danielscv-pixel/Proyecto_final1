# Caso de uso: priorización de merma por lote

## Problema

Los equipos de tienda revisan manualmente las fechas de caducidad y, cuando detectan un lote comprometido, suelen aplicar la rebaja demasiado tarde. Esto expone margen, genera desperdicio y dificulta decidir qué acción tomar primero.

## Usuario y decisión

El usuario principal es el responsable de frescos de una tienda. Al inicio de la jornada necesita responder:

1. ¿Qué lotes tienen mayor probabilidad de acabar en merma?
2. ¿Qué coste potencial está expuesto?
3. ¿Conviene mantener el precio, descontar o preparar una donación/retiro seguro?

## Producto

ResQData AI convierte los datos disponibles del lote en una recomendación:

- Probabilidad estimada de merma.
- Nivel de priorización mediante coste expuesto.
- Acción y descuento sugeridos con una razón legible.

La aplicación no ejecuta cambios en cajas, precios o sistemas de terceros. Es una herramienta de apoyo a decisiones para un piloto.

## Criterio de éxito

El modelo debe identificar lotes que acabarán en merma sin mezclar instantáneas del mismo lote entre entrenamiento y validación. El producto debe permitir introducir un lote nuevo y obtener una salida comprensible sin consultar el código.

## Alcance y límites

FreshMarket es una empresa ficticia y el histórico operativo es sintético. La fase siguiente antes de producción sería integrar registros reales anonimizados de inventario, ventas y bajas, acordar el coste de cada acción y ejecutar un piloto controlado por tienda.
