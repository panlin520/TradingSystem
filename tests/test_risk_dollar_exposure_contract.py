"""
tests/test_risk_dollar_exposure_contract.py

============================================================
Risk Dollar Exposure Contract
============================================================

验证：

1. ES 第一笔 ENTRY 在 Fill 前即可计算美元暴露
2. MES 使用独立 point value
3. 多 symbol gross_notional
4. LONG / SHORT 都使用绝对 notional
5. 减仓降低 gross_notional
6. 平仓移除该 symbol notional
7. 反手使用反手后的绝对仓位
8. 缺失 signal valuation price -> fail closed
9. 既有非零仓位缺失 market price -> fail closed
10. 缺失 point_value -> fail closed
11. max_exposure 边界保持 >= reject
12. total_position 仍然按手数

============================================================
"""


import pytest


from risk.exposure import (
    ExposureEngine,
)

from risk.risk_manager_v2 import (
    RiskManagerV2,
)

from risk.limits import (
    RiskLimits,
)

from signals.signal import (
    Signal,
    SignalSide,
)





class FakePosition:

    def __init__(
        self,
        quantity,
        point_value=None,
    ):

        self.quantity = quantity

        if point_value is not None:

            self.point_value = point_value





class FakePortfolio:

    def __init__(
        self,
        positions=None,
        market_prices=None,
        point_values=None,
    ):

        self.positions = {}

        self.market_prices = {
            str(k).upper(): v
            for k, v
            in (market_prices or {}).items()
        }

        self.point_values = {
            str(k).upper(): v
            for k, v
            in (point_values or {}).items()
        }


        for symbol, spec in (
            positions or {}
        ).items():

            if isinstance(
                spec,
                tuple,
            ):

                quantity, point_value = spec

            else:

                quantity = spec

                point_value = (
                    self.point_values
                    .get(
                        str(symbol).upper()
                    )
                )


            self.positions[
                str(symbol).upper()
            ] = FakePosition(
                quantity,
                point_value,
            )





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
        bid,
        ask,
    ):

        self.orderbook = FakeBook(
            bid,
            ask,
        )





def make_signal(
    symbol,
    side,
    quantity,
):

    return Signal(

        symbol=symbol,

        side=side,

        quantity=quantity,

        confidence=1.0,

    )





def make_risk(
    max_exposure=10_000_000.0,
):

    return RiskManagerV2(

        limits=RiskLimits(

            max_position=100,

            max_total_position=100,

            max_exposure=max_exposure,

        )

    )





def test_first_es_entry_uses_pre_fill_valuation_price():

    risk = make_risk()

    portfolio = FakePortfolio(

        point_values={
            "ESU6": 50.0,
        }

    )


    decision = risk.check_signal(

        make_signal(
            "ESU6",
            SignalSide.BUY,
            2,
        ),

        portfolio,

        state=FakeState(
            7_571_000_000_000,
            7_571_250_000_000,
        ),

    )


    assert decision.approved is True

    assert (
        risk.last_projected_exposure
        .gross_notional
        ==
        pytest.approx(
            757125.0
        )
    )





def test_mes_uses_its_own_point_value():

    engine = ExposureEngine()

    portfolio = FakePortfolio(

        point_values={
            "MESU6": 5.0,
        }

    )


    projected = engine.project_signals(

        portfolio,

        "MESU6",

        SignalSide.BUY,

        2,

        valuation_price=7571.25,

    )


    assert projected.gross_notional == pytest.approx(
        75712.5
    )





def test_multisymbol_gross_notional():

    engine = ExposureEngine()

    portfolio = FakePortfolio(

        positions={
            "ESU6": (2, 50.0),
            "NQU6": (-1, 20.0),
        },

        market_prices={
            "ESU6": 7571.25,
            "NQU6": 25000.0,
        },

        point_values={
            "ESU6": 50.0,
            "NQU6": 20.0,
        },

    )


    projected = engine.project_signals(

        portfolio,

        "ESU6",

        SignalSide.BUY,

        1,

        valuation_price=7572.0,

    )


    expected = (
        3 * 7572.0 * 50.0
        +
        1 * 25000.0 * 20.0
    )


    assert projected.total_position == 4

    assert projected.gross_notional == pytest.approx(
        expected
    )

    assert projected.valuation_valid is True





def test_short_notional_uses_absolute_quantity():

    engine = ExposureEngine()

    portfolio = FakePortfolio(

        point_values={
            "ESU6": 50.0,
        }

    )


    projected = engine.project_signals(

        portfolio,

        "ESU6",

        SignalSide.SELL,

        2,

        valuation_price=7571.0,

    )


    assert projected.position_quantity == -2

    assert projected.gross_notional == pytest.approx(
        2 * 7571.0 * 50.0
    )





