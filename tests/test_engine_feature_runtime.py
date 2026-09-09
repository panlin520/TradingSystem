"""
tests/test_engine_feature_runtime.py


============================================================
Engine Feature Runtime Contract Test
============================================================


验证：

    TradingEngine

        ↓

    FeatureRuntime

        ↓

    SystemState.feature_snapshot



目标：

    确认 Engine 接入 FeatureRuntime 后：

    1. MarketEvent 可以进入 Engine

    2. OrderBook 更新后触发 FeatureRuntime

    3. FeatureSnapshot 写入 SystemState



============================================================

"""


from core.engine import TradingEngine, EngineMode

from features.engine import FeatureEngine

from runtime.feature_runtime import FeatureRuntime

from features.snapshot import FeatureSnapshot





class FakeEvent:
    """
    最小 MarketEvent Mock。

    Engine 当前需要：

        ts_event

        flags


    """



    def __init__(self):

        self.ts_event = 100

        self.flags = 128





class FakeOrderBook:
    """
    最小 OrderBook Mock。



    FeatureEngine依赖：

        best_bid

        best_ask

        spread

        mid_price

        micro_price

        bid_volume

        ask_volume

        imbalance



    """



    def on_event(
        self,
        event
    ):

        pass



    def best_bid(self):

        return 7571000000000



    def best_ask(self):

        return 7571250000000



    def spread(self):

        return 250000000



    def mid_price(self):

        return 7571.125



    def micro_price(self):

        return 7571.13



    def bid_volume(self):

        return 1200



    def ask_volume(self):

        return 900



    def imbalance(self):

        return 0.1428





def create_engine():

    orderbook = FakeOrderBook()



    feature_engine = FeatureEngine(

        orderbook

    )


    feature_runtime = FeatureRuntime(

        feature_engine

    )



    engine = TradingEngine(

        mode=EngineMode.BACKTEST,

        orderbook=orderbook,

        feature_runtime=feature_runtime,

    )



    return engine





def test_engine_can_initialize_feature_runtime():


    engine = create_engine()



    assert engine.feature_runtime is not None





def test_engine_updates_feature_snapshot():


    engine = create_engine()



    engine.start()



    event = FakeEvent()



    engine.on_event(

        event

    )



    assert engine.state.feature_snapshot is not None





def test_engine_feature_snapshot_type():


    engine = create_engine()



    engine.start()



    engine.on_event(

        FakeEvent()

    )



    snapshot = engine.state.feature_snapshot



    assert isinstance(

        snapshot,

        FeatureSnapshot

    )





def test_engine_feature_snapshot_mapping():


    engine = create_engine()



    engine.start()



    engine.on_event(

        FakeEvent()

    )



    snapshot = engine.state.feature_snapshot



    assert snapshot.best_bid == 7571000000000


    assert snapshot.best_ask == 7571250000000


    assert snapshot.mid_price == 7571.125


    assert snapshot.obi == 0.1428


    assert snapshot.timestamp == 100





def test_engine_without_feature_runtime_still_runs():


    engine = TradingEngine(

        mode=EngineMode.BACKTEST,

        orderbook=FakeOrderBook(),

    )



    engine.start()



    engine.on_event(

        FakeEvent()

    )



    assert engine.state.feature_snapshot is None