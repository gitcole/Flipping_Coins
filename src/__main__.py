"""Main application entry point for the crypto trading bot."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys
import threading
import time
from typing import Optional

from .core.app.orchestrator import ApplicationOrchestrator
from .core.api.robinhood.client import RobinhoodClient
from .core.config import initialize_config
from .utils.logging import get_logger, setup_logging

# Global configuration
live_prices_enabled = True


def setup_api_credentials() -> None:
    """Interactive setup for API credentials."""
    config_dir = "config"
    env_file = os.path.join(config_dir, ".env")

    print("🔐 Crypto Trading Bot - Robinhood API Setup")
    print("=" * 50)

    # Check if .env already exists
    if os.path.exists(env_file):
        print("ℹ️  Configuration file already exists.")
        response = input("Do you want to update Robinhood API credentials? (y/N): ").strip().lower()
        if response != 'y':
            return

    print("\n📝 Please provide your Robinhood API credentials:")
    print("   You can get these from your Robinhood account settings:")
    print("   1. Go to robinhood.com → Account → Settings")
    print("   2. Scroll down to 'API Access' section")
    print("   3. Generate a new API token")
    print()

    # Default to Robinhood
    exchange_name = "robinhood"

    # API Token
    print("🔑 Robinhood API Token:")
    print("   This is your personal access token from Robinhood")
    api_key = input("Enter your Robinhood API Token: ").strip()
    if not api_key:
        print("❌ API Token is required.")
        return

    # Skip API Secret for Robinhood (they use tokens)
    api_secret = "robinhood_token_auth"

    # Sandbox mode
    print("\n🧪 Sandbox Mode (for testing):")
    sandbox_response = input("Use sandbox/test environment? (y/N): ").strip().lower()
    sandbox_mode = "true" if sandbox_response == 'y' else "false"

    # Trading pair selection
    print("\n📈 Trading Pairs:")
    print("   Common pairs: BTC/USD, ETH/USD, ADA/USD, SOL/USD")
    default_symbols = "BTC/USD,ETH/USD,ADA/USD"
    symbols = input(f"Enter supported symbols (comma-separated) [{default_symbols}]: ").strip()
    if not symbols:
        symbols = default_symbols

    # Risk settings
    print("\n⚠️  Risk Management:")
    max_portfolio_risk = input("Max portfolio risk per trade (0.01-0.05) [0.02]: ").strip()
    if not max_portfolio_risk:
        max_portfolio_risk = "0.02"

    default_risk_per_trade = input("Default risk per trade (0.005-0.02) [0.01]: ").strip()
    if not default_risk_per_trade:
        default_risk_per_trade = "0.01"

    # Create config directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)

    # Create .env file
    env_content = f"""# Robinhood Crypto Trading Bot Configuration
# Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}

# Robinhood API Configuration
ROBINHOOD_API_TOKEN={api_key}
ROBINHOOD_SANDBOX={sandbox_mode}

# Application Settings
APP_ENV=development
LOG_LEVEL=INFO
DEBUG=false

# Trading Configuration
TRADING_ENABLED=true
SUPPORTED_SYMBOLS={symbols}
MAX_POSITIONS=5
MIN_ORDER_SIZE=1.0
MAX_ORDER_VALUE=1000.0

# Risk Management
MAX_PORTFOLIO_RISK={max_portfolio_risk}
DEFAULT_RISK_PER_TRADE={default_risk_per_trade}
MAX_CORRELATION=0.7
MAX_DRAWDOWN=0.15
STOP_LOSS_DEFAULT=0.03
TAKE_PROFIT_DEFAULT=0.10

# Database & Caching
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=sqlite:///data/trading_bot.db

# Monitoring (Optional)
PROMETHEUS_ENABLED=false
GRAFANA_ENABLED=false
SLACK_WEBHOOK_URL=

