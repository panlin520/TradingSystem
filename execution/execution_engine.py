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

"""


from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
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
# Fill
# ============================================================


@dataclass
class Fill:
    """
    成交记录。


    ExecutionEngine生成。


    Portfolio只接收Fill。
    """


    fill_id: str


    order_id: str


    symbol: str


    side: OrderSide


    quantity: int


    price: float



    timestamp: datetime = field(
        default_factory=lambda:
        datetime.now(timezone.utc)
    )


    metadata: Dict[str, Any] = field(
        default_factory=dict
    )



    def snapshot(self):
        """
        Fill状态快照。
        """


        return {

            "fill_id":
                self.fill_id,


            "order_id":
                self.order_id,


            "symbol":
                self.symbol,


            "side":
                self.side.value,


            "quantity":
                self.quantity,


            "price":
                self.price,


            "timestamp":
                self.timestamp.isoformat(),


            "metadata":
                self.metadata.copy(),

        }






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



    Example:


        execution = ExecutionEngine(
            mode=ExecutionMode.BACKTEST,
            on_fill=portfolio.on_fill
        )


    ========================================================


    MARKET Order：

        BUY
          ↓
        Best Ask


        SELL
          ↓
        Best Bid


    ========================================================
    """




    def __init__(
        self,
        mode: ExecutionMode = ExecutionMode.BACKTEST,
        on_fill: Optional[
            Callable[[Fill], None]
        ] = None,
    ):


        # ==================================================
        # Mode
        # ==================================================


        self.mode = mode



        # ==================================================
        # Callback
        # ==================================================


        self.on_fill = on_fill




        # ==================================================
        # Statistics
        # ==================================================


        self.total_orders = 0


        self.total_fills = 0


        self.volume = 0



        self.cancelled_orders = 0




        # ==================================================
        # Orders
        # ==================================================


        self.orders: Dict[
            str,
            Order
        ] = {}



        self.order_history: List[
            Order
        ] = []




        # ==================================================
        # Fill History
        # ==================================================


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
        """
        提交订单。


        流程：


            CREATED

              ↓

            SUBMITTED
        """


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
        """
        Engine V2.1 compatibility interface.


        core.engine.py：

            execution.submit(
                order,
                state
            )


        ====================================================


        MARKET Price Resolution：


        第一优先：

            state.last_price


        这是为了兼容：

            unit test
            FakeState
            simple simulator


        第二优先：

            state.orderbook


        BUY：

            Best Ask


        SELL：

            Best Bid


        ====================================================
        """


        market_price = None



        # ==================================================
        # 1.
        # Compatibility:
        # state.last_price
        # ==================================================

        if state is not None:


            market_price = getattr(
                state,
                "last_price",
                None,
            )



        # ==================================================
        # 2.
        # Real Runtime:
        # state.orderbook
        # ==================================================

        if (
            market_price is None
            and
            state is not None
        ):


            market_price = (
                self._market_price_from_state(
                    order,
                    state,
                )
            )



        # ==================================================
        # Execute
        # ==================================================

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
        """
        从 SystemState 获取 MARKET Order 成交价格。


        规则：


            BUY：

                Best Ask


            SELL：

                Best Bid


        SystemState 当前保存：

            state.orderbook


        这里兼容两种对象结构：


            1.

            state.orderbook
                ↓
            OrderBookBuilder
                ↓
            .book
                ↓
            OrderBook


            2.

            state.orderbook
                ↓
            直接就是 OrderBook


        ====================================================


        注意：

        不使用当前 MarketEvent.price。


        因为 F_LAST event 可能是：

            ADD
            MODIFY
            CANCEL
            NONE


        event.price 并不代表真实可成交价格。


        ====================================================
        """


        orderbook = getattr(
            state,
            "orderbook",
            None,
        )



        if orderbook is None:

            return None



        # ==================================================
        # OrderBookBuilder → OrderBook
        # ==================================================

        book = getattr(
            orderbook,
            "book",
            orderbook,
        )



        # ==================================================
        # BUY MARKET → Best Ask
        # ==================================================

        if order.side == OrderSide.BUY:


            raw_price = self._get_best_ask(
                book
            )



        # ==================================================
        # SELL MARKET → Best Bid
        # ==================================================

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
        """
        获取 Best Bid。


        兼容：

            best_bid()
            best_bid property
            bids dict
        """


        # ==================================================
        # best_bid attribute / method
        # ==================================================

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



        # ==================================================
        # bids dictionary
        # ==================================================

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
        """
        获取 Best Ask。


        兼容：

            best_ask()
            best_ask property
            asks dict
        """


        # ==================================================
        # best_ask attribute / method
        # ==================================================

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



        # ==================================================
        # asks dictionary
        # ==================================================

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
        """
        从不同 Best Bid / Ask 返回结构中提取价格。


        兼容：

            int
            float

            tuple:
                (price, size)

            object:
                .price
        """


        if value is None:

            return None



        # ==================================================
        # Numeric
        # ==================================================

        if isinstance(
            value,
            (int, float),
        ):

            return value



        # ==================================================
        # Tuple / List
        # ==================================================

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



        # ==================================================
        # Object.price
        # ==================================================

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
        """
        将 OrderBook Price 转成 Execution Fill Price。


        Databento MBO：

            7557000000000

        实际：

            7557.0


        Databento price scale：

            1e9


        ====================================================


        同时兼容普通测试价格：

            6000.0

        不会再次除以 1e9。


        ====================================================
        """


        if price is None:

            raise ValueError(
                "market price cannot be None"
            )



        value = float(
            price
        )



        # ==================================================
        # Databento nano-dollar
        # ==================================================
        #
        # ES 正常价格约：
        #
        #     1000 ~ 10000
        #
        # Databento raw:
        #
        #     ~1e12
        #
        # ==================================================

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
        """
        执行订单。


        当前支持：


            BACKTEST

                模拟立即成交


            PAPER

                模拟成交


            LIVE

                预留Broker接口
        """



        # ==================================================
        # Submit
        # ==================================================


        if order.status == OrderStatus.CREATED:


            self.submit_order(
                order
            )




        # ==================================================
        # LIVE保护
        # ==================================================


        if self.mode == ExecutionMode.LIVE:


            return self._execute_live(
                order
            )




        # ==================================================
        # Accept
        # ==================================================


        order.accept()




        # ==================================================
        # Price
        # ==================================================


        fill_price = (
            self._determine_price(
                order,
                market_price,
            )
        )




        # ==================================================
        # Create Fill
        # ==================================================


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




        # ==================================================
        # Update Order
        # ==================================================


        order.fill(
            quantity=fill.quantity
        )




        # ==================================================
        # Save Fill
        # ==================================================


        self.fills.append(
            fill
        )


        self.last_fill = fill



        self.total_fills += 1



        self.volume += fill.quantity




        # ==================================================
        # Portfolio Callback
        # ==================================================


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
        """
        成交价格。


        MARKET：

            使用 Runtime 传入的 market_price。


        LIMIT / STOP：

            当前继续使用 order.price。


        后续扩展：


            slippage

            latency

            queue position

            L3 matching
        """



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
        """
        LIVE模式。


        这里以后连接：

            Broker API

            CME Gateway

            FIX Engine
        """



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
        """
        取消订单。
        """


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
        """
        查询订单。
        """


        return self.orders.get(
            order_id
        )






    # ========================================================
    # Active Orders
    # ========================================================


    def active_orders(self):
        """
        当前活动订单。
        """


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
        """
        生成成交ID。
        """


        import uuid


        return str(
            uuid.uuid4()
        )








    # ========================================================
    # Statistics
    # ========================================================


    def statistics(self):
        """
        Execution统计。
        """


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
        """
        Execution状态快照。


        用于：

            Web UI

            Monitoring

            Debug
        """


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
        """
        清空Execution状态。


        用于：

            回测重新运行

            测试
        """


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