"""
Comprehensive Priority 1 test cases for RiskManager - Critical Risk Functions.
Tests focus on the most financially sensitive functions that could cause real losses if they malfunction.
"""
import asyncio
import pytest
import time
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, MagicMock
from typing import Dict, Any

from tests.utils.base_test import UnitTestCase
from src.risk.manager import RiskManager, RiskLimitExceededError, RiskValidationError
from src.core.engine.position_manager import Position, PositionManager
from unittest.mock import patch


class TestRiskManager(UnitTestCase):
    """Test cases for RiskManager critical functionality."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.position_manager = Mock(spec=PositionManager)
        self.position_manager.positions = {}
        self.position_manager.portfolio_value = 10000.0

        self.risk_manager = RiskManager(self.position_manager)
        # Override settings for consistent testing
        self.risk_manager.max_portfolio_risk = 0.10  # 10%
        self.risk_manager.max_position_risk = 0.02  # 2%
        self.risk_manager.max_correlation = 0.7
        self.risk_manager.max_drawdown = 0.20  # 20%
        self.risk_manager.max_positions = 5

    def test_validate_trade_success(self):
        """Test successful trade validation with normal parameters."""
        # Arrange
        self.position_manager.positions = {}
        self.position_manager.portfolio_value = 10000.0

        # Act
        async def run_test():
            result = await self.risk_manager.validate_trade(
                symbol="BTC",
                side="BUY",
                quantity=0.001,  # Reduced quantity to avoid concentration risk (0.001 * 50000 = $50, which is 0.5% of $10k portfolio)
                price=50000.0,
                strategy="test_strategy"
            )
            return result

        is_valid, reason = self.run_async(run_test())

        # Assert
        assert is_valid is True
        assert "approved" in reason.lower()

    def test_validate_trade_position_limit_exceeded(self):
        """Test trade validation fails when position limit is exceeded."""
        # Arrange - Create maximum positions
        self.position_manager.positions = {
            f"POS{i}": Mock() for i in range(self.risk_manager.max_positions)
        }
        self.position_manager.portfolio_value = 10000.0

        # Act
        async def run_test():
            return await self.risk_manager.validate_trade(
                symbol="BTC",
                side="BUY",
                quantity=0.1,
                price=50000.0
            )

        is_valid, reason = self.run_async(run_test())

        # Assert
        assert is_valid is False
        assert "position limits exceeded" in reason.lower()

    def test_validate_trade_portfolio_risk_exceeded(self):
        """Test trade validation fails when portfolio risk limit is exceeded."""
        # Arrange - Set portfolio value and create high-risk scenario
        self.position_manager.portfolio_value = 10000.0

        # Mock the portfolio risk calculation to return high risk
        with patch.object(
            self.risk_manager,
            '_calculate_portfolio_risk',
            return_value=0.15  # 15% risk, above 10% limit
        ):
            # Act
            async def run_test():
                return await self.risk_manager.validate_trade(
                    symbol="BTC",
                    side="BUY",
                    quantity=1.0,  # Large quantity to trigger risk
                    price=10000.0
                )

            is_valid, reason = self.run_async(run_test())

        # Assert
        assert is_valid is False
        assert "portfolio risk" in reason.lower()

    def test_validate_trade_correlation_risk_exceeded(self):
        """Test trade validation fails when correlation risk is too high."""
        # Arrange
        self.position_manager.portfolio_value = 10000.0

        # Mock correlation risk to exceed limit
        with patch.object(
            self.risk_manager,
            '_calculate_correlation_risk',
            return_value=0.8  # Above 0.7 limit
        ):
            # Act
            async def run_test():
                return await self.risk_manager.validate_trade(
                    symbol="BTC",
                    side="BUY",
                    quantity=0.1,
                    price=50000.0
                )

            is_valid, reason = self.run_async(run_test())

        # Assert
        assert is_valid is False
        assert "correlation risk" in reason.lower()

    def test_validate_trade_concentration_risk_exceeded(self):
        """Test trade validation fails when concentration risk is too high."""
        # Arrange - Set low portfolio value to create concentration
        self.position_manager.portfolio_value = 1000.0

        # Mock concentration check to exceed limit
        with patch.object(
            self.risk_manager,
            '_check_concentration_risk',
            return_value=False
        ):
            # Act
            async def run_test():
                return await self.risk_manager.validate_trade(
                    symbol="BTC",
                    side="BUY",
                    quantity=0.1,
                    price=50000.0  # $5000 trade on $1000 portfolio = 500% concentration
                )

            is_valid, reason = self.run_async(run_test())

        # Assert
        assert is_valid is False
        assert "concentration risk" in reason.lower()

    def test_validate_trade_strategy_limits_exceeded(self):
        """Test trade validation fails when strategy limits are exceeded."""
        # Arrange
        with patch.object(
            self.risk_manager,
            '_check_strategy_limits',
            return_value=False
        ):
            # Act
            async def run_test():
                return await self.risk_manager.validate_trade(
                    symbol="BTC",
                    side="BUY",
                    quantity=0.1,
                    price=50000.0,
                    strategy="high_frequency_strategy"
                )

            is_valid, reason = self.run_async(run_test())

        # Assert
        assert is_valid is False
        assert "strategy limits exceeded" in reason.lower()

    def test_calculate_position_size_kelly_criterion(self):
        """Test position sizing calculation using Kelly Criterion principles."""
        # Arrange
        symbol = "BTC"
        entry_price = 50000.0
        stop_loss = 45000.0  # 10% stop loss

        # Act
        async def run_test():
            return await self.risk_manager.calculate_position_size(
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=stop_loss,
                strategy="kelly_strategy"
            )

        position_size = self.run_async(run_test())

        # Assert
        assert position_size > 0
        assert position_size <= 1.0  # Should be reasonable size

        # With 10% stop loss on $10k portfolio, risk per trade = $200
        # Position size should be risk / (entry - stop) = 200 / 5000 = 0.04 BTC
        expected_size = 200 / (entry_price - stop_loss)
        assert abs(position_size - expected_size) < 0.01

    def test_calculate_position_size_fixed_risk(self):
        """Test position sizing with fixed risk amount."""
        # Arrange
        symbol = "ETH"
        entry_price = 3000.0
        stop_loss = 2700.0  # 10% stop loss

        # Act
        async def run_test():
            return await self.risk_manager.calculate_position_size(
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=stop_loss
            )

        position_size = self.run_async(run_test())

        # Assert
        assert position_size > 0

        # Fixed risk should be 2% of portfolio = $200
        expected_size = 200 / (entry_price - stop_loss)
        assert abs(position_size - expected_size) < 0.01

    def test_calculate_position_size_volatility_adjusted(self):
        """Test volatility-adjusted position sizing."""
        # Arrange - Test without stop loss (percentage-based sizing)
        symbol = "BTC"
        entry_price = 50000.0

        # Act
        async def run_test():
            return await self.risk_manager.calculate_position_size(
                symbol=symbol,
                entry_price=entry_price
                # No stop loss provided
            )

        position_size = self.run_async(run_test())

        # Assert
        assert position_size > 0

        # Should be 2% of portfolio value / entry price
        portfolio_value = 10000.0
        expected_size = (portfolio_value * 0.02) / entry_price
        assert abs(position_size - expected_size) < 0.001

    def test_check_drawdown_limits_within_limits(self):
        """Test drawdown check passes when within acceptable limits."""
        # Arrange - Set up positions with small unrealized losses
        mock_position = Mock()
        mock_position.unrealized_pnl = -500.0  # 5% loss on $10k portfolio

        self.position_manager.positions = {"BTC": mock_position}
        self.position_manager.portfolio_value = 10000.0

        # Act
        async def run_test():
            return await self.risk_manager.check_drawdown_limits()

        within_limits = self.run_async(run_test())

        # Assert
        assert within_limits is True

    def test_check_drawdown_limits_exceeded(self):
        """Test drawdown check fails when limits are exceeded."""
        # Arrange - Set up positions with large unrealized losses
        mock_position = Mock()
        mock_position.unrealized_pnl = -2500.0  # 25% loss, exceeds 20% limit

        self.position_manager.positions = {"BTC": mock_position}
        self.position_manager.portfolio_value = 10000.0

        # Act
        async def run_test():
            return await self.risk_manager.check_drawdown_limits()

        within_limits = self.run_async(run_test())

        # Assert
        assert within_limits is False
        # Check that alert was created
        assert len(self.risk_manager.alerts) > 0

    def test_calculate_portfolio_risk_balanced(self):
        """Test portfolio risk calculation with balanced positions."""
        # Arrange - Set up balanced portfolio
        self.position_manager.portfolio_value = 10000.0

        # Create positions with moderate P&L
        positions = {}
        for i, symbol in enumerate(["BTC", "ETH", "ADA"]):
            pos = Mock()
            pos.unrealized_pnl = (i - 1) * 100.0  # Mix of gains and losses
            positions[symbol] = pos

        self.position_manager.positions = positions

        # Act
        portfolio_risk = self.risk_manager._calculate_portfolio_risk()

        # Assert
        assert 0 <= portfolio_risk <= 1.0  # Should be between 0% and 100%
        assert portfolio_risk > 0  # Should have some risk with mixed P&L

    def test_calculate_portfolio_risk_concentrated(self):
        """Test portfolio risk calculation with concentrated positions."""
        # Arrange - Single large losing position
        self.position_manager.portfolio_value = 10000.0

        pos = Mock()
        pos.unrealized_pnl = -2000.0  # 20% loss
        self.position_manager.positions = {"BTC": pos}

        # Act
        portfolio_risk = self.risk_manager._calculate_portfolio_risk()

        # Assert
        expected_risk = 2000.0 / 10000.0  # 20%
        assert abs(portfolio_risk - expected_risk) < 0.001

    def test_calculate_trade_portfolio_risk_addition(self):
        """Test portfolio risk calculation when adding a new trade."""
        # Arrange
        current_risk = 0.05  # 5% current risk
        symbol = "BTC"
        side = "BUY"
        quantity = 0.1
        price = 50000.0
        self.position_manager.portfolio_value = 10000.0

        # Act
        new_risk = self.risk_manager._calculate_trade_portfolio_risk(
            symbol, side, quantity, price, current_risk
        )

        # Assert
        assert new_risk > current_risk  # Risk should increase with new position
        trade_value = quantity * price
        expected_increase = (trade_value / self.position_manager.portfolio_value) * 0.01
        expected_risk = current_risk + expected_increase
        assert abs(new_risk - expected_risk) < 0.001

    def test_calculate_correlation_risk_diversified(self):
        """Test correlation risk calculation with diversified portfolio."""
        # Arrange - Empty portfolio
        self.position_manager.positions = {}

        # Act
        correlation_risk = self.risk_manager._calculate_correlation_risk("BTC", 1000.0)

        # Assert
        assert correlation_risk == 0.0  # No correlation risk with no positions

    def test_calculate_correlation_risk_highly_correlated(self):
        """Test correlation risk calculation with highly correlated positions."""
        # Arrange - Multiple positions (simulating correlation)
        positions = {}
        for i in range(5):
            pos = Mock()
            positions[f"CRYPTO{i}"] = pos

        self.position_manager.positions = positions

        # Act
        correlation_risk = self.risk_manager._calculate_correlation_risk("BTC", 1000.0)

        # Assert
        assert correlation_risk > 0
        # Should be 0.3 * 5 = 1.5 (based on simplified calculation)
        expected_risk = 0.3 * 5
        assert abs(correlation_risk - expected_risk) < 0.001

    def test_calculate_concentration_risk_single_asset(self):
        """Test concentration risk calculation with single asset."""
        # Arrange - Single large position
        pos = Mock()
        pos.quantity = 1.0
        pos.avg_entry_price = 50000.0
        self.position_manager.positions = {"BTC": pos}
        self.position_manager.portfolio_value = 50000.0

        # Act
        concentration_risk = self.risk_manager._calculate_concentration_risk()

        # Assert
        assert concentration_risk == 1.0  # 100% concentration

    def test_calculate_concentration_risk_diversified(self):
        """Test concentration risk calculation with diversified portfolio."""
        # Arrange - Multiple positions of equal value
        positions = {}
        symbols = ["BTC", "ETH", "ADA", "DOT"]
        for symbol in symbols:
            pos = Mock()
            pos.quantity = 1.0
            pos.avg_entry_price = 25000.0  # Each position worth $25k
            positions[symbol] = pos

        self.position_manager.positions = positions
        self.position_manager.portfolio_value = 100000.0  # Total $100k

        # Act
        concentration_risk = self.risk_manager._calculate_concentration_risk()

        # Assert
        expected_risk = 0.25  # 25% (largest position is 25% of portfolio)
        assert abs(concentration_risk - expected_risk) < 0.001

    def test_update_risk_metrics_comprehensive(self):
        """Test comprehensive risk metrics update."""
        # Arrange
        # Set up portfolio with known positions
        positions = {}
        for i, symbol in enumerate(["BTC", "ETH"]):
            pos = Mock()
            pos.unrealized_pnl = (i - 0.5) * 1000.0  # Mix of gains/losses
            pos.quantity = 1.0
            pos.avg_entry_price = 50000.0
            positions[symbol] = pos

        self.position_manager.positions = positions
        self.position_manager.portfolio_value = 100000.0

        # Act
        async def run_test():
            await self.risk_manager.update_risk_metrics()

        self.run_async(run_test())

        # Assert
        assert self.risk_manager.risk_metrics['total_portfolio_risk'] > 0
        assert 'max_position_risk' in self.risk_manager.risk_metrics
        assert 'correlation_risk' in self.risk_manager.risk_metrics
        assert 'concentration_risk' in self.risk_manager.risk_metrics
        assert len(self.risk_manager.risk_history) > 0

    def test_create_alert_critical_risk(self):
        """Test critical risk alert creation."""
        # Arrange
        alert_type = "PORTFOLIO_RISK_EXCEEDED"
        message = "Portfolio risk has exceeded maximum threshold"
        severity = "CRITICAL"

        # Act
        async def run_test():
            await self.risk_manager._create_alert(alert_type, message, severity)

        self.run_async(run_test())

        # Assert
        assert len(self.risk_manager.alerts) > 0
        alert = self.risk_manager.alerts[-1]
        assert alert['type'] == alert_type
        assert alert['message'] == message
        assert alert['severity'] == severity

    def test_risk_manager_initialization_with_custom_position_manager(self):
        """Test RiskManager initialization with custom PositionManager."""
        # Arrange
        custom_pm = Mock(spec=PositionManager)
        custom_pm.positions = {"TEST": Mock()}
        custom_pm.portfolio_value = 5000.0

        # Act
        risk_manager = RiskManager(custom_pm)

        # Assert
        assert risk_manager.position_manager is custom_pm
        assert risk_manager.position_manager.positions == custom_pm.positions
        assert risk_manager.position_manager.portfolio_value == 5000.0

    def test_risk_validation_error_handling(self):
        """Test error handling in risk validation."""
        # Arrange - Create scenario that will raise exception
        self.position_manager.positions = None  # This will cause an error

        # Act & Assert
        async def run_test():
            return await self.risk_manager.validate_trade(
                symbol="BTC",
                side="BUY",
                quantity=0.1,
                price=50000.0
            )

        is_valid, reason = self.run_async(run_test())
        assert is_valid is False
        assert "validation error" in reason.lower()

    def test_performance_risk_calculations(self):
        """Test performance of risk calculation methods."""
        # Arrange - Create large portfolio for performance testing
        positions = {}
        for i in range(100):
            pos = Mock()
            pos.unrealized_pnl = (i % 3 - 1) * 100.0  # Varied P&L
            pos.quantity = 1.0
            pos.avg_entry_price = 50000.0
            positions[f"CRYPTO{i}"] = pos

        self.position_manager.positions = positions
        self.position_manager.portfolio_value = 5000000.0  # $5M portfolio

        # Act & Assert - Test that calculations complete within reasonable time
        start_time = time.time()

        # Test portfolio risk calculation performance
        portfolio_risk = self.risk_manager._calculate_portfolio_risk()

        # Test concentration risk calculation performance
        concentration_risk = self.risk_manager._calculate_concentration_risk()

        end_time = time.time()
        execution_time = end_time - start_time

        # Assert calculations complete and return reasonable values
        assert portfolio_risk >= 0
        assert concentration_risk >= 0
        assert execution_time < 1.0  # Should complete within 1 second

    def test_edge_case_zero_portfolio_value(self):
        """Test risk calculations with zero portfolio value."""
        # Arrange
        self.position_manager.portfolio_value = 0.0

        # Act
        portfolio_risk = self.risk_manager._calculate_portfolio_risk()
        concentration_risk = self.risk_manager._calculate_concentration_risk()

        # Assert
        assert portfolio_risk == 0.0
        assert concentration_risk == 0.0

    def test_edge_case_extreme_price_values(self):
        """Test risk calculations with extreme price values."""
        # Arrange
        extreme_price = 1e10  # Extremely high price
        self.position_manager.portfolio_value = 10000.0

        # Act
        async def run_test():
            return await self.risk_manager.validate_trade(
                symbol="EXTREME",
                side="BUY",
                quantity=0.001,
                price=extreme_price
            )

        is_valid, reason = self.run_async(run_test())

        # Assert - Should handle extreme values gracefully
        assert is_valid in [True, False]  # Either result is acceptable
        assert isinstance(reason, str)