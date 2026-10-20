# Guion de presentación final

Duración orientativa: 8 a 10 minutos.

## 1. Problema: decidir antes de que caduque

“En frescos, detectar tarde un lote comprometido significa perder margen y alimento. La decisión no es solo si aplicar un descuento: es saber qué lote necesita atención primero y cuánto valor está en riesgo.”

Muestra: portada de ResQData AI y la pregunta de negocio.

## 2. Caso de uso y usuario

Presenta FreshMarket como escenario de piloto de cinco tiendas. Explica que el responsable de frescos necesita priorizar lotes cada mañana y que la aplicación no modifica TPVs.

Muestra: `docs/01_caso_de_uso.md`.

## 3. Datos y honestidad metodológica

“El histórico operativo es sintético y reproducible; por eso no presento las métricas como resultados de producción. Lo uso para probar un flujo completo. Para dimensionar el problema incorporo el indicador oficial de Eurostat: 65 kg por habitante en España en 2022.”

Muestra: fuente Eurostat y esquema de las seis tablas.

## 4. Evidencia del análisis

Destaca tres cifras:

- 17.422,10 EUR de coste de merma del piloto.
- 8.397,10 EUR concentrados en platos preparados.
- 16.196,60 EUR concentrados en Eixample, Vallecas y Ruzafa.

Conclusión: no conviene repartir el esfuerzo por igual; el piloto comercial debería centrarse en categorías y tiendas concretas.

## 5. Construcción del modelo

Explica las variables que estarían disponibles al tomar la decisión: días restantes, stock, velocidad de venta, categoría, tienda y coste. Aclara que las ventas futuras no se usan para construir la instantánea.

## 6. Validación

“No separé filas al azar: separé por lote. Así ningún lote aparece parcialmente en entrenamiento y parcialmente en prueba.”

Muestra: AUC-ROC 0,9897, precision 0,8743 y recall 0,9099. Inmediatamente recuerda que proceden de un piloto sintético.

## 7. Demostración de la aplicación

Abre la pestaña **Predicción por lote**:

1. Elige una tienda y una categoría de plato preparado.
2. Introduce dos días restantes, stock alto y venta diaria baja.
3. Ejecuta la predicción.
4. Explica la probabilidad, el coste expuesto y la acción recomendada.

Después abre **Cartera de riesgo** y enseña cómo se priorizan los lotes por coste expuesto, no solo por porcentaje de riesgo.

## 8. Valor de negocio

“La salida no promete ahorro: convierte el riesgo en una lista de trabajo priorizada. La cadena puede empezar por las tres tiendas con más coste expuesto, medir la respuesta al descuento y comparar el desperdicio frente a un periodo de referencia.”

## 9. Límites y siguiente paso

Termina con un plan de implantación:

1. Integrar inventario, ventas y bajas reales anonimizadas.
2. Ejecutar un piloto de ocho semanas en las tres tiendas prioritarias.
3. Medir merma, margen, venta acelerada y donación.
4. Ajustar umbrales antes de automatizar cualquier precio.

## Preguntas previsibles

**¿Por qué no automatizar ya los descuentos?**  
Porque el histórico es sintético y se debe medir el margen y la respuesta del cliente con datos reales.

**¿Qué haría primero un cliente real?**  
Conectar las fuentes mínimas: lote, caducidad, stock, venta diaria, precio y coste.

**¿Qué diferencia aporta frente a una hoja de cálculo?**  
La aplicación combina múltiples señales, calcula una probabilidad, prioriza por coste y mantiene una política de acción uniforme y auditable.
