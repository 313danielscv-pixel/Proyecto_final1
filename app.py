"""Interactive ResQData AI decision-support application."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import plotly.express as px
import streamlit as st

from src.bootstrap import ensure_application_assets
from src.recommendations import estimated_value_at_risk, recommend_action


ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "waste_risk_model.joblib"
SNAPSHOTS_PATH = ROOT / "data" / "processed" / "risk_snapshots.csv"
METRICS_PATH = ROOT / "data" / "processed" / "model_metrics.json"
EUROSTAT_PATH = ROOT / "data" / "external" / "eurostat_food_waste_spain_2022.json"


@st.cache_resource
def load_model() -> dict[str, object]:
    """Load the persisted training pipeline once per application session."""
    return joblib.load(MODEL_PATH)


@st.cache_data
def load_data() -> tuple[pd.DataFrame, dict[str, object], dict[str, object]]:
    """Load project data and the measured model context."""
    snapshots = pd.read_csv(SNAPSHOTS_PATH)
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    eurostat = json.loads(EUROSTAT_PATH.read_text(encoding="utf-8"))
    return snapshots, metrics, eurostat


def score_lot(model_bundle: dict[str, object], features: dict[str, object]) -> float:
    """Return a waste probability for one operational lot snapshot."""
    feature_frame = pd.DataFrame([features])[model_bundle["features"]]
    return float(model_bundle["model"].predict_proba(feature_frame)[0, 1])


def main() -> None:
    """Render the decision-support workflow."""
    st.set_page_config(page_title="ResQData AI", page_icon="🌱", layout="wide")
    st.title("ResQData AI")
    st.caption("Apoyo a decisiones para anticipar la merma de productos frescos por lote")

    required_assets = (MODEL_PATH, SNAPSHOTS_PATH, METRICS_PATH, EUROSTAT_PATH)
    if not all(path.exists() for path in required_assets):
        with st.spinner("Preparando los datos del piloto y el modelo para esta ejecución..."):
            try:
                ensure_application_assets()
            except (OSError, ValueError) as error:
                st.error(f"No se pudieron preparar los artefactos del proyecto: {error}")
                st.stop()

    snapshots, metrics, eurostat = load_data()
    model_bundle = load_model()

    with st.sidebar:
        st.header("Alcance del piloto")
        st.info(
            "Esta aplicación usa un piloto operativo sintético y reproducible. "
            "Las predicciones sirven para demostrar el flujo, no para operar un TPV real."
        )
        st.metric("Contexto España 2022", f"{eurostat['value_kg_per_capita']} kg/hab")
        st.caption("Indicador Eurostat cei_pc035: desperdicio alimentario recogido por habitante.")

    prediction_tab, portfolio_tab, eda_tab, evidence_tab = st.tabs(
        ["Predicción por lote", "Cartera de riesgo", "Análisis exploratorio", "Evidencia y método"]
    )

    with prediction_tab:
        st.subheader("Evalúa un lote")
        st.write("Introduce el estado disponible del lote para recibir una recomendación explicable.")
        categories = sorted(snapshots["categoria"].unique())
        stores = sorted(snapshots["tienda_nombre"].unique())
        selected_store = st.selectbox("Tienda", stores)
        store_row = snapshots.loc[snapshots["tienda_nombre"] == selected_store].iloc[0]

        left, middle, right = st.columns(3)
        with left:
            category = st.selectbox("Categoría", categories)
            shelf_life = st.number_input("Vida útil total (días)", 1, 30, 4)
            days_remaining = st.number_input("Días restantes", 0, int(shelf_life), min(2, int(shelf_life)))
        with middle:
            received_units = st.number_input("Unidades recibidas", 1, 1000, 40)
            stock = st.number_input("Stock disponible", 0, int(received_units), 24)
            sales_velocity = st.number_input("Venta media diaria", 0.0, 1000.0, 8.0, step=0.5)
        with right:
            sale_price = st.number_input("Precio de venta unitario (€)", 0.01, 1000.0, 5.00, step=0.05)
            unit_cost = st.number_input("Coste unitario (€)", 0.01, float(sale_price), 2.50, step=0.05)
            weekday = st.selectbox(
                "Día de la semana",
                ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            )

        if st.button("Calcular riesgo y recomendación", type="primary"):
            features = {
                "tienda_nombre": selected_store,
                "tipo_ubicacion": store_row["tipo_ubicacion"],
                "categoria": category,
                "dias_vida_util": shelf_life,
                "dias_restantes": days_remaining,
                "unidades_recibidas": received_units,
                "stock_estimado": stock,
                "velocidad_venta_diaria": sales_velocity,
                "precio_venta_base": sale_price,
                "coste_unitario": unit_cost,
                "dia_semana": weekday,
            }
            probability = score_lot(model_bundle, features)
            recommendation = recommend_action(probability, days_remaining)
            exposed_cost, recovered_cost = estimated_value_at_risk(probability, stock, unit_cost, recommendation)
            first, second, third = st.columns(3)
            first.metric("Probabilidad estimada de merma", f"{probability:.1%}")
            second.metric("Coste expuesto estimado", f"{exposed_cost:,.2f} €")
            third.metric("Coste potencialmente recuperable", f"{recovered_cost:,.2f} €")
            st.success(f"**Acción sugerida:** {recommendation.action}")
            st.write(
                f"{recommendation.rationale} Descuento sugerido: **{recommendation.discount_pct}%**. "
                "Los importes son escenarios calculados a partir del coste del lote, no ahorros realizados."
            )

    with portfolio_tab:
        st.subheader("Prioriza la cartera de lotes")
        st.write("Vista de ejemplo construida con la última instantánea disponible de cada lote del piloto.")
        latest = (
            snapshots.sort_values("snapshot_date")
            .groupby("lote_id", as_index=False)
            .tail(1)
            .copy()
        )
        latest["probabilidad_merma"] = load_model()["model"].predict_proba(
            latest[model_bundle["features"]]
        )[:, 1]
        latest["coste_expuesto"] = (
            latest["probabilidad_merma"] * latest["stock_estimado"] * latest["coste_unitario"]
        )
        store_filter = st.multiselect("Filtrar tiendas", stores, default=stores)
        filtered = latest.loc[latest["tienda_nombre"].isin(store_filter)].copy()
        kpi_one, kpi_two, kpi_three = st.columns(3)
        kpi_one.metric("Lotes analizados", f"{len(filtered):,}")
        kpi_two.metric("Riesgo medio", f"{filtered['probabilidad_merma'].mean():.1%}")
        kpi_three.metric("Coste expuesto estimado", f"{filtered['coste_expuesto'].sum():,.0f} €")

        ranking = filtered.nlargest(15, "coste_expuesto")[
            ["lote_id", "tienda_nombre", "categoria", "dias_restantes", "stock_estimado", "probabilidad_merma", "coste_expuesto"]
        ].rename(
            columns={
                "lote_id": "Lote",
                "tienda_nombre": "Tienda",
                "categoria": "Categoría",
                "dias_restantes": "Días restantes",
                "stock_estimado": "Stock",
                "probabilidad_merma": "Riesgo",
                "coste_expuesto": "Coste expuesto (€)",
            }
        )
        st.dataframe(
            ranking.style.format({"Riesgo": "{:.1%}", "Coste expuesto (€)": "{:,.2f}"}),
            use_container_width=True,
            hide_index=True,
        )
        chart = (
            filtered.groupby(["tienda_nombre", "categoria"], as_index=False)["coste_expuesto"]
            .sum()
            .sort_values("coste_expuesto", ascending=False)
        )
        st.plotly_chart(
            px.bar(
                chart,
                x="tienda_nombre",
                y="coste_expuesto",
                color="categoria",
                title="Coste expuesto estimado por tienda y categoría",
                labels={"tienda_nombre": "Tienda", "coste_expuesto": "Coste expuesto (€)", "categoria": "Categoría"},
            ),
            use_container_width=True,
        )

    with eda_tab:
        st.subheader("Dónde se concentra el coste de merma")
        st.write(
            "Este análisis usa los registros de merma observados en el piloto. "
            "Sirve para priorizar categorías y tiendas antes de aplicar el modelo a nuevos lotes."
        )
        observed_waste = snapshots.loc[
            snapshots["dias_restantes"] == 0,
            ["lote_id", "tienda_nombre", "categoria", "coste_merma_eur", "unidades_mermadas"],
        ].drop_duplicates("lote_id")
        category_waste = (
            observed_waste.groupby("categoria", as_index=False)["coste_merma_eur"]
            .sum()
            .sort_values("coste_merma_eur", ascending=False)
        )
        store_waste = (
            observed_waste.groupby("tienda_nombre", as_index=False)["coste_merma_eur"]
            .sum()
            .sort_values("coste_merma_eur", ascending=False)
        )
        total_cost = category_waste["coste_merma_eur"].sum()
        first, second, third = st.columns(3)
        first.metric("Coste de merma observado", f"{total_cost:,.2f} €")
        first_category = category_waste.iloc[0]
        second.metric("Categoría prioritaria", first_category["categoria"])
        second.caption(f"{first_category['coste_merma_eur']:,.2f} € de coste observado")
        top_three_cost = store_waste.head(3)["coste_merma_eur"].sum()
        third.metric("Concentración en tres tiendas", f"{top_three_cost / total_cost:.1%}")
        left, right = st.columns(2)
        with left:
            st.plotly_chart(
                px.bar(
                    category_waste,
                    x="coste_merma_eur",
                    y="categoria",
                    orientation="h",
                    title="Coste de merma por categoría",
                    labels={"coste_merma_eur": "Coste de merma (€)", "categoria": "Categoría"},
                ).update_layout(yaxis={"categoryorder": "total ascending"}),
                use_container_width=True,
            )
        with right:
            st.plotly_chart(
                px.bar(
                    store_waste,
                    x="tienda_nombre",
                    y="coste_merma_eur",
                    title="Coste de merma por tienda",
                    labels={"tienda_nombre": "Tienda", "coste_merma_eur": "Coste de merma (€)"},
                ),
                use_container_width=True,
            )
        st.info(
            "Decisión derivada: iniciar el piloto comercial en las tiendas y categorías con mayor coste "
            "observado, y comparar sus prácticas con las tiendas de menor merma."
        )

    with evidence_tab:
        st.subheader("Qué respalda la recomendación")
        metrics_columns = st.columns(4)
        metrics_columns[0].metric("AUC-ROC", metrics["roc_auc"])
        metrics_columns[1].metric("Precision", metrics["precision"])
        metrics_columns[2].metric("Recall", metrics["recall"])
        metrics_columns[3].metric("F1", metrics["f1"])
        st.caption(metrics["validation_strategy"])
        st.warning(metrics["data_limitation"])
        st.markdown(
            """
            **Variables utilizadas:** días restantes, stock, velocidad de venta, categoría,
            tienda, tipo de ubicación, precio, coste y día de la semana.

            **Uso responsable:** el descuento recomendado es una regla de negocio sobre la
            probabilidad predicha. Antes de automatizar decisiones se debe validar con datos
            reales de inventario, ventas y caducidades de cada cadena.
            """
        )


if __name__ == "__main__":
    main()
