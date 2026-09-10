"""
execution/simulator.py

============================================================
Execution Simulator
============================================================

BACKTEST / PAPER 使用。

流程：

Order
  |
  v
Simulator
  |
  v
Fill

============================================================
"""

from execution.order_executor import OrderExecutor


class ExecutionSimulator(OrderExecutor):
    """
    简单成交模拟器。

    当前：

    Market Order
        ->
    Immediate Fill

    后续可扩展：

    - queue position
    - latency
    - partial fill
    - slippage
    """


    mode = "SIMULATOR"


    def execute(
        self,
        order,
        market_price=None,
    ):

        return super().execute(
            order,
            price=market_price
        )
