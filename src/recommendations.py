"""Business action policy for waste-risk predictions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Recommendation:
    """A transparent operational action derived from risk and shelf-life."""

    action: str
    discount_pct: int
    recovery_rate: float
    rationale: str


def recommend_action(probability: float, days_remaining: int) -> Recommendation:
    """Return a conservative action that never recommends a discount after expiry."""
    if days_remaining <= 0 and probability >= 0.75:
        return Recommendation("Preparar donación o retirada segura", 0, 0.35, "Riesgo alto con caducidad hoy.")
    if probability >= 0.85:
        return Recommendation("Aplicar descuento de liquidación", 50, 0.70, "Riesgo crítico; conviene acelerar la salida.")
    if probability >= 0.60:
        return Recommendation("Aplicar descuento de aceleración", 30, 0.55, "Riesgo alto; la ventana de venta es limitada.")
    if probability >= 0.30:
        return Recommendation("Aplicar descuento preventivo", 15, 0.35, "Riesgo medio; se recomienda actuar antes de la caducidad.")
    return Recommendation("Mantener precio y vigilar", 0, 0.10, "Riesgo bajo según el piloto.")


def estimated_value_at_risk(
    probability: float, stock: int, unit_cost: float, recommendation: Recommendation
) -> tuple[float, float]:
    """Estimate exposed cost and recoverable cost; they are scenario estimates, not realised savings."""
    exposed_cost = probability * stock * unit_cost
    recovered_cost = exposed_cost * recommendation.recovery_rate
    return exposed_cost, recovered_cost
