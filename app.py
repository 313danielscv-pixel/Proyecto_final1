"""ResQ Intelligence Streamlit application."""

from __future__ import annotations

import os
from typing import Mapping

import pandas as pd
import streamlit as st

from src.chat_assistant import (
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_MODEL,
    OllamaError,
    ask_ollama,
    build_assistant_context,
    list_ollama_models,
)
from src.platform_ui import (
    render_advanced_eda,
    render_business_eda,
    render_data_sources,
    render_home,
    render_inventory_profitability,
    render_lot_risk,
    render_methodology,
    render_real_demand,
    render_report,
    render_scenarios,
    render_uploads,
)


PAGE_DESCRIPTIONS = {
    "Inicio": "Una vista rápida de los datos disponibles y de los indicadores respaldados por ellos.",
    "Datos y calidad": "Carga CSV o Excel, o conecta una base de datos de solo lectura; revisa los campos antes de analizar.",
    "Análisis exploratorio": "Explora demanda, distribuciones, relaciones y comportamiento temporal.",
    "Demanda": "Consulta la evaluación de una referencia de demanda sobre datos públicos reales.",
    "Inventario y rentabilidad": "Revisa cobertura, capital en inventario y señales de rotura o sobrestock.",
    "Riesgo por lote": "Prioriza lotes con fecha límite usando las ventas históricas cargadas.",
    "Escenarios": "Compara el margen base con supuestos explícitos de precio y demanda.",
    "Fuentes": "Comprueba la procedencia y naturaleza de los datos disponibles en esta sesión.",
    "Informe": "Descarga un resumen verificable de calidad, resultados, procedencia y limitaciones.",
    "Metodología": "Entiende qué calcula cada módulo y qué conclusiones no permite extraer.",
}


