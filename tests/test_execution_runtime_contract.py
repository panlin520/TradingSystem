"""
tests/test_execution_runtime_contract.py

============================================================
Execution Runtime Contract Test
============================================================

验证：

Order
    |
    v
ExecutionEngine
    |
    v
Fill
    |
    v
Portfolio Callback


覆盖：

    - Order lifecycle
    - Execution submit
    - Execution fill
    - Callback
    - Cancel
    - Snapshot
    - Reset


============================================================
"""


import pytest


from execution.order import (
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
)


from execution.execution_engine import (
    ExecutionEngine,
    ExecutionMode,
)





# ============================================================
# Fake Portfolio Callback
# ============================================================


class FakePortfolio:

    def __init__(self):

        self.fills = []


    def on_fill(
        self,
        fill
    ):

        self.fills.append(
            fill
        )






# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def execution():

    return ExecutionEngine(
        mode=ExecutionMode.BACKTEST
    )





@pytest.fixture
def portfolio():

    return FakePortfolio()





@pytest.fixture
def order():

    return Order(

        symbol="ESU6",

        side=OrderSide.BUY,

        order_type=OrderType.LIMIT,

        price=6000000000000,

        quantity=1,

    )







# ============================================================
# Order lifecycle
# ============================================================


def test_order_initial_state(
    order
):


    assert (
        order.status
        ==
        OrderStatus.CREATED
    )



def test_order_submit(
    order
):


    order.submit()


    assert (
        order.status
        ==
        OrderStatus.SUBMITTED
    )



def test_order_accept(
    order
):


    order.submit()

    order.accept()


    assert (
        order.status
        ==
        OrderStatus.ACCEPTED
    )



def test_order_fill(
    order
):


    order.submit()

    order.accept()


    order.fill(
        1
    )


    assert (
        order.status
        ==
        OrderStatus.FILLED
    )






# ============================================================
# ExecutionEngine initialize
# ============================================================


def test_execution_initial_state(
    execution
):


    assert (
        execution.mode
        ==
        ExecutionMode.BACKTEST
    )


    assert (
        execution.total_orders
        ==
        0
    )


    assert (
        execution.total_fills
        ==
        0
    )







# ============================================================
# Submit Order
# ============================================================


def test_execution_submit_order(
    execution,
    order
):


    execution.submit_order(
        order
    )


    assert (
        order.status
        ==
        OrderStatus.SUBMITTED
    )


    assert (
        execution.total_orders
        ==
        1
    )


    assert (
        order.order_id
        in
        execution.orders
    )







# ============================================================
# Execute MARKET order
# ============================================================


def test_market_order_execution(
    portfolio
):


    execution = ExecutionEngine(

        mode=ExecutionMode.BACKTEST,

        on_fill=portfolio.on_fill

    )


    order = Order(

        symbol="ESU6",

        side=OrderSide.BUY,

        order_type=OrderType.MARKET,

        quantity=1,

    )


    fill = execution.execute(

        order,

        market_price=6000

    )


    assert (
        fill.price
        ==
        6000
    )


    assert (
        execution.total_fills
        ==
        1
    )


    assert (
        len(
            portfolio.fills
        )
        ==
        1
    )






# ============================================================
# Limit order execution
# ============================================================


def test_limit_order_execution(
    execution
):


    order = Order(

        symbol="ESU6",

        side=OrderSide.BUY,

        order_type=OrderType.LIMIT,

        price=6000,

        quantity=1,

    )


    fill = execution.execute(
        order
    )


    assert (
        fill.price
        ==
        6000
    )



    assert (
        execution.total_fills
        ==
        1
    )







# ============================================================
# Cancel
# ============================================================


def test_cancel_order(
    execution,
    order
):


    execution.submit_order(
        order
    )


    result = execution.cancel_order(
        order.order_id
    )


    assert (
        result
        is
        True
    )


    assert (
        execution.cancelled_orders
        ==
        1
    )






# ============================================================
# Snapshot
# ============================================================


def test_execution_snapshot(
    execution
):


    snapshot = execution.snapshot()



    assert (
        "mode"
        in
        snapshot
    )


    assert (
        "statistics"
        in
        snapshot
    )


    assert (
        "orders"
        in
        snapshot
    )


    assert (
        "fills"
        in
        snapshot
    )






# ============================================================
# Statistics
# ============================================================


def test_execution_statistics(
    execution
):


    stats = execution.statistics()



    assert (
        stats["mode"]
        ==
        "BACKTEST"
    )


    assert (
        stats["total_orders"]
        ==
        0
    )







# ============================================================
# Reset
# ============================================================


def test_execution_reset(
    execution,
    order
):


    execution.execute(

        order,

        market_price=6000

    )


    assert (
        execution.total_fills
        ==
        1
    )



    execution.reset()



    assert (
        execution.total_fills
        ==
        0
    )


    assert (
        len(
            execution.fills
        )
        ==
        0
    )


    assert (
        len(
            execution.orders
        )
        ==
        0
    )






# ============================================================
# Diagnostic
# ============================================================


def test_execution_diagnostic(
    portfolio
):


    execution = ExecutionEngine(

        mode=ExecutionMode.BACKTEST,

        on_fill=portfolio.on_fill

    )


    order = Order(

        symbol="ESU6",

        side=OrderSide.BUY,

        order_type=OrderType.MARKET,

        quantity=1

    )


    fill = execution.execute(

        order,

        market_price=6000

    )


    print()
    print("=" * 60)
    print("EXECUTION RUNTIME DIAGNOSTIC")
    print("=" * 60)

    print(
        "mode =",
        execution.mode.value
    )

    print(
        "fills =",
        execution.total_fills
    )

    print(
        "volume =",
        execution.volume
    )

    print(
        "callback fills =",
        len(
            portfolio.fills
        )
    )

    print("=" * 60)


    assert (
        fill
        is
        not None
    )