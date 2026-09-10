"""
tests/test_exposure_enum_side_contract.py

============================================================
Exposure Enum Side Contract
============================================================

验证：

    ExposureEngine 必须正确识别 Runtime SignalSide Enum。

场景：

    LONG 3 + SELL 3
        -> projected position = 0

    LONG 3 + SELL 1
        -> projected position = 2

    SHORT -2 + BUY 2
        -> projected position = 0

    SHORT -2 + BUY 1
        -> projected position = -1

同时验证：

    project_signals() compatibility wrapper
    字符串 BUY / SELL 兼容行为保持不变

============================================================
"""


from risk.exposure import (
    ExposureEngine,
)

from signals.signal import (
    SignalSide,
)





class FakePosition:

    def __init__(
        self,
        quantity,
    ):

        self.quantity = quantity





class FakePortfolio:

    def __init__(
        self,
        positions=None,
    ):

        self.positions = (
            positions
            if positions is not None
            else {}
        )


    def get_position(
        self,
        symbol,
    ):

        return self.positions.get(
            symbol
        )





def make_portfolio(
    quantity,
    symbol="ESU6",
):

    return FakePortfolio(
        {
            symbol:
                FakePosition(
                    quantity
                )
        }
    )





def test_long_three_sell_three_enum_projects_flat():

    engine = ExposureEngine()

    portfolio = make_portfolio(
        quantity=3
    )


    projected = engine.project_signal(

        portfolio=portfolio,

        symbol="ESU6",

        side=SignalSide.SELL,

        quantity=3,

    )


    assert projected.position_quantity == 0

    assert projected.total_position == 0

    assert projected.gross_exposure == 0





def test_long_three_sell_one_enum_projects_long_two():

    engine = ExposureEngine()

    portfolio = make_portfolio(
        quantity=3
    )


    projected = engine.project_signal(

        portfolio=portfolio,

        symbol="ESU6",

        side=SignalSide.SELL,

        quantity=1,

    )


    assert projected.position_quantity == 2

    assert projected.total_position == 2

    assert projected.gross_exposure == 2





def test_short_two_buy_two_enum_projects_flat():

    engine = ExposureEngine()

    portfolio = make_portfolio(
        quantity=-2
    )


    projected = engine.project_signal(

        portfolio=portfolio,

        symbol="ESU6",

        side=SignalSide.BUY,

        quantity=2,

    )


    assert projected.position_quantity == 0

    assert projected.total_position == 0

    assert projected.gross_exposure == 0





def test_short_two_buy_one_enum_projects_short_one():

    engine = ExposureEngine()

    portfolio = make_portfolio(
        quantity=-2
    )


    projected = engine.project_signal(

        portfolio=portfolio,

        symbol="ESU6",

        side=SignalSide.BUY,

        quantity=1,

    )


    assert projected.position_quantity == -1

    assert projected.total_position == 1

    assert projected.gross_exposure == 1





def test_project_signals_wrapper_supports_enum_side():

    engine = ExposureEngine()

    portfolio = make_portfolio(
        quantity=4
    )


    projected = engine.project_signals(

        portfolio=portfolio,

        symbol="ESU6",

        side=SignalSide.SELL,

        quantity=4,

    )


    assert projected.position_quantity == 0

    assert projected.total_position == 0

    assert projected.gross_exposure == 0





def test_string_buy_remains_supported():

    engine = ExposureEngine()

    portfolio = make_portfolio(
        quantity=-2
    )


    projected = engine.project_signal(

        portfolio=portfolio,

        symbol="ESU6",

        side="BUY",

        quantity=2,

    )


    assert projected.position_quantity == 0





def test_string_sell_remains_supported():

    engine = ExposureEngine()

    portfolio = make_portfolio(
        quantity=3
    )


    projected = engine.project_signal(

        portfolio=portfolio,

        symbol="ESU6",

        side="SELL",

        quantity=3,

    )


    assert projected.position_quantity == 0
