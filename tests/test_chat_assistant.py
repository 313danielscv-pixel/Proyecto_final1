from __future__ import annotations

import json

import pandas as pd
import pytest

import src.chat_assistant as chat_assistant
from src.chat_assistant import (
    OllamaError,
    ask_ollama,
    build_assistant_context,
    list_ollama_models,
)


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_context_includes_project_docs_source_and_complete_small_dataset(tmp_path) -> None:
    (tmp_path / "README.md").write_text("ResQ es una plataforma Streamlit.", encoding="utf-8")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "02_datos_y_eda.md").write_text("Los días ausentes no son cero ventas.", encoding="utf-8")
    sales = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02"],
            "product_id": ["SKU-1", "SKU-1"],
            "quantity": [3, 5],
        }
    )

    context = build_assistant_context(
        business_data={"sales": sales},
        free_data={},
        data_sources={"sales": "CSV de prueba"},
        project_root=tmp_path,
    )

    assert "ResQ es una plataforma Streamlit." in context
    assert "Los días ausentes no son cero ventas." in context
    assert "CSV de prueba" in context
    assert "8 unidades" in context
    assert '"quantity":3' in context
    assert "conjunto completo" in context


def test_context_includes_complete_readme_and_all_available_methodology_docs(tmp_path) -> None:
    (tmp_path / "README.md").write_text(
        "Inicio del README.\n" + ("contenido largo.\n" * 700) + "MARCADOR_FINAL_README",
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    doc_paths = [
        docs / f"{number:02d}_metodologia.md"
        for number in (1, 2, 3, 5, 6, 7)
    ]
    for number, path in enumerate(doc_paths, start=1):
        path.write_text(f"METODOLOGIA_DOC_{number}", encoding="utf-8")

    context = build_assistant_context({}, {}, {}, project_root=tmp_path)

    assert "MARCADOR_FINAL_README" in context
    for path in doc_paths:
        assert path.read_text(encoding="utf-8") in context
    assert "Documentación recortada" not in context


def test_large_dataset_context_is_marked_as_a_sample(tmp_path) -> None:
    data = pd.DataFrame({"record_id": [f"row-{index}" for index in range(101)]})

    context = build_assistant_context({}, {"dataset": data}, {}, project_root=tmp_path)

    assert "muestra de hasta 8 filas" in context
    assert "row-7" in context
    assert "row-14" not in context
    assert "row-100" not in context


def test_context_keeps_lot_records_after_large_dataset_summaries() -> None:
    wide_data = pd.DataFrame(
        {f"measure_{column}": range(100) for column in range(40)}
    )
    lots = pd.DataFrame(
        {
            "lot_id": [f"LOT-{index:02d}" for index in range(1, 9)],
            "product_id": [f"SKU-{index:02d}" for index in range(1, 9)],
            "stock_available": [40] * 8,
            "expiry_date": ["2026-02-03"] * 8,
            "unit_cost": [4.0] * 8,
        }
    )

    context = build_assistant_context(
        {"sales": wide_data, "lots": lots},
        {"wide-1": wide_data, "wide-2": wide_data},
        {},
    )

    assert "LOT-08" in context
    assert "Contexto de datos recortado" not in context


def test_context_includes_calculated_lot_risk_not_only_raw_rows() -> None:
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    sales = pd.DataFrame(
        {"date": dates, "product_id": ["SKU-1"] * len(dates), "quantity": [1] * len(dates)}
    )
    lots = pd.DataFrame(
        {
            "lot_id": ["LOT-1"],
            "product_id": ["SKU-1"],
            "stock_available": [40],
            "expiry_date": ["2026-02-03"],
            "unit_cost": [4.0],
        }
    )

    context = build_assistant_context(
        {"sales": sales, "lots": lots},
        {},
        {},
        sales_period_complete=True,
    )

    assert "Riesgo por lote calculado por la aplicación" in context
    assert '"lot_id":"LOT-1"' in context
    assert '"risk_level":"Crítico"' in context
    assert "Liquidar o reasignar con prioridad" in context


def test_context_withholds_lot_risk_until_sales_period_is_confirmed() -> None:
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    sales = pd.DataFrame(
        {"date": dates, "product_id": ["SKU-1"] * len(dates), "quantity": [1] * len(dates)}
    )
    lots = pd.DataFrame(
        {
            "lot_id": ["LOT-1"],
            "product_id": ["SKU-1"],
            "stock_available": [40],
            "expiry_date": ["2026-02-03"],
            "unit_cost": [4.0],
        }
    )

    context = build_assistant_context({"sales": sales, "lots": lots}, {}, {})

    assert "Integridad del periodo de ventas: no confirmada" in context
    assert "Confirma que las ventas cubren todos los días" in context
    assert '"risk_level"' not in context


def test_list_ollama_models_returns_installed_chat_and_embedding_models(monkeypatch) -> None:
    response = FakeResponse(
        {
            "models": [
                {"name": "qwen3.6:latest"},
                {"name": "embeddinggemma:latest"},
            ]
        }
    )
    def fake_urlopen(request, timeout):
        assert request.full_url == "http://127.0.0.1:11434/api/tags"
        assert timeout == 5
        return response

    monkeypatch.setattr(chat_assistant, "urlopen", fake_urlopen)

    assert list_ollama_models() == ["embeddinggemma:latest", "qwen3.6:latest"]


def test_ask_ollama_sends_local_context_history_and_returns_answer(monkeypatch) -> None:
    response = FakeResponse({"message": {"content": "La demo registra 8 unidades."}})
    requests = []

    def fake_urlopen(*args, **kwargs):
        requests.append((args[0], kwargs["timeout"]))
        return response

    monkeypatch.setattr(chat_assistant, "urlopen", fake_urlopen)

    answer = ask_ollama(
        question="¿Cuántas unidades hay?",
        context="Ventas: 8 unidades.",
        model="qwen3.6:latest",
        history=[{"role": "user", "content": "Hola"}],
    )

    payload = json.loads(requests[0][0].data)
    assert requests[0][0].full_url == "http://127.0.0.1:11434/api/chat"
    assert requests[0][1] == chat_assistant.OLLAMA_TIMEOUT_SECONDS
    assert payload["model"] == "qwen3.6:latest"
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][0]["content"].endswith("Ventas: 8 unidades.")
    assert payload["messages"][1] == {"role": "user", "content": "Hola"}
    assert payload["messages"][-1] == {"role": "user", "content": "¿Cuántas unidades hay?"}
    assert answer == "La demo registra 8 unidades."


def test_assistant_rejects_remote_ollama_hosts() -> None:
    with pytest.raises(OllamaError, match="solo puede conectarse"):
        list_ollama_models("https://example.com")
