"""
Comprehensive Priority 4 test cases for PositionManager Utilities.
Tests focus on utility functions and helper methods for portfolio management operations.
"""
import json
import csv
import io
import time
import pytest
from unittest.mock import Mock, patch, mock_open
from typing import Dict, Any, List

from tests.utils.base_test import UnitTestCase
from core.engine.position_manager import Position, PositionManager


class TestPositionManagerUtilities(UnitTestCase):
    """Test cases for PositionManager utility functions."""

    def setup_method(self):
        """Setup for each test."""
        super().setup_method()
        self.position_manager = PositionManager()
        self.base_time = time.time()

    def test_get_positions_summary_empty_portfolio(self):
        """Test positions summary with empty portfolio."""
        # Arrange - Empty portfolio
        self.position_manager.positions = {}

        # Act
        summary = self.position_manager.get_positions_summary()

        # Assert
        assert summary['total_positions'] == 0
        assert summary['total_value'] == 0.0
        assert summary['long_positions'] == 0
        assert summary['short_positions'] == 0
        assert summary['winning_positions'] == 0
        assert summary['losing_positions'] == 0
        assert summary['win_rate'] == 0.0

    def test_get_positions_summary_mixed_portfolio(self):
        """Test positions summary with mixed long/short portfolio."""
        # Arrange - Mixed portfolio
        positions = {}
        btc_long = Position("BTC", 1.0, 50000.0, unrealized_pnl=5000.0)
        positions["BTC"] = btc_long

        eth_short = Position("ETH", -0.5, 3000.0, unrealized_pnl=-1500.0)
        positions["ETH"] = eth_short

        ada_profit = Position("ADA", 2.0, 1.0, unrealized_pnl=1.0)
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
        assert summary['win_rate'] == pytest.approx(66.67, abs=0.01)

    def test_get_positions_summary_detailed_metrics(self):
        """Test positions summary with detailed portfolio metrics."""
        # Arrange - Portfolio with various metrics
        positions = {}
        btc_pos = Position("BTC", 2.0, 50000.0, unrealized_pnl=10000.0, realized_pnl=2000.0)
        positions["BTC"] = btc_pos

        eth_pos = Position("ETH", 5.0, 3000.0, unrealized_pnl=-5000.0, realized_pnl=-1000.0)
        positions["ETH"] = eth_pos

        self.position_manager.positions = positions

        # Act
        summary = self.position_manager.get_positions_summary()

        # Assert - Check detailed metrics
        assert summary['total_unrealized_pnl'] == 5000.0  # 10000 - 5000
        assert summary['total_realized_pnl'] == 1000.0   # 2000 - 1000
        assert summary['total_pnl'] == 6000.0
        assert summary['largest_position'] == "BTC"
        assert summary['most_profitable'] == "BTC"

    def test_export_positions_json_format(self):
        """Test position export to JSON format."""
        # Arrange
        positions = {}
        btc_pos = Position("BTC", 1.0, 50000.0, strategy="momentum", unrealized_pnl=1000.0)
        positions["BTC"] = btc_pos

        eth_pos = Position("ETH", 0.5, 3000.0, strategy="mean_reversion", unrealized_pnl=-200.0)
        positions["ETH"] = eth_pos

        self.position_manager.positions = positions

        # Act
        exported = self.position_manager.export_positions(format='json')

        # Assert
        assert len(exported) == 2

        # Parse JSON to verify structure
        json_data = json.loads(exported)
        assert len(json_data) == 2

        btc_data = next(p for p in json_data if p['symbol'] == 'BTC')
        assert btc_data['quantity'] == 1.0
        assert btc_data['avg_entry_price'] == 50000.0
        assert btc_data['strategy'] == 'momentum'
        assert btc_data['unrealized_pnl'] == 1000.0

    def test_export_positions_csv_format(self):
        """Test position export to CSV format."""
        # Arrange
        positions = {}
        btc_pos = Position("BTC", 1.0, 50000.0, unrealized_pnl=1000.0)
        positions["BTC"] = btc_pos

        self.position_manager.positions = positions

        # Act
        exported = self.position_manager.export_positions(format='csv')

        # Assert
        assert isinstance(exported, str)
        assert 'symbol' in exported
        assert 'BTC' in exported
        assert '50000.0' in exported
        assert '1000.0' in exported

        # Verify CSV structure
        csv_reader = csv.DictReader(io.StringIO(exported))
        rows = list(csv_reader)
        assert len(rows) == 1
        assert rows[0]['symbol'] == 'BTC'

    def test_import_positions_json_format(self):
        """Test position import from JSON format."""
        # Arrange
        json_data = json.dumps([
            {
                'symbol': 'BTC',
                'quantity': 1.0,
                'avg_entry_price': 50000.0,
                'strategy': 'test_strategy',
                'unrealized_pnl': 1000.0,
                'realized_pnl': 0.0,
                'opened_at': self.base_time,
                'tags': {'source': 'test'}
            }
        ])

        # Act
        self.position_manager.import_positions(json_data, format='json')

        # Assert
        assert len(self.position_manager.positions) == 1
        assert "BTC" in self.position_manager.positions

        position = self.position_manager.positions["BTC"]
        assert position.quantity == 1.0
        assert position.avg_entry_price == 50000.0
        assert position.strategy == "test_strategy"
        assert position.tags['source'] == 'test'

    def test_import_positions_validation(self):
        """Test import data validation."""
        # Arrange - Invalid data
        invalid_data = json.dumps([
            {
                'symbol': 'BTC',
                'quantity': 'invalid',  # Should be number
                'avg_entry_price': 50000.0
            }
        ])

        # Act & Assert - Should handle validation errors gracefully
        with pytest.raises((ValueError, TypeError, json.JSONDecodeError)):
            self.position_manager.import_positions(invalid_data, format='json')

    def test_merge_positions_no_conflicts(self):
        """Test position merging without conflicts."""
        # Arrange - Different symbols
        positions_data = [
            {
                'symbol': 'BTC',
                'quantity': 1.0,
                'avg_entry_price': 50000.0
            },
            {
                'symbol': 'ETH',
                'quantity': 2.0,
                'avg_entry_price': 3000.0
            }
        ]

        # Act
        merged = self.position_manager.merge_positions(positions_data)

        # Assert
        assert len(merged) == 2
        assert merged['BTC']['quantity'] == 1.0
        assert merged['ETH']['quantity'] == 2.0

    def test_merge_positions_with_conflicts(self):
        """Test position merging with conflicts."""
        # Arrange - Same symbol with different data
        positions_data = [
            {
                'symbol': 'BTC',
                'quantity': 1.0,
                'avg_entry_price': 50000.0
            },
            {
                'symbol': 'BTC',
                'quantity': 2.0,
                'avg_entry_price': 55000.0
            }
        ]

        # Act
        merged = self.position_manager.merge_positions(positions_data)

        # Assert - Should merge conflicting positions
        assert len(merged) == 1
        btc_data = merged['BTC']
        assert btc_data['quantity'] == 3.0  # 1.0 + 2.0

        # Weighted average price
        expected_price = (1.0 * 50000.0 + 2.0 * 55000.0) / 3.0
        assert btc_data['avg_entry_price'] == expected_price

    def test_update_portfolio_value_calculation(self):
        """Test portfolio value update calculations."""
        # Arrange
        positions = {}
        btc_pos = Position("BTC", 2.0, 50000.0)
        positions["BTC"] = btc_pos

        eth_pos = Position("ETH", 10.0, 3000.0)
        positions["ETH"] = eth_pos

        self.position_manager.positions = positions

        # Act
        initial_value = self.position_manager.portfolio_value
        price_updates = {"BTC": 55000.0, "ETH": 3300.0}
        self.position_manager.update_position_prices(price_updates)
        updated_value = self.position_manager.portfolio_value

        # Assert
        expected_initial = 130000.0  # 2*50000 + 10*3000
        expected_updated = 143000.0  # 2*55000 + 10*3300

        assert abs(initial_value - expected_initial) < 0.01
        assert abs(updated_value - expected_updated) < 0.01

    def test_clear_positions_complete_removal(self):
        """Test complete position clearing."""
        # Arrange
        positions = {}
        btc_pos = Position("BTC", 1.0, 50000.0)
        positions["BTC"] = btc_pos

        eth_pos = Position("ETH", 2.0, 3000.0)
        positions["ETH"] = eth_pos

        self.position_manager.positions = positions
        initial_count = len(self.position_manager.positions)

        # Act
        cleared_positions = self.position_manager.clear_positions()

        # Assert
        assert initial_count == 2
        assert len(self.position_manager.positions) == 0
        assert len(cleared_positions) == 2
        assert btc_pos in cleared_positions
        assert eth_pos in cleared_positions

    def test_get_largest_positions_by_value(self):
        """Test largest positions by value."""
        # Arrange
        positions = {}
        btc_pos = Position("BTC", 1.0, 100000.0)  # $100k
        positions["BTC"] = btc_pos

        eth_pos = Position("ETH", 5.0, 4000.0)   # $20k
        positions["ETH"] = eth_pos

        ada_pos = Position("ADA", 1000.0, 50.0)  # $50k
        positions["ADA"] = ada_pos

        self.position_manager.positions = positions

        # Act
        largest = self.position_manager.get_largest_positions()

        # Assert
        assert len(largest) == 3
        assert largest[0]['symbol'] == 'BTC'  # Largest by value
        assert largest[1]['symbol'] == 'ADA'
        assert largest[2]['symbol'] == 'ETH'

    def test_get_largest_positions_with_limit(self):
        """Test largest positions with limit."""
        # Arrange
        positions = {}
        for i in range(5):
            symbol = f"CRYPTO{i}"
            pos = Position(symbol, 1.0, 1000.0 + i * 1000.0)
            positions[symbol] = pos

        self.position_manager.positions = positions

        # Act
        largest = self.position_manager.get_largest_positions(limit=3)

        # Assert
        assert len(largest) == 3
        assert largest[0]['symbol'] == 'CRYPTO4'  # Highest value
        assert largest[1]['symbol'] == 'CRYPTO3'
        assert largest[2]['symbol'] == 'CRYPTO2'

    def test_get_most_profitable_positions(self):
        """Test most profitable position filtering."""
        # Arrange
        positions = {}
        btc_pos = Position("BTC", 1.0, 50000.0, unrealized_pnl=10000.0)
        positions["BTC"] = btc_pos

        eth_pos = Position("ETH", 1.0, 3000.0, unrealized_pnl=500.0)
        positions["ETH"] = eth_pos

        ada_pos = Position("ADA", 1.0, 1.0, unrealized_pnl=-200.0)  # Loss
        positions["ADA"] = ada_pos

        self.position_manager.positions = positions

        # Act
        most_profitable = self.position_manager.get_most_profitable_positions()

        # Assert
        assert len(most_profitable) == 2  # BTC and ETH are profitable
        assert most_profitable[0]['symbol'] == 'BTC'  # Most profitable
        assert most_profitable[1]['symbol'] == 'ETH'
        assert 'ADA' not in [p['symbol'] for p in most_profitable]

    def test_get_worst_performing_positions(self):
        """Test worst performing position filtering."""
        # Arrange
        positions = {}
        btc_pos = Position("BTC", 1.0, 50000.0, unrealized_pnl=-10000.0)
        positions["BTC"] = btc_pos

        eth_pos = Position("ETH", 1.0, 3000.0, unrealized_pnl=-500.0)
        positions["ETH"] = eth_pos

        ada_pos = Position("ADA", 1.0, 1.0, unrealized_pnl=200.0)  # Profit
        positions["ADA"] = ada_pos

        self.position_manager.positions = positions

        # Act
        worst_performing = self.position_manager.get_worst_performing_positions()

        # Assert
        assert len(worst_performing) == 2  # BTC and ETH are losing
        assert worst_performing[0]['symbol'] == 'BTC'  # Worst performing
        assert worst_performing[1]['symbol'] == 'ETH'
        assert 'ADA' not in [p['symbol'] for p in worst_performing]

    def test_get_rebalance_suggestions_underweight(self):
        """Test rebalance suggestions for underweight positions."""
        # Arrange - Portfolio with underweight positions
        positions = {}
        btc_large = Position("BTC", 10.0, 50000.0)  # 90% of portfolio
        positions["BTC"] = btc_large

        eth_small = Position("ETH", 0.1, 3000.0)   # 2.7% of portfolio
        positions["ETH"] = eth_small

        self.position_manager.positions = positions
        self.position_manager.portfolio_value = 553000.0

        # Act
        suggestions = self.position_manager.get_rebalance_suggestions()

        # Assert
        assert 'underweight' in suggestions
        assert 'ETH' in suggestions['underweight']
        assert suggestions['underweight']['ETH']['current_weight'] < 0.05  # Less than 5%
        assert suggestions['underweight']['ETH']['target_weight'] > 0.05

    def test_get_rebalance_suggestions_overweight(self):
        """Test rebalance suggestions for overweight positions."""
        # Arrange - Portfolio with overweight positions
        positions = {}
        btc_small = Position("BTC", 0.1, 50000.0)  # 4.5% of portfolio
        positions["BTC"] = btc_small

        eth_large = Position("ETH", 20.0, 3000.0)  # 54% of portfolio
        positions["ETH"] = eth_large

        ada_medium = Position("ADA", 100.0, 1.0)   # 9% of portfolio
        positions["ADA"] = ada_medium

        self.position_manager.positions = positions
        self.position_manager.portfolio_value = 111100.0

        # Act
        suggestions = self.position_manager.get_rebalance_suggestions()

        # Assert
        assert 'overweight' in suggestions
        assert 'ETH' in suggestions['overweight']
        assert suggestions['overweight']['ETH']['current_weight'] > 0.25  # More than 25%
        assert suggestions['overweight']['ETH']['target_weight'] < 0.25

    def test_get_total_exposure_single_symbol(self):
        """Test total exposure for single symbol."""
        # Arrange
        position = Position("BTC", 2.0, 50000.0)
        self.position_manager.positions = {"BTC": position}

        # Act
        total_exposure = self.position_manager.get_total_exposure()
        btc_exposure = self.position_manager.get_total_exposure("BTC")

        # Assert
        assert total_exposure == 100000.0
        assert btc_exposure == 100000.0

    def test_get_total_exposure_multiple_symbols(self):
        """Test total exposure for multiple symbols."""
        # Arrange
        positions = {}
        btc_pos = Position("BTC", 2.0, 50000.0)  # $100k
        positions["BTC"] = btc_pos

        eth_pos = Position("ETH", 5.0, 3000.0)  # $15k
        positions["ETH"] = eth_pos

        ada_pos = Position("ADA", 100.0, 1.0)   # $100
        positions["ADA"] = ada_pos

        self.position_manager.positions = positions

        # Act
        total_exposure = self.position_manager.get_total_exposure()
        btc_exposure = self.position_manager.get_total_exposure("BTC")
        eth_exposure = self.position_manager.get_total_exposure("ETH")
        ada_exposure = self.position_manager.get_total_exposure("ADA")

        # Assert
        assert total_exposure == 115100.0  # 100k + 15k + 100
        assert btc_exposure == 100000.0
        assert eth_exposure == 15000.0
        assert ada_exposure == 100.0

    def test_get_net_exposure_long_positions(self):
        """Test net exposure for long positions."""
        # Arrange - All long positions
        positions = {}
        btc_pos = Position("BTC", 2.0, 50000.0)
        positions["BTC"] = btc_pos

        eth_pos = Position("ETH", 5.0, 3000.0)
        positions["ETH"] = eth_pos

        self.position_manager.positions = positions

        # Act
        net_exposure = self.position_manager.get_net_exposure()

        # Assert
        assert net_exposure['long'] == 115000.0  # Total long exposure
        assert net_exposure['short'] == 0.0      # No short positions
        assert net_exposure['net'] == 115000.0   # Net long

    def test_get_net_exposure_mixed_positions(self):
        """Test net exposure for mixed positions."""
        # Arrange - Mixed long/short positions
        positions = {}
        btc_long = Position("BTC", 2.0, 50000.0)    # Long $100k
        positions["BTC"] = btc_long

        eth_short = Position("ETH", -3.0, 3000.0)   # Short $9k
        positions["ETH"] = eth_short

        ada_long = Position("ADA", 10.0, 1.0)      # Long $10
        positions["ADA"] = ada_long

        self.position_manager.positions = positions

        # Act
        net_exposure = self.position_manager.get_net_exposure()

        # Assert
        assert net_exposure['long'] == 100010.0   # BTC + ADA
        assert net_exposure['short'] == 9000.0    # ETH short (absolute value)
        assert net_exposure['net'] == 91010.0     # Long - Short

    def test_has_position_existing_symbol(self):
        """Test position existence check for existing symbol."""
        # Arrange
        position = Position("BTC", 1.0, 50000.0)
        self.position_manager.positions = {"BTC": position}

        # Act
        exists = self.position_manager.has_position("BTC")

        # Assert
        assert exists is True

    def test_has_position_nonexistent_symbol(self):
        """Test position existence check for non-existent symbol."""
        # Arrange - Empty position manager
        self.position_manager.positions = {}

        # Act
        exists = self.position_manager.has_position("NONEXISTENT")

        # Assert
        assert exists is False