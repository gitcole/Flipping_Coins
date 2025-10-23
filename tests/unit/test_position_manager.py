"""
Comprehensive Priority 1 test cases for PositionManager - Critical Portfolio Management Functions.
Tests focus on the most financially sensitive portfolio operations that could cause real losses if they malfunction.
"""
import time
import json
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from tests.utils.base_test import UnitTestCase
from core.engine.position_manager import Position, PositionManager


class TestPositionManager(UnitTestCase):
    """Test cases for PositionManager critical functionality."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.position_manager = PositionManager()
        self.base_time = time.time()

    def test_calculate_portfolio_risk_empty_portfolio(self):
        """Test portfolio risk calculation with empty portfolio."""
        # Arrange - Empty portfolio
        self.position_manager.positions = {}
        self.position_manager.portfolio_value = 0.0

        # Act
        risk_metrics = self.position_manager.calculate_portfolio_risk()

        # Assert
        assert risk_metrics['total_risk'] == 0.0
        assert risk_metrics['max_position_risk'] == 0.0
        assert risk_metrics['concentration_risk'] == 0.0
        assert risk_metrics['correlation_risk'] == 0.0

    def test_calculate_portfolio_risk_mixed_positions(self):
        """Test portfolio risk calculation with mixed long/short positions."""
        # Arrange - Create positions with varied risk profiles
        positions = {}

        # Long position with profit
        btc_long = Position("BTC", 1.0, 50000.0, unrealized_pnl=5000.0)
        positions["BTC"] = btc_long

        # Short position with loss
        eth_short = Position("ETH", -0.5, 3000.0, unrealized_pnl=-1500.0)
        positions["ETH"] = eth_short

        # Neutral position
        ada_neutral = Position("ADA", 2.0, 1.0, unrealized_pnl=0.0)
        positions["ADA"] = ada_neutral

        self.position_manager.positions = positions
        self.position_manager.portfolio_value = 100000.0

        # Act
        risk_metrics = self.position_manager.calculate_portfolio_risk()

        # Assert
        assert risk_metrics['total_risk'] > 0  # Should have some risk
        assert risk_metrics['max_position_risk'] > 0  # Should have position risk
        assert risk_metrics['concentration_risk'] >= 0  # Valid concentration risk
        assert risk_metrics['correlation_risk'] >= 0  # Valid correlation risk

    def test_calculate_portfolio_risk_highly_correlated(self):
        """Test portfolio risk calculation with highly correlated positions."""
        # Arrange - Multiple similar positions
        positions = {}
        for i in range(5):
            pos = Position(f"BTC{i}", 1.0, 50000.0, unrealized_pnl=1000.0)
            positions[f"BTC{i}"] = pos

        self.position_manager.positions = positions
        self.position_manager.portfolio_value = 250000.0

        # Act
        risk_metrics = self.position_manager.calculate_portfolio_risk()

        # Assert
        assert risk_metrics['total_risk'] > 0
        # With 5 similar positions, correlation risk should be significant
        assert risk_metrics['correlation_risk'] > 0

    def test_check_position_limits_within_limits(self):
        """Test position limits check when within acceptable limits."""
        # Arrange - Set up positions within limits
        positions = {}
        for i in range(3):  # Below max limit of 5
            pos = Position(f"CRYPTO{i}", 1.0, 50000.0)
            positions[f"CRYPTO{i}"] = pos

        self.position_manager.positions = positions
        self.position_manager.portfolio_value = 150000.0

        # Act
        limit_checks = self.position_manager.check_position_limits()

        # Assert
        assert limit_checks['position_count_ok'] is True
        assert limit_checks['portfolio_risk_ok'] is True
        assert limit_checks['symbol_concentration_ok'] is True

    def test_check_position_limits_exceeded(self):
        """Test position limits check when limits are exceeded."""
        # Arrange - Create more positions than limit allows
        with patch.object(self.position_manager.settings, 'trading', max_positions=2):
            positions = {}
            for i in range(3):  # Exceeds limit of 2
                pos = Position(f"CRYPTO{i}", 1.0, 50000.0)
                positions[f"CRYPTO{i}"] = pos

            self.position_manager.positions = positions
            self.position_manager.portfolio_value = 150000.0

            # Act
            limit_checks = self.position_manager.check_position_limits()

        # Assert
        assert limit_checks['position_count_ok'] is False
        assert limit_checks['current_positions'] == 3
        assert limit_checks['max_positions'] == 2

    def test_update_position_prices_single_update(self):
        """Test single position price update."""
        # Arrange
        position = Position("BTC", 1.0, 50000.0, unrealized_pnl=0.0)
        self.position_manager.positions = {"BTC": position}

        # Act
        price_data = {"BTC": 55000.0}
        self.position_manager.update_position_prices(price_data)

        # Assert
        assert position.unrealized_pnl == 5000.0  # (55000 - 50000) * 1.0
        assert position.update_count == 1

    def test_update_position_prices_batch_update(self):
        """Test batch position price updates."""
        # Arrange
        positions = {}
        for symbol, entry_price in [("BTC", 50000.0), ("ETH", 3000.0), ("ADA", 1.0)]:
            pos = Position(symbol, 1.0, entry_price, unrealized_pnl=0.0)
            positions[symbol] = pos

        self.position_manager.positions = positions

        # Act
        price_data = {
            "BTC": 55000.0,
            "ETH": 3300.0,
            "ADA": 1.1
        }
        self.position_manager.update_position_prices(price_data)

        # Assert
        assert positions["BTC"].unrealized_pnl == 5000.0
        assert positions["ETH"].unrealized_pnl == 300.0
        assert positions["ADA"].unrealized_pnl == 0.1

    def test_calculate_drawdown_no_drawdown(self):
        """Test drawdown calculation with no drawdown scenario."""
        # Arrange - All positions profitable
        positions = {}
        for symbol in ["BTC", "ETH"]:
            pos = Position(symbol, 1.0, 50000.0, unrealized_pnl=5000.0)
            positions[symbol] = pos

        self.position_manager.positions = positions
        self.position_manager.portfolio_value = 110000.0

        # Act
        drawdown = self.position_manager.calculate_drawdown()

        # Assert
        assert drawdown['current_drawdown'] == 0.0  # No drawdown with profits
        assert drawdown['max_drawdown'] == 0.0
        assert drawdown['peak_value'] > 0

    def test_calculate_drawdown_peak_to_trough(self):
        """Test drawdown calculation from peak to trough."""
        # Arrange - Mix of profitable and losing positions
        positions = {}
        btc_pos = Position("BTC", 1.0, 50000.0, unrealized_pnl=-10000.0)  # Large loss
        positions["BTC"] = btc_pos

        eth_pos = Position("ETH", 1.0, 3000.0, unrealized_pnl=1000.0)   # Small profit
        positions["ETH"] = eth_pos

        self.position_manager.positions = positions
        self.position_manager.portfolio_value = 76000.0  # Net loss scenario

        # Act
        drawdown = self.position_manager.calculate_drawdown()

        # Assert
        assert drawdown['current_drawdown'] > 0  # Should show drawdown
        assert drawdown['max_drawdown'] >= drawdown['current_drawdown']
        assert drawdown['lowest_value'] > 0

    def test_calculate_drawdown_recovery(self):
        """Test drawdown calculation with partial recovery."""
        # Arrange - Positions showing partial recovery from losses
        positions = {}
        btc_pos = Position("BTC", 1.0, 50000.0, unrealized_pnl=-2000.0)  # Partial recovery
        positions["BTC"] = btc_pos

        self.position_manager.positions = positions
        self.position_manager.portfolio_value = 98000.0

        # Act
        drawdown = self.position_manager.calculate_drawdown()

        # Assert
        assert drawdown['current_drawdown'] > 0  # Still some drawdown
        assert drawdown['max_drawdown'] >= drawdown['current_drawdown']

    def test_add_position_success(self):
        """Test successful position addition."""
        # Arrange
        position = Position("BTC", 1.0, 50000.0, strategy="test_strategy")

        # Act
        self.position_manager.add_position(position)

        # Assert
        assert "BTC" in self.position_manager.positions
        assert self.position_manager.positions["BTC"] is position
        assert self.position_manager.portfolio_value == 50000.0

    def test_remove_position_success(self):
        """Test successful position removal."""
        # Arrange
        position = Position("BTC", 1.0, 50000.0)
        self.position_manager.positions = {"BTC": position}

        # Act
        removed_position = self.position_manager.remove_position("BTC")

        # Assert
        assert removed_position is position
        assert "BTC" not in self.position_manager.positions
        assert position in self.position_manager.closed_positions

    def test_get_position_by_symbol(self):
        """Test position retrieval by symbol."""
        # Arrange
        position = Position("BTC", 1.0, 50000.0)
        self.position_manager.positions = {"BTC": position}

        # Act
        retrieved = self.position_manager.get_position_by_symbol("BTC")

        # Assert
        assert retrieved is position
        assert retrieved.symbol == "BTC"

    def test_get_positions_by_strategy(self):
        """Test positions filtered by strategy."""
        # Arrange
        positions = {}
        btc_pos = Position("BTC", 1.0, 50000.0, strategy="momentum")
        positions["BTC"] = btc_pos

        eth_pos = Position("ETH", 1.0, 3000.0, strategy="momentum")
        positions["ETH"] = eth_pos

        ada_pos = Position("ADA", 1.0, 1.0, strategy="mean_reversion")
        positions["ADA"] = ada_pos

        self.position_manager.positions = positions

        # Act
        momentum_positions = self.position_manager.get_positions_by_strategy("momentum")

        # Assert
        assert len(momentum_positions) == 2
        assert btc_pos in momentum_positions
        assert eth_pos in momentum_positions
        assert ada_pos not in momentum_positions

    def test_get_long_positions(self):
        """Test long position filtering."""
        # Arrange
        positions = {}
        btc_long = Position("BTC", 1.0, 50000.0)  # Long
        positions["BTC"] = btc_long

        eth_short = Position("ETH", -0.5, 3000.0)  # Short
        positions["ETH"] = eth_short

        self.position_manager.positions = positions

        # Act
        long_positions = self.position_manager.get_long_positions()

        # Assert
        assert len(long_positions) == 1
        assert btc_long in long_positions
        assert eth_short not in long_positions

    def test_get_short_positions(self):
        """Test short position filtering."""
        # Arrange
        positions = {}
        btc_long = Position("BTC", 1.0, 50000.0)  # Long
        positions["BTC"] = btc_long

        eth_short = Position("ETH", -0.5, 3000.0)  # Short
        positions["ETH"] = eth_short

        self.position_manager.positions = positions

        # Act
        short_positions = self.position_manager.get_short_positions()

        # Assert
        assert len(short_positions) == 1
        assert eth_short in short_positions
        assert btc_long not in short_positions

    def test_calculate_daily_pnl(self):
        """Test daily P&L calculation."""
        # Arrange
        positions = {}
        btc_pos = Position("BTC", 1.0, 50000.0, unrealized_pnl=1000.0)
        positions["BTC"] = btc_pos

        eth_pos = Position("ETH", 1.0, 3000.0, unrealized_pnl=-500.0)
        positions["ETH"] = eth_pos

        self.position_manager.positions = positions

        # Act
        daily_pnl = self.position_manager.get_daily_pnl()

        # Assert
        assert daily_pnl == 500.0  # 1000 - 500

    def test_calculate_monthly_pnl(self):
        """Test monthly P&L calculation."""
        # Arrange
        positions = {}
        btc_pos = Position("BTC", 1.0, 50000.0, unrealized_pnl=5000.0)
        positions["BTC"] = btc_pos

        self.position_manager.positions = positions

        # Act
        monthly_pnl = self.position_manager.get_monthly_pnl()

        # Assert
        assert monthly_pnl == 5000.0

    def test_export_positions_json(self):
        """Test position data export to JSON-serializable format."""
        # Arrange
        positions = {}
        btc_pos = Position("BTC", 1.0, 50000.0, strategy="test", unrealized_pnl=1000.0)
        positions["BTC"] = btc_pos

        eth_pos = Position("ETH", 0.5, 3000.0, strategy="test", unrealized_pnl=-200.0)
        positions["ETH"] = eth_pos

        self.position_manager.positions = positions

        # Act
        exported = self.position_manager.export_positions()

        # Assert
        assert len(exported) == 2
        assert exported[0]['symbol'] == "BTC"
        assert exported[0]['quantity'] == 1.0
        assert exported[0]['unrealized_pnl'] == 1000.0
        assert exported[1]['symbol'] == "ETH"
        assert exported[1]['unrealized_pnl'] == -200.0

    def test_import_positions_json(self):
        """Test position data import from JSON format."""
        # Arrange
        positions_data = [
            {
                'symbol': 'BTC',
                'quantity': 1.0,
                'avg_entry_price': 50000.0,
                'strategy': 'test_strategy',
                'unrealized_pnl': 1000.0,
                'realized_pnl': 0.0,
                'stop_loss': None,
                'take_profit': None,
                'opened_at': self.base_time,
                'tags': {}
            }
        ]

        # Act
        self.position_manager.import_positions(positions_data)

        # Assert
        assert len(self.position_manager.positions) == 1
        assert "BTC" in self.position_manager.positions
        position = self.position_manager.positions["BTC"]
        assert position.quantity == 1.0
        assert position.avg_entry_price == 50000.0
        assert position.strategy == "test_strategy"

    def test_position_manager_position_merging(self):
        """Test position merging when adding position for existing symbol."""
        # Arrange - Add initial position
        initial_pos = Position("BTC", 1.0, 50000.0)
        self.position_manager.add_position(initial_pos)

        # Act - Add position for same symbol (should merge)
        new_pos = Position("BTC", 0.5, 55000.0)
        self.position_manager.add_position(new_pos)

        # Assert
        merged_position = self.position_manager.positions["BTC"]
        assert merged_position.quantity == 1.5  # 1.0 + 0.5

        # Weighted average price: (1.0 * 50000 + 0.5 * 55000) / 1.5
        expected_price = (50000.0 + 55000.0 * 0.5) / 1.5
        assert abs(merged_position.avg_entry_price - expected_price) < 0.01

    def test_position_manager_portfolio_value_calculation(self):
        """Test portfolio value calculation across multiple positions."""
        # Arrange
        positions = {}
        btc_pos = Position("BTC", 2.0, 50000.0)  # $100,000
        positions["BTC"] = btc_pos

        eth_pos = Position("ETH", 10.0, 3000.0)  # $30,000
        positions["ETH"] = eth_pos

        ada_pos = Position("ADA", 1000.0, 1.0)   # $1,000
        positions["ADA"] = ada_pos

        self.position_manager.positions = positions

        # Act (automatically calculated when positions are added)
        portfolio_value = self.position_manager.portfolio_value

        # Assert
        expected_value = 131000.0  # 100k + 30k + 1k
        assert abs(portfolio_value - expected_value) < 0.01

    def test_position_manager_get_positions_summary(self):
        """Test comprehensive positions summary generation."""
        # Arrange
        positions = {}
        btc_long = Position("BTC", 1.0, 50000.0, unrealized_pnl=5000.0)
        positions["BTC"] = btc_long

        eth_short = Position("ETH", -0.5, 3000.0, unrealized_pnl=-1500.0)
        positions["ETH"] = eth_short

        ada_profit = Position("ADA", 2.0, 1.0, unrealized_pnl=1.0)  # Profitable
        positions["ADA"] = ada_profit

        self.position_manager.positions = positions

        # Act
        summary = self.position_manager.get_positions_summary()

        # Assert
        assert summary['total_positions'] == 3
        assert summary['long_positions'] == 2  # BTC and ADA
        assert summary['short_positions'] == 1  # ETH
        assert summary['winning_positions'] == 2  # BTC and ADA
        assert summary['losing_positions'] == 1  # ETH
        assert summary['win_rate'] == pytest.approx(66.67, abs=0.01)  # 2/3 * 100

    def test_position_manager_edge_case_zero_positions(self):
        """Test position manager behavior with zero positions."""
        # Arrange - Empty position manager

        # Act & Assert - All operations should handle empty state gracefully
        assert len(self.position_manager.positions) == 0
        assert self.position_manager.portfolio_value == 0.0

        # Test retrieval operations
        assert self.position_manager.get_position("BTC") is None
        assert self.position_manager.get_positions_by_strategy("test") == []
        assert self.position_manager.get_long_positions() == []
        assert self.position_manager.get_short_positions() == []

        # Test calculations
        risk_metrics = self.position_manager.calculate_portfolio_risk()
        assert risk_metrics['total_risk'] == 0.0

        summary = self.position_manager.get_positions_summary()
        assert summary['total_positions'] == 0

    def test_position_manager_large_portfolio_performance(self):
        """Test position manager performance with large portfolio."""
        # Arrange - Create large portfolio for performance testing
        positions = {}
        start_time = time.time()

        for i in range(1000):
            symbol = f"CRYPTO{i}"
            pos = Position(symbol, 1.0, 50000.0, unrealized_pnl=(i % 3 - 1) * 100.0)
            positions[symbol] = pos

        self.position_manager.positions = positions

        # Act - Test various operations performance
        update_start = time.time()

        # Test price updates
        price_data = {f"CRYPTO{i}": 51000.0 for i in range(1000)}
        self.position_manager.update_position_prices(price_data)

        # Test portfolio calculations
        risk_metrics = self.position_manager.calculate_portfolio_risk()
        summary = self.position_manager.get_positions_summary()

        end_time = time.time()

        # Assert - Operations complete within reasonable time
        execution_time = end_time - update_start
        assert execution_time < 2.0  # Should complete within 2 seconds

        # Verify calculations are reasonable
        assert summary['total_positions'] == 1000
        assert risk_metrics['total_risk'] > 0

    def test_position_manager_error_handling_invalid_import(self):
        """Test error handling for invalid position import data."""
        # Arrange - Invalid position data
        invalid_data = [
            {
                'symbol': 'BTC',
                'quantity': 'invalid',  # Should be number
                'avg_entry_price': 50000.0
            }
        ]

        # Act & Assert - Should handle gracefully
        self.position_manager.import_positions(invalid_data)

        # Should not crash, but also should not import invalid data
        assert len(self.position_manager.positions) == 0

    def test_position_manager_position_aggregation(self):
        """Test position aggregation and filtering operations."""
        # Arrange - Mixed portfolio
        positions = {}
        profitable_long = Position("BTC", 1.0, 50000.0, unrealized_pnl=5000.0)
        positions["BTC"] = profitable_long

        unprofitable_short = Position("ETH", -0.5, 3000.0, unrealized_pnl=-2000.0)
        positions["ETH"] = unprofitable_short

        neutral_position = Position("ADA", 1.0, 1.0, unrealized_pnl=0.0)
        positions["ADA"] = neutral_position

        self.position_manager.positions = positions

        # Act - Test various filtering operations
        profitable = self.position_manager.get_profitable_positions()
        unprofitable = self.position_manager.get_unprofitable_positions()
        largest = self.position_manager.get_largest_positions(2)
        most_profitable = self.position_manager.get_most_profitable_positions(2)

        # Assert
        assert len(profitable) == 1  # Only BTC is profitable
        assert len(unprofitable) == 1  # Only ETH is unprofitable
        assert len(largest) == 2  # Top 2 by market value
        assert len(most_profitable) == 2  # Top 2 by P&L

    def test_position_manager_rebalance_suggestions(self):
        """Test portfolio rebalancing suggestions."""
        # Arrange - Create imbalanced portfolio
        positions = {}
        # Large position that's causing concentration risk
        btc_large = Position("BTC", 5.0, 50000.0)  # Very large position
        positions["BTC"] = btc_large

        # Small positions
        for symbol in ["ETH", "ADA"]:
            pos = Position(symbol, 0.1, 1000.0)
            positions[symbol] = pos

        self.position_manager.positions = positions
        self.position_manager.portfolio_value = 260000.0

        # Act
        suggestions = self.position_manager.get_rebalance_suggestions()

        # Assert
        assert 'close_positions' in suggestions
        assert 'reduce_positions' in suggestions
        assert 'increase_positions' in suggestions
        # Should suggest reducing the oversized BTC position
        assert len(suggestions['reduce_positions']) > 0

    def test_position_manager_total_exposure_calculation(self):
        """Test total exposure calculation."""
        # Arrange
        positions = {}
        btc_pos = Position("BTC", 2.0, 50000.0)  # $100k exposure
        positions["BTC"] = btc_pos

        eth_pos = Position("ETH", 5.0, 3000.0)  # $15k exposure
        positions["ETH"] = eth_pos

        self.position_manager.positions = positions

        # Act
        total_exposure = self.position_manager.get_total_exposure()
        btc_exposure = self.position_manager.get_total_exposure("BTC")
        eth_exposure = self.position_manager.get_total_exposure("ETH")

        # Assert
        assert total_exposure == 115000.0  # 100k + 15k
        assert btc_exposure == 100000.0
        assert eth_exposure == 15000.0

    def test_position_manager_net_exposure_by_asset(self):
        """Test net exposure calculation by asset class."""
        # Arrange - Only crypto positions for this test
        positions = {}
        btc_pos = Position("BTC", 1.0, 50000.0)
        positions["BTC"] = btc_pos

        self.position_manager.positions = positions

        # Act
        net_exposure = self.position_manager.get_net_exposure()

        # Assert
        assert 'crypto' in net_exposure
        assert 'fiat' in net_exposure
        assert net_exposure['crypto'] > 0
        assert net_exposure['fiat'] == 0.0  # No fiat positions

    def test_position_manager_position_iteration(self):
        """Test position manager iteration capabilities."""
        # Arrange
        positions = {}
        for i in range(3):
            symbol = f"CRYPTO{i}"
            pos = Position(symbol, 1.0, 50000.0)
            positions[symbol] = pos

        self.position_manager.positions = positions

        # Act - Test iteration
        iterated_positions = list(self.position_manager)
        position_count = len(self.position_manager)

        # Assert
        assert position_count == 3
        assert len(iterated_positions) == 3

        # Test containment check
        assert "CRYPTO0" in self.position_manager
        assert "NONEXISTENT" not in self.position_manager