def _apply_visual_style() -> None:
    """Apply a restrained shared visual theme to Streamlit's native components."""
    st.markdown(
        """
        <style>
        :root {
            --rq-ink: #e7eef7;
            --rq-muted: #9aa9bc;
            --rq-primary: #2cc9a7;
            --rq-border: #26364b;
            --rq-surface: #121d2d;
        }
        .stApp {
            background: #0b1220;
            color: var(--rq-ink);
        }
        [data-testid="stHeader"] {
            background: #0b1220;
        }
        [data-testid="stAppViewContainer"] .main .block-container {
            max-width: 1480px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        [data-testid="stSidebar"] {
            background: #0e1726;
            border-right: 1px solid var(--rq-border);
        }
        [data-testid="stDecoration"] {
            background: var(--rq-primary) !important;
            background-image: none !important;
        }
        [data-testid="stSidebar"] label[data-baseweb="radio"] {
            border-radius: 8px;
            padding: 0.35rem 0.5rem;
        }
        [data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
            background: #17263a;
        }
        [data-testid="stSidebar"] label[data-baseweb="radio"]:has(input[type="radio"]:checked) {
            background: #12352f;
        }
        [data-testid="stSidebar"] label[data-baseweb="radio"] > div:last-child {
            color: var(--rq-ink) !important;
        }
        [data-testid="stSidebar"] label[data-baseweb="radio"]:has(input[type="radio"]:checked) > div:first-child,
        [data-testid="stSidebar"] label[data-baseweb="radio"]:has(input[type="radio"]:checked) > div:first-child > div:first-child {
            border-color: var(--rq-primary) !important;
            background-color: var(--rq-primary) !important;
        }
        [data-testid="stSidebar"] label[data-baseweb="radio"]:has(input[type="radio"]:checked) > div:last-child {
            color: var(--rq-primary);
            font-weight: 650;
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4,
        h1, h2, h3, h4, h5 {
            color: var(--rq-ink);
        }
        [data-testid="stCaptionContainer"] {
            color: var(--rq-muted) !important;
        }
        [data-testid="stMetric"] {
            background: var(--rq-surface);
            border: 1px solid var(--rq-border);
            border-radius: 14px;
            padding: 1rem 1.1rem;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
        }
        [data-testid="stMetricLabel"] {
            color: var(--rq-muted);
        }
        div.stButton > button[kind="primary"],
        div.stDownloadButton > button[kind="primary"] {
            background: var(--rq-primary);
            border-color: var(--rq-primary);
        }
        div.stButton > button[kind="primary"]:hover,
        div.stDownloadButton > button[kind="primary"]:hover {
            background: #20a98d;
            border-color: #20a98d;
        }
        [data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--rq-primary);
        }
        [data-testid="stAlert"] {
            background: #13263a !important;
            border: 1px solid #24415e;
            border-radius: 12px;
            color: var(--rq-ink) !important;
        }
        [data-testid="stAlert"] p,
        [data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
            color: var(--rq-ink) !important;
        }
        a {
            color: var(--rq-primary);
        }
        @media (max-width: 700px) {
            [data-testid="stAppViewContainer"] .main .block-container {
                padding: 1rem 1rem 2rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar_chat(
    business_data: Mapping[str, pd.DataFrame],
    free_data: Mapping[str, pd.DataFrame],
    data_sources: Mapping[str, str],
) -> None:
    """Render an optional local-only assistant for project and session questions."""
    with st.expander("Chat sobre ResQ", expanded=False):
        st.caption("Asistente local para ResQ y los datos cargados.")
        with st.popover("Privacidad y límites"):
            st.caption("Pregunta sobre la aplicación, su metodología o los datos cargados.")
            st.caption("El modelo y el contexto se procesan en este equipo; no se llama a servicios externos.")
            st.caption(
                "Para tablas grandes, el chat recibe perfiles y una muestra, no todas las filas. "
                "La vista de Calidad conserva el archivo completo."
            )

        host = os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
        if st.button("Conectar con Ollama", key="resq_chat_connect"):
            try:
                st.session_state["resq_chat_models"] = list_ollama_models(host)
                st.session_state.pop("resq_chat_connection_error", None)
            except OllamaError as error:
                st.session_state["resq_chat_models"] = []
                st.session_state["resq_chat_connection_error"] = str(error)

        history = st.session_state.setdefault("resq_chat_messages", [])
        for message in history[-8:]:
            if isinstance(message, dict) and message.get("role") in {"user", "assistant"}:
                with st.chat_message(message["role"]):
                    st.markdown(str(message.get("content", "")))

        models = st.session_state.get("resq_chat_models")
        if models is None:
            st.info("Pulsa **Conectar con Ollama** para detectar los modelos locales.")
            return
        if not models:
            connection_error = st.session_state.get("resq_chat_connection_error")
            if connection_error:
                st.warning(connection_error)
                st.code("ollama serve", language="powershell")
            else:
                st.info("No hay modelos de chat instalados en Ollama.")
                st.code("ollama pull qwen3.6:latest", language="powershell")
            return

        chat_models = [model for model in models if "embed" not in model.lower()]
        if not chat_models:
            st.info("Los modelos instalados son de embeddings y no pueden responder en un chat.")
            st.code("ollama pull qwen3.6:latest", language="powershell")
            return

        st.success("Conectado con un modelo local de Ollama.")
        preferred_model = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        model_index = chat_models.index(preferred_model) if preferred_model in chat_models else 0
        model = st.selectbox(
            "Modelo local",
            chat_models,
            index=model_index,
            key="resq_chat_model",
        )
        with st.form("resq_sidebar_chat_form", clear_on_submit=True):
            question = st.text_input(
                "Chatbot",
                placeholder="¿Qué significan estos resultados?",
                max_chars=2000,
            )
            submitted = st.form_submit_button("Preguntar", type="primary")

        if not submitted:
            return
        if not question.strip():
            st.warning("Escribe una pregunta para el asistente.")
            return

        messages = st.session_state["resq_chat_messages"]
        messages.append({"role": "user", "content": question.strip()})
        try:
            context = build_assistant_context(
                business_data=business_data,
                free_data=free_data,
                data_sources=data_sources,
                sales_period_complete=bool(
                    st.session_state.get("sales_period_complete", st.session_state.get("demo_loaded", False))
                ),
            )
            answer = ask_ollama(
                question=question,
                context=context,
                model=model,
                history=messages[:-1],
                host=host,
            )
        except (OllamaError, OSError, TypeError, ValueError) as error:
            st.error(f"No se pudo responder con el asistente local: {error}")
            with st.chat_message("user"):
                st.markdown(question)
            st.session_state["resq_chat_messages"] = messages[-12:]
            return

        messages.append({"role": "assistant", "content": answer})
        st.session_state["resq_chat_messages"] = messages[-12:]
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            st.markdown(answer)


def main() -> None:
    """Render the platform through a persistent, task-oriented sidebar."""
    st.set_page_config(page_title="ResQ Intelligence", page_icon="📈", layout="wide")
    _apply_visual_style()

    with st.sidebar:
        st.markdown(
            """
            <div style="padding:0.4rem 0 1.1rem">
              <div style="font-size:0.75rem;letter-spacing:0.14em;font-weight:700;color:#2cc9a7">RESQ</div>
              <div style="font-size:1.35rem;font-weight:750;color:#e7eef7">Intelligence</div>
              <div style="font-size:0.83rem;color:#9aa9bc">Decisiones basadas en datos</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        section = st.radio(
            "Navegación",
            list(PAGE_DESCRIPTIONS),
            key="main_navigation",
            label_visibility="collapsed",
        )
        st.divider()
        business_data = st.session_state.get("business_data", {})
        free_data = st.session_state.get("free_eda_data", {})
        dataset_count = len(business_data) + len(free_data)
        st.caption("DATOS DE ESTA SESIÓN")
        if st.session_state.get("demo_loaded"):
            st.info("Demo activa: ventas reales derivadas; inventario, costes y lotes son supuestos.")
        elif dataset_count:
            st.success(f"{dataset_count} conjunto(s) cargado(s)")
        else:
            st.caption("Aún no has cargado datos.")
        st.caption("Los datos importados se mantienen en esta sesión; no se guardan en el repositorio.")
        st.divider()
        _render_sidebar_chat(
            business_data=business_data,
            free_data=free_data,
            data_sources=st.session_state.get("data_sources", {}),
        )

    st.markdown(
        '<div style="font-size:0.73rem;letter-spacing:0.12em;font-weight:700;color:#2cc9a7">RESQ INTELLIGENCE</div>',
        unsafe_allow_html=True,
    )
    st.title(section)
    st.caption(PAGE_DESCRIPTIONS[section])

    if section == "Inicio":
        render_home()
    elif section == "Datos y calidad":
        render_uploads()
    elif section == "Análisis exploratorio":
        analysis_view = st.radio(
            "Vista de análisis",
            ["Resumen empresarial", "EDA avanzado"],
            horizontal=True,
            key="analysis_view",
        )
        if analysis_view == "Resumen empresarial":
            render_business_eda()
        else:
            render_advanced_eda()
    elif section == "Demanda":
        render_real_demand()
    elif section == "Inventario y rentabilidad":
        render_inventory_profitability()
    elif section == "Riesgo por lote":
        render_lot_risk()
    elif section == "Escenarios":
        render_scenarios()
    elif section == "Fuentes":
        render_data_sources()
    elif section == "Informe":
        render_report()
    else:
        render_methodology()


if __name__ == "__main__":
    main()
