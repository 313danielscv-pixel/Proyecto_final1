"""Group-safe Naive Bayes evaluation for labelled lot-risk snapshots."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.train_model import CATEGORICAL_COLUMNS, FEATURE_COLUMNS, NUMERIC_COLUMNS


TARGET_COLUMN = "hubo_merma"
GROUP_COLUMN = "lote_id"
SNAPSHOT_COLUMN = "snapshot_date"
MINIMUM_LOTS = 20
MINIMUM_LOTS_PER_CLASS = 4
SNAPSHOT_COLUMNS = [
    GROUP_COLUMN,
    SNAPSHOT_COLUMN,
    *FEATURE_COLUMNS,
    TARGET_COLUMN,
]


def _create_model() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline([("imputer", SimpleImputer(strategy="median"))]),
                NUMERIC_COLUMNS,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="constant", fill_value="desconocido")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                CATEGORICAL_COLUMNS,
            ),
        ],
        sparse_threshold=0,
    )
    return Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("classifier", GaussianNB()),
        ]
    )


def evaluate_bayesian_waste_risk(snapshots: pd.DataFrame) -> dict[str, Any]:
    """Evaluate held-out lots and score unlabelled snapshots without lot leakage."""
    missing_columns = set(SNAPSHOT_COLUMNS) - set(snapshots.columns)
    if missing_columns:
        raise ValueError(
            "Faltan columnas necesarias para el análisis: "
            + ", ".join(sorted(missing_columns))
            + ". Descarga y completa la plantilla."
        )

    data = snapshots.loc[:, SNAPSHOT_COLUMNS].copy()
    labels = pd.to_numeric(data[TARGET_COLUMN], errors="coerce")
    invalid_labels = data[TARGET_COLUMN].notna() & labels.isna()
    if invalid_labels.any() or not set(labels.dropna().unique()).issubset({0, 1}):
        raise ValueError(f"La columna {TARGET_COLUMN} debe contener 0, 1 o celdas vacías.")

    data[TARGET_COLUMN] = labels
    data[GROUP_COLUMN] = data[GROUP_COLUMN].astype("string").str.strip()
    labelled = data.loc[data[TARGET_COLUMN].notna() & data[GROUP_COLUMN].notna()].copy()
    unlabelled = data.loc[data[TARGET_COLUMN].isna() & data[GROUP_COLUMN].notna()].copy()
    if labelled.empty:
        raise ValueError("No hay filas etiquetadas: indica 0 o 1 en hubo_merma para el historial.")
    if set(labelled[GROUP_COLUMN]).intersection(unlabelled[GROUP_COLUMN]):
        raise ValueError("Un lote no puede aparecer con y sin etiqueta; deja sin etiqueta todo el historial del lote.")

    label_counts = labelled.groupby(GROUP_COLUMN)[TARGET_COLUMN].nunique()
    if label_counts.gt(1).any():
        raise ValueError("Cada lote debe tener una única etiqueta de merma en todo su historial.")

    lot_labels = labelled.groupby(GROUP_COLUMN)[TARGET_COLUMN].first()
    lots_by_class = lot_labels.value_counts()
    if len(lot_labels) < MINIMUM_LOTS or any(
        lots_by_class.get(label, 0) < MINIMUM_LOTS_PER_CLASS for label in (0, 1)
    ):
        raise ValueError(
            f"Se necesitan al menos {MINIMUM_LOTS} lotes etiquetados y "
            f"{MINIMUM_LOTS_PER_CLASS} lotes de cada clase (merma: 1, sin merma: 0)."
        )

    for column in NUMERIC_COLUMNS:
        labelled[column] = pd.to_numeric(labelled[column], errors="coerce")
        unlabelled[column] = pd.to_numeric(unlabelled[column], errors="coerce")
    for column in CATEGORICAL_COLUMNS:
        labelled[column] = labelled[column].astype("string")
        unlabelled[column] = unlabelled[column].astype("string")

    splitter = GroupShuffleSplit(n_splits=40, test_size=0.25, random_state=42)
    split = None
    for train_indices, test_indices in splitter.split(
        labelled[FEATURE_COLUMNS],
        labelled[TARGET_COLUMN],
        groups=labelled[GROUP_COLUMN],
    ):
        train_lots = set(labelled.iloc[train_indices][GROUP_COLUMN])
        test_lots = set(labelled.iloc[test_indices][GROUP_COLUMN])
        train_labels = labelled.iloc[train_indices][TARGET_COLUMN]
        test_labels = labelled.iloc[test_indices][TARGET_COLUMN]
        if (
            train_labels.nunique() == 2
            and test_labels.nunique() == 2
            and train_lots.isdisjoint(test_lots)
        ):
            split = train_indices, test_indices
            break
    if split is None:
        raise ValueError(
            "No se pudo separar entrenamiento y validación conservando ambas clases. "
            "Carga más lotes etiquetados de ambas clases."
        )

    train_indices, test_indices = split
    train = labelled.iloc[train_indices]
    test = labelled.iloc[test_indices]
    evaluation_model = _create_model()
    evaluation_model.fit(train[FEATURE_COLUMNS], train[TARGET_COLUMN].astype(int))
    test_probabilities = evaluation_model.predict_proba(test[FEATURE_COLUMNS])[:, 1]

    test_results = test.loc[:, [GROUP_COLUMN, SNAPSHOT_COLUMN, TARGET_COLUMN]].copy()
    test_results["probabilidad_merma"] = test_probabilities
    lot_results = (
        test_results.groupby(GROUP_COLUMN, as_index=False)
        .agg(
            snapshot_date=(SNAPSHOT_COLUMN, "max"),
            hubo_merma=(TARGET_COLUMN, "first"),
            probabilidad_merma=("probabilidad_merma", "mean"),
        )
        .assign(tipo_resultado="validación")
    )
    metrics = {
        "lotes_entrenamiento": int(train[GROUP_COLUMN].nunique()),
        "lotes_validacion": int(test[GROUP_COLUMN].nunique()),
        "snapshots_validacion": int(len(test)),
        "tasa_merma_validacion": float(lot_results["hubo_merma"].mean()),
        "auc_roc_por_lote": float(
            roc_auc_score(lot_results["hubo_merma"], lot_results["probabilidad_merma"])
        ),
        "precision_05_por_lote": float(
            precision_score(
                lot_results["hubo_merma"],
                lot_results["probabilidad_merma"].ge(0.5),
                zero_division=0,
            )
        ),
        "recall_05_por_lote": float(
            recall_score(
                lot_results["hubo_merma"],
                lot_results["probabilidad_merma"].ge(0.5),
                zero_division=0,
            )
        ),
        "average_precision_por_lote": float(
            average_precision_score(lot_results["hubo_merma"], lot_results["probabilidad_merma"])
        ),
    }
    if not unlabelled.empty:
        final_model = _create_model()
        final_model.fit(labelled[FEATURE_COLUMNS], labelled[TARGET_COLUMN].astype(int))
        unlabelled_results = unlabelled.loc[:, [GROUP_COLUMN, SNAPSHOT_COLUMN]].copy()
        lot_results["hubo_merma"] = lot_results["hubo_merma"].astype("object")
        unlabelled_results["hubo_merma"] = pd.Series(
            [None] * len(unlabelled_results),
            index=unlabelled_results.index,
            dtype="object",
        )
        unlabelled_results["probabilidad_merma"] = final_model.predict_proba(
            unlabelled[FEATURE_COLUMNS]
        )[:, 1]
        unlabelled_results["tipo_resultado"] = "lote sin etiqueta"
        lot_results = pd.concat([lot_results, unlabelled_results], ignore_index=True)

    lot_results["probabilidad_merma"] = lot_results["probabilidad_merma"].astype(float)
    lot_results = lot_results.sort_values("probabilidad_merma", ascending=False).reset_index(drop=True)
    return {"metrics": metrics, "predictions": lot_results}
