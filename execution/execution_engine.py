"""
execution/execution_engine.py


============================================================

Execution Engine V2

============================================================


职责：

    Order
        ↓
    ExecutionEngine
        ↓
    Fill
        ↓
    Portfolio


============================================================


负责：

    - Order执行
    - 模拟撮合
    - 生成Fill
    - Order状态管理
    - Execution统计
    - Fill回调


不负责：

    - Strategy
    - Risk
    - Portfolio计算
    - Position管理
    - PnL


============================================================


运行模式：

    BACKTEST

        历史行情模拟成交


    PAPER

        实时行情模拟成交


    LIVE

        Broker执行接口


============================================================


MARKET Order Price Rule：

    优先级：

        1. state.last_price
           用于已有测试 / 简单模拟环境

        2. state.orderbook
           用于真实 L3 Runtime


    BUY MARKET：

        Best Ask


    SELL MARKET：

        Best Bid


============================================================


Databento Price：

    OrderBook 当前保存的是 Databento 原始 nano-dollar：

        7557000000000

    Execution Fill 使用正常交易价格：

        7557.00


    因此：

        OrderBook Raw Price
             ↓
        Execution
             ↓
        Normalized Fill Price


============================================================

Fill Contract：

    Fill 唯一定义：

        execution/fill.py

    ExecutionEngine 不再维护内部重复 Fill 类型。

============================================================

"""


from enum import Enum
from typing import (
    Optional,
    Dict,
    Any,
    List,
    Callable,
)


from order.order import (
    Order,
    OrderStatus,
    OrderSide,
)

from execution.fill import Fill


# ============================================================
# Execution Mode
# ============================================================


class ExecutionMode(Enum):
    """
    Execution运行模式。
    """

    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    LIVE = "LIVE"


# ============================================================
# Execution Engine
# ============================================================


