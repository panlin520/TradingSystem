"""
tests/test_execution_risk_pipeline.py

============================================================
Execution Pipeline Contract

验证：

Order
  ->
Fill
  ->
Portfolio

============================================================
"""

import pytest

from execution.fill import Fill
from execution.simulator import ExecutionSimulator



class FakeOrder:

    def __init__(self):

        self.order_id = "ORDER001"

        self.symbol = "ESU6"

        self.side = "BUY"

        self.quantity = 1



def test_fill_can_initialize():

    fill = Fill(

        order_id="1",

        symbol="ESU6",

        side="BUY",

        quantity=1,

        price=7571.25,

    )


    assert fill.symbol == "ESU6"

    assert fill.price == 7571.25



def test_fill_rejects_zero_quantity():

    with pytest.raises(
        ValueError
    ):

        Fill(

            order_id="1",

            symbol="ESU6",

            side="BUY",

            quantity=0,

            price=7571.25,

        )



def test_executor_creates_fill():

    executor = ExecutionSimulator()

    order = FakeOrder()


    fill = executor.execute(

        order,

        market_price=7571.25,

    )


    assert fill.symbol == "ESU6"

    assert fill.quantity == 1

    assert fill.price == 7571.25



def test_executor_counts_execution():

    executor = ExecutionSimulator()

    order = FakeOrder()


    executor.execute(
        order,
        market_price=7571.25,
    )


    assert executor.execution_count == 1
