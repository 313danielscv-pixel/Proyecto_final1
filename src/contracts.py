"""Reusable input contracts for the ResQ Intelligence business modules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BusinessModule(StrEnum):
    """Business capabilities that can be enabled from uploaded company data."""

    DEMAND = "demand"
    INVENTORY = "inventory"
    PROFITABILITY = "profitability"
    SUPPLIERS = "suppliers"
    PERISHABLES = "perishables"


class ValueType(StrEnum):
    """Expected value types for CSV fields after parsing."""

    DATE = "date"
    NUMBER = "number"
    TEXT = "text"
    BOOLEAN = "boolean"


@dataclass(frozen=True)
class ColumnContract:
    """Describe one canonical field and the business modules that require it."""

    name: str
    label: str
    value_type: ValueType
    aliases: tuple[str, ...]
    required_by: tuple[BusinessModule, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class DatasetContract:
    """Describe a CSV accepted by the platform."""

    key: str
    filename: str
    title: str
    purpose: str
    columns: tuple[ColumnContract, ...]

    def required_columns(self, module: BusinessModule) -> tuple[ColumnContract, ...]:
        """Return the fields that must be available before enabling a module."""
        return tuple(column for column in self.columns if module in column.required_by)


SALES_CONTRACT = DatasetContract(
    key="sales",
    filename="ventas.csv",
    title="Ventas",
    purpose="Analizar demanda, facturación y tendencias por producto, centro o canal.",
    columns=(
        ColumnContract(
            "date",
            "Fecha",
            ValueType.DATE,
            ("date", "sale_date", "fecha", "fecha_venta"),
            (BusinessModule.DEMAND,),
            "Día de la venta o del agregado de ventas.",
        ),
        ColumnContract(
            "product_id",
            "Producto o servicio",
            ValueType.TEXT,
            ("sku", "item_id", "product", "producto", "codigo_producto"),
            (BusinessModule.DEMAND,),
            "Identificador estable del producto o servicio.",
        ),
        ColumnContract(
            "quantity",
            "Cantidad vendida",
            ValueType.NUMBER,
            ("units", "unidades", "cantidad", "sales_quantity"),
            (BusinessModule.DEMAND,),
            "Unidades positivas vendidas durante el periodo.",
        ),
        ColumnContract(
            "unit_price",
            "Precio unitario",
            ValueType.NUMBER,
            ("price", "precio", "precio_unitario"),
            (BusinessModule.PROFITABILITY,),
            "Precio de venta sin impuestos si está disponible.",
        ),
        ColumnContract(
            "store_id",
            "Centro, tienda o canal",
            ValueType.TEXT,
            ("store", "store_id", "tienda", "centro", "canal"),
            (),
            "Centro operativo, tienda física o canal de venta.",
        ),
        ColumnContract(
            "category",
            "Categoría",
            ValueType.TEXT,
            ("categoria", "department", "family", "product_category"),
            (),
            "Agrupación de productos para análisis.",
        ),
        ColumnContract(
            "promotion",
            "Promoción",
            ValueType.BOOLEAN,
            ("promo", "promotion_flag", "en_promocion"),
            (),
            "Indica si la venta se produjo bajo promoción.",
        ),
    ),
)

INVENTORY_CONTRACT = DatasetContract(
    key="inventory",
    filename="inventario.csv",
    title="Inventario",
    purpose="Calcular cobertura, riesgos de rotura, sobrestock y capital expuesto.",
    columns=(
        ColumnContract(
            "snapshot_date",
            "Fecha de inventario",
            ValueType.DATE,
            ("date", "fecha", "inventory_date"),
            (BusinessModule.INVENTORY,),
            "Fecha a la que corresponde el stock registrado.",
        ),
        ColumnContract(
            "product_id",
            "Producto o servicio",
            ValueType.TEXT,
            ("sku", "item_id", "product", "producto", "codigo_producto"),
            (BusinessModule.INVENTORY,),
            "Identificador estable, igual al usado en ventas.",
        ),
        ColumnContract(
            "on_hand_units",
            "Stock disponible",
            ValueType.NUMBER,
            ("stock", "stock_actual", "units_on_hand", "inventory_units"),
            (BusinessModule.INVENTORY,),
            "Unidades disponibles al cierre de la fecha de inventario.",
        ),
        ColumnContract(
            "unit_cost",
            "Coste unitario",
            ValueType.NUMBER,
            ("cost", "coste", "coste_unitario", "purchase_cost"),
            (BusinessModule.PROFITABILITY,),
            "Coste unitario de adquisición o producción.",
        ),
        ColumnContract(
            "reorder_lead_days",
            "Plazo de reposición",
            ValueType.NUMBER,
            ("lead_time_days", "dias_reposicion", "plazo_entrega"),
            (),
            "Días habituales desde el pedido hasta la recepción.",
        ),
        ColumnContract(
            "minimum_stock",
            "Stock mínimo",
            ValueType.NUMBER,
            ("min_stock", "safety_stock", "stock_seguridad"),
            (),
            "Nivel mínimo definido por la empresa.",
        ),
        ColumnContract(
            "store_id",
            "Centro, tienda o almacén",
            ValueType.TEXT,
            ("store", "store_id", "tienda", "centro", "warehouse"),
            (),
            "Ubicación física o lógica del inventario.",
        ),
        ColumnContract(
            "expiry_date",
            "Fecha de caducidad",
            ValueType.DATE,
            ("expiry", "expiration_date", "fecha_caducidad"),
            (BusinessModule.PERISHABLES,),
            "Campo opcional que activa análisis específico de perecederos.",
        ),
    ),
)

COSTS_CONTRACT = DatasetContract(
    key="costs",
    filename="costes.csv",
    title="Costes y precios",
    purpose="Completar los cálculos de margen y la simulación de escenarios.",
    columns=(
        ColumnContract(
            "effective_date",
            "Fecha de vigencia",
            ValueType.DATE,
            ("date", "fecha", "valid_from"),
            (),
            "Fecha desde la que aplica el precio o coste.",
        ),
        ColumnContract(
            "product_id",
            "Producto o servicio",
            ValueType.TEXT,
            ("sku", "item_id", "product", "producto", "codigo_producto"),
            (BusinessModule.PROFITABILITY,),
            "Identificador estable, igual al usado en ventas o inventario.",
        ),
        ColumnContract(
            "unit_cost",
            "Coste unitario",
            ValueType.NUMBER,
            ("cost", "coste", "coste_unitario", "purchase_cost"),
            (BusinessModule.PROFITABILITY,),
            "Coste de adquisición o producción por unidad.",
        ),
        ColumnContract(
            "unit_price",
            "Precio unitario",
            ValueType.NUMBER,
            ("price", "precio", "precio_unitario"),
            (BusinessModule.PROFITABILITY,),
            "Precio de venta por unidad sin impuestos si está disponible.",
        ),
        ColumnContract(
            "holding_cost_per_unit_day",
            "Coste diario de almacenamiento",
            ValueType.NUMBER,
            ("holding_cost", "storage_cost", "coste_almacenamiento"),
            (),
            "Coste diario estimado de mantener una unidad en inventario.",
        ),
    ),
)

SUPPLIERS_CONTRACT = DatasetContract(
    key="suppliers",
    filename="proveedores.csv",
    title="Proveedores",
    purpose="Analizar reposición, coste de compra y dependencia de proveedores.",
    columns=(
        ColumnContract(
            "supplier_id",
            "Proveedor",
            ValueType.TEXT,
            ("supplier", "proveedor", "supplier_code"),
            (BusinessModule.SUPPLIERS,),
            "Identificador estable del proveedor.",
        ),
        ColumnContract(
            "product_id",
            "Producto o servicio",
            ValueType.TEXT,
            ("sku", "item_id", "product", "producto", "codigo_producto"),
            (BusinessModule.SUPPLIERS,),
            "Producto suministrado.",
        ),
        ColumnContract(
            "lead_time_days",
            "Plazo de entrega",
            ValueType.NUMBER,
            ("lead_time", "dias_reposicion", "plazo_entrega"),
            (BusinessModule.SUPPLIERS,),
            "Días habituales desde el pedido hasta la recepción.",
        ),
        ColumnContract(
            "minimum_order_quantity",
            "Pedido mínimo",
            ValueType.NUMBER,
            ("moq", "pedido_minimo", "minimum_order"),
            (),
            "Cantidad mínima aceptada por el proveedor.",
        ),
        ColumnContract(
            "purchase_unit_cost",
            "Coste de compra unitario",
            ValueType.NUMBER,
            ("purchase_cost", "coste_compra", "unit_cost"),
            (),
            "Coste de compra pactado con el proveedor.",
        ),
    ),
)

LOTS_CONTRACT = DatasetContract(
    key="lots",
    filename="lotes.csv",
    title="Lotes y caducidades",
    purpose="Priorizar inventario con fecha límite usando ventas históricas por producto.",
    columns=(
        ColumnContract(
            "lot_id",
            "Identificador de lote",
            ValueType.TEXT,
            ("batch_id", "lote", "lote_id", "batch"),
            (BusinessModule.PERISHABLES,),
            "Identificador único del lote o partida.",
        ),
        ColumnContract(
            "product_id",
            "Producto",
            ValueType.TEXT,
            ("sku", "item_id", "product", "producto", "codigo_producto"),
            (BusinessModule.PERISHABLES,),
            "Identificador del producto, igual al usado en ventas.",
        ),
        ColumnContract(
            "stock_available",
            "Stock disponible",
            ValueType.NUMBER,
            ("stock", "stock_disponible", "on_hand_units", "unidades_disponibles"),
            (BusinessModule.PERISHABLES,),
            "Unidades actualmente disponibles dentro del lote.",
        ),
        ColumnContract(
            "expiry_date",
            "Fecha de caducidad o límite",
            ValueType.DATE,
            ("expiry", "expiration_date", "fecha_caducidad", "fecha_limite"),
            (BusinessModule.PERISHABLES,),
            "Fecha límite de venta, uso o consumo.",
        ),
        ColumnContract(
            "unit_cost",
            "Coste unitario",
            ValueType.NUMBER,
            ("cost", "coste", "coste_unitario", "purchase_cost"),
            (BusinessModule.PERISHABLES,),
            "Coste de adquisición o producción por unidad.",
        ),
        ColumnContract(
            "store_id",
            "Centro, tienda o almacén",
            ValueType.TEXT,
            ("store", "store_id", "tienda", "centro", "warehouse"),
            (),
            "Centro en el que se encuentra el lote.",
        ),
    ),
)

DATASET_CONTRACTS = (SALES_CONTRACT, INVENTORY_CONTRACT, COSTS_CONTRACT, SUPPLIERS_CONTRACT, LOTS_CONTRACT)


def get_contract(key: str) -> DatasetContract:
    """Return a contract by key or raise a clear error for an unsupported dataset."""
    for contract in DATASET_CONTRACTS:
        if contract.key == key:
            return contract
    supported = ", ".join(contract.key for contract in DATASET_CONTRACTS)
    raise ValueError(f"Dataset '{key}' is not supported. Supported datasets: {supported}.")
