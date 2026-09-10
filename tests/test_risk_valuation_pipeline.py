"""
tests/test_risk_valuation_pipeline.py

============================================================
Risk Valuation Pipeline Contract
============================================================

验证：

    Runtime Signal
        ↓
    RiskManagerV2
        ↓
    state.orderbook
        ↓
    RiskMarketValuation
        ↓
    normalized valuation price
        ↓
    ExposureEngine.project_signals()

当前阶段不启用 Dollar Exposure，
只验证 valuation price 已经正确贯通。

============================================================
"""


import pytest


from risk.risk_manager_v2 import (
    RiskManagerV2,
)

from risk.limits import (
    RiskLimits,
)

from risk.exposure import (
    ExposureEngine,
)

from signals.signal import (
    Signal,
    SignalSide,
)





class FakePosition:

    def __init__(
        self,
        quantity=0,
    ):

        self.quantity = quantity





class FakePortfolio:

    def __init__(self):

        self.positions = {}


    def get_position(
        self,
        symbol,
    ):

        if symbol not in self.positions:

            self.positions[symbol] = (
                FakePosition()
            )


        return self.positions[symbol]





class FakeBook:

    def __init__(
        self,
        bid,
        ask,
    ):

        self._bid = bid

        self._ask = ask


    def best_bid(self):

        return self._bid


    def best_ask(self):

        return self._ask





class FakeState:

    def __init__(
        self,
        orderbook,
    ):

        self.orderbook = orderbook





def make_risk():

    return RiskManagerV2(

        limits=RiskLimits(

            max_position=10,

            max_total_position=20,

            max_exposure=1000,

        )

    )





def test_buy_signal_gets_normalized_best_ask():

    risk = make_risk()

    portfolio = FakePortfolio()


    signal = Signal(

        symbol="ESU6",

        side=SignalSide.BUY,

        quantity=1,

        confidence=1.0,

    )


    state = FakeState(

        FakeBook(

            bid=7_571_000_000_000,

            ask=7_571_250_000_000,

        )

    )


    decision = risk.check_signal(

        signal,

        portfolio,

        state=state,

    )


    assert decision.approved is True

    assert risk.last_valuation_price == pytest.approx(
        7571.25
    )





def test_sell_signal_gets_normalized_best_bid():

    risk = make_risk()

    portfolio = FakePortfolio()


    signal = Signal(

        symbol="ESU6",

        side=SignalSide.SELL,

        quantity=1,

        confidence=1.0,

    )


    state = FakeState(

        FakeBook(

            bid=7_571_000_000_000,

            ask=7_571_250_000_000,

        )

    )


    decision = risk.check_signal(

        signal,

        portfolio,

        state=state,

    )


    assert decision.approved is True

    assert risk.last_valuation_price == pytest.approx(
        7571.00
    )





def test_exposure_engine_receives_valuation_price():

    engine = ExposureEngine()

    portfolio = FakePortfolio()


    projected = engine.project_signals(

        portfolio,

        "ESU6",

        SignalSide.BUY,

        2,

        valuation_price=7571.25,

    )


    assert projected.position_quantity == 2

    assert projected.valuation_price == pytest.approx(
        7571.25
    )





def test_old_risk_call_without_state_remains_supported():

    risk = make_risk()

    portfolio = FakePortfolio()


    signal = Signal(

        symbol="ESU6",

        side=SignalSide.BUY,

        quantity=1,

        confidence=1.0,

    )


    decision = risk.check_signal(

        signal,

        portfolio,

    )


    assert decision.approved is True

    assert risk.last_valuation_price is None





def test_missing_buy_ask_is_visible_in_diagnostics():

    risk = make_risk()

    portfolio = FakePortfolio()


    signal = Signal(

        symbol="ESU6",

        side=SignalSide.BUY,

        quantity=1,

        confidence=1.0,

    )


    state = FakeState(

        FakeBook(

            bid=7_571_000_000_000,

            ask=None,

        )

    )


    decision = risk.check_signal(

        signal,

        portfolio,

        state=state,

    )


    # 当前阶段 Dollar Exposure 尚未启用，
    # 所以这里暂时不 fail closed。
    assert decision.approved is True

    assert risk.last_valuation_price is None

    assert (
        decision.checks["valuation_price"]
        is False
    )
