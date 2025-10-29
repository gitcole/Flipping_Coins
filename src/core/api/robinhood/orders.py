"""
Robinhood Order Management

Handles order operations including placing, canceling, and tracking
orders for all instrument types on Robinhood.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode

import structlog
from pydantic import BaseModel, Field, field_validator

from ..exceptions import RobinhoodAPIError

logger = structlog.get_logger(__name__)


class Order(BaseModel):
    """Order model for all instrument types."""

    symbol: str = Field(..., description="Instrument symbol")
    quantity: Union[float, str] = Field(..., description="Order quantity")
    side: str = Field(..., description="Order side (buy or sell)")
    order_type: str = Field(..., description="Order type (market, limit, stop, etc.)")
    time_in_force: str = Field(default="gtc", description="Time in force")
    price: Optional[Union[float, str]] = Field(None, description="Limit price")
    stop_price: Optional[Union[float, str]] = Field(None, description="Stop price")
    extended_hours: bool = Field(default=False, description="Allow extended hours")
    account_id: Optional[str] = Field(None, description="Account ID")
    instrument_id: Optional[str] = Field(None, description="Instrument ID")

    @field_validator('side')
    @classmethod
    def validate_side(cls, v):
        if v.lower() not in ['buy', 'sell']:
            raise ValueError('Side must be "buy" or "sell"')
        return v.lower()

    @field_validator('order_type')
    @classmethod
    def validate_order_type(cls, v):
        valid_types = ['market', 'limit', 'stop', 'stop_limit', 'trailing_stop']
        if v.lower() not in valid_types:
            raise ValueError(f'Order type must be one of: {valid_types}')
        return v.lower()

    @field_validator('time_in_force')
    @classmethod
    def validate_time_in_force(cls, v):
        valid_tif = ['gtc', 'gtd', 'ioc', 'fok', 'opg']
        if v.lower() not in valid_tif:
            raise ValueError(f'Time in force must be one of: {valid_tif}')
        return v.lower()


class OrderResponse(BaseModel):
    """Order response model."""

    order_id: str = Field(..., description="Order ID")
    symbol: str = Field(..., description="Instrument symbol")
    quantity: float = Field(..., description="Order quantity")
    side: str = Field(..., description="Order side")
    order_type: str = Field(..., description="Order type")
    time_in_force: str = Field(..., description="Time in force")
    status: str = Field(..., description="Order status")
    price: Optional[float] = Field(None, description="Order price")
    stop_price: Optional[float] = Field(None, description="Stop price")
    filled_quantity: float = Field(..., description="Filled quantity")
    average_fill_price: float = Field(..., description="Average fill price")
    fees: float = Field(..., description="Order fees")
    created_at: str = Field(..., description="Order creation time")
    updated_at: str = Field(..., description="Last update time")
    executed_at: Optional[str] = Field(None, description="Execution time")
    cancelled_at: Optional[str] = Field(None, description="Cancellation time")
    rejected_at: Optional[str] = Field(None, description="Rejection time")
    state: str = Field(..., description="Order state")
    rejection_reason: Optional[str] = Field(None, description="Rejection reason")
    extended_hours: bool = Field(..., description="Extended hours flag")


class OrderFilter(BaseModel):
    """Order filtering options."""

    symbol: Optional[str] = Field(None, description="Filter by symbol")
    side: Optional[str] = Field(None, description="Filter by side")
    order_type: Optional[str] = Field(None, description="Filter by order type")
    status: Optional[str] = Field(None, description="Filter by status")
    start_date: Optional[str] = Field(None, description="Start date filter")
    end_date: Optional[str] = Field(None, description="End date filter")
    account_id: Optional[str] = Field(None, description="Account ID filter")


class RobinhoodOrders:
    """
    Handles order management operations for Robinhood.

    Features:
    - Place orders for stocks, options, and crypto
    - Cancel and modify orders
    - Track order status and history
    - Order filtering and search
    - Bulk order operations
    - Order validation and error handling
    """

    def __init__(self, client: RobinhoodClient):
        """Initialize order management module.

        Args:
            client: Robinhood API client instance
        """
        self.client = client
        self.logger = structlog.get_logger("robinhood.orders")

    async def place_order(self, order: Order) -> OrderResponse:
        """Place a trading order.

        Args:
            order: Order to place

        Returns:
            Order response with order details
        """
        # Validate order
        if order.order_type in ['limit', 'stop_limit', 'trailing_stop'] and not order.price:
            raise ValueError("Price is required for limit orders")

        if order.order_type in ['stop', 'stop_limit'] and not order.stop_price:
            raise ValueError("Stop price is required for stop orders")

        # Get account ID if not provided
        from .account import RobinhoodAccount
        account_module = RobinhoodAccount(self.client)
        account_id = order.account_id or await account_module._get_default_account_id()

        # Get instrument ID if not provided
        instrument_id = order.instrument_id or await self._get_instrument_id(order.symbol)

        # Prepare order data
        order_data = {
            "account": f"account:{account_id}",
            "instrument": f"instrument:{instrument_id}",
            "symbol": order.symbol.upper(),
            "type": order.order_type,
            "time_in_force": order.time_in_force,
            "quantity": str(order.quantity),
            "side": order.side,
        }

        if order.price:
            order_data["price"] = str(order.price)
        if order.stop_price:
            order_data["stop_price"] = str(order.stop_price)
        if order.extended_hours:
            order_data["extended_hours"] = order.extended_hours

        try:
            response = await self.client.post("/orders/", data=order_data)
            self.logger.info("Placed order",
                           symbol=order.symbol,
                           side=order.side,
                           quantity=order.quantity,
                           order_type=order.order_type)

            return await self._parse_order_response(response.data)
        except Exception as e:
            self.logger.error("Failed to place order",
                            symbol=order.symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to place order for {order.symbol}: {e}")

    async def place_market_buy_order(
        self,
        symbol: str,
        quantity: Union[float, str],
        account_id: Optional[str] = None,
        extended_hours: bool = False
    ) -> OrderResponse:
        """Place a market buy order.

        Args:
            symbol: Instrument symbol
            quantity: Order quantity
            account_id: Optional account ID
            extended_hours: Allow extended hours trading

        Returns:
            Order response
        """
        order = Order(
            symbol=symbol,
            quantity=quantity,
            side="buy",
            order_type="market",
            extended_hours=extended_hours,
            account_id=account_id
        )
        return await self.place_order(order)

    async def place_market_sell_order(
        self,
        symbol: str,
        quantity: Union[float, str],
        account_id: Optional[str] = None,
        extended_hours: bool = False
    ) -> OrderResponse:
        """Place a market sell order.

        Args:
            symbol: Instrument symbol
            quantity: Order quantity
            account_id: Optional account ID
            extended_hours: Allow extended hours trading

        Returns:
            Order response
        """
        order = Order(
            symbol=symbol,
            quantity=quantity,
            side="sell",
            order_type="market",
            extended_hours=extended_hours,
            account_id=account_id
        )
        return await self.place_order(order)

    async def place_limit_buy_order(
        self,
        symbol: str,
        quantity: Union[float, str],
        price: Union[float, str],
        account_id: Optional[str] = None,
        time_in_force: str = "gtc",
        extended_hours: bool = False
    ) -> OrderResponse:
        """Place a limit buy order.

        Args:
            symbol: Instrument symbol
            quantity: Order quantity
            price: Limit price
            account_id: Optional account ID
            time_in_force: Time in force policy
            extended_hours: Allow extended hours trading

        Returns:
            Order response
        """
        order = Order(
            symbol=symbol,
            quantity=quantity,
            side="buy",
            order_type="limit",
            price=price,
            time_in_force=time_in_force,
            extended_hours=extended_hours,
            account_id=account_id
        )
        return await self.place_order(order)

    async def place_limit_sell_order(
        self,
        symbol: str,
        quantity: Union[float, str],
        price: Union[float, str],
        account_id: Optional[str] = None,
        time_in_force: str = "gtc",
        extended_hours: bool = False
    ) -> OrderResponse:
        """Place a limit sell order.

        Args:
            symbol: Instrument symbol
            quantity: Order quantity
            price: Limit price
            account_id: Optional account ID
            time_in_force: Time in force policy
            extended_hours: Allow extended hours trading

        Returns:
            Order response
        """
        order = Order(
            symbol=symbol,
            quantity=quantity,
            side="sell",
            order_type="limit",
            price=price,
            time_in_force=time_in_force,
            extended_hours=extended_hours,
            account_id=account_id
        )
        return await self.place_order(order)

    async def place_stop_order(
        self,
        symbol: str,
        quantity: Union[float, str],
        stop_price: Union[float, str],
        side: str = "sell",
        account_id: Optional[str] = None,
        time_in_force: str = "gtc"
    ) -> OrderResponse:
        """Place a stop order.

        Args:
            symbol: Instrument symbol
            quantity: Order quantity
            stop_price: Stop price
            side: Order side (buy or sell)
            account_id: Optional account ID
            time_in_force: Time in force policy

        Returns:
            Order response
        """
        order = Order(
            symbol=symbol,
            quantity=quantity,
            side=side,
            order_type="stop",
            stop_price=stop_price,
            time_in_force=time_in_force,
            account_id=account_id
        )
        return await self.place_order(order)

    async def place_trailing_stop_order(
        self,
        symbol: str,
        quantity: Union[float, str],
        trail_price: Union[float, str],
        side: str = "sell",
        account_id: Optional[str] = None,
        time_in_force: str = "gtc"
    ) -> OrderResponse:
        """Place a trailing stop order.

        Args:
            symbol: Instrument symbol
            quantity: Order quantity
            trail_price: Trailing price offset
            side: Order side (buy or sell)
            account_id: Optional account ID
            time_in_force: Time in force policy

        Returns:
            Order response
        """
        order = Order(
            symbol=symbol,
            quantity=quantity,
            side=side,
            order_type="trailing_stop",
            price=trail_price,  # For trailing stops, price is the trail amount
            time_in_force=time_in_force,
            account_id=account_id
        )
        return await self.place_order(order)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancellation successful
        """
        try:
            await self.client.delete(f"/orders/{order_id}/")
            self.logger.info("Cancelled order", order_id=order_id)
            return True
        except Exception as e:
            self.logger.error("Failed to cancel order", order_id=order_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to cancel order {order_id}: {e}")

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """Cancel all open orders.

        Args:
            symbol: Optional symbol filter

        Returns:
            Number of orders cancelled
        """
        try:
            orders = await self.get_orders(status="open", symbol=symbol)
            cancelled_count = 0

            for order in orders:
                try:
                    await self.cancel_order(order.order_id)
                    cancelled_count += 1
                except Exception as e:
                    self.logger.warning("Failed to cancel order",
                                      order_id=order.order_id, error=str(e))

            self.logger.info("Cancelled orders", count=cancelled_count, symbol=symbol)
            return cancelled_count
        except Exception as e:
            self.logger.error("Failed to cancel all orders", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to cancel all orders: {e}")

    async def get_order(self, order_id: str) -> OrderResponse:
        """Get order details.

        Args:
            order_id: Order ID

        Returns:
            Order details
        """
        try:
            response = await self.client.get(f"/orders/{order_id}/")
            return await self._parse_order_response(response.data)
        except Exception as e:
            self.logger.error("Failed to get order", order_id=order_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get order {order_id}: {e}")

    async def get_orders(
        self,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        order_type: Optional[str] = None,
        account_id: Optional[str] = None,
        limit: int = 100
    ) -> List[OrderResponse]:
        """Get orders with optional filtering.

        Args:
            status: Order status filter
            symbol: Symbol filter
            side: Side filter
            order_type: Order type filter
            account_id: Account ID filter
            limit: Maximum number of orders

        Returns:
            List of orders
        """
        params = {"limit": limit}

        if status:
            params["status"] = status
        if symbol:
            params["symbol"] = symbol
        if side:
            params["side"] = side
        if order_type:
            params["type"] = order_type
        if account_id:
            params["account_id"] = account_id

        try:
            response = await self.client.get("/orders/", params=params)
            orders_data = response.data.get("results", [])
            orders = []

            for order_data in orders_data:
                orders.append(await self._parse_order_response(order_data))

            return orders
        except Exception as e:
            self.logger.error("Failed to get orders",
                            status=status, symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get orders: {e}")

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResponse]:
        """Get all open orders.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of open orders
        """
        return await self.get_orders(status="open", symbol=symbol)

    async def get_order_history(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[OrderResponse]:
        """Get order history.

        Args:
            symbol: Optional symbol filter
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of orders

        Returns:
            List of historical orders
        """
        params = {"limit": limit}

        if symbol:
            params["symbol"] = symbol
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        try:
            response = await self.client.get("/orders/history/", params=params)
            orders_data = response.data.get("results", [])
            orders = []

            for order_data in orders_data:
                orders.append(await self._parse_order_response(order_data))

            return orders
        except Exception as e:
            self.logger.error("Failed to get order history", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get order history: {e}")

    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[Union[float, str]] = None,
        price: Optional[Union[float, str]] = None,
        stop_price: Optional[Union[float, str]] = None,
        time_in_force: Optional[str] = None
    ) -> OrderResponse:
        """Modify an existing order.

        Args:
            order_id: Order ID to modify
            quantity: New quantity
            price: New price
            stop_price: New stop price
            time_in_force: New time in force

        Returns:
            Updated order information
        """
        # Get current order
        current_order = await self.get_order(order_id)

        # Prepare update data
        update_data = {}
        if quantity is not None:
            update_data["quantity"] = str(quantity)
        if price is not None:
            update_data["price"] = str(price)
        if stop_price is not None:
            update_data["stop_price"] = str(stop_price)
        if time_in_force is not None:
            update_data["time_in_force"] = time_in_force

        try:
            response = await self.client.patch(f"/orders/{order_id}/", data=update_data)
            self.logger.info("Modified order", order_id=order_id)
            return await self._parse_order_response(response.data)
        except Exception as e:
            self.logger.error("Failed to modify order", order_id=order_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to modify order {order_id}: {e}")

    async def replace_order(self, order_id: str, new_order: Order) -> OrderResponse:
        """Replace an existing order with a new one.

        Args:
            order_id: Order ID to replace
            new_order: New order parameters

        Returns:
            New order information
        """
        # Cancel the old order first
        await self.cancel_order(order_id)

        # Place the new order
        return await self.place_order(new_order)

    async def get_order_executions(self, order_id: str) -> List[Dict]:
        """Get execution details for an order.

        Args:
            order_id: Order ID

        Returns:
            List of execution details
        """
        try:
            response = await self.client.get(f"/orders/{order_id}/executions/")
            return response.data.get("results", [])
        except Exception as e:
            self.logger.error("Failed to get order executions", order_id=order_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get executions for order {order_id}: {e}")

    async def _parse_order_response(self, order_data: Dict) -> OrderResponse:
        """Parse order response data into OrderResponse model.

        Args:
            order_data: Raw order data from API

        Returns:
            Parsed order response
        """
        return OrderResponse(
            order_id=order_data.get("id", ""),
            symbol=order_data.get("symbol", ""),
            quantity=float(order_data.get("quantity", 0)),
            side=order_data.get("side", ""),
            order_type=order_data.get("type", ""),
            time_in_force=order_data.get("time_in_force", ""),
            status=order_data.get("status", ""),
            price=float(order_data.get("price", 0)) if order_data.get("price") else None,
            stop_price=float(order_data.get("stop_price", 0)) if order_data.get("stop_price") else None,
            filled_quantity=float(order_data.get("filled_quantity", 0)),
            average_fill_price=float(order_data.get("average_fill_price", 0)),
            fees=float(order_data.get("fees", 0)),
            created_at=order_data.get("created_at", ""),
            updated_at=order_data.get("updated_at", ""),
            executed_at=order_data.get("executed_at"),
            cancelled_at=order_data.get("cancelled_at"),
            rejected_at=order_data.get("rejected_at"),
            state=order_data.get("state", ""),
            rejection_reason=order_data.get("rejection_reason"),
            extended_hours=order_data.get("extended_hours", False),
        )


    async def _get_instrument_id(self, symbol: str) -> str:
        """Get instrument ID for a symbol.

        Args:
            symbol: Instrument symbol

        Returns:
            Instrument ID

        Raises:
            RobinhoodAPIError: If symbol not found
        """
        try:
            response = await self.client.get("/instruments/", params={"symbol": symbol.upper()})
            instruments = response.data.get("results", [])

            if not instruments:
                raise RobinhoodAPIError(f"Symbol {symbol} not found")

            return instruments[0]["id"]
        except Exception as e:
            self.logger.error("Failed to get instrument ID", symbol=symbol, error=str(e))
            raise RobinhoodAPIError(f"Failed to get instrument ID for {symbol}: {e}")

    async def validate_order(self, order: Order) -> Dict:
        """Validate an order before placing.

        Args:
            order: Order to validate

        Returns:
            Validation result with any warnings or errors
        """
        validation_result = {
            "valid": True,
            "warnings": [],
            "errors": []
        }

        try:
            # Check if symbol exists
            await self._get_instrument_id(order.symbol)

            # Check if account exists and has permissions
            if order.account_id:
                account_id = order.account_id
            else:
                from .account import RobinhoodAccount
                account_module = RobinhoodAccount(self.client)
                account_id = await account_module._get_default_account_id()

            # Additional validation logic can be added here
            # - Check buying power
            # - Check position limits
            # - Check trading hours
            # - Check order size limits

            return validation_result

        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(str(e))
            return validation_result

    async def get_order_summary(self, account_id: Optional[str] = None) -> Dict:
        """Get order summary for an account.

        Args:
            account_id: Optional account ID

        Returns:
            Order summary statistics
        """
        try:
            orders = await self.get_orders(account_id=account_id, limit=1000)

            summary = {
                "total_orders": len(orders),
                "open_orders": len([o for o in orders if o.status.lower() == "open"]),
                "filled_orders": len([o for o in orders if o.status.lower() == "filled"]),
                "cancelled_orders": len([o for o in orders if o.status.lower() == "cancelled"]),
                "rejected_orders": len([o for o in orders if o.status.lower() == "rejected"]),
                "total_fees": sum(o.fees for o in orders),
                "total_quantity": sum(o.quantity for o in orders),
                "buy_orders": len([o for o in orders if o.side.lower() == "buy"]),
                "sell_orders": len([o for o in orders if o.side.lower() == "sell"]),
            }

            return summary
        except Exception as e:
            self.logger.error("Failed to get order summary", account_id=account_id, error=str(e))
            raise RobinhoodAPIError(f"Failed to get order summary: {e}")

    async def bulk_cancel_orders(self, order_ids: List[str]) -> Dict:
        """Cancel multiple orders in bulk.

        Args:
            order_ids: List of order IDs to cancel

        Returns:
            Bulk cancellation results
        """
        results = {
            "successful": [],
            "failed": [],
            "total_requested": len(order_ids)
        }

        for order_id in order_ids:
            try:
                await self.cancel_order(order_id)
                results["successful"].append(order_id)
            except Exception as e:
                self.logger.warning("Failed to cancel order in bulk",
                                  order_id=order_id, error=str(e))
                results["failed"].append({"order_id": order_id, "error": str(e)})

        self.logger.info("Bulk cancel completed",
                        total=results["total_requested"],
                        successful=len(results["successful"]),
                        failed=len(results["failed"]))

        return results