"""
tests/test_context_builder_runtime.py


============================================================
Context Builder Runtime Contract Test
============================================================

验证：

    FeatureSnapshot
          +
    OrderBook
          +
    Portfolio
          +
    RiskManager

          ↓

    ContextBuilder

          ↓

    StrategyContext


不测试：

    Engine
    Strategy
    Signal
    Order
    Execution


============================================================
"""


from runtime.context_builder import ContextBuilder

from features.snapshot import FeatureSnapshot

from strategy.context import StrategyContext





class FakeOrderBook:
    """
    最小 OrderBook Mock

    只提供 ContextBuilder 当前需要的接口。
    """

    def __init__(self):

        self.best_bid = 7571000000000

        self.best_ask = 7571250000000

        self.orders = {
            1: object(),
            2: object(),
        }


    def bid_volume(self):

        return 120


    def ask_volume(self):

        return 100





class FakePosition:

    def __init__(self):

        self.quantity = 2

        self.side = "LONG"

        self.avg_price = 7570.0





class FakePortfolio:

    def __init__(self):

        self.position = FakePosition()


    def get_position(
        self,
        symbol
    ):

        return self.position





class FakeRiskManager:

    def snapshot(self):

        return {

            "approved": True,

            "kill_switch": False

        }







def test_context_builder_can_initialize():

    builder = ContextBuilder()

    assert builder is not None







def test_context_builder_build_strategy_context():


    snapshot = FeatureSnapshot(

        timestamp=100,

        sequence=10,

        symbol="ESU6",

        best_bid=7571000000000,

        best_ask=7571250000000,

        mid_price=7571.125,

        micro_price=7571.13,

        obi=0.25,

        ofi=0.15,

        trade_volume=500,

        aggressive_buy_volume=300,

        aggressive_sell_volume=200,

        trade_imbalance=0.2,

    )


    builder = ContextBuilder()


    context = builder.build(

        snapshot,

        FakeOrderBook(),

        FakePortfolio(),

        FakeRiskManager(),

    )



    assert isinstance(

        context,

        StrategyContext

    )



    assert context.timestamp == 100


    assert context.symbol == "ESU6"







def test_context_builder_orderbook_mapping():


    builder = ContextBuilder()


    context = builder.build(

        FeatureSnapshot(

            symbol="ESU6"

        ),

        FakeOrderBook(),

        FakePortfolio(),

        FakeRiskManager(),

    )



    assert context.orderbook.best_bid == 7571000000000


    assert context.orderbook.best_ask == 7571250000000


    assert context.orderbook.bid_size == 120


    assert context.orderbook.ask_size == 100


    assert context.orderbook.active_orders == 2







def test_context_builder_feature_mapping():


    snapshot = FeatureSnapshot(

        symbol="ESU6",

        mid_price=7571.125,

        micro_price=7571.13,

        obi=0.5,

        ofi=0.3,

        trade_volume=1000,

        aggressive_buy_volume=700,

        aggressive_sell_volume=300,

    )


    context = ContextBuilder().build(

        snapshot,

        FakeOrderBook(),

        FakePortfolio(),

        FakeRiskManager(),

    )


    assert context.features.mid_price == 7571.125


    assert context.features.micro_price == 7571.13


    assert context.features.obi == 0.5


    assert context.features.ofi == 0.3


    assert context.features.trade_volume == 1000


    assert context.features.aggressive_buy_volume == 700


    assert context.features.aggressive_sell_volume == 300







def test_context_builder_position_mapping():


    context = ContextBuilder().build(

        FeatureSnapshot(

            symbol="ESU6"

        ),

        FakeOrderBook(),

        FakePortfolio(),

        FakeRiskManager(),

    )


    assert context.position.symbol == "ESU6"


    assert context.position.quantity == 2


    assert context.position.side == "LONG"


    assert context.position.entry_price == 7570.0







def test_context_builder_risk_mapping():


    context = ContextBuilder().build(

        FeatureSnapshot(

            symbol="ESU6"

        ),

        FakeOrderBook(),

        FakePortfolio(),

        FakeRiskManager(),

    )


    assert context.risk.allowed is True


    assert context.risk.kill_switch is False