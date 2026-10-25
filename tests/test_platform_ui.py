from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.demo_data import DEMO_COLUMN_UNITS
from src.platform_ui import _eda_axis_label


def test_navigation_ends_at_report_without_methodology() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run()

    navigation = next(widget for widget in app.radio if widget.key == "main_navigation")
    assert navigation.options[-1] == "Informe"
    assert "Metodología" not in navigation.options


def test_eda_axis_label_requires_a_declared_unit() -> None:
    assert _eda_axis_label("units", " kg ") == "units (kg)"
    assert _eda_axis_label("units") == "units (unidad no especificada)"


def test_advanced_eda_applies_declared_units_to_chart_axes() -> None:
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=40),
            "units": [float(value + 1) for value in range(40)],
            "revenue": [
                float((value + 1) * 2 + value % 3) for value in range(40)
            ],
            "promotion": [value % 2 == 0 for value in range(40)],
        }
    )
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path))
    app.session_state["free_eda_data"] = {"sample": frame}
    app.run()
    next(widget for widget in app.radio if widget.key == "main_navigation").set_value(
        "Análisis exploratorio"
    )
    app.run()
    next(widget for widget in app.radio if widget.key == "analysis_view").set_value(
        "EDA avanzado"
    )
    app.run()

    figures = [json.loads(chart.proto.spec) for chart in app.get("plotly_chart")]
    serialized_figures = json.dumps(figures, ensure_ascii=False)
    assert "units (unidad no especificada)" in serialized_figures
    assert "revenue (unidad no especificada)" in serialized_figures

    units_by_widget = {
        "Unidad de units": "unidades/día",
        "Unidad de revenue": "€",
    }
    for widget in app.text_input:
        widget.set_value(units_by_widget[widget.label])
    app.run()

    figures = [json.loads(chart.proto.spec) for chart in app.get("plotly_chart")]
    serialized_figures = json.dumps(figures, ensure_ascii=False)
    assert "units (unidades/día)" in serialized_figures
    assert "revenue (€)" in serialized_figures

    next(widget for widget in app.button if widget.label == "Crear segmentos").click()
    app.run()
    cluster_figure = next(
        json.loads(chart.proto.spec)
        for chart in app.get("plotly_chart")
        if json.loads(chart.proto.spec).get("layout", {}).get("title", {}).get("text")
        == "Segmentación exploratoria"
    )
    assert (
        cluster_figure["layout"]["xaxis"]["title"]["text"]
        == "units (unidades/día)"
    )
    assert cluster_figure["layout"]["yaxis"]["title"]["text"] == "revenue (€)"
    assert len(app.exception) == 0


def test_business_distribution_histogram_labels_frequency_axis() -> None:
    demo_sales = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "demo"
        / "ventas_demanda_real_demo.csv"
    )
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.session_state["business_data"] = {"sales": pd.read_csv(demo_sales)}
    app.run()
    next(widget for widget in app.radio if widget.key == "main_navigation").set_value(
        "Análisis exploratorio"
    )
    app.run()

    histogram = next(
        json.loads(chart.proto.spec)
        for chart in app.get("plotly_chart")
        if json.loads(chart.proto.spec).get("layout", {}).get("title", {}).get("text")
        == "Frecuencia de unidades por fecha observada"
    )
    assert histogram["layout"]["xaxis"]["title"]["text"] == "Unidades por fecha"
    assert histogram["layout"]["yaxis"]["title"]["text"] == "Número de fechas"
    for chart in app.get("plotly_chart"):
        layout = json.loads(chart.proto.spec)["layout"]
        assert layout.get("title", {}).get("text")
        assert any(
            layout.get(axis, {}).get("title", {}).get("text")
            for axis in ("xaxis", "yaxis")
        )
    assert len(app.exception) == 0


def test_demo_unit_metadata_covers_all_populated_numeric_columns() -> None:
    demo_directory = Path(__file__).resolve().parents[1] / "data" / "demo"
    metadata = json.loads((demo_directory / "README_DEMO.json").read_text(encoding="utf-8"))
    assert metadata["column_units"] == DEMO_COLUMN_UNITS
    file_names = {
        "sales": "ventas_demanda_real_demo.csv",
        "inventory": "inventario_escenario_demo.csv",
        "costs": "costes_escenario_demo.csv",
        "lots": "lotes_escenario_demo.csv",
    }
    for dataset_name, file_name in file_names.items():
        data = pd.read_csv(demo_directory / file_name)
        populated_numeric_columns = {
            column
            for column in data.select_dtypes(include="number").columns
            if pd.to_numeric(data[column], errors="coerce")
            .replace([float("inf"), float("-inf")], float("nan"))
            .notna()
            .any()
        }
        assert set(DEMO_COLUMN_UNITS[dataset_name]) == populated_numeric_columns


