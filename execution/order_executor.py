"""
execution/order_executor.py

============================================================
Order Executor
============================================================

职责：

    Order
      |
      v
    Fill

负责：

- 接收 Order
- 创建成交结果

不负责：

- Risk
- Portfolio
- Position
- Strategy

============================================================
"""

from execution.fill import Fill


class OrderExecutor:
    """
    Execution 基础接口。

    BACKTEST / PAPER / LIVE 可以继承此接口。
    """

    def __init__(self):
        self.execution_count = 0

    def execute(
        self,
        order,
        price=None,
    ):
        """
        执行订单。

        当前默认：Immediate Fill。
        """

        if price is None:
            price = getattr(
                order,
                "price",
                None,
            )

        if price is None:
            raise ValueError(
                "Execution requires price"
            )

        self.execution_count += 1

        return Fill(
            order_id=str(
                getattr(
                    order,
                    "order_id",
                    "",
                )
            ),
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=float(price),
        )
