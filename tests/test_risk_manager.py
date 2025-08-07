import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import RiskManager


def test_risk_manager_initialization():
    """Test that RiskManager initializes with correct default values."""
    rm = RiskManager()
    assert rm.max_portfolio_risk == 0.02
    assert rm.max_position_risk == 0.01
    assert rm.max_positions == 5


def test_position_size_calculation():
    """Test Kelly Criterion position size calculation."""
    rm = RiskManager()

    size = rm.calculate_position_size_kelly(
        win_rate=0.6, avg_win=100, avg_loss=50, confidence=70, capital=10000
    )

    assert size > 0
    assert size < 10000 * 0.25  # Should not exceed 25% of capital


def test_risk_limits():
    """Test risk limit checking functionality."""
    rm = RiskManager()

    approved, message = rm.check_risk_limits(
        symbol="TEST", position_size=500, current_positions={}, account_value=10000
    )

    assert approved == True
    assert message == "Risk check passed"


def test_stop_loss_calculation():
    """Test stop loss calculation methods."""
    rm = RiskManager()

    # Test fixed stop loss
    stop_loss = rm.calculate_stop_loss("TEST", 100.0, method="fixed")
    assert stop_loss == 97.0  # 3% below entry

    # Test that stop loss is below entry price
    assert stop_loss < 100.0


def test_take_profit_calculation():
    """Test take profit calculation."""
    rm = RiskManager()

    stop_loss = 97.0
    take_profit = rm.calculate_take_profit("TEST", 100.0, stop_loss, risk_reward_ratio=2)

    # With 3% risk and 2:1 ratio, take profit should be 6% above entry
    assert take_profit == 106.0


if __name__ == "__main__":
    # Run tests manually if executed directly
    test_risk_manager_initialization()
    test_position_size_calculation()
    test_risk_limits()
    test_stop_loss_calculation()
    test_take_profit_calculation()
    print("✅ All tests passed!")