"""
execution/order_manager.py

============================================================
Order Manager
============================================================

职责：

    管理交易系统自己的订单生命周期。


============================================================


订单流程：


Signal


    |

    v


OrderManager


    |

    v


Order


    |

    v


Execution Engine


    |

    v


Fill


    |

    v


Portfolio



============================================================


支持：

    BACKTEST

    PAPER

    LIVE


统一订单管理。



============================================================


"""



from typing import Dict, Optional, List, Any



from execution.order import (
    Order,
    OrderStatus,
    OrderSide,
    OrderType,
)



from strategy.signal import (
    Signal,
    SignalSide,
)




class OrderManager:
    """
    订单管理器。


    """



    def __init__(self):


        # ====================================================
        # 当前订单
        #
        # order_id -> Order
        #
        # ====================================================

        self.orders: Dict[
            str,
            Order
        ] = {}



        # ====================================================
        # 历史订单
        #
        # ====================================================

        self.history: List[
            Order
        ] = []



        # ====================================================
        # 统计
        #
        # ====================================================

        self.total_orders = 0



        self.filled_orders = 0




    # ========================================================
    # Signal 创建订单
    # ========================================================

    def create_order(
        self,
        signal: Signal,
        symbol: str
    ) -> Order:
        """
        根据Signal创建Order。


        注意：

        不执行风控。


        风控应该在这里之前完成。


        """



        side = (

            OrderSide.BUY

            if signal.side == SignalSide.BUY

            else

            OrderSide.SELL

        )



        order = Order(


            symbol=symbol,


            side=side,


            order_type=OrderType.LIMIT,


            price=signal.price,


            quantity=signal.size,


            timestamp=signal.timestamp,


            strategy=signal.strategy,


            metadata=signal.metadata,

        )



        return order




    # ========================================================
    # 提交订单
    # ========================================================

    def submit(
        self,
        order: Order
    ):
        """
        注册订单。


        """

        order.submit()



        self.orders[
            order.order_id
        ] = order



        self.total_orders += 1




    # ========================================================
    # 接受订单
    # ========================================================

    def accept(
        self,
        order_id: str
    ):
        """
        Execution确认订单。


        """

        order = self.orders.get(
            order_id
        )


        if order:

            order.accept()




    # ========================================================
    # 更新成交
    # ========================================================

    def on_fill(
        self,
        order_id: str,
        quantity: int
    ):
        """
        成交更新。


        """

        order = self.orders.get(
            order_id
        )


        if order is None:

            return



        before = order.status



        order.fill(
            quantity
        )



        if order.status == OrderStatus.FILLED:


            self.filled_orders += 1



            self.history.append(
                order
            )



            del self.orders[
                order_id
            ]




    # ========================================================
    # 取消订单
    # ========================================================

    def cancel(
        self,
        order_id: str
    ):
        """
        取消订单。


        """

        order = self.orders.get(
            order_id
        )


        if order is None:

            return



        order.cancel()



        self.history.append(
            order
        )



        del self.orders[
            order_id
        ]




    # ========================================================
    # 获取订单
    # ========================================================

    def get(
        self,
        order_id: str
    ) -> Optional[Order]:
        """
        查询订单。


        """

        return self.orders.get(
            order_id
        )




    # ========================================================
    # 活跃订单
    # ========================================================

    def active_orders(
        self
    ) -> List[Order]:
        """
        当前活动订单。


        """

        return list(
            self.orders.values()
        )




    # ========================================================
    # 所有订单
    # ========================================================

    def all_orders(
        self
    ) -> List[Order]:
        """
        返回历史订单。


        """

        return self.history




    # ========================================================
    # 状态
    # ========================================================

    def status(
        self
    ) -> dict:
        """
        返回订单状态。


        """

        return {


            "active_orders":
                len(self.orders),


            "history_orders":
                len(self.history),


            "total_orders":
                self.total_orders,


            "filled_orders":
                self.filled_orders,


        }