import pytest
from sqlalchemy import create_engine, text
from streamlit.testing.v1 import AppTest

from src.database_connector import (
    DatabaseConfig,
    DatabaseConnectionError,
    allowed_database_hosts,
    create_database_engine,
    list_tables,
    read_table,
    validate_database_config,
    verify_connection,
)


def _create_sqlite_engine():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE sales (product_id TEXT, quantity INTEGER)"))
        connection.execute(
            text("INSERT INTO sales VALUES ('SKU-1', 3), ('SKU-2', 5), ('SKU-3', 7)")
        )
    return engine


@pytest.mark.parametrize(
    ("dialect", "expected_driver", "port"),
    [
        ("mysql", "mysql+pymysql", 3306),
        ("postgresql", "postgresql+psycopg", 5432),
        ("mssql", "mssql+pyodbc", 1433),
    ],
)
def test_database_config_uses_supported_driver_and_keeps_password_masked(
    dialect: str,
    expected_driver: str,
    port: int,
) -> None:
    config = DatabaseConfig(
        dialect=dialect,
        host="localhost",
        port=port,
        database="resq",
        username="reader",
        password="p@ss:/word",
    )

    engine = create_database_engine(config, allowed_hosts=("localhost",))
    try:
        assert engine.url.drivername == expected_driver
        assert engine.url.password == "p@ss:/word"
        assert "p@ss:/word" not in engine.url.render_as_string(hide_password=True)
    finally:
        engine.dispose()


def test_database_config_rejects_hosts_outside_server_allowlist() -> None:
    config = DatabaseConfig(
        dialect="mysql",
        host="database.example",
        port=3306,
        database="resq",
        username="reader",
        password="secret",
    )

    with pytest.raises(DatabaseConnectionError, match="no está autorizado"):
        validate_database_config(config, allowed_hosts=("localhost",))


def test_database_host_allowlist_defaults_to_loopback(monkeypatch) -> None:
    monkeypatch.delenv("RESQ_DB_ALLOWED_HOSTS", raising=False)

    assert set(allowed_database_hosts()) == {"localhost", "127.0.0.1", "::1"}


def test_database_config_rejects_unsupported_dialects() -> None:
    config = DatabaseConfig(
        dialect="sqlite",
        host="localhost",
        port=0,
        database="resq",
        username="reader",
        password="secret",
    )

    with pytest.raises(DatabaseConnectionError, match="SQL Server"):
        validate_database_config(config, allowed_hosts=("localhost",))


def test_sql_server_connection_uses_encryption_and_optional_certificate_trust() -> None:
    config = DatabaseConfig(
        dialect="mssql",
        host="localhost",
        port=1433,
        database="resq",
        username="reader",
        password="secret",
    )

    engine = create_database_engine(config, allowed_hosts=("localhost",))
    try:
        assert engine.url.query["driver"] == "ODBC Driver 18 for SQL Server"
        assert engine.url.query["Encrypt"] == "yes"
        assert "TrustServerCertificate" not in engine.url.query
    finally:
        engine.dispose()

    windows_auth_config = DatabaseConfig(
        dialect="mssql",
        host="localhost",
        port=1433,
        database="resq",
        username="",
        password="",
        use_windows_auth=True,
    )
    engine = create_database_engine(windows_auth_config, allowed_hosts=("localhost",))
    try:
        assert engine.url.username is None
        assert engine.url.password is None
        assert engine.url.query["Trusted_Connection"] == "yes"
    finally:
        engine.dispose()

    trusted_config = DatabaseConfig(
        dialect="mssql",
        host="localhost",
        port=1433,
        database="resq",
        username="reader",
        password="secret",
        trust_server_certificate=True,
    )
    engine = create_database_engine(trusted_config, allowed_hosts=("localhost",))
    try:
        assert engine.url.query["TrustServerCertificate"] == "yes"
    finally:
        engine.dispose()


def test_read_only_helpers_list_and_read_a_bounded_table() -> None:
    engine = _create_sqlite_engine()
    try:
        verify_connection(engine)

        assert list_tables(engine) == ["sales"]
        data = read_table(engine, "sales", limit=3)
        assert data["product_id"].tolist() == ["SKU-1", "SKU-2", "SKU-3"]
    finally:
        engine.dispose()


def test_streamlit_exposes_the_database_source_mode() -> None:
    app = AppTest.from_file("app.py").run()
    app.radio(key="main_navigation").set_value("Datos y calidad").run()
    source_mode = next(widget for widget in app.radio if widget.key == "upload_source_mode")
    source_mode.set_value("Base de datos").run()

    assert not app.exception
    assert any(button.label == "Probar conexión y listar tablas" for button in app.button)
    assert next(widget for widget in app.selectbox if widget.label == "Motor").options == [
        "MySQL",
        "PostgreSQL",
        "SQL Server",
    ]
    next(widget for widget in app.selectbox if widget.label == "Motor").set_value(
        "SQL Server"
    ).run()
    assert not app.exception
    assert next(widget for widget in app.radio if widget.key == "database_auth_mode").options == [
        "Windows",
        "SQL Server",
    ]


def test_read_table_rejects_missing_tables_and_oversized_imports() -> None:
    engine = _create_sqlite_engine()
    try:
        with pytest.raises(DatabaseConnectionError, match="ya no está disponible"):
            read_table(engine, "sales; DROP TABLE sales", limit=3)
        with pytest.raises(DatabaseConnectionError, match="supera el límite"):
            read_table(engine, "sales", limit=2)
    finally:
        engine.dispose()
