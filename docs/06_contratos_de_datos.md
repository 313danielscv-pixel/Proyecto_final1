# Contratos de datos de ResQ Intelligence

ResQ Intelligence no presupone que todas las empresas tengan la misma estructura de datos. En lugar de exigir un único archivo rígido, la plataforma acepta conjuntos opcionales y habilita cada módulo solo cuando dispone de los campos necesarios.

## Plantillas

| Archivo | Finalidad | Módulos que puede habilitar |
|---|---|---|
| [`ventas.csv`](../data/templates/ventas.csv) | Historial de unidades vendidas. | Demanda, análisis de facturación y rentabilidad si incluye precio. |
| [`inventario.csv`](../data/templates/inventario.csv) | Stock a una fecha concreta. | Cobertura, rotura, sobrestock y capital inmovilizado. |
| [`costes.csv`](../data/templates/costes.csv) | Precio, coste y almacenamiento. | Margen y escenarios económicos. |
| [`proveedores.csv`](../data/templates/proveedores.csv) | Plazos, pedido mínimo y coste de compra. | Riesgo de reposición y análisis de proveedores. |
| [`lotes.csv`](../data/templates/lotes.csv) | Stock por lote y fecha límite. | Riesgo por lote para perecederos, obsolescencia o caducidad. |

Los ejemplos contienen datos ficticios de una sola fila. Son plantillas, no datos de demostración.

## Permisos y datos personales

El proyecto no utiliza datos personales en sus fuentes públicas ni en la demo. Quien cargue datos de una empresa debe contar con autorización para utilizarlos y retirar o anonimizar identificadores personales antes de la carga. ResQ valida columnas y calidad, pero no detecta ni anonimiza automáticamente datos personales.

## Mínimos por módulo

| Módulo | Datos necesarios | Si faltan datos |
|---|---|---|
| Demanda | Fecha, producto y cantidad vendida. | Solo se muestra análisis disponible; no se genera previsión. |
| Inventario | Fecha de inventario, producto y stock disponible. | No se calculan cobertura ni riesgos de stock. |
| Rentabilidad | Producto, coste y precio. | No se calcula margen ni escenarios económicos. |
| Proveedores | Proveedor, producto y plazo de entrega. | No se calcula dependencia ni riesgo de reposición por proveedor. |
| Perecederos | Fecha de caducidad, además de inventario. | El sistema mantiene el análisis general y oculta el riesgo de caducidad. |
| Riesgo por lote | Lote, producto, stock, fecha límite, coste, confirmación de cobertura completa y al menos 30 días naturales desde el primer registro del producto hasta el final del extracto. | No estima el riesgo y explica que falta confirmación o historial. |

## Reglas de validación que se implementarán en la Fase 1

1. Las columnas obligatorias deben existir o estar correctamente mapeadas desde un alias conocido.
2. Las fechas deben poder convertirse a fecha válida.
3. Las cantidades, precios, costes y plazos deben ser numéricos y no negativos.
4. `product_id` no puede estar vacío en filas usadas para análisis.
5. Las filas duplicadas se señalarán y no se eliminarán sin informar al usuario.
6. Los valores ausentes se contabilizarán por campo y se indicará el módulo afectado.
7. Un archivo inválido mostrará un mensaje con la columna, el motivo y el número de filas afectadas.

## Principio de disponibilidad responsable

La plataforma no completará datos que no existen ni inventará predicciones:

- Menos de 30 observaciones históricas de un producto: no hay previsión, solo análisis descriptivo.
- Sin coste o precio: no hay margen ni resultado económico.
- Sin stock: no hay cobertura ni alerta de sobrestock.
- Sin caducidad: no hay recomendación de liquidación o donación.

Esto permite que la misma plataforma funcione para sectores distintos sin ocultar las limitaciones de cada carga.