class ExecutionEngine:
    """
    执行引擎。

    交易链：

        Order
          ↓
        ExecutionEngine
          ↓
        Fill
          ↓
        Portfolio.on_fill()
    """

    def __init__(
        self,
        mode: ExecutionMode = ExecutionMode.BACKTEST,
        on_fill: Optional[
            Callable[[Fill], None]
        ] = None,
    ):

        self.mode = mode
        self.on_fill = on_fill

        self.total_orders = 0
        self.total_fills = 0
        self.volume = 0
        self.cancelled_orders = 0

        self.orders: Dict[
            str,
            Order
        ] = {}

        self.order_history: List[
            Order
        ] = []

        self.fills: List[
            Fill
        ] = []

        self.last_fill: Optional[
            Fill
        ] = None

    # ========================================================
    # Submit Order
    # ========================================================

    def submit_order(
        self,
        order: Order,
    ):
        if not order.validate():
            raise ValueError(
                "Invalid Order"
            )

        order.submit()

        self.orders[
            order.order_id
        ] = order

        self.order_history.append(
            order
        )

        self.total_orders += 1

        return order

    # ========================================================
    # Engine Compatibility Submit
    # ========================================================

    def submit(
        self,
        order: Order,
        state=None,
    ):
        market_price = None

        if state is not None:
            market_price = getattr(
                state,
                "last_price",
                None,
            )

        if (
            market_price is None
            and state is not None
        ):
            market_price = (
                self._market_price_from_state(
                    order,
                    state,
                )
            )

        return self.execute(
            order,
            market_price=market_price,
        )

    # ========================================================
    # Market Price From State
    # ========================================================

    def _market_price_from_state(
        self,
        order: Order,
        state,
    ):
        orderbook = getattr(
            state,
            "orderbook",
            None,
        )

        if orderbook is None:
            return None

        book = getattr(
            orderbook,
            "book",
            orderbook,
        )

        if order.side == OrderSide.BUY:
            raw_price = self._get_best_ask(
                book
            )

        elif order.side == OrderSide.SELL:
            raw_price = self._get_best_bid(
                book
            )

        else:
            raise ValueError(
                "Unsupported OrderSide for "
                f"MARKET execution: {order.side}"
            )

        if raw_price is None:
            return None

        return self._normalize_market_price(
            raw_price
        )

    # ========================================================
    # Best Bid
    # ========================================================

    @staticmethod
    def _get_best_bid(
        book,
    ):
        if hasattr(
            book,
            "best_bid",
        ):
            value = getattr(
                book,
                "best_bid",
            )

            if callable(value):
                value = value()

            value = (
                ExecutionEngine
                ._extract_price_value(
                    value
                )
            )

            if value is not None:
                return value

        bids = getattr(
            book,
            "bids",
            None,
        )

        if bids:
            return max(
                bids.keys()
            )

        return None

    # ========================================================
    # Best Ask
    # ========================================================

    @staticmethod
    def _get_best_ask(
        book,
    ):
        if hasattr(
            book,
            "best_ask",
        ):
            value = getattr(
                book,
                "best_ask",
            )

            if callable(value):
                value = value()

            value = (
                ExecutionEngine
                ._extract_price_value(
                    value
                )
            )

            if value is not None:
                return value

        asks = getattr(
            book,
            "asks",
            None,
        )

        if asks:
            return min(
                asks.keys()
            )

        return None

    # ========================================================
    # Extract Price
    # ========================================================

    @staticmethod
    def _extract_price_value(
        value,
    ):
        if value is None:
            return None

        if isinstance(
            value,
            (int, float),
        ):
            return value

        if isinstance(
            value,
            (tuple, list),
        ):
            if not value:
                return None

            first = value[0]

            if isinstance(
                first,
                (int, float),
            ):
                return first

        price = getattr(
            value,
            "price",
            None,
        )

        if isinstance(
            price,
            (int, float),
        ):
            return price

        return None

    # ========================================================
    # Normalize Market Price
    # ========================================================

    @staticmethod
    def _normalize_market_price(
        price,
    ) -> float:
        if price is None:
            raise ValueError(
                "market price cannot be None"
            )

        value = float(
            price
        )

        if abs(value) >= 1_000_000_000:
            value = (
                value
                /
                1_000_000_000
            )

        return value

    # ========================================================
    # Execute
    # ========================================================

    def execute(
        self,
        order: Order,
        market_price: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        if order.status == OrderStatus.CREATED:
            self.submit_order(
                order
            )

        if self.mode == ExecutionMode.LIVE:
            return self._execute_live(
                order
            )

        order.accept()

        fill_price = (
            self._determine_price(
                order,
                market_price,
            )
        )

        fill = Fill(
            fill_id=
                self._generate_fill_id(),
            order_id=
                order.order_id,
            symbol=
                order.symbol,
            side=
                order.side,
            quantity=
                order.quantity,
            price=
                fill_price,
            metadata=
                metadata or {},
        )

        order.fill(
            quantity=fill.quantity
        )

        self.fills.append(
            fill
        )

        self.last_fill = fill
        self.total_fills += 1
        self.volume += fill.quantity

        if self.on_fill:
            self.on_fill(
                fill
            )

        return fill

    # ========================================================
    # Price Determination
    # ========================================================

    def _determine_price(
        self,
        order: Order,
        market_price: Optional[float],
    ):
        if order.order_type.value == "MARKET":
            if market_price is None:
                raise ValueError(
                    "MARKET order requires market_price"
                )

            return float(
                market_price
            )

        return order.price

    # ========================================================
    # LIVE Execution Placeholder
    # ========================================================

    def _execute_live(
        self,
        order: Order,
    ):
        raise NotImplementedError(
            "LIVE execution requires broker adapter"
        )

    # ========================================================
    # Cancel Order
    # ========================================================

    def cancel_order(
        self,
        order_id: str,
    ):
        order = self.orders.get(
            order_id
        )

        if order is None:
            return False

        order.cancel()
        self.cancelled_orders += 1

        return True

    # ========================================================
    # Query Order
    # ========================================================

    def get_order(
        self,
        order_id: str,
    ):
        return self.orders.get(
            order_id
        )

    # ========================================================
    # Active Orders
    # ========================================================

    def active_orders(self):
        return [
            order
            for order
            in self.orders.values()
            if order.status not in (
                OrderStatus.FILLED,
                OrderStatus.CANCELLED,
            )
        ]

    # ========================================================
    # Generate Fill ID
    # ========================================================

    def _generate_fill_id(
        self,
    ):
        import uuid

        return str(
            uuid.uuid4()
        )

    # ========================================================
    # Statistics
    # ========================================================

    def statistics(self):
        return {
            "mode":
                self.mode.value,
            "total_orders":
                self.total_orders,
            "total_fills":
                self.total_fills,
            "volume":
                self.volume,
            "cancelled_orders":
                self.cancelled_orders,
            "active_orders":
                len(
                    self.active_orders()
                ),
        }

    # ========================================================
    # Snapshot
    # ========================================================

    def snapshot(self):
        return {
            "mode":
                self.mode.value,
            "statistics":
                self.statistics(),
            "orders":
                {
                    order_id:
                        order.snapshot()
                    for order_id, order
                    in self.orders.items()
                },
            "fills":
                [
                    fill.snapshot()
                    for fill
                    in self.fills
                ],
            "last_fill":
                None
                if self.last_fill is None
                else self.last_fill.snapshot(),
        }

    # ========================================================
    # Reset
    # ========================================================

    def reset(self):
        self.total_orders = 0
        self.total_fills = 0
        self.volume = 0
        self.cancelled_orders = 0

        self.orders.clear()
        self.order_history.clear()
        self.fills.clear()

        self.last_fill = None

    # ========================================================
    # String
    # ========================================================

    def __repr__(self):
        return (
            f"<ExecutionEngine "
            f"mode={self.mode.value} "
            f"orders={self.total_orders} "
            f"fills={self.total_fills} "
            f"volume={self.volume}>"
        )
