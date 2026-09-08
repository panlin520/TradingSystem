"""
tests/test_trading_pipeline.py


============================================================
Trading Pipeline Integration Test
============================================================


验证完整交易链：

Signal

    ↓

RiskManagerV2

    ↓

Order

    ↓

ExecutionEngine

    ↓

Fill

    ↓

Portfolio

    ↓

Position


============================================================

"""


from signals.signal import Signal


from risk.risk_manager_v2 import (
    RiskManagerV2
)


from order.order import (
    Order,
    OrderSide,
)


from execution.execution_engine import (
    ExecutionEngine,
    ExecutionMode,
)


from portfolio.portfolio import (
    Portfolio
)





# ============================================================
# Fake Signal
# ============================================================


from signals.signal import SignalSide

def create_signal():

    return Signal(

        symbol="ESU6",

        side=SignalSide.BUY,

        quantity=1,

    )






# ============================================================
# Pipeline Test
# ============================================================


def test_complete_trading_pipeline():


    # ==================================================
    # Portfolio
    # ==================================================

    portfolio = Portfolio(
        initial_capital=100000
    )



    # ==================================================
    # Execution
    # ==================================================

    execution = ExecutionEngine(

        mode=ExecutionMode.BACKTEST,

        on_fill=portfolio.on_fill

    )



    # ==================================================
    # Risk
    # ==================================================

    risk_manager = RiskManagerV2()



    # ==================================================
    # Strategy Signal
    # ==================================================

    signal = create_signal()



    # ==================================================
    # Risk Check
    # ==================================================

    decision = risk_manager.check_signals(
        signal,
        portfolio
    )

    assert decision.approved is True





    # ==================================================
    # Create Order
    # ==================================================

    order = Order(

        symbol=signal.symbol,

        side=OrderSide.BUY,

        quantity=signal.quantity,

    )



    assert order.validate() is True






    # ==================================================
    # Execute
    # ==================================================

    class FakeState:
        last_price = 6000.00

    fill = execution.submit(

        order,

        FakeState()

    )

    assert fill is not None

    assert fill.symbol == "ESU6"

    assert fill.quantity == 1

    assert fill.price == 6000.00






    # ==================================================
    # Portfolio Check
    # ==================================================

    position = portfolio.get_position(
        "ESU6"
    )



    assert position.quantity == 1



    assert portfolio.trade_count == 1



    assert execution.total_fills == 1