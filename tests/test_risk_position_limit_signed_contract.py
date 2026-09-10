"""
tests/test_risk_position_limit_signed_contract.py

============================================================
Risk Position Limit Signed Quantity Contract
============================================================

验证：

    单品种 max_position_size 必须同时限制 LONG / SHORT。

场景：

    max_position = 5

    FLAT + BUY 5  -> +5  -> approve
    FLAT + BUY 6  -> +6  -> reject

    FLAT + SELL 5 -> -5  -> approve
    FLAT + SELL 6 -> -6  -> reject

    LONG 3 + BUY 3  -> +6 -> reject
    SHORT -3 + SELL 3 -> -6 -> reject

同时验证：

    减仓 / 平仓不会因 signed quantity 产生错误：

    LONG 5 + SELL 5  -> 0 -> approve
    SHORT -5 + BUY 5 -> 0 -> approve

============================================================
"""


from risk.risk_manager_v2 import RiskManagerV2
from risk.limits import RiskLimits

from signals.signal import (
    Signal,
    SignalSide,
    SignalType,
)





class FakePosition:

    def __init__(
        self,
        quantity=0,
    ):

        self.quantity = quantity





class FakePortfolio:

    def __init__(
        self,
        quantity=0,
        symbol="ESU6",
    ):

        self.positions = {}


        if quantity != 0:

            self.positions[symbol] = FakePosition(
                quantity=quantity
            )


    def get_position(
        self,
        symbol,
    ):

        position = self.positions.get(
            symbol
        )


        if position is None:

            position = FakePosition(
                quantity=0
            )

            self.positions[symbol] = position


        return position





def make_risk():

    return RiskManagerV2(

        limits=RiskLimits(

            max_position=5,

            max_total_position=100,

            max_exposure=1000,

        )

    )





def make_signal(
    side,
    quantity,
    signal_type=SignalType.ENTRY,
):

    return Signal(

        symbol="ESU6",

        side=side,

        quantity=quantity,

        signal_type=signal_type,

        confidence=1.0,

    )





def test_long_at_position_limit_is_approved():

    risk = make_risk()

    portfolio = FakePortfolio(
        quantity=0
    )


    decision = risk.check_signal(

        make_signal(
            SignalSide.BUY,
            5,
        ),

        portfolio,

    )


    assert decision.approved is True

    assert decision.checks["position_limit"] is True





def test_long_above_position_limit_is_rejected():

    risk = make_risk()

    portfolio = FakePortfolio(
        quantity=0
    )


    decision = risk.check_signal(

        make_signal(
            SignalSide.BUY,
            6,
        ),

        portfolio,

    )


    assert decision.approved is False

    assert decision.reason == "Position limit exceeded"

    assert decision.checks["position_limit"] is False





def test_short_at_position_limit_is_approved():

    risk = make_risk()

    portfolio = FakePortfolio(
        quantity=0
    )


    decision = risk.check_signal(

        make_signal(
            SignalSide.SELL,
            5,
        ),

        portfolio,

    )


    assert decision.approved is True

    assert decision.checks["position_limit"] is True





def test_short_above_position_limit_is_rejected():

    risk = make_risk()

    portfolio = FakePortfolio(
        quantity=0
    )


    decision = risk.check_signal(

        make_signal(
            SignalSide.SELL,
            6,
        ),

        portfolio,

    )


    assert decision.approved is False

    assert decision.reason == "Position limit exceeded"

    assert decision.checks["position_limit"] is False





def test_existing_long_cannot_expand_beyond_limit():

    risk = make_risk()

    portfolio = FakePortfolio(
        quantity=3
    )


    decision = risk.check_signal(

        make_signal(
            SignalSide.BUY,
            3,
        ),

        portfolio,

    )


    assert decision.approved is False

    assert decision.checks["position_limit"] is False





def test_existing_short_cannot_expand_beyond_limit():

    risk = make_risk()

    portfolio = FakePortfolio(
        quantity=-3
    )


    decision = risk.check_signal(

        make_signal(
            SignalSide.SELL,
            3,
        ),

        portfolio,

    )


    assert decision.approved is False

    assert decision.checks["position_limit"] is False





def test_full_long_exit_is_approved():

    risk = make_risk()

    portfolio = FakePortfolio(
        quantity=5
    )


    decision = risk.check_signal(

        make_signal(
            SignalSide.SELL,
            5,
            signal_type=SignalType.EXIT,
        ),

        portfolio,

    )


    assert decision.approved is True

    assert decision.checks["position_limit"] is True





def test_full_short_exit_is_approved():

    risk = make_risk()

    portfolio = FakePortfolio(
        quantity=-5
    )


    decision = risk.check_signal(

        make_signal(
            SignalSide.BUY,
            5,
            signal_type=SignalType.EXIT,
        ),

        portfolio,

    )


    assert decision.approved is True

    assert decision.checks["position_limit"] is True
