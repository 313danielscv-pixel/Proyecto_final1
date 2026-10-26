"""Streamlit views for the reusable ResQ Intelligence platform."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from src.database_connector import (
    MAX_IMPORT_ROWS,
    DatabaseConfig,
    DatabaseConnectionError,
    create_database_engine,
    list_tables,
    read_table,
    verify_connection,
)
from src.business_intelligence import (
    average_daily_demand,
    attach_cost_reference,
    compare_scenario,
    inventory_intelligence,
    sales_eda,
    scenario_sensitivity,
)
from src.advanced_eda import (
    bootstrap_mean_interval,
    numeric_summary,
    population_stability_index,
    profile_data,
    quality_summary,
    segment_rows,
    temporal_summary,
)
from src.bayesian_waste_risk import SNAPSHOT_COLUMNS, evaluate_bayesian_waste_risk
from src.contracts import DATASET_CONTRACTS, COSTS_CONTRACT, INVENTORY_CONTRACT, LOTS_CONTRACT, SALES_CONTRACT
from src.demo_data import DEMO_COLUMN_UNITS, DEMO_DIRECTORY
from src.ingestion import parse_frame, parse_free_tabular, parse_tabular
from src.lot_risk import build_lot_risk
from src.real_demand import FORECAST_PATH, METRICS_PATH, SOURCE_URL
from src.resqdata_case import load_resqdata_case
from src.reporting import build_analysis_report


def load_demo_data() -> bool:
    """Load explicitly labelled real sales and synthetic business assumptions."""
    demo_files = {
        "sales": DEMO_DIRECTORY / "ventas_demanda_real_demo.csv",
        "inventory": DEMO_DIRECTORY / "inventario_escenario_demo.csv",
        "costs": DEMO_DIRECTORY / "costes_escenario_demo.csv",
        "lots": DEMO_DIRECTORY / "lotes_escenario_demo.csv",
    }
    if not all(path.exists() for path in demo_files.values()):
        st.error("Faltan los archivos de demostración. Ejecuta `python -m src.demo_data`.")
        return False
    st.session_state["business_data"] = {
        dataset_key: pd.read_csv(path) for dataset_key, path in demo_files.items()
    }
    st.session_state["data_sources"] = {
        **st.session_state.get("data_sources", {}),
        "sales": "Ventas derivadas de datos reales de FreshRetailNet-50K",
        "inventory": "Supuesto sintético de la demostración",
        "costs": "Supuesto sintético de la demostración",
        "lots": "Supuesto sintético de la demostración",
    }
    st.session_state["sales_period_complete"] = True
    st.session_state["sales_period_source_signature"] = "demo"
    for dataset_name, units_by_column in DEMO_COLUMN_UNITS.items():
        for column, unit in units_by_column.items():
            st.session_state[_advanced_eda_unit_widget_key(dataset_name, column)] = unit
    ingestion_reports = dict(st.session_state.get("ingestion_reports", {}))
    for dataset_key in demo_files:
        ingestion_reports.pop(dataset_key, None)
    st.session_state["ingestion_reports"] = ingestion_reports
    st.session_state["demo_loaded"] = True
    return True


def _source_label(dataset_name: str) -> str:
    sources = st.session_state.get("data_sources", {})
    return sources.get(dataset_name, "Origen no registrado; verifica la procedencia.")


def _period_label(data: pd.DataFrame) -> str:
    candidates = [
        column
        for column in data.columns
        if any(token in str(column).lower() for token in ("date", "fecha", "datetime", "timestamp"))
        or str(column).lower() == "dt"
    ]
    for column in candidates:
        dates = pd.to_datetime(data[column], errors="coerce").dropna()
        if not dates.empty:
            return f"{dates.min().date().isoformat()} – {dates.max().date().isoformat()}"
    return "Periodo no disponible"


def _format_eda_number(value: float, decimals: int = 1) -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def _eda_axis_label(column: object, unit: str = "") -> str:
    unit = unit.strip()
    return f"{column} ({unit})" if unit else f"{column} (unidad no especificada)"


def _advanced_eda_unit_widget_key(dataset_name: str, column: object) -> str:
    column_key = hashlib.sha256(str(column).encode("utf-8")).hexdigest()[:12]
    return f"advanced_eda_unit_{dataset_name}_{column_key}"


def _format_eda_date(value: object) -> str:
    return pd.Timestamp(value).strftime("%d/%m/%Y")


def render_home() -> None:
    """Show a data-aware overview without fabricating unavailable indicators."""
    business = _business_data()
    free_data = st.session_state.get("free_eda_data", {})
    all_data = {**business, **free_data}
    st.markdown("## Decisiones más claras, desde tus datos")
    st.write(
        "Carga archivos para explorar demanda, inventario y rentabilidad. "
        "Los indicadores se muestran únicamente cuando existen los campos necesarios."
    )
    if not all_data:
        st.info("Aún no hay datos en esta sesión. Puedes empezar con tus archivos o probar la demostración.")
        if st.button("Cargar demostración", type="primary", key="home_load_demo"):
            if load_demo_data():
                st.success("Demostración cargada. Sus ventas son reales; inventario, costes y lotes son supuestos.")
                st.rerun()

    sales = business.get(SALES_CONTRACT.key)
    inventory = business.get(INVENTORY_CONTRACT.key)
    costs = business.get(COSTS_CONTRACT.key)
    lots = business.get(LOTS_CONTRACT.key)
    metrics = st.columns(4)

    if sales is not None and "quantity" in sales:
        units = pd.to_numeric(sales["quantity"], errors="coerce").sum()
        metrics[0].metric("Unidades", f"{units:,.0f}")
        metrics[0].caption(
            f"{_source_label(SALES_CONTRACT.key)} · {len(sales):,} filas · {_period_label(sales)}"
        )
    else:
        metrics[0].metric("Unidades", "—")
        metrics[0].caption("Carga un archivo de ventas.")

    if sales is not None and "quantity" in sales and "product_id" in sales:
        valued_sales = attach_cost_reference(sales, costs)
        if {"unit_price", "unit_cost"}.issubset(valued_sales.columns):
            valued_sales["quantity"] = pd.to_numeric(valued_sales["quantity"], errors="coerce")
            valued_sales["unit_price"] = pd.to_numeric(valued_sales["unit_price"], errors="coerce")
            valued_sales["unit_cost"] = pd.to_numeric(valued_sales["unit_cost"], errors="coerce")
            valid_margin = valued_sales.dropna(subset=["quantity", "unit_price", "unit_cost"])
            if not valid_margin.empty:
                margin = (valid_margin["quantity"] * (valid_margin["unit_price"] - valid_margin["unit_cost"])).sum()
                metrics[1].metric("Margen estimado", f"{margin:,.2f} €")
                margin_note = (
                    "El precio y el coste unitarios son supuestos sintéticos de la demo."
                    if st.session_state.get("demo_loaded")
                    else "Resultado estimado a partir de los precios y costes cargados."
                )
                metrics[1].caption(f"{len(valid_margin):,} filas con precio y coste. {margin_note}")
            else:
                metrics[1].metric("Margen estimado", "—")
                metrics[1].caption("Faltan precios o costes válidos.")
        else:
            metrics[1].metric("Margen estimado", "—")
            metrics[1].caption("Requiere precio y coste unitario.")
    else:
        metrics[1].metric("Margen estimado", "—")
        metrics[1].caption("Carga ventas con producto, precio y coste.")

    if inventory is not None and "on_hand_units" in inventory:
        valued_inventory = attach_cost_reference(inventory, costs)
        if "unit_cost" in valued_inventory:
            capital = (
                pd.to_numeric(valued_inventory["on_hand_units"], errors="coerce")
                * pd.to_numeric(valued_inventory["unit_cost"], errors="coerce")
            ).sum()
            metrics[2].metric("Capital stock", f"{capital:,.2f} €")
            capital_note = (
                "El coste unitario es un supuesto sintético de la demo."
                if st.session_state.get("demo_loaded")
                else "Estimación basada en stock y coste unitario cargado."
            )
            metrics[2].caption(capital_note)
        else:
            metrics[2].metric("Capital stock", "—")
            metrics[2].caption("Carga costes unitarios para calcularlo.")
    else:
        metrics[2].metric("Capital stock", "—")
        metrics[2].caption("Carga un inventario para activarlo.")

    required_lot_columns = {"lot_id", "product_id", "stock_available", "expiry_date", "unit_cost"}
    if (
        sales is not None
        and lots is not None
        and required_lot_columns.issubset(lots.columns)
        and {"date", "product_id", "quantity"}.issubset(sales.columns)
    ):
        risk, warnings = build_lot_risk(
            lots,
            sales,
            assume_complete_period=_sales_period_complete(),
        )
        if not risk.empty and "estimated_unsold_stock_ratio" in risk:
            valid_risk = risk.dropna(subset=["estimated_unsold_stock_ratio"])
            priority_count = int(valid_risk["risk_level"].isin(["Alto", "Crítico"]).sum())
            metrics[3].metric("Alertas lote", f"{priority_count:,}")
            metrics[3].caption(f"De {len(valid_risk):,} lotes con historial suficiente.")
        else:
            metrics[3].metric("Alertas lote", "—")
            metrics[3].caption(
                warnings[0] if warnings else "No hay historial suficiente para estimar el riesgo."
            )
    else:
        metrics[3].metric("Alertas lote", "—")
        metrics[3].caption("Carga ventas y datos de lotes para activarlo.")

    if all_data:
        st.markdown("### Datos disponibles en esta sesión")
        rows = [
            {
                "Conjunto": name,
                "Filas": len(data),
                "Columnas": len(data.columns),
                "Procedencia": _source_label(name),
            }
            for name, data in sorted(all_data.items())
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("Los archivos permanecen en la sesión de Streamlit; no se guardan automáticamente en el repositorio.")
    st.markdown("### Siguiente paso")
    step_columns = st.columns(3)
    next_steps = [
        ("1. Cargar y validar", "Abre Datos y calidad para ver campos y advertencias."),
        ("2. Explorar", "Revisa tendencias y calidad en Análisis exploratorio."),
        ("3. Comparar", "Prueba supuestos en Escenarios y consulta el Informe."),
    ]
    for column, (title, description) in zip(step_columns, next_steps):
        with column:
            st.markdown(f"#### {title}")
            st.caption(description)


def render_resqdata_case() -> None:
    """Show the synthetic FreshMarket case from the original ResQ Data project."""
    case = load_resqdata_case()
    summary = case["summary"].iloc[0]
    categories = case["categories"]
    stores = case["stores"]

    st.subheader("Caso FreshMarket de ResQ Data")
    st.warning(
        "Esta base es sintética y se creó para el prototipo: no contiene datos reales de FreshMarket. "
        "Esta vista es descriptiva; no ejecuta un modelo predictivo validado ni aplica cambios al TPV."
    )

    first, second, third, fourth = st.columns(4)
    first.metric("Tiendas del escenario", f"{int(summary['tiendas']):,}")
    second.metric("Lotes", f"{int(summary['lotes']):,}")
    third.metric("Registros de venta", f"{int(summary['registros_venta']):,}")
    fourth.metric("Coste de merma simulado", f"{summary['coste_merma_eur']:,.2f} €")

    first, second, third, fourth = st.columns(4)
    first.metric("Registros de merma", f"{int(summary['registros_merma']):,}")
    second.metric("Unidades mermadas", f"{summary['unidades_mermadas']:,.0f}")
    third.metric("Unidades donadas", f"{summary['unidades_donadas']:,.0f}")
    fourth.metric("Días con ventas", f"{int(summary['dias_venta']):,}")

    categories_column, stores_column = st.columns(2)
    with categories_column:
        st.plotly_chart(
            px.bar(
                categories,
                x="coste_merma_eur",
                y="categoria",
                orientation="h",
                text_auto=".0f",
                title="Coste de merma por categoría (escenario)",
                labels={
                    "coste_merma_eur": "Coste simulado (€)",
                    "categoria": "Categoría",
                },
            ),
            use_container_width=True,
        )
    with stores_column:
        st.plotly_chart(
            px.bar(
                stores,
                x="coste_merma_eur",
                y="tienda",
                orientation="h",
                text_auto=".0f",
                title="Coste de merma por tienda (escenario)",
                labels={
                    "coste_merma_eur": "Coste simulado (€)",
                    "tienda": "Tienda ficticia",
                },
            ),
            use_container_width=True,
        )

    category_share = categories.set_index("categoria")["porcentaje_coste"]
    prepared_share = float(category_share.get("Platos Preparados", 0))
    fish_share = float(category_share.get("Pescadería", 0))
    st.info(
        f"En este caso sintético, Platos Preparados concentra el {prepared_share:.1f}% "
        f"y Pescadería el {fish_share:.1f}% del coste de merma "
        f"({prepared_share + fish_share:.1f}% entre ambas)."
    )
    st.markdown("#### Productos con mayor coste de merma")
    st.dataframe(
        case["top_products"].rename(
            columns={
                "producto": "Producto",
                "categoria": "Categoría",
                "unidades_mermadas": "Unidades mermadas",
                "coste_merma_eur": "Coste simulado (€)",
            }
        ).style.format(
            {"Unidades mermadas": "{:,.0f}", "Coste simulado (€)": "{:,.2f}"}
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        f"La base también contiene {int(summary['registros_donacion']):,} registros de donación "
        f"({summary['valor_donacion_eur']:,.2f} € de valor simulado). "
        "Las cifras no validan ahorros, impacto ambiental ni la eficacia de descuentos."
    )


def render_report() -> None:
    """Offer a provenance-aware report without exporting raw records."""
    st.subheader("Informe de análisis")
    business_data = _business_data()
    free_data = st.session_state.get("free_eda_data", {})
    if not business_data and not free_data:
        st.info("Carga datos para generar un informe verificable.")
        return
    report = build_analysis_report(
        business_data,
        free_data,
        {name: _source_label(name) for name in {**business_data, **free_data}},
        st.session_state.get("scenario_report"),
        st.session_state.get("ingestion_reports", {}),
        sales_period_complete=_sales_period_complete(),
    )
    st.write("Resumen de calidad, resultados disponibles, procedencia, supuestos y límites. No incluye filas originales.")
    st.download_button(
        "Descargar informe Markdown",
        data=report.encode("utf-8"),
        file_name="informe_resq_intelligence.md",
        mime="text/markdown",
        type="primary",
    )
    st.caption("El informe se genera en memoria para esta descarga; los archivos originales no se guardan.")


def render_uploads() -> None:
    """Choose between file uploads and a read-only database source."""
    source_mode = st.radio(
        "Origen de datos",
        ["Archivos CSV/Excel", "Base de datos"],
        horizontal=True,
        key="upload_source_mode",
    )
    if source_mode == "Base de datos":
        _render_database_import()
    else:
        _render_file_uploads()
    _render_sales_period_confirmation()


def _render_file_uploads() -> None:
    """Let an organisation upload independent CSVs and inspect their quality."""
    st.subheader("Carga y calidad de datos")
    st.write("Carga solo los archivos que tengas. Cada módulo se habilita cuando existen los campos necesarios.")
    if st.session_state.get("demo_loaded"):
        st.info(
            "Demostración activa: ventas reales de FreshRetailNet-50K. Inventario, costes y lote son "
            "supuestos de escenario claramente identificados, no datos observados de la fuente."
        )
    free_upload = st.file_uploader(
        "Dataset libre para EDA: CSV o Excel",
        type=["csv", "xlsx"],
        help="Conserva todas las columnas originales. No activa módulos de negocio hasta que cargues su archivo contratado.",
        key="upload_free_eda",
    )
    if free_upload is not None:
        try:
            st.session_state["free_eda_data"] = {
                "EDA libre": parse_free_tabular(free_upload.getvalue(), free_upload.name)
            }
            sources = dict(st.session_state.get("data_sources", {}))
            sources["EDA libre"] = f"Dataset libre cargado por el usuario: {free_upload.name}"
            st.session_state["data_sources"] = sources
            st.success("Dataset libre cargado para el EDA avanzado; sus columnas originales se han conservado.")
        except (UnicodeDecodeError, ValueError, pd.errors.ParserError) as error:
            st.error(f"No se pudo leer el dataset libre: {error}")
    loaded: dict[str, pd.DataFrame] = dict(_business_data())
    for contract in DATASET_CONTRACTS:
        upload = st.file_uploader(
            f"{contract.title}: {contract.filename}",
            type=["csv", "xlsx"],
            help=contract.purpose,
            key=f"upload_{contract.key}",
        )
        if upload is None:
            continue
        try:
            uploaded_bytes = upload.getvalue()
            data, report = parse_tabular(uploaded_bytes, upload.name, contract)
        except (UnicodeDecodeError, ValueError, pd.errors.ParserError) as error:
            st.error(f"No se pudo leer {contract.filename}: {error}")
            continue
        loaded[contract.key] = data
        st.session_state["demo_loaded"] = False
        if contract.key == SALES_CONTRACT.key:
            source_signature = hashlib.sha256(uploaded_bytes).hexdigest()
            if source_signature != st.session_state.get("sales_period_source_signature"):
                st.session_state["sales_period_complete"] = False
            st.session_state["sales_period_source_signature"] = source_signature
        sources = dict(st.session_state.get("data_sources", {}))
        sources[contract.key] = f"Archivo cargado por el usuario: {upload.name}"
        st.session_state["data_sources"] = sources
        ingestion_reports = dict(st.session_state.get("ingestion_reports", {}))
        ingestion_reports[contract.key] = {
            "valid_rows": report.valid_rows,
            "total_rows": report.total_rows,
            "missing_required": report.missing_required,
            "invalid_values": report.invalid_values,
            "duplicate_rows": report.duplicate_rows,
            "mapped_columns": report.mapped_columns,
        }
        st.session_state["ingestion_reports"] = ingestion_reports
        if report.missing_required:
            st.error(f"{contract.title}: faltan campos obligatorios: {', '.join(report.missing_required)}.")
        else:
            st.success(f"{contract.title}: {report.valid_rows}/{report.total_rows} filas aptas para su módulo principal.")
        if report.invalid_values:
            st.warning(f"Valores no válidos o negativos: {report.invalid_values}.")
        if report.duplicate_rows:
            st.warning(f"Filas duplicadas detectadas: {report.duplicate_rows}. No se han eliminado automáticamente.")
        st.caption(f"Mapeo detectado: {report.mapped_columns}")
        st.dataframe(data.head(20), use_container_width=True, hide_index=True)
    if loaded:
        st.session_state["business_data"] = loaded
        st.info("Los datos cargados permanecen solo en esta sesión del navegador; no se guardan en el repositorio.")


def _connect_and_list_tables(config: DatabaseConfig) -> list[str]:
    engine = create_database_engine(config)
    try:
        verify_connection(engine)
        return list_tables(engine)
    finally:
        engine.dispose()


def _read_database_table(config: DatabaseConfig, table_name: str, limit: int) -> pd.DataFrame:
    engine = create_database_engine(config)
    try:
        return read_table(engine, table_name, limit)
    finally:
        engine.dispose()


def _render_database_import() -> None:
    """Connect to a trusted database and refresh one bounded table into this session."""
    st.subheader("Conectar una base de datos")
    st.write(
        "La app solo ejecuta consultas de lectura. Usa una cuenta de base de datos con permiso "
        "SELECT únicamente; los cambios se reflejan al pulsar «Actualizar datos»."
    )
    st.caption(
        "La conexión se realiza desde el equipo que ejecuta Streamlit. Las credenciales viven "
        "solo en esta sesión y no se guardan en archivos."
    )

    config = st.session_state.get("database_config")
    if not isinstance(config, DatabaseConfig):
        with st.form("database_connection_form"):
            dialect_options = {
                "MySQL": ("mysql", 3306),
                "PostgreSQL": ("postgresql", 5432),
                "SQL Server": ("mssql", 1433),
            }
            dialect_label = st.selectbox(
                "Motor", list(dialect_options), key="database_dialect"
            )
            dialect, default_port = dialect_options[dialect_label]
            host = st.text_input("Host", value="localhost", key="database_host")
            port = st.number_input(
                "Puerto",
                min_value=1,
                max_value=65_535,
                value=default_port,
                step=1,
                key=f"database_port_{dialect}",
            )
            database = st.text_input("Base de datos", key="database_name")
            use_windows_auth = False
            trust_server_certificate = False
            if dialect == "mssql":
                authentication_label = st.radio(
                    "Autenticación",
                    ["Windows", "SQL Server"],
                    horizontal=True,
                    key="database_auth_mode",
                )
                use_windows_auth = authentication_label == "Windows"
                st.caption(
                    "Con Windows se usará la cuenta que ejecuta ResQ; debe tener solo permiso "
                    "SELECT en la base de datos. "
                    "Configura SQL Server para aceptar conexiones TCP en el puerto indicado."
                )
                if not use_windows_auth:
                    st.caption("Utiliza una cuenta de SQL Server con permiso SELECT únicamente.")
                trust_server_certificate = st.checkbox(
                    "Confiar en el certificado del servidor",
                    help=(
                        "Actívalo solo para una conexión local de prueba con un certificado "
                        "autofirmado. En conexiones remotas, usa un certificado válido."
                    ),
                    key="database_trust_server_certificate",
                )
            if dialect != "mssql" or not use_windows_auth:
                username = st.text_input("Usuario de solo lectura", key="database_username")
                password = st.text_input("Contraseña", type="password", key="database_password")
            else:
                username = ""
                password = ""
            connect_clicked = st.form_submit_button("Probar conexión y listar tablas", type="primary")

        if connect_clicked:
            config = DatabaseConfig(
                dialect=dialect,
                host=host,
                port=int(port),
                database=database,
                username=username,
                password=password,
                trust_server_certificate=trust_server_certificate,
                use_windows_auth=use_windows_auth,
            )
            try:
                tables = _connect_and_list_tables(config)
            except DatabaseConnectionError as error:
                st.error(str(error))
            else:
                st.session_state["database_config"] = config
                st.session_state["database_tables"] = tables
                if tables:
                    st.success(f"Conexión verificada: {len(tables)} tablas o vistas disponibles.")
                else:
                    st.warning("Conexión verificada, pero no hay tablas o vistas visibles.")

    config = st.session_state.get("database_config")
    if not isinstance(config, DatabaseConfig):
        return
    tables = st.session_state.get("database_tables", [])

    if st.button("Desconectar", key="disconnect_database"):
        for key in (
            "database_config",
            "database_tables",
            "database_selected_table",
            "database_dialect",
            "database_host",
            "database_name",
            "database_username",
            "database_password",
            "database_port_mysql",
            "database_port_postgresql",
            "database_port_mssql",
            "database_trust_server_certificate",
            "database_auth_mode",
        ):
            st.session_state.pop(key, None)
        st.rerun()

    if not tables:
        return

    st.success(f"Fuente conectada: {config.dialect} · {config.database} · {config.host}:{config.port}")
    st.caption(
        "Por defecto solo se permiten hosts locales. Para autorizar otro host de confianza, "
        "configura RESQ_DB_ALLOWED_HOSTS en el equipo que ejecuta Streamlit."
    )

    contract_by_key = {contract.key: contract for contract in DATASET_CONTRACTS}
    contract_labels = {"free": "EDA libre"}
    contract_labels.update({key: contract.title for key, contract in contract_by_key.items()})
    dataset_key = st.selectbox(
        "Tipo de datos que quieres cargar",
        options=list(contract_labels),
        format_func=contract_labels.__getitem__,
        key="database_dataset_key",
    )
    table_name = st.selectbox("Tabla o vista", options=tables, key="database_selected_table")
    row_limit = int(
        st.number_input(
            "Máximo de filas",
            min_value=1,
            max_value=MAX_IMPORT_ROWS,
            value=10_000,
            step=1_000,
        )
    )
    st.caption(
        f"Se admiten hasta {MAX_IMPORT_ROWS:,} filas por actualización para proteger la memoria. "
        "Para tablas mayores, prepara una vista agregada en la base de datos."
    )

    preview_column, refresh_column = st.columns(2)
    with preview_column:
        preview_clicked = st.button("Vista previa", key="preview_database_table")
    with refresh_column:
        refresh_clicked = st.button("Actualizar datos", type="primary", key="refresh_database_table")

    if preview_clicked:
        try:
            preview = _read_database_table(config, table_name, min(100, row_limit))
        except DatabaseConnectionError as error:
            st.error(str(error))
        else:
            st.dataframe(preview, use_container_width=True, hide_index=True)

    if not refresh_clicked:
        return

    try:
        raw_data = _read_database_table(config, table_name, row_limit)
    except DatabaseConnectionError as error:
        st.error(str(error))
        return

    refreshed_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    source_label = (
        f"{config.dialect} · {config.database}.{table_name} · actualizada {refreshed_at}"
    )
    if dataset_key == "free":
        free_data = dict(st.session_state.get("free_eda_data", {}))
        free_data["EDA libre"] = raw_data
        st.session_state["free_eda_data"] = free_data
        source_key = "EDA libre"
        st.success(f"Datos actualizados: {len(raw_data):,} filas.")
    else:
        contract = contract_by_key[dataset_key]
        normalized, report = parse_frame(raw_data, contract)
        business_data = dict(st.session_state.get("business_data", {}))
        business_data[dataset_key] = normalized
        st.session_state["business_data"] = business_data
        st.session_state["demo_loaded"] = False
        if dataset_key == SALES_CONTRACT.key:
            st.session_state["sales_period_complete"] = False
            st.session_state.pop("sales_period_source_signature", None)
        ingestion_reports = dict(st.session_state.get("ingestion_reports", {}))
        ingestion_reports[dataset_key] = {
            "valid_rows": report.valid_rows,
            "total_rows": report.total_rows,
            "missing_required": report.missing_required,
            "invalid_values": report.invalid_values,
            "duplicate_rows": report.duplicate_rows,
            "mapped_columns": report.mapped_columns,
        }
        st.session_state["ingestion_reports"] = ingestion_reports
        source_key = dataset_key
        if report.missing_required:
            st.error(f"Faltan campos obligatorios: {', '.join(report.missing_required)}.")
        else:
            st.success(f"Datos actualizados: {report.valid_rows:,}/{report.total_rows:,} filas aptas.")
        if report.invalid_values:
            st.warning(f"Valores no válidos: {report.invalid_values}.")
        if report.duplicate_rows:
            st.warning(f"Se detectaron {report.duplicate_rows} filas duplicadas; no se eliminaron.")
        st.caption(f"Mapeo detectado: {report.mapped_columns}")

    sources = dict(st.session_state.get("data_sources", {}))
    sources[source_key] = source_label
    st.session_state["data_sources"] = sources
    st.dataframe(
        st.session_state["free_eda_data"]["EDA libre"]
        if dataset_key == "free"
        else st.session_state["business_data"][dataset_key],
        use_container_width=True,
        hide_index=True,
    )


def _business_data() -> dict[str, pd.DataFrame]:
    return st.session_state.get("business_data", {})


def _sales_period_complete() -> bool:
    return bool(
        st.session_state.get(
            "sales_period_complete",
            st.session_state.get("demo_loaded", False),
        )
    )


def _render_sales_period_confirmation() -> bool:
    """Ask whether absent transaction dates mean zero sales for the full period."""
    if SALES_CONTRACT.key not in _business_data():
        return False
    if "sales_period_complete" not in st.session_state:
        st.session_state["sales_period_complete"] = bool(st.session_state.get("demo_loaded", False))
    return st.checkbox(
        "Confirmo que el extracto de ventas incluye todos los días del periodo",
        key="sales_period_complete",
        help=(
            "Actívalo solo si el archivo o la vista incluye todo el periodo, también los días "
            "sin ventas. Al confirmarlo, esos días cuentan como cero en la demanda media y el riesgo por lote."
        ),
    )


def _eda_data() -> dict[str, pd.DataFrame]:
    """Expose free EDA uploads alongside normalized business datasets."""
    return {**_business_data(), **st.session_state.get("free_eda_data", {})}


def render_business_eda() -> None:
    """Render a business-focused EDA dashboard with explicit data limitations."""
    st.subheader("Análisis exploratorio empresarial")
    sales = _business_data().get(SALES_CONTRACT.key)
    if sales is None or not {"date", "product_id", "quantity"}.issubset(sales.columns):
        st.info("Carga un archivo de ventas válido en **Datos y calidad** para activar este análisis.")
        return

    base_results = sales_eda(sales)
    base_quality = base_results["quality"]
    base_daily = base_results["daily_demand"]
    base_products = base_results["products"]
    assert isinstance(base_quality, dict)
    assert isinstance(base_daily, pd.DataFrame)
    assert isinstance(base_products, pd.DataFrame)

    st.caption(
        f"Fuente: {_source_label(SALES_CONTRACT.key)} · {len(sales):,} filas · "
        f"{_period_label(sales)} · las métricas superiores describen el conjunto completo."
    )

    valid_dates = pd.to_datetime(sales["date"], errors="coerce").dropna().dt.normalize()
    products = sales["product_id"].astype("string").str.strip()
    product_options = sorted(products.dropna().loc[products.dropna().ne("")].unique().tolist())
    filters = st.columns([2, 3])
    if valid_dates.empty:
        selected_start = selected_end = None
        selected_products: list[str] = []
        filters[0].info("No hay fechas válidas para filtrar el periodo.")
    else:
        minimum_date = valid_dates.min().date()
        maximum_date = valid_dates.max().date()
        period_key = f"business_eda_period_{minimum_date}_{maximum_date}"
        selected_period = filters[0].date_input(
            "Periodo de análisis",
            value=(minimum_date, maximum_date),
            min_value=minimum_date,
            max_value=maximum_date,
            key=period_key,
        )
        if isinstance(selected_period, (tuple, list)):
            selected_start = (
                selected_period[0]
                if selected_period and selected_period[0] is not None
                else minimum_date
            )
            selected_end = (
                selected_period[1]
                if len(selected_period) > 1 and selected_period[1] is not None
                else maximum_date
            )
        else:
            selected_start = selected_end = selected_period
        product_key = f"business_eda_products_{hash(tuple(product_options))}"
        selected_products = filters[1].multiselect(
            "Productos",
            product_options,
            key=product_key,
            placeholder="Todos los productos",
            help="Deja la selección vacía para incluir todos los productos.",
        )

    date_values = pd.to_datetime(sales["date"], errors="coerce").dt.normalize()
    if selected_start is None or selected_end is None:
        date_mask = pd.Series(False, index=sales.index)
    else:
        date_mask = date_values.between(pd.Timestamp(selected_start), pd.Timestamp(selected_end))
    product_values = sales["product_id"].astype("string").str.strip()
    product_mask = (
        product_values.isin(selected_products)
        if selected_products
        else pd.Series(True, index=sales.index)
    )
    results = sales_eda(sales.loc[date_mask & product_mask])
    daily = results["daily_demand"]
    product_summary = results["products"]
    weekday_summary = results["weekday_demand"]
    weekly_summary = results["weekly_demand"]
    assert isinstance(daily, pd.DataFrame)
    assert isinstance(product_summary, pd.DataFrame)
    assert isinstance(weekday_summary, pd.DataFrame)
    assert isinstance(weekly_summary, pd.DataFrame)

    total_units = base_daily["quantity"].sum()
    valid_row_count = int(base_quality["valid_rows"])
    total_row_count = int(base_quality["total_rows"])
    coverage = float(base_quality["coverage_pct"])
    observed_day_count = int(base_quality["observed_days"])
    calendar_day_count = int(base_quality["calendar_days"])
    kpis = st.columns(4)
    kpis[0].metric(
        "Unidades",
        f"{total_units:,.0f}" if valid_row_count else "—",
        help="Suma de cantidades válidas del archivo completo; no es una previsión.",
    )
    kpis[1].metric(
        "Fechas",
        f"{observed_day_count:,} / {calendar_day_count:,}",
        help="Fechas con filas válidas frente a días del rango entre la primera y la última fecha observada.",
    )
    kpis[2].metric("Productos", f"{len(base_products):,}")
    kpis[3].metric(
        "Filas aptas",
        f"{valid_row_count:,} / {total_row_count:,}",
        help="Requiere fecha válida, producto informado y cantidad numérica no negativa.",
    )
    st.caption(
        f"Cobertura de fechas: {coverage:.1f}% dentro del rango observado. "
        "Los días sin fila se mantienen como desconocidos, no como cero ventas."
    )
    st.caption(
        f"Vista filtrada: {len(daily.loc[daily['has_observation']]) if 'has_observation' in daily else 0:,} "
        "fechas con ventas registradas. Las cantidades negativas y los campos esenciales inválidos "
        "se reportan en Calidad y no se incluyen en la demanda."
    )

    summary_tab, products_tab, distribution_tab, temporal_tab, quality_tab, findings_tab = st.tabs(
        ["Resumen", "Productos", "Distribución", "Temporal", "Calidad", "Hallazgos"]
    )
    with summary_tab:
        st.markdown("#### Evolución de la demanda")
        if daily.empty:
            st.info("No hay filas válidas para los filtros seleccionados.")
        else:
            chart_data = daily.rename(
                columns={
                    "quantity": "Unidades registradas",
                    "average_7d": "Media móvil 7 días",
                    "average_30d": "Media móvil 30 días",
                }
            )
            figure = px.line(
                chart_data,
                x="date",
                y=["Unidades registradas", "Media móvil 7 días", "Media móvil 30 días"],
                title="Unidades registradas y medias móviles",
                labels={
                    "date": "Fecha",
                    "value": "Unidades",
                    "variable": "Serie",
                },
            )
            figure.update_traces(connectgaps=False)
            figure.update_xaxes(tickformat="%d/%m")
            st.plotly_chart(figure, use_container_width=True, theme="streamlit")
            observed_daily = daily.loc[daily["has_observation"]]
            peak_day = observed_daily.loc[observed_daily["quantity"].idxmax()]
            lowest_day = observed_daily.loc[observed_daily["quantity"].idxmin()]
            latest_day = observed_daily.iloc[-1]
            mean_units = observed_daily["quantity"].mean()
            mean_7d = float(latest_day["average_7d"])
            mean_30d = float(latest_day["average_30d"])
            if mean_7d > mean_30d:
                moving_average_reading = (
                    f"La media de 7 días está {_format_eda_number(mean_7d - mean_30d)} unidades por encima "
                    "de la de 30, señal de un ritmo reciente superior al promedio más amplio."
                )
            elif mean_7d < mean_30d:
                moving_average_reading = (
                    f"La media de 7 días está {_format_eda_number(mean_30d - mean_7d)} unidades por debajo "
                    "de la de 30, señal de un ritmo reciente inferior al promedio más amplio."
                )
            else:
                moving_average_reading = "Las dos medias coinciden, por lo que el ritmo reciente es similar al promedio amplio."
            st.caption(
                f"En {len(observed_daily)} fechas con registro, la media fue "
                f"{_format_eda_number(mean_units)} unidades. El máximo fue "
                f"{_format_eda_number(float(peak_day['quantity']))} el {_format_eda_date(peak_day['date'])} "
                f"y el mínimo {_format_eda_number(float(lowest_day['quantity']))} el "
                f"{_format_eda_date(lowest_day['date'])}. En la última fecha observada "
                f"({_format_eda_date(latest_day['date'])}), las medias móviles son "
                f"{_format_eda_number(mean_7d)} unidades (7 días) y "
                f"{_format_eda_number(mean_30d)} (30 días). {moving_average_reading} "
                "Las fechas sin fila no se interpretan como ventas cero."
            )

    with products_tab:
        st.markdown("#### Rendimiento por producto")
        if product_summary.empty:
            st.info("No hay productos válidos en el periodo y filtros elegidos.")
        else:
            if len(product_summary) == 1:
                st.info("Solo aparece un producto en esta selección: no es posible compararlo con otros.")
            product_chart = px.bar(
                product_summary.head(15).sort_values("quantity"),
                x="quantity",
                y="product_id",
                orientation="h",
                title="Productos con más unidades registradas",
                labels={"quantity": "Unidades", "product_id": "Producto"},
                color="quantity",
                color_continuous_scale=["#183047", "#2CC9A7"],
            )
            st.plotly_chart(product_chart, use_container_width=True, theme="streamlit")
            leading_product = product_summary.iloc[0]
            lowest_shown_product = product_summary.head(15).iloc[-1]
            if len(product_summary) == 1:
                product_reading = (
                    f"Solo aparece {leading_product['product_id']}, con "
                    f"{_format_eda_number(float(leading_product['quantity']))} unidades; "
                    "no hay otros productos para comparar."
                )
            else:
                share = leading_product["share_pct"]
                share_text = (
                    f" ({_format_eda_number(float(share))}% del total)"
                    if pd.notna(share)
                    else ""
                )
                product_reading = (
                    f"{leading_product['product_id']} lidera con "
                    f"{_format_eda_number(float(leading_product['quantity']))} unidades{share_text}. "
                    f"Entre los productos mostrados, {lowest_shown_product['product_id']} registra "
                    f"menos unidades ({_format_eda_number(float(lowest_shown_product['quantity']))})."
                )
            st.caption(
                f"En el periodo y filtros elegidos, {product_reading} El gráfico ordena por unidades, "
                "no por facturación ni beneficio."
            )
            display_products = product_summary.rename(
                columns={
                    "product_id": "Producto",
                    "quantity": "Unidades",
                    "share_pct": "Participación (%)",
                    "sale_days": "Días con registro",
                    "records": "Registros",
                }
            ).copy()
            display_products["Participación (%)"] = display_products["Participación (%)"].round(1)
            st.dataframe(display_products, use_container_width=True, hide_index=True)
        if "revenue_by_product" in results:
            revenue = results["revenue_by_product"]
            assert isinstance(revenue, pd.DataFrame)
            st.markdown("#### Facturación calculada")
            st.dataframe(
                revenue.rename(columns={"product_id": "Producto", "revenue": "Facturación (€)"}),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                "Facturación = precio unitario observado × unidades válidas. "
                "No equivale a margen ni a beneficio."
            )

    with distribution_tab:
        st.markdown("#### Distribución de las ventas diarias")
        observed_daily = daily.loc[daily["has_observation"], ["date", "quantity"]]
        if observed_daily.empty:
            st.info("No hay fechas observadas para calcular estadísticas.")
        else:
            statistics = numeric_summary(observed_daily, "quantity")
            st.dataframe(
                statistics.rename(
                    columns={
                        "media": "Media",
                        "mediana": "Mediana",
                        "desviacion_estandar": "Desviación estándar",
                        "minimo": "Mínimo",
                        "percentil_25": "Percentil 25",
                        "percentil_75": "Percentil 75",
                        "maximo": "Máximo",
                        "asimetria": "Asimetría",
                        "atipicos_iqr": "Candidatos IQR",
                        "muestra": "Fechas observadas",
                    }
                ).round(2),
                use_container_width=True,
                hide_index=True,
            )
            candidate_count = int(daily["outlier_iqr"].sum())
            daily_mean = float(observed_daily["quantity"].mean())
            daily_median = float(observed_daily["quantity"].median())
            daily_max = observed_daily.loc[observed_daily["quantity"].idxmax()]
            daily_min = observed_daily.loc[observed_daily["quantity"].idxmin()]
            mean_median_reading = (
                "La media por encima de la mediana sugiere que algunas fechas altas elevan el promedio."
                if daily_mean > daily_median
                else "La media por debajo de la mediana sugiere que algunas fechas bajas reducen el promedio."
                if daily_mean < daily_median
                else "Media y mediana coinciden en esta selección."
            )
            chart_columns = st.columns(2)
            distribution_figure = px.histogram(
                observed_daily,
                x="quantity",
                nbins=20,
                title="Frecuencia de unidades por fecha observada",
                labels={"quantity": "Unidades por fecha"},
            )
            distribution_figure.update_yaxes(title_text="Número de fechas")
            chart_columns[0].plotly_chart(
                distribution_figure,
                use_container_width=True,
                theme="streamlit",
            )
            chart_columns[0].caption(
                f"En {len(observed_daily)} fechas, la media fue {_format_eda_number(daily_mean)} y la mediana "
                f"{_format_eda_number(daily_median)} unidades. El máximo fue "
                f"{_format_eda_number(float(daily_max['quantity']))} el {_format_eda_date(daily_max['date'])}; "
                f"el mínimo, {_format_eda_number(float(daily_min['quantity']))} el "
                f"{_format_eda_date(daily_min['date'])}. {mean_median_reading}"
            )
            chart_columns[1].plotly_chart(
                px.box(
                    observed_daily,
                    y="quantity",
                    points="outliers",
                    title="Variabilidad y valores extremos",
                    labels={"quantity": "Unidades por fecha"},
                ),
                use_container_width=True,
                theme="streamlit",
            )
            q1, q3 = observed_daily["quantity"].quantile([0.25, 0.75])
            box_outlier_reading = (
                f"La mitad central de las fechas quedó entre {_format_eda_number(float(q1))} y "
                f"{_format_eda_number(float(q3))} unidades; la mediana fue "
                f"{_format_eda_number(daily_median)}. La regla IQR señaló {candidate_count} "
                "candidato(s), que requieren revisión y no son errores confirmados."
                if len(observed_daily) >= 14
                else f"La mitad central de las fechas quedó entre {_format_eda_number(float(q1))} y "
                f"{_format_eda_number(float(q3))} unidades; la muestra es corta para evaluar candidatos IQR."
            )
            chart_columns[1].caption(
                box_outlier_reading
            )
            if len(observed_daily) < 14:
                st.info("Muestra corta: se necesitan al menos 14 fechas para señalar candidatos IQR.")
            elif candidate_count:
                st.warning(
                    f"{candidate_count} fecha(s) candidatas a revisión por la regla IQR. "
                    "Un valor extremo no confirma un error."
                )
                st.dataframe(
                    daily.loc[daily["outlier_iqr"], ["date", "quantity"]].rename(
                        columns={"date": "Fecha", "quantity": "Unidades"}
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.success("No se detectaron candidatos IQR en las fechas observadas.")
    with temporal_tab:
        st.markdown("#### Patrones temporales observados")
        temporal_charts = st.columns(2)
        if not weekly_summary.empty:
            temporal_charts[0].plotly_chart(
                px.bar(
                    weekly_summary,
                    x="week_start",
                    y="quantity",
                    hover_data=["observed_days", "max_daily_units"],
                    title="Unidades por semana (solo días observados)",
                    labels={
                        "week_start": "Inicio de semana",
                        "quantity": "Unidades",
                        "observed_days": "Días con registro",
                        "max_daily_units": "Máximo diario",
                    },
                ),
                use_container_width=True,
                theme="streamlit",
            )
            peak_week = weekly_summary.loc[weekly_summary["quantity"].idxmax()]
            lowest_week = weekly_summary.loc[weekly_summary["quantity"].idxmin()]
            temporal_charts[0].caption(
                f"La semana del {_format_eda_date(peak_week['week_start'])} tuvo más unidades: "
                f"{_format_eda_number(float(peak_week['quantity']))} en {int(peak_week['observed_days'])} "
                f"días observados. La menor fue la del {_format_eda_date(lowest_week['week_start'])}, "
                f"con {_format_eda_number(float(lowest_week['quantity']))}. Compara también los días "
                "observados: las semanas pueden tener cobertura distinta."
            )
        if not weekday_summary.empty:
            temporal_charts[1].plotly_chart(
                px.bar(
                    weekday_summary,
                    x="weekday",
                    y="average_per_observed_day",
                    hover_data=["observed_days", "quantity"],
                    title="Media por día de la semana observado",
                    labels={
                        "weekday": "Día",
                        "average_per_observed_day": "Media de unidades",
                        "observed_days": "Fechas observadas",
                        "quantity": "Unidades acumuladas",
                    },
                ),
                use_container_width=True,
                theme="streamlit",
            )
            busiest_weekday = weekday_summary.loc[
                weekday_summary["average_per_observed_day"].idxmax()
            ]
            quietest_weekday = weekday_summary.loc[
                weekday_summary["average_per_observed_day"].idxmin()
            ]
            temporal_charts[1].caption(
                f"{busiest_weekday['weekday']} muestra la mayor media "
                f"({_format_eda_number(float(busiest_weekday['average_per_observed_day']))} unidades por "
                f"fecha observada); {quietest_weekday['weekday']} la menor "
                f"({_format_eda_number(float(quietest_weekday['average_per_observed_day']))}). "
                "Es una diferencia observada en este periodo, no prueba que se repita siempre."
            )
        if weekly_summary.empty and weekday_summary.empty:
            st.info("No hay fechas válidas para comparar semanas o días de la semana.")
    with quality_tab:
        st.markdown("#### Calidad y cobertura del archivo completo")
        quality_columns = st.columns(4)
        quality_columns[0].metric("Fechas inválidas", f"{int(base_quality['invalid_dates']):,}")
        quality_columns[1].metric("Productos vacíos", f"{int(base_quality['missing_products']):,}")
        quality_columns[2].metric("Cantidades inválidas", f"{int(base_quality['invalid_quantities']):,}")
        quality_columns[3].metric("Duplicados", f"{int(base_quality['duplicate_rows']):,}")
        quality_details = pd.DataFrame(
            [
                {
                    "Indicador": "Celdas vacías",
                    "Resultado": f"{int(base_quality['missing_cells']):,}",
                    "Interpretación": "Nulos explícitos en el archivo original.",
                },
                {
                    "Indicador": "Fechas de calendario sin fila",
                    "Resultado": f"{int(base_quality['missing_days']):,}",
                    "Interpretación": "Dentro de la primera y última fecha válida; no equivale a cero ventas.",
                },
                {
                    "Indicador": "Días con cero unidades registradas",
                    "Resultado": f"{int(base_quality['zero_sales_days']):,}",
                    "Interpretación": "Existe al menos una fecha con filas válidas cuyo total es exactamente cero.",
                },
                {
                    "Indicador": "Filas aptas para demanda",
                    "Resultado": f"{valid_row_count:,} de {total_row_count:,}",
                    "Interpretación": "Fecha válida, producto informado y cantidad válida no negativa.",
                },
            ]
        )
        st.dataframe(quality_details, use_container_width=True, hide_index=True)
        st.caption("Los duplicados y las filas inválidas se informan, pero no se borran del archivo cargado.")
        st.markdown("#### Perfil de columnas")
        st.dataframe(profile_data(sales), use_container_width=True, hide_index=True)

    with findings_tab:
        st.markdown("#### Hallazgos respaldados por esta selección")
        filtered_quality = results["quality"]
        assert isinstance(filtered_quality, dict)
        filtered_units = float(daily["quantity"].sum()) if not daily.empty else 0.0
        observed_filtered = daily.loc[daily["has_observation"]] if not daily.empty else daily
        if observed_filtered.empty:
            st.info("Los filtros no contienen fechas con registros válidos; no hay hallazgos que resumir.")
        else:
            peak = observed_filtered.loc[observed_filtered["quantity"].idxmax()]
            st.markdown(
                f"**Observado:** se registraron **{filtered_units:,.0f} unidades** en "
                f"**{len(observed_filtered):,} fechas**. El máximo diario fue "
                f"**{peak['quantity']:,.0f} unidades** el **{peak['date'].date().isoformat()}**."
            )
            if len(product_summary) == 1:
                st.markdown(
                    f"**Calculado:** solo hay un producto en la selección "
                    f"(**{product_summary.iloc[0]['product_id']}**); no es posible establecer un ranking."
                )
            elif len(product_summary) > 1:
                leader = product_summary.iloc[0]
                st.markdown(
                    f"**Calculado:** **{leader['product_id']}** concentra "
                    f"**{leader['share_pct']:.1f}%** de las unidades de esta selección."
                )
            candidate_count = int(daily["outlier_iqr"].sum())
            if len(observed_filtered) < 14:
                st.markdown("**Pendiente de validar:** la muestra es demasiado corta para revisar candidatos IQR.")
            elif candidate_count:
                st.markdown(
                    f"**Detectado:** {candidate_count} fecha(s) extrema(s) según IQR; "
                    "requieren revisión y no se consideran errores confirmados."
                )
            else:
                st.markdown("**Detectado:** la regla IQR no señaló fechas extremas en esta selección.")
        st.markdown(
            "**Pendiente de validar:** la falta de una fila no demuestra que no hubiera ventas. "
            "Este EDA describe los registros; no demuestra causalidad, rentabilidad ni demanda futura."
        )

    if "revenue_by_product" in base_results:
        st.caption("La facturación está disponible en Productos cuando el archivo incluye precios unitarios válidos.")


def render_advanced_eda() -> None:
    """Render a generic EDA workbench for any currently loaded business dataset."""
    st.subheader("EDA avanzado y calidad")
    st.write("Sigue este recorrido: selecciona datos, revisa su calidad y después explora la pregunta que te interesa.")
    data_sets = _eda_data()
    if not data_sets:
        st.info("Carga un CSV o Excel para analizar tus datos. El caso sintético ResQ Data sigue disponible como referencia.")
        bayesian_tab, case_tab = st.tabs(["Riesgo bayesiano", "Caso ResQ Data"])
        with bayesian_tab:
            _render_bayesian_risk_tab(None)
        with case_tab:
            render_resqdata_case()
        return
    dataset_options = sorted(data_sets)
    default_dataset = "sales" if "sales" in data_sets else dataset_options[0]
    selected_key = st.selectbox(
        "Conjunto de datos",
        dataset_options,
        index=dataset_options.index(default_dataset),
        format_func=lambda key: key.capitalize(),
    )
    data = data_sets[selected_key].copy()
    st.caption(
        f"Fuente: {_source_label(selected_key)} · {len(data):,} filas · {len(data.columns):,} columnas · "
        f"{_period_label(data)}."
    )
    st.info(
        "Empieza por **Perfil y calidad**. Explora distribuciones, cambios temporales y robustez; "
        "termina revisando las limitaciones antes de interpretar los resultados."
    )
    numeric_columns = [
        column
        for column in data.select_dtypes(include="number").columns
        if pd.to_numeric(data[column], errors="coerce")
        .replace([float("inf"), float("-inf")], float("nan"))
        .notna()
        .any()
    ]
    unit_labels: dict[object, str] = {}
    if numeric_columns:
        with st.expander("Unidades de medida", expanded=False):
            st.caption(
                "Indica la unidad declarada para cada variable numérica. "
                "Estas etiquetas solo describen los gráficos; no convierten los datos."
            )
            demo_units = (
                DEMO_COLUMN_UNITS.get(selected_key, {})
                if st.session_state.get("demo_loaded")
                else {}
            )
            for column in numeric_columns:
                widget_key = _advanced_eda_unit_widget_key(selected_key, column)
                if widget_key not in st.session_state and column in demo_units:
                    st.session_state[widget_key] = demo_units[column]
                unit_labels[column] = st.text_input(
                    f"Unidad de {column}",
                    key=widget_key,
                    placeholder="p. ej., unidades, kg, €",
                ).strip()
            missing_units = [str(column) for column in numeric_columns if not unit_labels[column]]
            if missing_units:
                st.warning(
                    "Pendiente de revisar: no se ha indicado la unidad de "
                    f"{', '.join(missing_units)}. Los ejes lo mostrarán explícitamente."
                )

    def axis_label(column: object) -> str:
        return _eda_axis_label(column, unit_labels.get(column, ""))

    profile_tab, univariate_tab, time_tab, robustness_tab, bayesian_tab, case_tab = st.tabs(
        [
            "Perfil y calidad",
            "Distribuciones",
            "Tiempo y anomalías",
            "Robustez",
            "Riesgo bayesiano",
            "Caso ResQ Data",
        ]
    )
    with profile_tab:
        report = quality_summary(data)
        first, second, third, fourth = st.columns(4)
        first.metric("Filas", report["rows"])
        second.metric("Columnas", report["columns"])
        third.metric("Celdas nulas", report["missing_cells"])
        fourth.metric("Filas duplicadas", report["duplicate_rows"])
        if report["negative_values"]:
            st.warning(f"Valores negativos detectados: {report['negative_values']}. Revísalos según las reglas de negocio.")
        if report["potential_leakage_columns"]:
            st.warning(
                "Posible fuga de información por nombre de columna: "
                f"{report['potential_leakage_columns']}. Si se entrena un modelo, confirma que estas variables "
                "no contengan un resultado conocido después de la decisión."
            )
        st.caption("No hay un modelo predictivo compatible cargado: SHAP/LIME no se aplican en este EDA.")
        st.dataframe(
            profile_data(data).style.format({"porcentaje_nulo": "{:.1%}"}),
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "Descargar perfil CSV",
            profile_data(data).to_csv(index=False).encode("utf-8"),
            file_name=f"perfil_{selected_key}.csv",
            mime="text/csv",
        )
    with univariate_tab:
        if not numeric_columns:
            st.info("Este conjunto no contiene columnas numéricas analizables.")
        else:
            column = st.selectbox("Variable numérica", numeric_columns, key="univariate_column")
            st.dataframe(numeric_summary(data, column), use_container_width=True, hide_index=True)
            values = (
                pd.to_numeric(data[column], errors="coerce")
                .replace([float("inf"), float("-inf")], float("nan"))
                .dropna()
            )
            left, right = st.columns(2)
            with left:
                distribution_figure = px.histogram(
                    data,
                    x=column,
                    nbins=30,
                    title=f"Distribución de {column}",
                )
                distribution_figure.update_xaxes(title_text=axis_label(column))
                distribution_figure.update_yaxes(title_text="Número de registros")
                st.plotly_chart(distribution_figure, use_container_width=True)
                if not values.empty:
                    mean_value = float(values.mean())
                    median_value = float(values.median())
                    skew = float(values.skew())
                    if skew > 0.5:
                        shape_reading = "La asimetría positiva indica una cola más extendida hacia valores altos."
                    elif skew < -0.5:
                        shape_reading = "La asimetría negativa indica una cola más extendida hacia valores bajos."
                    else:
                        shape_reading = "La distribución no muestra una asimetría marcada con esta medida."
                    st.caption(
                        f"De {len(values):,} valores válidos de {column}, la media es "
                        f"{_format_eda_number(mean_value)} y la mediana "
                        f"{_format_eda_number(median_value)}; el rango va de "
                        f"{_format_eda_number(float(values.min()))} a "
                        f"{_format_eda_number(float(values.max()))}. {shape_reading}"
                    )
            with right:
                box_figure = px.box(data, y=column, title=f"Valores atípicos de {column}")
                box_figure.update_yaxes(title_text=axis_label(column))
                st.plotly_chart(box_figure, use_container_width=True)
                if not values.empty:
                    first_quartile, third_quartile = values.quantile([0.25, 0.75])
                    iqr = third_quartile - first_quartile
                    outlier_count = int(
                        (
                            (values < first_quartile - 1.5 * iqr)
                            | (values > third_quartile + 1.5 * iqr)
                        ).sum()
                    )
                    st.caption(
                        f"La mediana es {_format_eda_number(float(values.median()))}; la mitad central "
                        f"de los registros está entre {_format_eda_number(float(first_quartile))} y "
                        f"{_format_eda_number(float(third_quartile))}. La regla IQR marca {outlier_count} "
                        "candidato(s) extremo(s), que conviene revisar y no son errores confirmados."
                    )
    with time_tab:
        possible_dates = [
            column
            for column in data.columns
            if any(token in str(column).lower() for token in ("date", "fecha", "datetime", "timestamp"))
            or str(column).lower() == "dt"
        ]
        if not possible_dates or not numeric_columns:
            st.info("Se necesita una columna de fecha y una variable numérica para el análisis temporal.")
        else:
            date_column = st.selectbox("Fecha", possible_dates, key="time_date")
            value_column = st.selectbox("Variable temporal", numeric_columns, key="time_value")
            series, warnings = temporal_summary(data, date_column, value_column)
            for warning in warnings:
                st.warning(warning.message)
            temporal_figure = px.line(
                series,
                x=date_column,
                y=value_column,
                color="anomaly",
                title="Evolución temporal y anomalías",
                labels={
                    date_column: "Fecha",
                    value_column: axis_label(value_column),
                    "anomaly": "Candidata a anomalía",
                },
            )
            st.plotly_chart(
                temporal_figure,
                use_container_width=True,
            )
            if series.empty:
                st.info("No hay fechas y valores numéricos válidos para resumir esta selección.")
            else:
                peak_period = series.loc[series[value_column].idxmax()]
                lowest_period = series.loc[series[value_column].idxmin()]
                anomaly_count = int(series["anomaly"].sum())
                anomaly_reading = (
                    f"Se marcaron {anomaly_count} fecha(s) como candidatas a anomalía (|z| ≥ 3)."
                    if len(series) >= 14 and series[value_column].std() > 0
                    else "No se evaluaron anomalías: la serie es demasiado corta o no presenta variación."
                )
                st.caption(
                    f"La suma diaria de {value_column} fue, en promedio, "
                    f"{_format_eda_number(float(series[value_column].mean()))}. En {len(series):,} fechas "
                    f"observadas, el máximo fue "
                    f"{_format_eda_number(float(peak_period[value_column]))} el "
                    f"{_format_eda_date(peak_period[date_column])} y el mínimo "
                    f"{_format_eda_number(float(lowest_period[value_column]))} el "
                    f"{_format_eda_date(lowest_period[date_column])}. {anomaly_reading} "
                    "Si aparece un punto marcado, merece revisión, pero no confirma un error."
                )
            if len(series) >= 14:
                weekday_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                weekday_profile = series.assign(day_of_week=series[date_column].dt.dayofweek)
                weekday_profile = (
                    weekday_profile.groupby("day_of_week", as_index=False)[value_column]
                    .mean()
                    .assign(day_name=lambda frame: frame["day_of_week"].map(dict(enumerate(weekday_names))))
                )
                st.plotly_chart(
                    px.bar(
                        weekday_profile,
                        x="day_name",
                        y=value_column,
                        category_orders={"day_name": weekday_names},
                        title="Perfil medio por día de la semana",
                        labels={
                            "day_name": "Día de la semana",
                            value_column: axis_label(value_column),
                        },
                    ),
                    use_container_width=True,
                )
                busiest_day = weekday_profile.loc[weekday_profile[value_column].idxmax()]
                quietest_day = weekday_profile.loc[weekday_profile[value_column].idxmin()]
                st.caption(
                    f"{busiest_day['day_name']} tiene la media más alta "
                    f"({_format_eda_number(float(busiest_day[value_column]))} unidades) y "
                    f"{quietest_day['day_name']} la más baja "
                    f"({_format_eda_number(float(quietest_day[value_column]))}). "
                    "Es un patrón observado en este periodo, no una prueba de que se repita."
                )
            if len(series) >= 40:
                middle = len(series) // 2
                try:
                    psi = population_stability_index(series[value_column].iloc[:middle], series[value_column].iloc[middle:])
                    st.metric("Deriva de distribución (PSI)", f"{psi:.3f}")
                    st.caption("PSI cercano a 0 indica distribuciones similares; valores altos sugieren revisar cambios de datos o negocio.")
                except ValueError as error:
                    st.info(str(error))
    with robustness_tab:
        if not numeric_columns:
            st.info("Se necesita una variable numérica para bootstrap y segmentación.")
            return
        bootstrap_column = st.selectbox("Variable para bootstrap", numeric_columns, key="bootstrap_column")
        try:
            mean, lower, upper = bootstrap_mean_interval(data[bootstrap_column])
            st.metric("Media observada", f"{mean:,.3f}")
            st.caption(f"Intervalo bootstrap del 95 %: [{lower:,.3f}, {upper:,.3f}].")
            st.warning(
                "Este intervalo asume observaciones independientes. Para una serie temporal con autocorrelación, "
                "no debe interpretarse como una medida de incertidumbre temporal."
            )
        except ValueError as error:
            st.warning(str(error))
        if len(numeric_columns) >= 2:
            cluster_columns = st.multiselect("Variables para segmentación", numeric_columns, default=numeric_columns[:2])
            clusters = st.slider("Número de segmentos", 2, 6, 3)
            if len(cluster_columns) >= 2 and st.button("Crear segmentos"):
                try:
                    segmented = data.copy()
                    segmented["segment"] = segment_rows(data, cluster_columns, clusters)
                    cluster_figure = px.scatter(
                        segmented.dropna(subset=["segment"]),
                        x=cluster_columns[0],
                        y=cluster_columns[1],
                        color="segment",
                        title="Segmentación exploratoria",
                        labels={
                            cluster_columns[0]: axis_label(cluster_columns[0]),
                            cluster_columns[1]: axis_label(cluster_columns[1]),
                            "segment": "Segmento",
                        },
                    )
                    st.plotly_chart(
                        cluster_figure,
                        use_container_width=True,
                    )
                    cluster_points = segmented.dropna(subset=["segment"])
                    cluster_profile = cluster_points.groupby("segment").agg(
                        rows=("segment", "size"),
                        first_mean=(cluster_columns[0], "mean"),
                        second_mean=(cluster_columns[1], "mean"),
                    )
                    first_leader = cluster_profile["first_mean"].idxmax()
                    second_leader = cluster_profile["second_mean"].idxmax()
                    st.caption(
                        f"El segmento {first_leader} presenta la media más alta de "
                        f"{cluster_columns[0]} ({_format_eda_number(float(cluster_profile.loc[first_leader, 'first_mean']))}); "
                        f"el segmento {second_leader}, la de {cluster_columns[1]} "
                        f"({_format_eda_number(float(cluster_profile.loc[second_leader, 'second_mean']))}). "
                        f"Los segmentos contienen entre {int(cluster_profile['rows'].min())} y "
                        f"{int(cluster_profile['rows'].max())} filas completas. Son grupos exploratorios, "
                        "no categorías reales ni una explicación causal."
                    )
                except ValueError as error:
                    st.warning(str(error))
    with bayesian_tab:
        _render_bayesian_risk_tab(data)
    with case_tab:
        render_resqdata_case()


def _render_bayesian_risk_tab(data: pd.DataFrame | None) -> None:
    st.subheader("Riesgo de merma con Naive Bayes")
    st.write(
        "Compara snapshots históricos de lotes con y sin merma para estimar su nivel de riesgo. "
        "Sube aquí un CSV/Excel ya preparado o cárgalo en **Datos y calidad → Dataset libre para EDA**."
    )
    st.warning(
        "La probabilidad es orientativa y no está calibrada. Naive Bayes supone independencia entre variables; "
        "la asociación no demuestra causalidad ni garantiza el resultado de lotes futuros."
    )
    template = pd.DataFrame(columns=SNAPSHOT_COLUMNS)
    st.download_button(
        "Descargar plantilla de snapshots",
        template.to_csv(index=False).encode("utf-8"),
        file_name="plantilla_riesgo_merma.csv",
        mime="text/csv",
    )
    st.caption(
        "Una fila representa un lote en una fecha de corte. Separa los lotes: todas las filas de un lote "
        "deben compartir su etiqueta final `hubo_merma` (0/1); déjala vacía solo para lotes aún sin resultado. "
        "Incluye al menos 20 lotes etiquetados, con al menos 4 de cada clase. Usa solo variables conocidas "
        "en la fecha del snapshot, nunca información posterior al resultado."
    )
    upload = st.file_uploader(
        "Snapshots de riesgo (CSV o Excel)",
        type=["csv", "xlsx"],
        key="bayesian_waste_risk_upload",
    )
    uploaded_data: pd.DataFrame | None = None
    if upload is not None:
        try:
            uploaded_data = parse_free_tabular(upload.getvalue(), upload.name)
        except (UnicodeDecodeError, ValueError, pd.errors.ParserError) as error:
            st.error(f"No se pudo leer el archivo de snapshots: {error}")
            return
    selected_data = uploaded_data if uploaded_data is not None else data
    if selected_data is None:
        st.info("Carga un dataset de snapshots para ejecutar el análisis.")
        return
    missing_columns = set(SNAPSHOT_COLUMNS) - set(selected_data.columns)
    if missing_columns:
        st.info(
            "El conjunto seleccionado no tiene el formato de snapshots necesario. "
            f"Faltan: {', '.join(sorted(missing_columns))}."
        )
        return
    if st.button("Calcular riesgo bayesiano", key="run_bayesian_waste_risk"):
        try:
            result = evaluate_bayesian_waste_risk(selected_data)
        except ValueError as error:
            st.warning(str(error))
            return
        metrics = result["metrics"]
        first, second, third, fourth = st.columns(4)
        first.metric("Lotes de entrenamiento", metrics["lotes_entrenamiento"])
        second.metric("Lotes de validación", metrics["lotes_validacion"])
        third.metric("AUC-ROC por lote", f"{metrics['auc_roc_por_lote']:.3f}")
        fourth.metric("Tasa de merma validación", f"{metrics['tasa_merma_validacion']:.1%}")
        st.caption(
            f"Precisión al umbral 0,5: {metrics['precision_05_por_lote']:.1%} · "
            f"sensibilidad: {metrics['recall_05_por_lote']:.1%} · "
            f"precisión media (PR): {metrics['average_precision_por_lote']:.3f}. "
            "Las métricas se calculan sobre lotes separados del entrenamiento."
        )
        predictions = result["predictions"].rename(
            columns={
        "lote_id": "lote",
        "snapshot_date": "fecha_snapshot",
        "hubo_merma": "merma_observada",
        "probabilidad_merma": "probabilidad_merma",
        "tipo_resultado": "tipo_resultado",
            }
        )
        st.dataframe(predictions, use_container_width=True, hide_index=True)
        st.download_button(
            "Descargar resultados bayesianos",
            predictions.to_csv(index=False).encode("utf-8"),
            file_name="riesgo_bayesiano_lotes.csv",
            mime="text/csv",
        )

def render_inventory_profitability() -> None:
    """Render coverage and capital metrics if sales and inventory are available."""
    st.subheader("Inventario y rentabilidad")
    data = _business_data()
    sales, inventory = data.get(SALES_CONTRACT.key), data.get(INVENTORY_CONTRACT.key)
    if sales is None or inventory is None:
        st.info("Carga ventas e inventario para calcular cobertura, capital expuesto y riesgos.")
        return
    missing_sales = {"date", "product_id", "quantity"} - set(sales.columns)
    missing_inventory = {"product_id", "on_hand_units"} - set(inventory.columns)
    if missing_sales or missing_inventory:
        st.warning(
            "No se puede calcular inventario todavía. "
            f"Faltan campos de ventas: {', '.join(sorted(missing_sales)) or 'ninguno'}; "
            f"de inventario: {', '.join(sorted(missing_inventory)) or 'ninguno'}."
        )
        return
    costs = data.get(COSTS_CONTRACT.key)
    inventory = attach_cost_reference(inventory, costs)
    period_complete = _render_sales_period_confirmation()
    daily = average_daily_demand(sales, assume_complete_period=period_complete)
    intelligence = inventory_intelligence(inventory, daily)
    total_capital = intelligence["capital_exposed"].sum()
    first, second, third = st.columns(3)
    first.metric("Capital expuesto", f"{total_capital:,.2f} €")
    second.metric("Riesgo de rotura", int(intelligence["risk"].eq("rotura").sum()))
    third.metric("Riesgo de sobrestock", int(intelligence["risk"].eq("sobrestock").sum()))
    display_columns = ["product_id", "on_hand_units", "daily_demand", "coverage_days", "capital_exposed"]
    if "unit_margin" in intelligence:
        display_columns.append("unit_margin")
    display_columns.append("risk")
    st.dataframe(
        intelligence[display_columns].sort_values("capital_exposed", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
    if period_complete:
        st.caption(
            "Periodo completo confirmado: la demanda divide las unidades por los días naturales desde la primera "
            "fecha registrada de cada producto hasta el final del extracto; los días sin filas cuentan como cero. "
            "Las fechas anteriores al primer registro son desconocidas. No es una previsión."
        )
    else:
        st.warning(
            "Periodo no confirmado completo: la demanda media usa solo fechas con registro. "
            "Las señales de inventario son provisionales y pueden ocultar sobrestock o riesgo."
        )


def render_lot_risk() -> None:
    """Render the specialised expiry-risk view only for companies that provide lot data."""
    st.markdown(
        """
        <style>
        .lot-dashboard-title {font-size: 1.6rem; font-weight: 700; color: var(--rq-ink); margin-bottom: 0.15rem;}
        .lot-dashboard-subtitle {color: var(--rq-muted); margin-bottom: 1rem;}
        .lot-alert {background: #30251a; border: 1px solid #76511e; border-radius: 0.6rem;
                    padding: 1rem; color: #f5c578; margin: 1rem 0;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="lot-dashboard-title">Centro de control de riesgos por lote</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="lot-dashboard-subtitle">Prioriza inventario con fecha límite según demanda, stock y coste de tu empresa.</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Riesgo por lote")
    st.write(
        "Este módulo estima qué proporción del stock podría quedar sin vender antes de la fecha límite, "
        "a partir de ventas y datos de lote cargados. En la demostración, las ventas derivan de FreshRetailNet "
        "y los campos de lote son supuestos sintéticos, no observaciones de una empresa. Los días sin filas "
        "cuentan como cero ventas únicamente si confirmas que el extracto cubre todos los días del periodo."
    )
    data = _business_data()
    sales, lots = data.get(SALES_CONTRACT.key), data.get(LOTS_CONTRACT.key)
    if sales is None or lots is None:
        st.info("Carga ventas.csv y lotes.csv para habilitar el riesgo por lote.")
        return
    missing_sales = {"date", "product_id", "quantity"} - set(sales.columns)
    missing_lots = {"lot_id", "product_id", "stock_available", "expiry_date", "unit_cost"} - set(lots.columns)
    if missing_sales or missing_lots:
        st.warning(
            "No se puede calcular riesgo por lote. "
            f"Faltan campos de ventas: {', '.join(sorted(missing_sales)) or 'ninguno'}; "
            f"de lotes: {', '.join(sorted(missing_lots)) or 'ninguno'}."
        )
        return
    period_complete = _render_sales_period_confirmation()
    risks, warnings = build_lot_risk(
        lots,
        sales,
        assume_complete_period=period_complete,
    )
    for warning in warnings:
        st.warning(warning)
    if risks.empty:
        return
    valid_risks = risks.dropna(subset=["estimated_unsold_stock_ratio"]).copy()
    if valid_risks.empty:
        st.info("Ningún lote tiene todavía suficiente historial de ventas para estimar su riesgo.")
        return
    critical_lots = valid_risks.loc[valid_risks["risk_level"].isin(["Alto", "Crítico"])]
    first, second, third, fourth = st.columns(4)
    first.metric("Coste expuesto estimado", f"{valid_risks['cost_exposed'].sum():,.2f} €")
    second.metric("Lotes prioritarios", len(critical_lots))
    third.metric("Stock no vendido estimado", f"{valid_risks['estimated_unsold_stock_ratio'].mean():.1%}")
    fourth.metric("Stock analizado", f"{valid_risks['stock_available'].sum():,.0f} ud")
    if not critical_lots.empty:
        top_lot = critical_lots.sort_values("cost_exposed", ascending=False).iloc[0]
        st.markdown(
            (
                '<div class="lot-alert"><strong>Acción prioritaria:</strong> '
                f'Lote {top_lot["lot_id"]} · {top_lot["product_id"]} · '
                f'coste expuesto estimado de {top_lot["cost_exposed"]:,.2f} € · '
                f'{top_lot["recommendation"]}.</div>'
            ),
            unsafe_allow_html=True,
        )
    else:
        st.success("No hay lotes con riesgo alto según el historial y los datos cargados.")
    ranked_lots = valid_risks.copy()
    display_columns = [
        "lot_id",
        "product_id",
        "stock_available",
        "expiry_date",
        "days_remaining",
        "sales_days",
        "history_days",
        "daily_demand",
        "estimated_unsold_stock_ratio",
        "risk_level",
        "cost_exposed",
        "recommendation",
    ]
    st.dataframe(
        ranked_lots[display_columns]
        .sort_values("cost_exposed", ascending=False)
        .style.format({"estimated_unsold_stock_ratio": "{:.1%}", "cost_exposed": "{:,.2f} €", "daily_demand": "{:,.2f}"}),
        use_container_width=True,
        hide_index=True,
    )
    selected_lot = st.selectbox("Ver detalle de un lote", valid_risks["lot_id"].astype(str).tolist())
    selected = valid_risks.loc[valid_risks["lot_id"].astype(str) == selected_lot].iloc[0]
    detail_left, detail_right = st.columns(2)
    with detail_left:
        st.markdown("#### Explicación del riesgo")
        st.write(
            f"Con una demanda media de **{selected['daily_demand']:.2f} unidades/día** durante "
            f"**{selected['history_days']} días naturales** ({selected['sales_days']} fechas con registros), "
            f"se estiman **{selected['expected_sales_before_expiry']:.2f} unidades** vendidas antes "
            f"de la fecha límite. El lote tiene {selected['stock_available']:.2f} unidades disponibles."
        )
    with detail_right:
        st.markdown("#### Acción recomendada")
        st.success(selected["recommendation"])
        st.write(
            f"Proporción de stock no vendido estimada: **{selected['estimated_unsold_stock_ratio']:.1%}**. "
            f"Coste expuesto estimado: **{selected['cost_exposed']:,.2f} €**."
        )
    st.caption(
        "Riesgo estimado = unidades que previsiblemente no se venderán antes de la fecha límite / stock del lote. "
        "La demanda cuenta como cero los días sin filas desde el primer registro del producto hasta el final "
        "del extracto confirmado. Es una estimación, no una probabilidad calibrada ni una merma confirmada."
    )


def render_scenarios() -> None:
    """Expose scenario calculations with explicit assumptions and no claims of realised savings."""
    st.subheader("Simulador económico")
    st.write("Compara un escenario con su línea base. Los resultados son estimaciones, no ahorros realizados.")
    left, middle, right = st.columns(3)
    with left:
        units = st.number_input("Unidades base", min_value=1.0, value=100.0)
        price = st.number_input("Precio unitario base (€)", min_value=0.01, value=10.0)
        cost = st.number_input("Coste unitario (€)", min_value=0.0, value=5.0)
    with middle:
        holding = st.number_input("Coste de almacenamiento (€/ud/día)", min_value=0.0, value=0.05)
        days = st.number_input("Días de almacenamiento", min_value=0.0, value=7.0)
    with right:
        price_change = st.slider("Cambio de precio (%)", -80, 50, -10)
        demand_change = st.slider("Cambio supuesto en demanda (%)", -80, 200, 15)
    result = compare_scenario(units, price, cost, holding, days, price_change, demand_change)
    baseline = compare_scenario(units, price, cost, holding, days, 0, 0)
    st.session_state["scenario_report"] = {
        "price_change_pct": price_change,
        "demand_change_pct": demand_change,
        "baseline_margin": baseline.gross_margin,
        "scenario_margin": result.gross_margin,
        "margin_change": result.margin_change,
    }
    first, second, third = st.columns(3)
    first.metric("Margen base estimado", f"{baseline.gross_margin:,.2f} €")
    second.metric("Margen de escenario", f"{result.gross_margin:,.2f} €")
    third.metric("Variación estimada", f"{result.margin_change:,.2f} €")
    st.caption(
        "Supuesto: el cambio de demanda indicado es una hipótesis del usuario. "
        "El sistema no afirma que el descuento vaya a producir ese efecto."
    )
    sensitivity = scenario_sensitivity(units, price, cost, holding, days)
    sensitivity_matrix = sensitivity.pivot(
        index="demand_change_pct",
        columns="price_change_pct",
        values="margin_change",
    )
    st.markdown("#### Sensibilidad del margen a precio y demanda")
    st.plotly_chart(
        px.imshow(
            sensitivity_matrix,
            text_auto=".1f",
            aspect="auto",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
            labels={
                "x": "Cambio supuesto de precio (%)",
                "y": "Cambio supuesto de demanda (%)",
                "color": "Variación estimada de margen (€)",
            },
            title="Variación estimada frente al escenario base",
        ),
        use_container_width=True,
    )
    st.caption(
        "Matriz de escenarios hipotéticos (−20 % a +20 %). No son probabilidades, predicciones ni ahorros realizados."
    )


def render_real_demand() -> None:
    """Show evaluated real-data demand evidence without claiming it represents the user's company."""
    st.subheader("Previsión de demanda con datos reales")
    st.write(
        "Esta demostración usa FreshRetailNet-50K, un conjunto real de ventas de perecederos. "
        "No representa la empresa del usuario ni contiene sus costes internos."
    )
    if not METRICS_PATH.exists() or not FORECAST_PATH.exists():
        st.warning("No hay artefactos de evaluación real disponibles. Ejecuta `python -m src.real_demand` después de descargar la fuente.")
        st.link_button("Fuente oficial FreshRetailNet-50K", SOURCE_URL)
        return
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    model_metrics = metrics["models"]
    baseline = model_metrics["seasonal_naive"]
    moving_average = model_metrics["moving_average_7d"]
    first, second, third, fourth = st.columns(4)
    first.metric("MAE · baseline estacional", baseline["mae"])
    second.metric("MAE · media móvil 7 días", moving_average["mae"])
    third.metric("RMSE · baseline estacional", baseline["rmse"])
    fourth.metric("RMSE · media móvil 7 días", moving_average["rmse"])
    st.caption(f"Observaciones evaluadas: {metrics['evaluation_rows']:,} · Series: {metrics['series_evaluated']:,}.")
    st.caption(metrics["evaluation_method"])
    forecasts = pd.read_csv(FORECAST_PATH)
    sample_key = forecasts[["store_id", "product_id"]].iloc[0]
    sample = forecasts.loc[
        (forecasts["store_id"] == sample_key["store_id"])
        & (forecasts["product_id"] == sample_key["product_id"])
    ]
    st.plotly_chart(
        px.line(
            sample,
            x="dt",
            y=["sale_amount", "forecast_units", "moving_average_7d_units"],
            title="Ventas reales frente a baseline y media móvil",
            labels={
                "value": "Unidades vendidas",
                "dt": "Fecha",
                "variable": "Serie",
                "sale_amount": "Ventas reales",
                "forecast_units": "Baseline estacional",
                "moving_average_7d_units": "Media móvil (7 días)",
            },
        ),
        use_container_width=True,
    )
    st.link_button("Fuente y licencia CC BY 4.0", SOURCE_URL)