# Security Note: Keep this file secure and never commit to version control
# Your Robinhood API token is stored here - protect this file!
"""

    try:
        with open(env_file, 'w') as f:
            f.write(env_content)

        print(f"\n✅ Configuration saved to {env_file}")
        print("\n🚀 Robinhood Crypto Bot setup complete!")
        print("   You can now run the trading bot with:")
        print("   python -m src")
        print("\n💡 Tips:")
        print("   - Use sandbox mode for testing (no real money)")
        print("   - Start with small amounts until you're comfortable")
        print("   - Monitor your bot's performance regularly")
        print("   - Use Ctrl+C to stop the bot safely")
        print("   - Your API token is saved in config/.env (keep it secure!)")

    except Exception as e:
        print(f"❌ Failed to save configuration: {str(e)}")


def check_configuration() -> bool:
    """Check if configuration is complete."""
    env_file = os.path.join("config", ".env")
    return os.path.exists(env_file)


class RuntimeManager:
    """Runtime management interface for the trading bot."""

    def __init__(self, orchestrator: ApplicationOrchestrator):
        """Initialize runtime manager."""
        self.orchestrator = orchestrator
        self.logger = get_logger("runtime")
        self.running = False
        self.command_thread: Optional[threading.Thread] = None

    def start_interactive_mode(self):
        """Start interactive command mode in a separate thread."""
        self.running = True
        self.command_thread = threading.Thread(target=self._command_loop, daemon=True)
        self.command_thread.start()
        self.logger.info("Interactive mode started")

    def stop_interactive_mode(self):
        """Stop interactive command mode."""
        self.running = False
        if self.command_thread and self.command_thread.is_alive():
            self.command_thread.join(timeout=2)
        self.logger.info("Interactive mode stopped")

    def _command_loop(self):
        """Main command loop for interactive mode."""
        print("\n🎮 ROBINHOOD CRYPTO BOT - INTERACTIVE MODE")
        print("=" * 50)
        print("🤖 Welcome to your Robinhood Crypto Trading Bot!")
        print("\n📋 AVAILABLE COMMANDS:")
        print("   📊 status     - Show bot status & component health")
        print("   💰 prices     - Show current crypto prices")
        print("   💱 cryptos    - Show crypto positions & available cryptos")
        print("   📈 portfolio  - Show portfolio information")
        print("   🎯 strategies - List/manage trading strategies")
        print("   ⚠️  risk       - Show/modify risk settings")
        print("   ⚙️  config     - Show current configuration")
        print("   ⚡ trading    - Enable/disable trading")
        print("   🆘 help       - Show this help message")
        print("   👋 quit       - Exit interactive mode")
        print("\n💡 TIP: Use these commands to monitor and control your bot!")
        print()

        while self.running:
            try:
                command = input("🤖 Robinhood Bot > ").strip().lower()

                if command == "status":
                    self._show_status()
                elif command == "prices":
                    self._show_prices()
                elif command == "cryptos":
                    self._show_cryptos()
                elif command == "portfolio":
                    self._show_portfolio()
                elif command == "strategies":
                    self._manage_strategies()
                elif command == "risk":
                    self._manage_risk()
                elif command == "config":
                    self._show_config()
                elif command == "trading":
                    self._manage_trading()
                elif command == "help":
                    self._show_help()
                elif command == "quit":
                    break
                else:
                    print(f"❌ Unknown command: '{command}'")
                    print("💡 Type 'help' to see all available commands.")

            except (EOFError, KeyboardInterrupt):
                print("\n⏹️  Exiting interactive mode...")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")

    def _show_status(self):
        """Show bot status."""
        if not self.orchestrator:
            print("❌ Bot not initialized")
            return

        try:
            print("\n📊 ROBINHOOD CRYPTO BOT STATUS")
            print("=" * 40)
            print(f"   🤖 Status: {'🟢 RUNNING' if self.orchestrator.is_running else '🔴 STOPPED'}")

            # Show component status
            print("\n🔧 COMPONENTS:")
            if self.orchestrator.strategy_registry:
                status_icon = "✅" if self.orchestrator.strategy_registry._running else "❌"
                print(f"   {status_icon} strategy_registry")
            else:
                print("   ❌ strategy_registry")

            if self.orchestrator.market_data_client:
                status_icon = "✅" if self.orchestrator.market_data_client.is_connected else "❌"
                print(f"   {status_icon} market_data_client")
            else:
                print("   ❌ market_data_client")

            if self.orchestrator.strategy_executor:
                status_icon = "✅" if self.orchestrator.strategy_executor.is_running else "❌"
                print(f"   {status_icon} strategy_executor")
            else:
                print("   ❌ strategy_executor")

            if self.orchestrator.risk_manager:
                print("   ✅ risk_manager")
            else:
                print("   ❌ risk_manager")

            print("   ℹ️  WebSocket disabled (normal for Robinhood)")
            print("   ℹ️  Trading engine not configured (placeholder)")

        except Exception as e:
            print(f"❌ Error getting status: {str(e)}")

    def _show_prices(self):
        """Show current crypto prices with dynamic updates."""
        print("\n💰 ROBINHOOD CRYPTO PRICES")
        print("=" * 50)
        print("   Symbol      Price          Change")
        print("   ----------  -----------    ------")

        # Get supported symbols from configuration
        try:
            from ..core.config import get_settings
            settings = get_settings()
            symbols_to_check = settings.trading.supported_symbols
        except (ImportError, AttributeError, Exception):
            symbols_to_check = [
                "BTC", "ETH", "ADA", "SOL", "DOT",
                "AVAX", "MATIC", "LINK", "UNI", "LTC",
                "BCH", "XLM", "ETC", "AAVE", "COMP",
                "SNX", "YFI", "SUSHI", "CRV", "1INCH"
            ]

        current_time = time.strftime("%H:%M:%S")
        display_symbols = symbols_to_check[:10] if len(symbols_to_check) > 10 else symbols_to_check
    
        if live_prices_enabled:
            try:
                # Fetch real prices from Robinhood API
                async def fetch_quotes():
                    async with RobinhoodClient() as client:
                        await client.initialize()
                        symbols_list = [s.split('/')[0].upper() for s in display_symbols]
                        return await client.crypto.get_crypto_quotes(symbols_list)
    
                quotes = asyncio.run(fetch_quotes())
    
                for i, symbol in enumerate(display_symbols):
                    if i < len(quotes) and quotes[i] and quotes[i].last_trade_price > 0:
                        quote = quotes[i]
                        price = quote.last_trade_price
                        # Calculate approximate change based on 24h high/low
                        change = (quote.high_24h - quote.low_24h) / quote.low_24h * 100 if quote.low_24h > 0 else 0
                        change_icon = "📈" if change >= 0 else "📉"
                        print(f"   {symbol:<10} ${price:>10.2f}    {change_icon} {change:+.2f}%")
                    else:
                        # Fallback for failed quotes
                        print(f"   {symbol:<10} {'N/A':>10}    {'-':>4} {'N/A':>6}%")
    
                if len(symbols_to_check) > 10:
                    remaining = len(symbols_to_check) - 10
                    print(f"   ... and {remaining} more symbols available")
    
                print(f"\n🕐 Last updated: {current_time}")
                print(f"💡 Total supported symbols: {len(symbols_to_check)}")
                print("💡 Prices are live from Robinhood API")
    
            except Exception as e:
                print(f"Error fetching live prices: {e}")
                print("Falling back to simulated data...")
    
                # Fallback to mock data
                import random
                import time as time_module
    
                current_timestamp = int(time_module.time())
                random.seed(current_timestamp // 60)  # Change every minute
    
                for symbol in display_symbols:
                    # Generate dynamic price with realistic movement
                    base_price = 1000.0  # Base price for simulation
                    volatility = 0.05  # 5% volatility
                    random_factor = random.uniform(-volatility, volatility)
                    current_price = base_price * (1 + random_factor)
    
                    change_percent = random_factor * 100
                    change_icon = "📈" if change_percent >= 0 else "📉"
                    print(f"   {symbol:<10} ${current_price:>10.2f}    {change_icon} {change_percent:+.2f}%")
    
                if len(symbols_to_check) > 10:
                    remaining = len(symbols_to_check) - 10
                    print(f"   ... and {remaining} more symbols available")
    
                print(f"\n🕐 Last updated: {current_time}")
                print(f"💡 Total supported symbols: {len(symbols_to_check)}")
                print("💡 Prices update every minute")
        else:
            # Use mock data only
            import random
            import time as time_module
    
            current_timestamp = int(time_module.time())
            random.seed(current_timestamp // 60)  # Change every minute
    
            for symbol in display_symbols:
                # Generate dynamic price with realistic movement
                base_price = 1000.0  # Base price for simulation
                volatility = 0.05  # 5% volatility
                random_factor = random.uniform(-volatility, volatility)
                current_price = base_price * (1 + random_factor)
    
                change_percent = random_factor * 100
                change_icon = "📈" if change_percent >= 0 else "📉"
                print(f"   {symbol:<10} ${current_price:>10.2f}    {change_icon} {change_percent:+.2f}%")
    
            if len(symbols_to_check) > 10:
                remaining = len(symbols_to_check) - 10
                print(f"   ... and {remaining} more symbols available")
    
            print(f"\n🕐 Last updated: {current_time}")
            print(f"💡 Total supported symbols: {len(symbols_to_check)}")
            print("💡 Prices update every minute")

    def _show_cryptos(self):
        """Show crypto positions and available cryptos."""
        print("\n💱 ROBINHOOD CRYPTO POSITIONS & ASSETS")
        print("=" * 45)

        # Show current crypto positions (mock data for now)
        print("\n📊 CURRENT CRYPTO POSITIONS:")
        print("   Symbol    Quantity      Value     P&L")
        print("   --------  ------------  --------  --------")

        # Mock positions - in real implementation would come from position manager
        mock_positions = [
            {"symbol": "BTC", "quantity": 0.05, "value": 3000.00, "pnl": 150.00},
            {"symbol": "ETH", "quantity": 1.2, "value": 2400.00, "pnl": -45.00},
            {"symbol": "ADA", "quantity": 500.0, "value": 250.00, "pnl": 25.00},
        ]

        total_value = 0
        total_pnl = 0

        for pos in mock_positions:
            pnl_icon = "📈" if pos["pnl"] >= 0 else "📉"
            print(f"   {pos['symbol']:<8}  {pos['quantity']:>10.4f}  ${pos['value']:>8.2f}  {pnl_icon} ${pos['pnl']:>+7.2f}")
            total_value += pos["value"]
            total_pnl += pos["pnl"]

        print("   --------  ------------  --------  --------")
        pnl_icon = "📈" if total_pnl >= 0 else "📉"
        print(f"   {'TOTAL':<8}  {'' :>10}  ${total_value:>8.2f}  {pnl_icon} ${total_pnl:+7.2f}")

        # Show available cryptos to trade
        print("\n\n💰 AVAILABLE CRYPTOS TO TRADE:")
        print("   Symbol    Name                    Status")
        print("   --------  ----------------------  --------")

        available_cryptos = [
            {"symbol": "BTC", "name": "Bitcoin", "status": "Available"},
            {"symbol": "ETH", "name": "Ethereum", "status": "Available"},
            {"symbol": "ADA", "name": "Cardano", "status": "Available"},
            {"symbol": "SOL", "name": "Solana", "status": "Available"},
            {"symbol": "DOT", "name": "Polkadot", "status": "Available"},
            {"symbol": "AVAX", "name": "Avalanche", "status": "Available"},
            {"symbol": "MATIC", "name": "Polygon", "status": "Available"},
            {"symbol": "LINK", "name": "Chainlink", "status": "Available"},
            {"symbol": "UNI", "name": "Uniswap", "status": "Available"},
            {"symbol": "LTC", "name": "Litecoin", "status": "Available"},
            {"symbol": "BCH", "name": "Bitcoin Cash", "status": "Available"},
            {"symbol": "XLM", "name": "Stellar", "status": "Available"},
            {"symbol": "ETC", "name": "Ethereum Classic", "status": "Available"},
            {"symbol": "AAVE", "name": "Aave", "status": "Available"},
            {"symbol": "COMP", "name": "Compound", "status": "Available"},
            {"symbol": "SNX", "name": "Synthetix", "status": "Available"},
            {"symbol": "YFI", "name": "Yearn Finance", "status": "Available"},
            {"symbol": "SUSHI", "name": "SushiSwap", "status": "Available"},
            {"symbol": "CRV", "name": "Curve DAO Token", "status": "Available"},
            {"symbol": "1INCH", "name": "1inch", "status": "Available"},
        ]

        for crypto in available_cryptos:
            print(f"   {crypto['symbol']:<8}  {crypto['name']:<21}  {crypto['status']}")

        print(f"\n📈 Total Available Cryptos: {len(available_cryptos)}")
        print("\n💡 TIP: Use 'prices' to see current market prices")
        print("   💡 TIP: Use 'strategies' to start trading these cryptos")

    def _show_portfolio(self):
        """Show portfolio information."""
        if not self.orchestrator or not self.orchestrator.trading_engine:
            print("❌ Trading engine not available")
            return

        print("\n📈 ROBINHOOD PORTFOLIO")
        print("=" * 25)
        print("💼 Portfolio information will be available once connected")
        print("   This feature requires active Robinhood API connection")
        print("   Check 'status' to see if all components are connected")

    def _manage_strategies(self):
        """Manage trading strategies."""
        if not self.orchestrator or not self.orchestrator.strategy_registry:
            print("❌ Strategy registry not available")
            return

        print("🎯 Strategy Management:")

        # Show current strategies
        strategies = self.orchestrator.strategy_registry.get_all_strategies()
        running_strategies = self.orchestrator.strategy_registry.get_running_strategies()

        print(f"   Total strategies: {len(strategies)}")
        print(f"   Running strategies: {len(running_strategies)}")

        for name, info in strategies.items():
            status_icon = "✅" if info.status.value == "RUNNING" else "❌"
            print(f"     {name}: {status_icon} {info.status.value}")

        print("   Commands:")
        print("     start STRATEGY   - Start a strategy")
        print("     stop STRATEGY    - Stop a strategy")
        print("     list             - List all strategies")
        print("     status           - Show strategy status")

        while True:
            cmd = input("   Strategy > ").strip().lower()
            if cmd.startswith("start "):
                strategy = cmd[6:]
                if strategy in strategies:
                    print(f"   Starting strategy: {strategy}")
                else:
                    print(f"   ❌ Strategy '{strategy}' not found")
            elif cmd.startswith("stop "):
                strategy = cmd[5:]
                if strategy in strategies:
                    print(f"   Stopping strategy: {strategy}")
                else:
                    print(f"   ❌ Strategy '{strategy}' not found")
            elif cmd == "list":
                print("   Available strategies:")
                for name in strategies.keys():
                    print(f"     - {name}")
            elif cmd == "status":
                summary = self.orchestrator.strategy_registry.get_strategy_status_summary()
                print(f"   Registry Stats: {summary}")
            elif cmd == "back":
                break
            else:
                print("   ❌ Invalid command")

    def _manage_risk(self):
        """Manage risk settings."""
        if not self.orchestrator or not self.orchestrator.risk_manager:
            print("❌ Risk manager not available")
            return

        print("⚠️  Risk Management:")

        # Show current risk metrics
        risk_summary = self.orchestrator.risk_manager.get_risk_summary()
        metrics = risk_summary['risk_metrics']
        limits = risk_summary['limits']

        print(f"   Portfolio Risk: {metrics['total_portfolio_risk']:.2%}")
        print(f"   Max Position Risk: {metrics['max_position_risk']:.2%}")
        print(f"   Current Drawdown: {metrics['current_drawdown']:.2%}")
        print(f"   Concentration Risk: {metrics['concentration_risk']:.2%}")
        print(f"   Active Positions: {risk_summary['current_positions']}")
        print(f"   Portfolio Value: ${risk_summary['portfolio_value']:,.2f}")

        print("   Current Limits:")
        print(f"     Max Portfolio Risk: {limits['max_portfolio_risk']:.2%}")
        print(f"     Max Position Risk: {limits['max_position_risk']:.2%}")
        print(f"     Max Correlation: {limits['max_correlation']}")
        print(f"     Max Drawdown: {limits['max_drawdown']:.2%}")

        print("   Commands:")
        print("     set portfolio_risk 0.10    - Set max portfolio risk")
        print("     set position_risk 0.02     - Set max position risk")
        print("     set correlation 0.7        - Set max correlation")
        print("     set drawdown 0.15          - Set max drawdown")
        print("     refresh                    - Refresh risk metrics")

        while True:
            cmd = input("   Risk > ").strip().lower()
            if cmd.startswith("set portfolio_risk "):
                try:
                    value = float(cmd[19:])
                    if 0.01 <= value <= 0.5:
                        self.orchestrator.risk_manager.max_portfolio_risk = value
                        print(f"   ✅ Max portfolio risk set to {value:.2%}")
                    else:
                        print("   ❌ Value must be between 0.01 (1%) and 0.5 (50%)")
                except ValueError:
                    print("   ❌ Invalid value")
            elif cmd.startswith("set position_risk "):
                try:
                    value = float(cmd[17:])
                    if 0.005 <= value <= 0.1:
                        self.orchestrator.risk_manager.max_position_risk = value
                        print(f"   ✅ Max position risk set to {value:.2%}")
                    else:
                        print("   ❌ Value must be between 0.005 (0.5%) and 0.1 (10%)")
                except ValueError:
                    print("   ❌ Invalid value")
            elif cmd.startswith("set correlation "):
                try:
                    value = float(cmd[15:])
                    if 0.1 <= value <= 0.9:
                        self.orchestrator.risk_manager.max_correlation = value
                        print(f"   ✅ Max correlation set to {value:.2f}")
                    else:
                        print("   ❌ Value must be between 0.1 and 0.9")
                except ValueError:
                    print("   ❌ Invalid value")
            elif cmd.startswith("set drawdown "):
                try:
                    value = float(cmd[13:])
                    if 0.05 <= value <= 0.5:
                        self.orchestrator.risk_manager.max_drawdown = value
                        print(f"   ✅ Max drawdown set to {value:.2%}")
                    else:
                        print("   ❌ Value must be between 0.05 (5%) and 0.5 (50%)")
                except ValueError:
                    print("   ❌ Invalid value")
            elif cmd == "refresh":
                asyncio.create_task(self.orchestrator.risk_manager.update_risk_metrics())
                print("   🔄 Refreshing risk metrics...")
            elif cmd == "back":
                break
            else:
                print("   ❌ Invalid command")

    def _show_config(self):
        """Show current configuration."""
        print("⚙️  Current Configuration:")
        print("   Max Portfolio Risk: 10%")
        print("   Max Position Risk: 2%")
        print("   Supported Symbols: BTC/USD, ETH/USD, ADA/USD, SOL/USD")
        print("   Active Strategies: market_making")

    def _manage_trading(self):
        """Manage trading enable/disable."""
        print("⚡ TRADING MANAGEMENT")
        print("=" * 25)
        print("Current trading status: Disabled (no trading engine)")
        print("Commands:")
        print("  on   - Enable trading")
        print("  off  - Disable trading")
        print("  back - Return to main menu")

        while True:
            cmd = input("  Trading > ").strip().lower()

            if cmd == "on":
                print("  Trading enabled")
                break
            elif cmd == "off":
                print("  Trading disabled")
                break
            elif cmd == "back":
                break
            else:
                print("  Invalid command")

    def _show_help(self):
        """Show help information."""
        print("\n🆘 ROBINHOOD CRYPTO BOT - COMMAND HELP")
        print("=" * 45)
        print("📋 COMMAND REFERENCE:")
        print()
        print("🤖 BOT MANAGEMENT:")
        print("   📊 status     - Show bot status & component health")
        print("   ⚙️  config     - Show current configuration")
        print("   👋 quit       - Exit interactive mode")
        print()
        print("💰 MARKET DATA:")
        print("   💰 prices     - Show current crypto prices")
        print("   💱 cryptos    - Show crypto positions & available cryptos")
        print()
        print("📈 TRADING:")
        print("   📈 portfolio  - Show portfolio information")
        print("   🎯 strategies - List/manage trading strategies")
        print("   ⚠️  risk       - Show/modify risk settings")
        print("   ⚡ trading    - Enable/disable trading")
        print()
        print("🔧 MONITORING:")
        print("   💡 View clean logs: Run bot in terminal to see readable logs")
        print("   💡 Monitor live: Use commands to check real-time status")
        print()
        print("💡 TIPS:")
        print("   • Use 'status' to check if your bot is running properly")
        print("   • Use 'prices' to see current market data")
        print("   • Use 'cryptos' to view your positions and available assets")
        print("   • Use 'quit' to exit gracefully")
        print("   • All commands are case-insensitive")
        print("   • Logs are now human-readable (no more JSON!)")


class TradingBot:
    """
    Main trading bot application.

    This class serves as the entry point for the Robinhood Crypto Trading Bot.
    It manages the application lifecycle, including initialization, starting,
    stopping, and interactive mode.

    Features:
    - Interactive command-line interface for real-time monitoring
    - Live price data fetching from Robinhood API
    - Trading enable/disable controls
    - Component health monitoring
    - Graceful shutdown handling

    Attributes:
        logger: Application logger instance
        orchestrator: Main application orchestrator
        runtime_manager: Interactive mode manager
    """

    def __init__(self):
        """Initialize the trading bot."""
        self.logger = get_logger("main")
        self.orchestrator: Optional[ApplicationOrchestrator] = None
        self.runtime_manager: Optional[RuntimeManager] = None

    async def initialize(self) -> None:
        """Initialize the trading bot."""
        try:
            self.logger.info("Initializing crypto trading bot...")

            # Initialize configuration and logging
            initialize_config()
            setup_logging()

            # Create and initialize orchestrator
            self.orchestrator = ApplicationOrchestrator()
            await self.orchestrator.initialize()

            self.logger.info("Trading bot initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize trading bot: {str(e)}")
            raise

    async def start(self) -> None:
        """Start the trading bot."""
        if not self.orchestrator:
            await self.initialize()

        await self.orchestrator.start()

        # Start runtime manager if available
        if self.runtime_manager:
            self.runtime_manager.start_interactive_mode()

    async def stop(self) -> None:
        """Stop the trading bot."""
        if self.orchestrator:
            await self.orchestrator.stop()

        # Stop runtime manager
        if self.runtime_manager:
            self.runtime_manager.stop_interactive_mode()

    async def run(self) -> None:
        """Run the trading bot until shutdown."""
        if not self.orchestrator:
            await self.initialize()

        # Initialize runtime manager
        if self.orchestrator:
            self.runtime_manager = RuntimeManager(self.orchestrator)

        # Start orchestrator in background task
        orchestrator_task = asyncio.create_task(self.orchestrator.run())

        # Start interactive mode
        if self.runtime_manager:
            self.runtime_manager.start_interactive_mode()

        # Wait for orchestrator to complete (when shutdown signal received)
        await orchestrator_task

    def get_status(self) -> dict:
        """Get current bot status."""
        if self.orchestrator:
            return self.orchestrator.get_status()
        else:
            return {
                'is_running': False,
                'status': 'not_initialized',
                'components': {},
            }


async def main() -> None:
    """Main application entry point."""
    # Check if configuration exists, offer setup if not
    if not check_configuration():
        print("⚙️  No configuration found.")
        setup_response = input("Would you like to set up API credentials now? (Y/n): ").strip().lower()
        if setup_response in ('y', ''):
            setup_api_credentials()
        else:
            print("❌ Configuration required. Please run setup or create config/.env file.")
            print("See README.md for configuration details.")
            sys.exit(1)

    # Run comprehensive connectivity check before starting
    print("\n🔍 Running connectivity checks...")
    print("   This ensures your bot can connect to Robinhood API before starting")

    try:
        from .core.api.connectivity_check import comprehensive_connectivity_check, print_connectivity_status

        # Run connectivity check
        connectivity_result = await comprehensive_connectivity_check()

        # Display results
        print_connectivity_status(connectivity_result)

        # Check if we should proceed
        if not connectivity_result.is_healthy:
            print("\n" + "="*60)
            print("❌ CONNECTIVITY ISSUES PREVENT STARTUP")
            print("="*60)
            print("The trading bot cannot start safely due to connectivity issues.")
            print("Please address the issues above and try again.")
            print("\n💡 Quick fix suggestions:")
            print("   • Check your internet connection")
            print("   • Verify API credentials in config/.env")
            print("   • Run: python verify_connection.py")
            print("   • Check Robinhood API status")
            sys.exit(1)

        print("\n" + "="*60)
        print("✅ CONNECTIVITY CHECK PASSED")
        print("="*60)
        print("All systems are ready! Starting the trading bot...")

    except Exception as e:
        print(f"❌ Error during connectivity check: {str(e)}")
        print("   🔧 Continuing with startup anyway...")
        print("   💡 If issues persist, run: python verify_connection.py")

    bot = TradingBot()

    try:
        print("\n🚀 Starting Robinhood Crypto Trading Bot...")
        print("   🌟 Welcome to automated crypto trading!")
        print("   📱 Press Ctrl+C to stop gracefully")
        print("   🎮 Use interactive commands to monitor your bot")
        await bot.run()
    except KeyboardInterrupt:
        print("\n⏹️  Shutdown requested by user")
        print("   👋 Thanks for using Robinhood Crypto Bot!")
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        print("   🔧 Check your configuration and try again")
        sys.exit(1)
    finally:
        print("✅ Robinhood Crypto Bot shutdown complete")


def main_sync() -> None:
    """Synchronous main entry point."""
    parser = argparse.ArgumentParser(description='Robinhood Crypto Trading Bot')
    parser.add_argument('--no-live', action='store_true', help='Disable live price fetching (use mock data only)')
    args = parser.parse_args()

    global live_prices_enabled
    live_prices_enabled = not args.no_live

    asyncio.run(main())


if __name__ == "__main__":
    main_sync()