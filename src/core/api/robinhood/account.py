"""
Robinhood Account Management

Handles account information, portfolio data, positions, and balances
for Robinhood trading accounts.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional, Union, TYPE_CHECKING
from urllib.parse import urlencode

import structlog
from pydantic import BaseModel, Field, validator

from ..exceptions import RobinhoodAPIError

if TYPE_CHECKING:
    from .client import RobinhoodClient

logger = structlog.get_logger(__name__)


class AccountProfile(BaseModel):
    """Account profile information."""

    account_id: str = Field(..., description="Account ID")
    account_number: str = Field(..., description="Account number")
    account_type: str = Field(..., description="Account type")
    status: str = Field(..., description="Account status")
    currency: str = Field(..., description="Account currency")
    buying_power: float = Field(..., description="Buying power")
    cash_balance: float = Field(..., description="Cash balance")
    portfolio_value: float = Field(..., description="Portfolio value")
    day_trading_count: int = Field(..., description="Day trading count")
    day_trading_remaining: int = Field(..., description="Remaining day trades")
    maintenance_excess: float = Field(..., description="Maintenance excess")
    uncleared_deposits: float = Field(..., description="Uncleared deposits")
    unsettled_funds: float = Field(..., description="Unsettled funds")
    crypto_buying_power: float = Field(..., description="Crypto buying power")
    max_ach_early_access_amount: float = Field(..., description="Max ACH early access")
    cash_available_for_withdrawal: float = Field(..., description="Cash available for withdrawal")
    sma: float = Field(..., description="Special memorandum account")
    sweep_enabled: bool = Field(..., description="Sweep enabled")
    instant_eligibility: Dict = Field(..., description="Instant eligibility info")
    option_level: str = Field(..., description="Options trading level")
    shorting_enabled: bool = Field(..., description="Shorting enabled")
    crypto_trading_enabled: bool = Field(..., description="Crypto trading enabled")
    fractional_trading: bool = Field(..., description="Fractional trading enabled")


class Position(BaseModel):
    """Portfolio position model."""

    symbol: str = Field(..., description="Instrument symbol")
    instrument_id: str = Field(..., description="Instrument ID")
    quantity: float = Field(..., description="Position quantity")
    average_buy_price: float = Field(..., description="Average buy price")
    current_price: float = Field(..., description="Current price")
    market_value: float = Field(..., description="Market value")
    cost_basis: float = Field(..., description="Cost basis")
    unrealized_pl: float = Field(..., description="Unrealized P&L")
    unrealized_pl_percent: float = Field(..., description="Unrealized P&L percentage")
    shares_available_for_exercise: float = Field(..., description="Shares available for exercise")
    shares_pending: float = Field(..., description="Shares pending")
    shares_held_for_options_collateral: float = Field(..., description="Shares for options collateral")
    shares_held_for_options_events: float = Field(..., description="Shares for options events")
    shares_held_for_stock_grants: float = Field(..., description="Shares for stock grants")
    intraday_average_buy_price: float = Field(..., description="Intraday average buy price")
    intraday_quantity: float = Field(..., description="Intraday quantity")
    shares_held_for_sells: float = Field(..., description="Shares held for sells")
    shares_held_for_buys: float = Field(..., description="Shares held for buys")
    shares_available_for_closing_short_positions: float = Field(..., description="Shares for closing shorts")


class PortfolioSummary(BaseModel):
    """Portfolio summary information."""

    account_id: str = Field(..., description="Account ID")
    total_value: float = Field(..., description="Total portfolio value")
    extended_hours_value: float = Field(..., description="Extended hours value")
    total_return: float = Field(..., description="Total return")
    total_return_percent: float = Field(..., description="Total return percentage")
    adjusted_total_return: float = Field(..., description="Adjusted total return")
    adjusted_total_return_percent: float = Field(..., description="Adjusted total return percentage")
    start_date: str = Field(..., description="Portfolio start date")
    market_value: float = Field(..., description="Market value")
    cash_value: float = Field(..., description="Cash value")
    base_currency: str = Field(..., description="Base currency")


class Dividend(BaseModel):
    """Dividend information."""

    symbol: str = Field(..., description="Symbol")
    instrument_id: str = Field(..., description="Instrument ID")
    amount: float = Field(..., description="Dividend amount")
    currency: str = Field(..., description="Currency")
    ex_dividend_date: str = Field(..., description="Ex-dividend date")
    payable_date: str = Field(..., description="Payable date")
    record_date: str = Field(..., description="Record date")
    state: str = Field(..., description="Dividend state")
    position_id: str = Field(..., description="Position ID")


class RobinhoodAccount:
    """
    Handles account and portfolio operations for Robinhood.

    Features:
    - Account information and profiles
    - Portfolio management and summaries
    - Position tracking and management
    - Balance and buying power information
    - Dividend tracking
    - Account settings and preferences
    - Trading permissions and restrictions
    """

    def __init__(self, client: RobinhoodClient):
        """Initialize account management module.

        Args:
            client: Robinhood API client instance
        """
        self.client = client
        self.logger = structlog.get_logger("robinhood.account")

    async def get_accounts(self) -> List[Dict]:
        """Get all user accounts.

        Returns:
            List of account information
        """
        try:
            response = await self.client.get("/accounts/")
            return response.data.get("results", [])
        except Exception as e:
            self.logger.error("Failed to get accounts", error=str(e))
            raise RobinhoodAPIError(f"Failed to get accounts: {e}")

    async def get_account_profile(self, account_id: Optional[str] = None) -> AccountProfile:
        """Get account profile information.

        Args:
            account_id: Optional account ID (uses default if not provided)

        Returns:
            Account profile information
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            response = await self.client.get(f"/accounts/{account_id}/")
            account_data = response.data

            return AccountProfile(
                account_id=account_data.get("id", ""),
                account_number=account_data.get("account_number", ""),
                account_type=account_data.get("type", ""),
                status=account_data.get("status", ""),
                currency=account_data.get("currency", "USD"),
                buying_power=float(account_data.get("buying_power", 0)),
                cash_balance=float(account_data.get("cash", 0)),
                portfolio_value=float(account_data.get("portfolio_value", 0)),
                day_trading_count=int(account_data.get("day_trading_count", 0)),
                day_trading_remaining=int(account_data.get("day_trading_remaining", 0)),
                maintenance_excess=float(account_data.get("maintenance_excess", 0)),
                uncleared_deposits=float(account_data.get("uncleared_deposits", 0)),
                unsettled_funds=float(account_data.get("unsettled_funds", 0)),
                crypto_buying_power=float(account_data.get("crypto_buying_power", 0)),
                max_ach_early_access_amount=float(account_data.get("max_ach_early_access_amount", 0)),
                cash_available_for_withdrawal=float(account_data.get("cash_available_for_withdrawal", 0)),
                sma=float(account_data.get("sma", 0)),
                sweep_enabled=account_data.get("sweep_enabled", False),
                instant_eligibility=account_data.get("instant_eligibility", {}),
                option_level=account_data.get("option_level", ""),
                shorting_enabled=account_data.get("shorting_enabled", False),
                crypto_trading_enabled=account_data.get("crypto_trading_enabled", False),
                fractional_trading=account_data.get("fractional_trading", False),
            )
        except Exception as e:
            self.logger.error("Failed to get account profile", account_id=account_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get account profile: {e}")

    async def get_portfolio_summary(self, account_id: Optional[str] = None) -> PortfolioSummary:
        """Get portfolio summary.

        Args:
            account_id: Optional account ID (uses default if not provided)

        Returns:
            Portfolio summary information
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            response = await self.client.get(f"/portfolios/{account_id}/")
            portfolio_data = response.data

            return PortfolioSummary(
                account_id=portfolio_data.get("account", ""),
                total_value=float(portfolio_data.get("total_value", 0)),
                extended_hours_value=float(portfolio_data.get("extended_hours_value", 0)),
                total_return=float(portfolio_data.get("total_return", 0)),
                total_return_percent=float(portfolio_data.get("total_return_percent", 0)),
                adjusted_total_return=float(portfolio_data.get("adjusted_total_return", 0)),
                adjusted_total_return_percent=float(portfolio_data.get("adjusted_total_return_percent", 0)),
                start_date=portfolio_data.get("start_date", ""),
                market_value=float(portfolio_data.get("market_value", 0)),
                cash_value=float(portfolio_data.get("cash_value", 0)),
                base_currency=portfolio_data.get("base_currency", "USD"),
            )
        except Exception as e:
            self.logger.error("Failed to get portfolio summary", account_id=account_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get portfolio summary: {e}")

    async def get_positions(self, account_id: Optional[str] = None) -> List[Position]:
        """Get account positions.

        Args:
            account_id: Optional account ID (uses default if not provided)

        Returns:
            List of position information
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            response = await self.client.get(f"/positions/?account={account_id}")
            positions_data = response.data.get("results", [])
            positions = []

            for pos_data in positions_data:
                positions.append(Position(
                    symbol=pos_data.get("symbol", ""),
                    instrument_id=pos_data.get("instrument_id", ""),
                    quantity=float(pos_data.get("quantity", 0)),
                    average_buy_price=float(pos_data.get("average_buy_price", 0)),
                    current_price=float(pos_data.get("current_price", 0)),
                    market_value=float(pos_data.get("market_value", 0)),
                    cost_basis=float(pos_data.get("cost_basis", 0)),
                    unrealized_pl=float(pos_data.get("unrealized_pl", 0)),
                    unrealized_pl_percent=float(pos_data.get("unrealized_pl_percent", 0)),
                    shares_available_for_exercise=float(pos_data.get("shares_available_for_exercise", 0)),
                    shares_pending=float(pos_data.get("shares_pending", 0)),
                    shares_held_for_options_collateral=float(pos_data.get("shares_held_for_options_collateral", 0)),
                    shares_held_for_options_events=float(pos_data.get("shares_held_for_options_events", 0)),
                    shares_held_for_stock_grants=float(pos_data.get("shares_held_for_stock_grants", 0)),
                    intraday_average_buy_price=float(pos_data.get("intraday_average_buy_price", 0)),
                    intraday_quantity=float(pos_data.get("intraday_quantity", 0)),
                    shares_held_for_sells=float(pos_data.get("shares_held_for_sells", 0)),
                    shares_held_for_buys=float(pos_data.get("shares_held_for_buys", 0)),
                    shares_available_for_closing_short_positions=float(pos_data.get("shares_available_for_closing_short_positions", 0)),
                ))

            return positions
        except Exception as e:
            self.logger.error("Failed to get positions", account_id=account_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get positions: {e}")

    async def get_position(self, symbol: str, account_id: Optional[str] = None) -> Optional[Position]:
        """Get specific position.

        Args:
            symbol: Instrument symbol
            account_id: Optional account ID

        Returns:
            Position information or None if not found
        """
        positions = await self.get_positions(account_id)
        for position in positions:
            if position.symbol.upper() == symbol.upper():
                return position
        return None

    async def get_dividends(
        self,
        account_id: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[Dividend]:
        """Get dividend information.

        Args:
            account_id: Optional account ID
            symbol: Optional symbol filter

        Returns:
            List of dividend information
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            endpoint = f"/dividends/?account_id={account_id}"
            if symbol:
                endpoint += f"&symbol={symbol}"

            response = await self.client.get(endpoint)
            dividends_data = response.data.get("results", [])
            dividends = []

            for div_data in dividends_data:
                dividends.append(Dividend(
                    symbol=div_data.get("symbol", ""),
                    instrument_id=div_data.get("instrument_id", ""),
                    amount=float(div_data.get("amount", 0)),
                    currency=div_data.get("currency", "USD"),
                    ex_dividend_date=div_data.get("ex_dividend_date", ""),
                    payable_date=div_data.get("payable_date", ""),
                    record_date=div_data.get("record_date", ""),
                    state=div_data.get("state", ""),
                    position_id=div_data.get("position_id", ""),
                ))

            return dividends
        except Exception as e:
            self.logger.error("Failed to get dividends", account_id=account_id, symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get dividends: {e}")

    async def get_watchlists(self) -> List[Dict]:
        """Get user watchlists.

        Returns:
            List of watchlist information
        """
        try:
            response = await self.client.get("/watchlists/")
            return response.data.get("results", [])
        except Exception as e:
            self.logger.error("Failed to get watchlists", error=str(e))
            raise RobinhoodAPIError(f"Failed to get watchlists: {e}")

    async def create_watchlist(self, name: str) -> Dict:
        """Create a new watchlist.

        Args:
            name: Watchlist name

        Returns:
            Created watchlist information
        """
        try:
            data = {"name": name}
            response = await self.client.post("/watchlists/", data=data)
            self.logger.info("Created watchlist", name=name)
            return response.data
        except Exception as e:
            self.logger.error("Failed to create watchlist", name=name, error=str(e))
            raise RobinhoodAPIError(f"Failed to create watchlist: {e}")

    async def delete_watchlist(self, watchlist_id: str) -> bool:
        """Delete a watchlist.

        Args:
            watchlist_id: Watchlist ID to delete

        Returns:
            True if deletion successful
        """
        try:
            await self.client.delete(f"/watchlists/{watchlist_id}/")
            self.logger.info("Deleted watchlist", watchlist_id=watchlist_id)
            return True
        except Exception as e:
            self.logger.error("Failed to delete watchlist", watchlist_id=watchlist_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to delete watchlist: {e}")

    async def add_to_watchlist(self, watchlist_id: str, symbol: str) -> Dict:
        """Add symbol to watchlist.

        Args:
            watchlist_id: Watchlist ID
            symbol: Symbol to add

        Returns:
            Updated watchlist information
        """
        try:
            response = await self.client.get(f"/instruments/?symbol={symbol}")
            instruments = response.data.get("results", [])

            if not instruments:
                raise RobinhoodAPIError(f"Symbol {symbol} not found")

            instrument_id = instruments[0]["id"]
            data = {"instrument": {"id": instrument_id}}

            response = await self.client.post(f"/watchlists/{watchlist_id}/", data=data)
            self.logger.info("Added to watchlist", watchlist_id=watchlist_id, symbol=symbol)
            return response.data
        except Exception as e:
            self.logger.error("Failed to add to watchlist",
                           watchlist_id=watchlist_id, symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to add {symbol} to watchlist: {e}")

    async def remove_from_watchlist(self, watchlist_id: str, symbol: str) -> bool:
        """Remove symbol from watchlist.

        Args:
            watchlist_id: Watchlist ID
            symbol: Symbol to remove

        Returns:
            True if removal successful
        """
        try:
            # Get watchlist items first to find the specific item ID
            response = await self.client.get(f"/watchlists/{watchlist_id}/")
            watchlist_data = response.data

            # Find the item with the symbol
            for item in watchlist_data.get("watchlist_items", []):
                if item.get("instrument", {}).get("symbol", "").upper() == symbol.upper():
                    item_id = item["id"]
                    await self.client.delete(f"/watchlists/{watchlist_id}/{item_id}/")
                    self.logger.info("Removed from watchlist",
                                   watchlist_id=watchlist_id, symbol=symbol)
                    return True

            return False  # Symbol not found in watchlist
        except Exception as e:
            self.logger.error("Failed to remove from watchlist",
                           watchlist_id=watchlist_id, symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to remove {symbol} from watchlist: {e}")

    async def get_account_history(
        self,
        account_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "day"
    ) -> List[Dict]:
        """Get account history and performance data.

        Args:
            account_id: Optional account ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval (day, week, month)

        Returns:
            Account history data
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            params = {"account_id": account_id, "interval": interval}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date

            response = await self.client.get("/portfolios/historicals/", params=params)
            return response.data.get("results", [])
        except Exception as e:
            self.logger.error("Failed to get account history",
                           account_id=account_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get account history: {e}")

    async def get_ach_relationships(self) -> List[Dict]:
        """Get ACH relationships for bank transfers.

        Returns:
            List of ACH relationships
        """
        try:
            response = await self.client.get("/ach_relationships/")
            return response.data.get("results", [])
        except Exception as e:
            self.logger.error("Failed to get ACH relationships", error=str(e))
            raise RobinhoodAPIError(f"Failed to get ACH relationships: {e}")

    async def get_linked_bank_accounts(self) -> List[Dict]:
        """Get linked bank accounts.

        Returns:
            List of linked bank accounts
        """
        try:
            response = await self.client.get("/linked/bank_accounts/")
            return response.data.get("results", [])
        except Exception as e:
            self.logger.error("Failed to get linked bank accounts", error=str(e))
            raise RobinhoodAPIError(f"Failed to get linked bank accounts: {e}")

    async def get_transfer_history(
        self,
        account_id: Optional[str] = None,
        direction: Optional[str] = None
    ) -> List[Dict]:
        """Get transfer history.

        Args:
            account_id: Optional account ID
            direction: Transfer direction (in, out)

        Returns:
            List of transfer records
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            endpoint = f"/transfers/?account_id={account_id}"
            if direction:
                endpoint += f"&direction={direction}"

            response = await self.client.get(endpoint)
            return response.data.get("results", [])
        except Exception as e:
            self.logger.error("Failed to get transfer history", account_id=account_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get transfer history: {e}")

    async def get_margin_calls(self, account_id: Optional[str] = None) -> List[Dict]:
        """Get margin calls.

        Args:
            account_id: Optional account ID

        Returns:
            List of margin calls
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            response = await self.client.get(f"/margin_calls/?account_id={account_id}")
            return response.data.get("results", [])
        except Exception as e:
            self.logger.error("Failed to get margin calls", account_id=account_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get margin calls: {e}")

    async def get_documents(self, account_id: Optional[str] = None) -> List[Dict]:
        """Get account documents.

        Args:
            account_id: Optional account ID

        Returns:
            List of account documents
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            response = await self.client.get(f"/documents/?account_id={account_id}")
            return response.data.get("results", [])
        except Exception as e:
            self.logger.error("Failed to get documents", account_id=account_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get documents: {e}")

    async def get_notifications(self) -> List[Dict]:
        """Get account notifications.

        Returns:
            List of notifications
        """
        try:
            response = await self.client.get("/notifications/")
            return response.data.get("results", [])
        except Exception as e:
            self.logger.error("Failed to get notifications", error=str(e))
            raise RobinhoodAPIError(f"Failed to get notifications: {e}")

    async def get_subscription_fees(self, account_id: Optional[str] = None) -> Dict:
        """Get subscription fees for the account.

        Args:
            account_id: Optional account ID

        Returns:
            Subscription fees information
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            response = await self.client.get(f"/subscription/fees/?account_id={account_id}")
            return response.data
        except Exception as e:
            self.logger.error("Failed to get subscription fees", account_id=account_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get subscription fees: {e}")

    async def _get_default_account_id(self) -> str:
        """Get the default account ID.

        Returns:
            Default account ID

        Raises:
            RobinhoodAPIError: If no accounts found
        """
        try:
            accounts = await self.get_accounts()
            if not accounts:
                raise RobinhoodAPIError("No accounts found")

            # Return the first account (usually the default)
            return accounts[0]["id"]
        except Exception as e:
            self.logger.error("Failed to get default account ID", error=str(e))
            raise RobinhoodAPIError(f"Failed to get default account ID: {e}")

    async def get_account_analytics(self, account_id: Optional[str] = None) -> Dict:
        """Get account analytics and insights.

        Args:
            account_id: Optional account ID

        Returns:
            Account analytics data
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            response = await self.client.get(f"/accounts/{account_id}/analytics/")
            return response.data
        except Exception as e:
            self.logger.error("Failed to get account analytics", account_id=account_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get account analytics: {e}")

    async def get_risk_assessment(self, account_id: Optional[str] = None) -> Dict:
        """Get risk assessment for the account.

        Args:
            account_id: Optional account ID

        Returns:
            Risk assessment data
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            response = await self.client.get(f"/accounts/{account_id}/risk_assessment/")
            return response.data
        except Exception as e:
            self.logger.error("Failed to get risk assessment", account_id=account_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get risk assessment: {e}")

    async def get_investment_objective(self, account_id: Optional[str] = None) -> Dict:
        """Get investment objective settings.

        Args:
            account_id: Optional account ID

        Returns:
            Investment objective data
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            response = await self.client.get(f"/accounts/{account_id}/investment_objective/")
            return response.data
        except Exception as e:
            self.logger.error("Failed to get investment objective",
                           account_id=account_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get investment objective: {e}")

    async def get_employment_status(self, account_id: Optional[str] = None) -> Dict:
        """Get employment status information.

        Args:
            account_id: Optional account ID

        Returns:
            Employment status data
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            response = await self.client.get(f"/accounts/{account_id}/employment/")
            return response.data
        except Exception as e:
            self.logger.error("Failed to get employment status",
                           account_id=account_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get employment status: {e}")

    async def get_financial_suitability(self, account_id: Optional[str] = None) -> Dict:
        """Get financial suitability information.

        Args:
            account_id: Optional account ID

        Returns:
            Financial suitability data
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            response = await self.client.get(f"/accounts/{account_id}/suitability/")
            return response.data
        except Exception as e:
            self.logger.error("Failed to get financial suitability",
                           account_id=account_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get financial suitability: {e}")

    async def get_tax_documents(self, account_id: Optional[str] = None, year: Optional[int] = None) -> List[Dict]:
        """Get tax documents.

        Args:
            account_id: Optional account ID
            year: Tax year

        Returns:
            List of tax documents
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            endpoint = f"/tax_documents/?account_id={account_id}"
            if year:
                endpoint += f"&year={year}"

            response = await self.client.get(endpoint)
            return response.data.get("results", [])
        except Exception as e:
            self.logger.error("Failed to get tax documents", account_id=account_id, year=year, error=str(e))
            raise RobinhoodAPIError(f"Failed to get tax documents: {e}")

    async def get_monthly_statement(
        self,
        account_id: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> Dict:
        """Get monthly statement.

        Args:
            account_id: Optional account ID
            year: Statement year (default: current year)
            month: Statement month (default: current month)

        Returns:
            Monthly statement data
        """
        try:
            if account_id is None:
                account_id = await self._get_default_account_id()

            if year is None:
                year = datetime.now().year
            if month is None:
                month = datetime.now().month

            response = await self.client.get(f"/statements/{account_id}/{year}/{month:02d}/")
            return response.data
        except Exception as e:
            self.logger.error("Failed to get monthly statement",
                           account_id=account_id, year=year, month=month, error=str(e))
            raise RobinhoodAPIError(f"Failed to get monthly statement: {e}")