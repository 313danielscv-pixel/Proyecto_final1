"""Bounded, read-only table access for configured relational database sources."""

from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd
from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import SQLAlchemyError

MAX_IMPORT_ROWS = 100_000
DEFAULT_ALLOWED_HOSTS = ("localhost", "127.0.0.1", "::1")
SUPPORTED_DIALECTS = {
    "mysql": ("mysql+pymysql", 3306),
    "postgresql": ("postgresql+psycopg", 5432),
    "mssql": ("mssql+pyodbc", 1433),
}


class DatabaseConnectionError(RuntimeError):
    """Raised when a database source cannot be safely inspected or queried."""


@dataclass(frozen=True)
class DatabaseConfig:
    dialect: str
    host: str
    port: int
    database: str
    username: str
    password: str
    trust_server_certificate: bool = False
    use_windows_auth: bool = False


def allowed_database_hosts() -> tuple[str, ...]:
    """Return the server-side allowlist; default to loopback for local demos."""
    configured = os.environ.get("RESQ_DB_ALLOWED_HOSTS", "")
    hosts = configured.split(",") if configured.strip() else DEFAULT_ALLOWED_HOSTS
    normalized = {_normalize_host(host) for host in hosts if host.strip()}
    return tuple(sorted(normalized))


def _normalize_host(host: str) -> str:
    return host.strip().casefold().strip("[]").rstrip(".")


def validate_database_config(
    config: DatabaseConfig,
    allowed_hosts: tuple[str, ...] | None = None,
) -> None:
    """Reject unsupported drivers and hosts not explicitly trusted by the server."""
    if config.dialect not in SUPPORTED_DIALECTS:
        raise DatabaseConnectionError("El conector admite MySQL, PostgreSQL y SQL Server.")
    if not 1 <= config.port <= 65_535:
        raise DatabaseConnectionError("El puerto debe estar entre 1 y 65535.")
    needs_credentials = not (config.dialect == "mssql" and config.use_windows_auth)
    if not config.database.strip() or (
        needs_credentials and (not config.username.strip() or not config.password)
    ):
        raise DatabaseConnectionError("Indica la base de datos, el usuario y la contraseña.")

    host = _normalize_host(config.host)
    trusted_hosts = allowed_hosts if allowed_hosts is not None else allowed_database_hosts()
    normalized_allowlist = {_normalize_host(item) for item in trusted_hosts}
    if not host or host not in normalized_allowlist:
        raise DatabaseConnectionError(
            "El host no está autorizado por el servidor. Añádelo a RESQ_DB_ALLOWED_HOSTS "
            "solo si confías en esa base de datos."
        )


def create_database_engine(
    config: DatabaseConfig,
    allowed_hosts: tuple[str, ...] | None = None,
) -> Engine:
    """Create an engine for one approved host without exposing credentials in a URL string."""
    validate_database_config(config, allowed_hosts)
    driver, _ = SUPPORTED_DIALECTS[config.dialect]
    query = {}
    connect_args = {"connect_timeout": 5}
    if config.dialect == "mssql":
        query = {
            "driver": "ODBC Driver 18 for SQL Server",
            "Encrypt": "yes",
        }
        if config.trust_server_certificate:
            query["TrustServerCertificate"] = "yes"
        if config.use_windows_auth:
            query["Trusted_Connection"] = "yes"
        connect_args = {"timeout": 5}
    url = URL.create(
        driver,
        username=None if config.use_windows_auth else config.username,
        password=None if config.use_windows_auth else config.password,
        host=_normalize_host(config.host),
        port=config.port,
        database=config.database,
        query=query,
    )
    try:
        return create_engine(
            url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
    except (ImportError, SQLAlchemyError, ValueError) as error:
        raise DatabaseConnectionError(
            f"No se pudo preparar el conector {config.dialect}. Comprueba que sus dependencias estén instaladas."
        ) from error


def verify_connection(engine: Engine) -> None:
    """Verify connectivity using a harmless SELECT."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError as error:
        raise DatabaseConnectionError(
            "No se pudo conectar. Comprueba el host, el puerto, las credenciales, la red "
            "y que el usuario tenga permiso de lectura."
        ) from error


def list_tables(engine: Engine) -> list[str]:
    """List tables and views visible in the database's default schema."""
    try:
        inspector = inspect(engine)
        return sorted(set(inspector.get_table_names()) | set(inspector.get_view_names()))
    except SQLAlchemyError as error:
        raise DatabaseConnectionError(
            "No se pudieron listar las tablas. Comprueba los permisos de lectura del usuario."
        ) from error


def read_table(engine: Engine, table_name: str, limit: int = MAX_IMPORT_ROWS) -> pd.DataFrame:
    """Read a bounded table selection; never execute SQL supplied by the user."""
    if not 1 <= limit <= MAX_IMPORT_ROWS:
        raise DatabaseConnectionError(f"El límite debe estar entre 1 y {MAX_IMPORT_ROWS:,} filas.")

    available_tables = list_tables(engine)
    if table_name not in available_tables:
        raise DatabaseConnectionError("La tabla seleccionada ya no está disponible en la base de datos.")

    try:
        table = Table(table_name, MetaData(), autoload_with=engine)
        with engine.connect() as connection:
            data = pd.read_sql_query(select(table).limit(limit + 1), connection)
    except (SQLAlchemyError, pd.errors.DatabaseError, ValueError) as error:
        raise DatabaseConnectionError(
            "No se pudo leer la tabla. Comprueba que el usuario tenga permiso SELECT."
        ) from error

    if len(data) > limit:
        raise DatabaseConnectionError(
            f"La tabla supera el límite de {limit:,} filas. Elige una vista o tabla agregada más pequeña."
        )
    return data
