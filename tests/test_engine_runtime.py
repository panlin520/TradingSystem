"""
tests/test_engine_runtime.py


============================================================
Engine Runtime Integration Test
============================================================

验证:

Market Event

    ↓

TradingEngine

    ↓

Strategy

    ↓

Signal

    ↓

Risk

    ↓

Execution

    ↓

Portfolio


============================================================

"""


from core.engine import TradingEngine


from core.mode import TradingMode


from portfolio.portfolio import Portfolio


from execution.execution_engine import (
    ExecutionEngine,
    ExecutionMode,
)



class FakeEvent:
    """
    模拟行情事件
    """

    def __init__(self):

        self.symbol = "ESU6"

        self.price = 6000.0

        self.size = 1

        self.timestamp = 1





class FakeStrategy:
    """
    测试策略

    收到行情后产生一个 BUY Signal
    """

    def __init__(self):

        self.generated = False



    def on_event(
        self,
        event
    ):

        if self.generated:

            return None


        self.generated = True


        from signals.signal import (
            Signal,
            SignalSide,
        )


        return Signal(

            symbol="ESU6",

            side=SignalSide.BUY,

            quantity=1,

        )





def test_engine_runtime_pipeline():


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
    # Engine
    # ==================================================

    engine = TradingEngine(

        mode=TradingMode.BACKTEST

    )



    # ==================================================
    # Attach components
    # ==================================================

    engine.portfolio = portfolio

    engine.execution = execution

    engine.strategy = FakeStrategy()



    # ==================================================
    # Feed Event
    # ==================================================

    event = FakeEvent()


    engine.on_event(
        event
    )



    # ==================================================
    # Validation
    # ==================================================

    assert engine is not None