def test_reduce_position_reduces_notional():

    engine = ExposureEngine()

    portfolio = FakePortfolio(

        positions={
            "ESU6": (3, 50.0),
        },

        market_prices={
            "ESU6": 7571.25,
        },

    )


    projected = engine.project_signals(

        portfolio,

        "ESU6",

        SignalSide.SELL,

        1,

        valuation_price=7571.0,

    )


    assert projected.position_quantity == 2

    assert projected.gross_notional == pytest.approx(
        2 * 7571.0 * 50.0
    )





def test_flatten_removes_signal_symbol_notional():

    engine = ExposureEngine()

    portfolio = FakePortfolio(

        positions={
            "ESU6": (3, 50.0),
            "NQU6": (-1, 20.0),
        },

        market_prices={
            "ESU6": 7571.25,
            "NQU6": 25000.0,
        },

    )


    projected = engine.project_signals(

        portfolio,

        "ESU6",

        SignalSide.SELL,

        3,

        valuation_price=7571.0,

    )


    assert projected.position_quantity == 0

    assert projected.total_position == 1

    assert projected.gross_notional == pytest.approx(
        500000.0
    )





def test_reversal_uses_projected_absolute_position():

    engine = ExposureEngine()

    portfolio = FakePortfolio(

        positions={
            "ESU6": (3, 50.0),
        },

        market_prices={
            "ESU6": 7571.25,
        },

    )


    projected = engine.project_signals(

        portfolio,

        "ESU6",

        SignalSide.SELL,

        5,

        valuation_price=7571.0,

    )


    assert projected.position_quantity == -2

    assert projected.total_position == 2

    assert projected.gross_notional == pytest.approx(
        2 * 7571.0 * 50.0
    )





def test_missing_signal_valuation_price_fails_closed():

    risk = make_risk()

    portfolio = FakePortfolio(

        point_values={
            "ESU6": 50.0,
        }

    )


    decision = risk.check_signal(

        make_signal(
            "ESU6",
            SignalSide.BUY,
            1,
        ),

        portfolio,

        state=FakeState(
            bid=7571.0,
            ask=None,
        ),

    )


    assert decision.approved is False

    assert decision.checks["valuation"] is False

    assert "ESU6" in decision.reason





def test_existing_position_missing_market_price_fails_closed():

    risk = make_risk()

    portfolio = FakePortfolio(

        positions={
            "NQU6": (-1, 20.0),
        },

        market_prices={},

        point_values={
            "ESU6": 50.0,
            "NQU6": 20.0,
        },

    )


    decision = risk.check_signal(

        make_signal(
            "ESU6",
            SignalSide.BUY,
            1,
        ),

        portfolio,

        state=FakeState(
            7571.0,
            7571.25,
        ),

    )


    assert decision.approved is False

    assert "NQU6" in decision.reason





def test_missing_point_value_fails_closed():

    risk = make_risk()

    portfolio = FakePortfolio()


    decision = risk.check_signal(

        make_signal(
            "ESU6",
            SignalSide.BUY,
            1,
        ),

        portfolio,

        state=FakeState(
            7571.0,
            7571.25,
        ),

    )


    assert decision.approved is False

    assert "ESU6" in decision.reason





def test_max_exposure_boundary_is_rejected():

    exact_notional = (
        1
        *
        7571.25
        *
        50.0
    )


    risk = make_risk(
        max_exposure=exact_notional
    )


    portfolio = FakePortfolio(

        point_values={
            "ESU6": 50.0,
        }

    )


    decision = risk.check_signal(

        make_signal(
            "ESU6",
            SignalSide.BUY,
            1,
        ),

        portfolio,

        state=FakeState(
            7571.0,
            7571.25,
        ),

    )


    assert decision.approved is False

    assert (
        decision.checks["exposure_limit"]
        is False
    )





def test_total_position_remains_contract_count():

    engine = ExposureEngine()

    portfolio = FakePortfolio(

        positions={
            "ESU6": (2, 50.0),
            "NQU6": (-4, 20.0),
        },

        market_prices={
            "ESU6": 7571.25,
            "NQU6": 25000.0,
        },

    )


    projected = engine.project_signals(

        portfolio,

        "ESU6",

        SignalSide.BUY,

        1,

        valuation_price=7572.0,

    )


    assert projected.position_quantity == 3

    assert projected.total_position == 7
