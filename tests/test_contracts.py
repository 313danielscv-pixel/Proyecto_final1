import csv
from pathlib import Path

import pytest

from src.contracts import (
    DATASET_CONTRACTS,
    BusinessModule,
    INVENTORY_CONTRACT,
    LOTS_CONTRACT,
    SALES_CONTRACT,
    get_contract,
)


ROOT = Path(__file__).resolve().parents[1]


def test_demand_does_not_require_perishable_fields() -> None:
    required_names = {column.name for column in SALES_CONTRACT.required_columns(BusinessModule.DEMAND)}

    assert required_names == {"date", "product_id", "quantity"}
    assert "expiry_date" not in required_names


def test_inventory_requires_core_fields_but_not_expiry() -> None:
    required_names = {column.name for column in INVENTORY_CONTRACT.required_columns(BusinessModule.INVENTORY)}

    assert required_names == {"snapshot_date", "product_id", "on_hand_units"}
    assert "expiry_date" not in required_names


def test_lot_contract_requires_expiry_but_keeps_it_optional_for_inventory() -> None:
    required_names = {column.name for column in LOTS_CONTRACT.required_columns(BusinessModule.PERISHABLES)}

    assert required_names == {"lot_id", "product_id", "stock_available", "expiry_date", "unit_cost"}


@pytest.mark.parametrize("contract", DATASET_CONTRACTS, ids=lambda contract: contract.key)
def test_template_headers_match_contract(contract) -> None:
    template_path = ROOT / "data" / "templates" / contract.filename
    with template_path.open(newline="", encoding="utf-8") as template_file:
        header = next(csv.reader(template_file))

    assert header == [column.name for column in contract.columns]


def test_unknown_contract_has_clear_error() -> None:
    with pytest.raises(ValueError, match="not supported"):
        get_contract("desconocido")