def test_demo_eda_preloads_units_for_each_dataset() -> None:
    demo_directory = Path(__file__).resolve().parents[1] / "data" / "demo"
    file_names = {
        "sales": "ventas_demanda_real_demo.csv",
        "inventory": "inventario_escenario_demo.csv",
        "costs": "costes_escenario_demo.csv",
        "lots": "lotes_escenario_demo.csv",
    }
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.session_state["business_data"] = {
        dataset_name: pd.read_csv(demo_directory / file_name)
        for dataset_name, file_name in file_names.items()
    }
    app.session_state["demo_loaded"] = True
    app.run()
    next(widget for widget in app.radio if widget.key == "main_navigation").set_value(
        "Análisis exploratorio"
    )
    app.run()
    next(widget for widget in app.radio if widget.key == "analysis_view").set_value(
        "EDA avanzado"
    )
    app.run()

    dataset_selector = next(
        widget for widget in app.selectbox if widget.label == "Conjunto de datos"
    )
    assert dataset_selector.value == "sales"

    for dataset_name in ("sales", "inventory", "costs", "lots"):
        selector = next(
            widget for widget in app.selectbox if widget.label == "Conjunto de datos"
        )
        selector.set_value(dataset_name)
        app.run()
        units = {
            widget.label.replace("Unidad de ", "", 1): widget.value
            for widget in app.text_input
        }
        assert units == DEMO_COLUMN_UNITS[dataset_name]
        figures = [json.loads(chart.proto.spec) for chart in app.get("plotly_chart")]
        serialized_figures = json.dumps(figures, ensure_ascii=False)
        for figure in figures:
            layout = figure["layout"]
            assert layout.get("title", {}).get("text")
            assert any(
                layout.get(axis, {}).get("title", {}).get("text")
                for axis in ("xaxis", "yaxis")
            )
        for column, unit in units.items():
            assert f"{column} ({unit})" in serialized_figures
        assert "unidad no especificada" not in serialized_figures
    assert len(app.exception) == 0


def test_uploaded_sales_replace_demo_sales_and_update_home(monkeypatch) -> None:
    demo_directory = Path(__file__).resolve().parents[1] / "data" / "demo"
    file_names = {
        "sales": "ventas_demanda_real_demo.csv",
        "inventory": "inventario_escenario_demo.csv",
        "costs": "costes_escenario_demo.csv",
        "lots": "lotes_escenario_demo.csv",
    }
    demo_data = {
        dataset_name: pd.read_csv(demo_directory / file_name)
        for dataset_name, file_name in file_names.items()
    }
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.session_state["business_data"] = demo_data
    app.session_state["demo_loaded"] = True
    app.run()
    next(widget for widget in app.radio if widget.key == "main_navigation").set_value(
        "Datos y calidad"
    )

    class UploadedSales:
        name = "ventas_empresa.csv"

        @staticmethod
        def getvalue() -> bytes:
            return b"date,product_id,quantity,store_id\n2026-10-24,REAL-001,42,REAL-STORE\n"

    def file_uploader(label, *args, **kwargs):
        if kwargs.get("key") == "upload_sales":
            return UploadedSales()
        return None

    monkeypatch.setattr("streamlit.file_uploader", file_uploader)
    app.run()

    assert app.session_state["demo_loaded"] is False
    business_data = app.session_state["business_data"]
    assert business_data["sales"]["product_id"].tolist() == ["REAL-001"]
    assert business_data["sales"]["quantity"].sum() == 42
    assert business_data["inventory"].equals(demo_data["inventory"])
    assert (
        app.session_state["data_sources"]["sales"]
        == "Archivo cargado por el usuario: ventas_empresa.csv"
    )
    assert len(app.exception) == 0

    next(widget for widget in app.radio if widget.key == "main_navigation").set_value(
        "Inicio"
    )
    app.run()
    units_metric = next(
        metric for metric in app.get("metric") if metric.label == "Unidades"
    )
    assert units_metric.value == "42"
    assert len(app.exception) == 0
