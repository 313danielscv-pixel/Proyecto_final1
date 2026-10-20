# Modelo de riesgo y validación

## Enfoque

El problema se formula como clasificación binaria: para cada instantánea, estimar si el lote acabará con merma. Se utiliza un `RandomForestClassifier` porque combina relaciones no lineales, variables numéricas y categorías codificadas sin exigir una relación lineal entre ellas.

El pipeline aplica imputación y codificación one-hot solo dentro del modelo. Esto evita que la preparación de categorías use información de la partición de validación.

## Separación de datos

Una misma mercancía puede producir varias instantáneas a lo largo de su vida útil. Dividir filas al azar permitiría que instantáneas del mismo lote aparecieran en entrenamiento y prueba, aumentando artificialmente las métricas.

Por ello se usa `GroupShuffleSplit` con `lote_id` como grupo:

- Entrenamiento: 20.426 instantáneas, 2.707 lotes.
- Validación: 7.049 instantáneas, 903 lotes.
- Tasa positiva en validación: 18,43 %.

## Resultados medidos

| Métrica | Resultado |
|---|---:|
| AUC-ROC | 0,9897 |
| Average precision | 0,9546 |
| Precisión | 0,8743 |
| Recall | 0,9099 |
| F1 | 0,8917 |
| Umbral | 0,50 |

Estas métricas se generan en `data/processed/model_metrics.json` al ejecutar `python -m src.train_model`.

## Traducción a decisión

La probabilidad no ejecuta automáticamente una acción. La política de negocio usa niveles transparentes:

| Condición | Acción |
|---|---|
| Riesgo inferior al 30 % | Mantener precio y vigilar |
| Riesgo entre 30 % y 60 % | Descuento preventivo del 15 % |
| Riesgo entre 60 % y 85 % | Descuento de aceleración del 30 % |
| Riesgo superior al 85 % | Descuento de liquidación del 50 % |
| Riesgo superior al 75 % y caducidad hoy | Preparar donación o retirada segura |

El coste expuesto se calcula como `probabilidad × stock × coste unitario`. El importe recuperable es una estimación de escenario según la acción; no es un ahorro ya conseguido.

## Limitaciones

Los resultados son altos porque el generador del piloto incorpora patrones de tienda, categoría y descuentos. No demuestran que el algoritmo alcance el mismo rendimiento con datos reales.

Antes de desplegar se debe:

1. Reentrenar con datos históricos reales y anonimizados.
2. Validar temporalmente, usando un periodo futuro como prueba.
3. Medir el efecto causal de los descuentos con un piloto controlado.
4. Definir restricciones de margen, seguridad alimentaria y disponibilidad de ONG.
5. Monitorizar deriva de datos, tasa de alertas y ahorro realizado.
