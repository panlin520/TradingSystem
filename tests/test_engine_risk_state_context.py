"""
tests/test_engine_risk_state_context.py

============================================================
Engine -> Risk State Context Contract
============================================================

验证：

1. 支持 state context 的 Risk：
       Engine 会传 self.state

2. 旧 Risk：
       Engine 仍然只传 signal + portfolio

3. 不破坏 Runtime Signal -> Order pipeline

============================================================
"""


from dataclasses import dataclass


from core.engine import (
    TradingEngine,
    EngineMode,
)

from signals.signal import (
    Signal,
    SignalSide,
)





@dataclass
class FakeDecision:

    approved: bool = True





class StateAwareRisk:

    supports_state_context = True


    def __init__(self):

        self.last_signal = None

        self.last_portfolio = None

        self.last_state = None


    def check_signal(
        self,
        signal,
        portfolio,
        state=None,
    ):

        self.last_signal = signal

        self.last_portfolio = portfolio

        self.last_state = state


        return FakeDecision(
            approved=True
        )





class LegacyRisk:

    def __init__(self):

        self.last_signal = None

        self.last_portfolio = None


    def check_signal(
        self,
        signal,
        portfolio,
    ):

        self.last_signal = signal

        self.last_portfolio = portfolio


        return FakeDecision(
            approved=True
        )





class FakePortfolio:

    pass





def make_signal():

    return Signal(

        symbol="ESU6",

        side=SignalSide.BUY,

        quantity=1,

        confidence=1.0,

    )





def test_engine_passes_state_to_state_aware_risk():

    risk = StateAwareRisk()

    portfolio = FakePortfolio()


    engine = TradingEngine(

        mode=EngineMode.BACKTEST,

        risk=risk,

        portfolio=portfolio,

    )


    signal = make_signal()


    engine._process_signal(
        signal
    )


    assert risk.last_signal is signal

    assert risk.last_portfolio is portfolio

    assert risk.last_state is engine.state





def test_engine_keeps_legacy_risk_signature_compatible():

    risk = LegacyRisk()

    portfolio = FakePortfolio()


    engine = TradingEngine(

        mode=EngineMode.BACKTEST,

        risk=risk,

        portfolio=portfolio,

    )


    signal = make_signal()


    engine._process_signal(
        signal
    )


    assert risk.last_signal is signal

    assert risk.last_portfolio is portfolio





def test_state_aware_risk_does_not_break_order_creation():

    risk = StateAwareRisk()

    portfolio = FakePortfolio()


    engine = TradingEngine(

        mode=EngineMode.BACKTEST,

        risk=risk,

        portfolio=portfolio,

    )


    signal = make_signal()


    engine._process_signal(
        signal
    )


    assert engine.signal_count == 1

    assert engine.order_count == 1

    assert engine.last_order is not None

    assert engine.last_order.symbol == "ESU6"

    assert engine.last_order.quantity == 1

    assert engine.last_order.side.value == "BUY"
