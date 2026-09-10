"""
tests/test_strategy_context_runtime.py


============================================================
Strategy Context Runtime Contract Test
============================================================


验证：

    SystemState

        ↓

    StrategyContextRuntime

        ↓

    ContextBuilder

        ↓

    StrategyContext



不测试：

    Engine

    Strategy

    Signal

    Risk

    Execution



============================================================

"""


from core.state import SystemState

from runtime.strategy_context_runtime import (
    StrategyContextRuntime,
)

from strategy.context import StrategyContext

from features.snapshot import FeatureSnapshot





class FakeOrderBook:
    """
    最小 OrderBook Mock
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

            "kill_switch": False,

        }





def create_state():

    """
    创建完整 SystemState。
    """

    state = SystemState()



    state.feature_snapshot = FeatureSnapshot(

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



    state.orderbook = FakeOrderBook()


    state.portfolio = FakePortfolio()



    state.risk_manager = FakeRiskManager()



    return state





def test_strategy_context_runtime_can_initialize():


    runtime = StrategyContextRuntime()



    assert runtime is not None





def test_strategy_context_runtime_build_context():


    runtime = StrategyContextRuntime()


    state = create_state()



    context = runtime.build(

        state

    )



    assert isinstance(

        context,

        StrategyContext

    )





def test_strategy_context_runtime_feature_mapping():


    runtime = StrategyContextRuntime()


    state = create_state()



    context = runtime.build(

        state

    )



    assert context.features.mid_price == 7571.125


    assert context.features.micro_price == 7571.13


    assert context.features.obi == 0.25


    assert context.features.trade_volume == 500





def test_strategy_context_runtime_orderbook_mapping():


    runtime = StrategyContextRuntime()


    context = runtime.build(

        create_state()

    )



    assert context.orderbook.best_bid == 7571000000000


    assert context.orderbook.best_ask == 7571250000000


    assert context.orderbook.bid_size == 120


    assert context.orderbook.ask_size == 100





def test_strategy_context_runtime_position_mapping():


    runtime = StrategyContextRuntime()


    context = runtime.build(

        create_state()

    )



    assert context.position.symbol == "ESU6"


    assert context.position.quantity == 2


    assert context.position.side == "LONG"





def test_strategy_context_runtime_has_feature():


    runtime = StrategyContextRuntime()


    state = create_state()



    assert runtime.has_feature(

        state

    ) is True





def test_strategy_context_runtime_without_feature():


    runtime = StrategyContextRuntime()


    state = SystemState()



    assert runtime.has_feature(

        state

    ) is False