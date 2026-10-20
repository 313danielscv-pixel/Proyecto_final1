from src.recommendations import estimated_value_at_risk, recommend_action


def test_critical_expiring_lot_is_routed_to_donation() -> None:
    recommendation = recommend_action(0.90, 0)

    assert recommendation.action == "Preparar donación o retirada segura"
    assert recommendation.discount_pct == 0


def test_high_risk_lot_gets_liquidation_discount() -> None:
    recommendation = recommend_action(0.90, 2)

    assert recommendation.discount_pct == 50


def test_exposure_and_recovery_are_consistent() -> None:
    recommendation = recommend_action(0.70, 1)
    exposed, recovered = estimated_value_at_risk(0.70, 10, 2.0, recommendation)

    assert exposed == 14.0
    assert 0 < recovered < exposed
