"""
Comprehensive Priority 1 test cases for Position - Critical Position Management Functions.
Tests focus on the most financially sensitive position operations that could cause real losses if they malfunction.
"""
import time
import pytest
from unittest.mock import Mock
from typing import Dict, Any

from tests.utils.base_test import UnitTestCase
from core.engine.position_manager import Position


class TestPosition(UnitTestCase):
    """Test cases for Position critical functionality."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.base_time = time.time()

    def test_update_unrealized_pnl_long_position_profit(self):
        """Test unrealized P&L update for long position showing profit."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0,
            strategy="test_strategy"
        )

        # Act
        position.update_unrealized_pnl(current_price=55000.0)  # 10% profit

        # Assert
        assert position.unrealized_pnl == 5000.0  # (55000 - 50000) * 1.0
        assert position.total_pnl == 5000.0
        assert position.pnl_percentage == 10.0  # 10% profit
        assert position.is_profitable is True
        assert position.update_count == 1

    def test_update_unrealized_pnl_long_position_loss(self):
        """Test unrealized P&L update for long position showing loss."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0,
            strategy="test_strategy"
        )

        # Act
        position.update_unrealized_pnl(current_price=45000.0)  # 10% loss

        # Assert
        assert position.unrealized_pnl == -5000.0  # (45000 - 50000) * 1.0
        assert position.total_pnl == -5000.0
        assert position.pnl_percentage == -10.0  # 10% loss
        assert position.is_profitable is False

    def test_update_unrealized_pnl_short_position_profit(self):
        """Test unrealized P&L update for short position showing profit."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=-1.0,  # Short position
            avg_entry_price=50000.0,
            strategy="test_strategy"
        )

        # Act
        position.update_unrealized_pnl(current_price=45000.0)  # Price decreased, short profits

        # Assert
        assert position.unrealized_pnl == 5000.0  # (50000 - 45000) * 1.0
        assert position.total_pnl == 5000.0
        assert position.pnl_percentage == 10.0  # 10% profit
        assert position.is_profitable is True
        assert position.is_short is True

    def test_update_unrealized_pnl_short_position_loss(self):
        """Test unrealized P&L update for short position showing loss."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=-1.0,  # Short position
            avg_entry_price=50000.0,
            strategy="test_strategy"
        )

        # Act
        position.update_unrealized_pnl(current_price=55000.0)  # Price increased, short loses

        # Assert
        assert position.unrealized_pnl == -5000.0  # (50000 - 55000) * 1.0
        assert position.total_pnl == -5000.0
        assert position.pnl_percentage == -10.0  # 10% loss
        assert position.is_profitable is False
        assert position.is_short is True

    def test_should_trigger_stop_loss_hit(self):
        """Test stop loss trigger at exact price."""
        # Arrange - Long position with stop loss
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0,
            stop_loss=45000.0
        )

        # Act & Assert - Test at stop loss price
        assert position.should_trigger_stop_loss(45000.0) is True

        # Test below stop loss (should trigger)
        assert position.should_trigger_stop_loss(44000.0) is True

        # Test above stop loss (should not trigger)
        assert position.should_trigger_stop_loss(46000.0) is False

    def test_should_trigger_stop_loss_not_hit(self):
        """Test stop loss not triggered when price is above stop level."""
        # Arrange - Long position with high stop loss
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0,
            stop_loss=30000.0  # Low stop loss
        )

        # Act & Assert - Current price well above stop loss
        assert position.should_trigger_stop_loss(45000.0) is False

    def test_should_trigger_stop_loss_trailing(self):
        """Test trailing stop loss trigger."""
        # Arrange - Short position with trailing stop
        position = Position(
            symbol="BTC",
            quantity=-1.0,  # Short position
            avg_entry_price=50000.0,
            stop_loss=55000.0  # Trailing stop above entry
        )
        position.add_tag("trailing_stop", "true")

        # Act & Assert - Test trailing stop behavior
        # For short position, stop loss triggers when price goes ABOVE stop level
        assert position.should_trigger_stop_loss(56000.0) is True  # Above stop loss
        assert position.should_trigger_stop_loss(54000.0) is False  # Below stop loss

    def test_should_trigger_take_profit_hit(self):
        """Test take profit trigger at exact price."""
        # Arrange - Long position with take profit
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0,
            take_profit=55000.0
        )

        # Act & Assert - Test at take profit price
        assert position.should_trigger_take_profit(55000.0) is True

        # Test above take profit (should trigger)
        assert position.should_trigger_take_profit(56000.0) is True

        # Test below take profit (should not trigger)
        assert position.should_trigger_take_profit(54000.0) is False

    def test_should_trigger_take_profit_not_hit(self):
        """Test take profit not triggered when price is below target."""
        # Arrange - Long position with high take profit
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0,
            take_profit=70000.0  # High take profit target
        )

        # Act & Assert - Current price below take profit
        assert position.should_trigger_take_profit(60000.0) is False

    def test_set_stop_loss_fixed_price(self):
        """Test fixed price stop loss setting."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0
        )

        # Act
        position.set_stop_loss(45000.0, use_trailing=False)

        # Assert
        assert position.stop_loss == 45000.0
        assert position.get_tag("trailing_stop") == ""  # Should be empty for fixed stop

    def test_set_stop_loss_trailing_stop(self):
        """Test trailing stop loss setting."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0
        )

        # Act
        position.set_stop_loss(45000.0, use_trailing=True)

        # Assert
        assert position.stop_loss == 45000.0
        assert position.get_tag("trailing_stop") == "true"

    def test_set_take_profit_fixed_price(self):
        """Test fixed price take profit setting."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0
        )

        # Act
        position.set_take_profit(55000.0)

        # Assert
        assert position.take_profit == 55000.0

    def test_position_tagging_metadata(self):
        """Test position metadata tagging functionality."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0
        )

        # Act - Add multiple tags
        position.add_tag("strategy", "momentum")
        position.add_tag("timeframe", "1h")
        position.add_tag("entry_signal", "breakout")

        # Assert
        assert position.get_tag("strategy") == "momentum"
        assert position.get_tag("timeframe") == "1h"
        assert position.get_tag("entry_signal") == "breakout"
        assert position.get_tag("nonexistent", "default") == "default"

    def test_position_tags_retrieval(self):
        """Test position tag retrieval with defaults."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0,
            tags={"initial_tag": "initial_value"}
        )

        # Act & Assert - Test tag retrieval
        assert position.get_tag("initial_tag") == "initial_value"
        assert position.get_tag("missing_tag") == ""  # Default empty string
        assert position.get_tag("missing_tag", "custom_default") == "custom_default"

    def test_position_properties_calculations(self):
        """Test position property calculations."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=2.5,
            avg_entry_price=40000.0,
            unrealized_pnl=2500.0,
            realized_pnl=1000.0
        )

        # Act & Assert - Test all properties
        assert position.market_value == 100000.0  # 2.5 * 40000
        assert position.total_pnl == 3500.0  # 2500 + 1000
        assert position.pnl_percentage == 3.5  # (3500 / 100000) * 100
        assert position.is_long is True
        assert position.is_short is False
        assert position.is_profitable is True

    def test_position_with_zero_quantity(self):
        """Test position behavior with zero quantity."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=0.0,
            avg_entry_price=50000.0
        )

        # Act
        position.update_unrealized_pnl(55000.0)

        # Assert
        assert position.quantity == 0.0
        assert position.unrealized_pnl == 0.0
        assert position.market_value == 0.0
        assert position.is_long is False
        assert position.is_short is False

    def test_position_extreme_values(self):
        """Test position handling of extreme price values."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0
        )

        # Act - Test with extreme price values
        extreme_prices = [1e-8, 1e8, float('inf'), 0.0]

        for price in extreme_prices:
            if price == float('inf'):
                continue  # Skip infinity for now

            position.update_unrealized_pnl(price)

            # Assert - Should handle gracefully without exceptions
            assert isinstance(position.unrealized_pnl, (int, float))
            assert isinstance(position.pnl_percentage, (int, float))

    def test_position_update_tracking(self):
        """Test position update tracking functionality."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0
        )

        # Act - Multiple updates
        position.update_unrealized_pnl(51000.0)
        position.update_unrealized_pnl(52000.0)
        position.update_unrealized_pnl(53000.0)

        # Assert
        assert position.update_count == 3
        assert position.last_update > position.opened_at

    def test_position_to_dict_serialization(self):
        """Test position serialization to dictionary."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0,
            strategy="test_strategy",
            unrealized_pnl=1000.0,
            realized_pnl=500.0,
            stop_loss=45000.0,
            take_profit=55000.0,
            opened_at=self.base_time,
            tags={"tag1": "value1", "tag2": "value2"}
        )

        # Act
        position_dict = position.to_dict()

        # Assert
        required_fields = [
            'symbol', 'quantity', 'avg_entry_price', 'strategy',
            'unrealized_pnl', 'realized_pnl', 'total_pnl', 'pnl_percentage',
            'market_value', 'risk_amount', 'stop_loss', 'take_profit',
            'opened_at', 'last_update', 'update_count', 'tags',
            'is_long', 'is_short', 'is_profitable'
        ]

        for field in required_fields:
            assert field in position_dict

        assert position_dict['symbol'] == "BTC"
        assert position_dict['quantity'] == 1.0
        assert position_dict['total_pnl'] == 1500.0  # 1000 + 500
        assert position_dict['is_long'] is True
        assert position_dict['tags'] == {"tag1": "value1", "tag2": "value2"}

    def test_position_string_representation(self):
        """Test position string representation."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=1.5,
            avg_entry_price=50000.0
        )

        # Act
        position_str = str(position)

        # Assert
        assert "Position(BTC" in position_str
        assert "LONG" in position_str
        assert "1.5" in position_str
        assert "50000.0" in position_str

    def test_position_risk_amount_calculation(self):
        """Test position risk amount calculation."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=2.0,
            avg_entry_price=50000.0
        )

        # Act
        risk_amount = position.risk_amount

        # Assert - Risk amount should be position value * default risk per trade (2%)
        expected_risk = 100000.0 * 0.02  # 2% of $100k position
        assert abs(risk_amount - expected_risk) < 0.01

    def test_position_with_realized_pnl_only(self):
        """Test position with only realized P&L (closed position)."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=0.0,  # Closed position
            avg_entry_price=50000.0,
            realized_pnl=2500.0,
            unrealized_pnl=0.0
        )

        # Act - Update with current price (shouldn't change anything for closed position)
        position.update_unrealized_pnl(55000.0)

        # Assert
        assert position.quantity == 0.0
        assert position.unrealized_pnl == 0.0
        assert position.realized_pnl == 2500.0
        assert position.total_pnl == 2500.0
        assert position.market_value == 0.0

    def test_position_multiple_pnl_updates(self):
        """Test multiple P&L updates accumulate correctly."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0,
            realized_pnl=1000.0  # Start with some realized P&L
        )

        # Act - Multiple price updates
        position.update_unrealized_pnl(51000.0)  # +1000 unrealized
        position.update_unrealized_pnl(52000.0)  # +2000 unrealized (cumulative)
        position.update_unrealized_pnl(50000.0)  # 0 unrealized

        # Assert
        assert position.realized_pnl == 1000.0  # Unchanged
        assert position.unrealized_pnl == 0.0   # Back to entry price
        assert position.total_pnl == 1000.0    # Only realized P&L

    def test_position_negative_quantity_short_position(self):
        """Test position with negative quantity represents short position."""
        # Arrange
        position = Position(
            symbol="BTC",
            quantity=-0.5,
            avg_entry_price=50000.0
        )

        # Act - Update P&L
        position.update_unrealized_pnl(48000.0)  # Price decreased

        # Assert
        assert position.is_short is True
        assert position.is_long is False
        assert position.unrealized_pnl == 1000.0  # (50000 - 48000) * 0.5 = 1000 profit
        assert position.quantity == -0.5  # Remains negative

    def test_position_with_custom_opened_at(self):
        """Test position with custom opening timestamp."""
        # Arrange
        custom_time = time.time() - 3600  # 1 hour ago

        # Act
        position = Position(
            symbol="BTC",
            quantity=1.0,
            avg_entry_price=50000.0,
            opened_at=custom_time
        )

        # Assert
        assert position.opened_at == custom_time
        assert position.last_update >= custom_time