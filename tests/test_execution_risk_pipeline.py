"""
tests/test_execution_risk_pipeline.py

============================================================
Execution Pipeline Contract
============================================================

验证正式执行链：

Order
  ->
ExecutionEngine
  ->
Fill
  ->
Execution Statistics

本测试只使用当前项目正式接口：

    order.order.Order
    execution.execution_engine.ExecutionEngine
    execution.fill.Fill

不再依赖旧的 ExecutionSimulator / OrderExecutor 测试路径。

============================================================
"""

import pytest

from execution.fill import Fill
from execution.execution_engine import (
    ExecutionEngine,
    ExecutionMode,
)
from order.order import (
    Order,
    OrderSide,
    OrderType,
)


# ============================================================
# Fill Contract
# ============================================================


def test_fill_can_initialize():

    fill = Fill(
        order_id="1",
        symbol="ESU6",
        side=OrderSide.BUY,
        quantity=1,
        price=7571.25,
    )

    assert fill.symbol == "ESU6"
    assert fill.side == OrderSide.BUY
    assert fill.quantity == 1
    assert fill.price == 7571.25
    assert fill.fill_id



def test_fill_rejects_zero_quantity():

    with pytest.raises(ValueError):

        Fill(
            order_id="1",
            symbol="ESU6",
            side=OrderSide.BUY,
            quantity=0,
            price=7571.25,
        )


# ============================================================
# Canonical ExecutionEngine Contract
# ============================================================


def test_execution_engine_creates_fill():

    execution = ExecutionEngine(
        mode=ExecutionMode.BACKTEST
    )

    order = Order(
        symbol="ESU6",
        side=OrderSide.BUY,
        quantity=1,
        order_type=OrderType.MARKET,
    )

    fill = execution.execute(
        order,
        market_price=7571.25,
    )

    assert isinstance(fill, Fill)
    assert fill.order_id == order.order_id
    assert fill.symbol == "ESU6"
    assert fill.side == OrderSide.BUY
    assert fill.quantity == 1
    assert fill.price == 7571.25



def test_execution_engine_counts_execution():

    execution = ExecutionEngine(
        mode=ExecutionMode.BACKTEST
    )

    order = Order(
        symbol="ESU6",
        side=OrderSide.BUY,
        quantity=1,
        order_type=OrderType.MARKET,
    )

    execution.execute(
        order,
        market_price=7571.25,
    )

    assert execution.total_orders == 1
    assert execution.total_fills == 1
    assert execution.volume == 1
    assert len(execution.fills) == 1
    assert execution.last_fill is execution.fills[0]
