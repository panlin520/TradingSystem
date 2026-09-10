"""
tests/test_exposure_multisymbol_contract.py

============================================================
Exposure Multi-Symbol Contract
============================================================

验证：

    total_position
        =
    Σ abs(position.quantity)

    gross_exposure
        =
    Σ abs(position.quantity)

当前 ExposureEngine 尚未接入价格和合约乘数，
因此 exposure 使用数量型定义。

覆盖：

1. 多品种已有仓位
2. 新 symbol
3. 已有 symbol 增仓
4. 已有 symbol 减仓
5. 已有 symbol 平仓
6. 已有 symbol 反手
7. LONG / SHORT 混合
8. Runtime SignalSide Enum

============================================================
"""


from risk.exposure import ExposureEngine

from signals.signal import SignalSide





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

        self.positions = {

            symbol:
                FakePosition(quantity)

            for symbol, quantity
            in (positions or {}).items()

        }


    def get_position(
        self,
        symbol,
    ):

        return self.positions.get(
            symbol
        )





def test_multisymbol_current_symbol_increase():

    engine = ExposureEngine()

    portfolio = FakePortfolio(
        {
            "ESU6": 3,
            "NQU6": -4,
        }
    )


    projected = engine.project_signal(

        portfolio=portfolio,

        symbol="ESU6",

        side=SignalSide.BUY,

        quantity=2,

    )


    assert projected.position_quantity == 5

    assert projected.total_position == 9

    assert projected.gross_exposure == 9





def test_multisymbol_current_symbol_reduce():

    engine = ExposureEngine()

    portfolio = FakePortfolio(
        {
            "ESU6": 3,
            "NQU6": -4,
        }
    )


    projected = engine.project_signal(

        portfolio=portfolio,

        symbol="ESU6",

        side=SignalSide.SELL,

        quantity=1,

    )


    assert projected.position_quantity == 2

    assert projected.total_position == 6

    assert projected.gross_exposure == 6





def test_multisymbol_current_symbol_flatten():

    engine = ExposureEngine()

    portfolio = FakePortfolio(
        {
            "ESU6": 3,
            "NQU6": -4,
        }
    )


    projected = engine.project_signal(

        portfolio=portfolio,

        symbol="ESU6",

        side=SignalSide.SELL,

        quantity=3,

    )


    assert projected.position_quantity == 0

    assert projected.total_position == 4

    assert projected.gross_exposure == 4





def test_multisymbol_short_reduce():

    engine = ExposureEngine()

    portfolio = FakePortfolio(
        {
            "ESU6": 3,
            "NQU6": -4,
        }
    )


    projected = engine.project_signal(

        portfolio=portfolio,

        symbol="NQU6",

        side=SignalSide.BUY,

        quantity=2,

    )


    assert projected.position_quantity == -2

    assert projected.total_position == 5

    assert projected.gross_exposure == 5





def test_multisymbol_reversal():

    engine = ExposureEngine()

    portfolio = FakePortfolio(
        {
            "ESU6": 3,
            "NQU6": -4,
        }
    )


    projected = engine.project_signal(

        portfolio=portfolio,

        symbol="ESU6",

        side=SignalSide.SELL,

        quantity=5,

    )


    assert projected.position_quantity == -2

    assert projected.total_position == 6

    assert projected.gross_exposure == 6





def test_new_symbol_is_added_once():

    engine = ExposureEngine()

    portfolio = FakePortfolio(
        {
            "ESU6": 3,
            "NQU6": -4,
        }
    )


    projected = engine.project_signal(

        portfolio=portfolio,

        symbol="MESU6",

        side=SignalSide.BUY,

        quantity=2,

    )


    assert projected.position_quantity == 2

    assert projected.total_position == 9

    assert projected.gross_exposure == 9





def test_new_short_symbol_is_added_once():

    engine = ExposureEngine()

    portfolio = FakePortfolio(
        {
            "ESU6": 3,
            "NQU6": -4,
        }
    )


    projected = engine.project_signal(

        portfolio=portfolio,

        symbol="MNQU6",

        side=SignalSide.SELL,

        quantity=2,

    )


    assert projected.position_quantity == -2

    assert projected.total_position == 9

    assert projected.gross_exposure == 9
