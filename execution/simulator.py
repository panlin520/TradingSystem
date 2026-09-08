"""
execution/simulator.py

============================================================
Execution Simulator
============================================================

职责：

    回测 / 模拟交易成交引擎。


============================================================


运行模式：

BACKTEST

    Historical MBO

          |

          v

    Execution Simulator



PAPER

    Live Market Data

          |

          v

    Execution Simulator



LIVE

    使用 Broker


============================================================


核心：

模拟真实成交：

    Limit Order

    Market Order

    Partial Fill

    Queue Position

    Slippage

    Latency



============================================================


"""



from dataclasses import dataclass
from typing import Optional, List, Dict, Any



from execution.order import (
    Order,
    OrderType,
    OrderStatus,
)



from orderbook.book import OrderBook



# ============================================================
# Fill
# ============================================================

@dataclass(slots=True)
class Fill:
    """
    成交记录。


    """

    order_id: str


    price: int


    quantity: int


    timestamp: int



    # 成交原因

    reason: str = ""




# ============================================================
# Execution Simulator
# ============================================================

class ExecutionSimulator:
    """
    模拟成交引擎。


    """



    def __init__(
        self,
        orderbook: OrderBook,

        latency_ns: int = 0,

        slippage_ticks: int = 0,

    ):


        # 当前盘口

        self.orderbook = orderbook



        # 模拟延迟

        self.latency_ns = latency_ns



        # 滑点tick

        self.slippage_ticks = slippage_ticks



        # 当前订单

        self.orders: Dict[
            str,
            Order
        ] = {}



        # 成交记录

        self.fills: List[
            Fill
        ] = []




    # ========================================================
    # 提交订单
    # ========================================================

    def submit(
        self,
        order: Order
    ):
        """
        提交模拟订单。


        """

        order.submit()


        self.orders[
            order.order_id
        ] = order




    # ========================================================
    # 市场事件
    # ========================================================

    def on_market_event(
        self,
        event: Any,
        timestamp: int
    ):
        """
        每个市场事件调用。


        """

        self.match(
            timestamp
        )




    # ========================================================
    # 撮合检查
    # ========================================================

    def match(
        self,
        timestamp: int
    ):
        """
        检查订单是否成交。


        """

        completed = []



        for order in self.orders.values():


            if order.status in (

                OrderStatus.CANCELLED,

                OrderStatus.FILLED,

                OrderStatus.REJECTED,

            ):

                continue



            fills = self._match_order(
                order,
                timestamp
            )



            for fill in fills:

                self.fills.append(
                    fill
                )


                order.fill(
                    fill.quantity
                )



            if order.is_done():

                completed.append(
                    order.order_id
                )



        for oid in completed:

            del self.orders[
                oid
            ]




    # ========================================================
    # 单订单匹配
    # ========================================================

    def _match_order(
        self,
        order: Order,
        timestamp: int
    ) -> List[Fill]:
        """
        判断单个订单成交。


        """

        fills = []



        # ====================================================
        # Market Order
        # ====================================================

        if order.order_type == OrderType.MARKET:

            fill = self._market_fill(
                order,
                timestamp
            )


            if fill:

                fills.append(
                    fill
                )


            return fills




        # ====================================================
        # Limit BUY
        # ====================================================

        if order.side.value == "BUY":


            ask = self.orderbook.best_ask()



            if ask is None:

                return fills



            if order.price >= ask:


                fills.append(

                    Fill(

                        order_id=
                            order.order_id,


                        price=
                            ask,


                        quantity=
                            order.remaining(),


                        timestamp=
                            timestamp,


                        reason=
                            "Limit Buy Hit Ask"

                    )

                )



        # ====================================================
        # Limit SELL
        # ====================================================

        else:


            bid = self.orderbook.best_bid()



            if bid is None:

                return fills



            if order.price <= bid:


                fills.append(

                    Fill(

                        order_id=
                            order.order_id,


                        price=
                            bid,


                        quantity=
                            order.remaining(),


                        timestamp=
                            timestamp,


                        reason=
                            "Limit Sell Hit Bid"

                    )

                )



        return fills




    # ========================================================
    # Market成交
    # ========================================================

    def _market_fill(
        self,
        order: Order,
        timestamp: int
    ) -> Optional[Fill]:
        """
        市价成交。


        """

        if order.side.value == "BUY":


            price = self.orderbook.best_ask()



        else:


            price = self.orderbook.best_bid()



        if price is None:

            return None



        return Fill(

            order_id=
                order.order_id,


            price=
                price,


            quantity=
                order.remaining(),


            timestamp=
                timestamp,


            reason=
                "Market Order"

        )




    # ========================================================
    # 获取成交
    # ========================================================

    def get_fills(
        self
    ) -> List[Fill]:
        """
        返回成交。


        """

        return self.fills




    # ========================================================
    # 状态
    # ========================================================

    def status(
        self
    ) -> dict:
        """
        状态。


        """

        return {


            "active_orders":
                len(self.orders),


            "fills":
                len(self.fills),


            "latency_ns":
                self.latency_ns,


            "slippage_ticks":
                self.slippage_ticks,

        }