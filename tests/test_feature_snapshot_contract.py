"""
tests/test_feature_snapshot_contract.py


============================================================
Feature Snapshot Contract Test
============================================================


验证：

    OrderBook

        ↓

    FeatureEngine

        ↓

    features.snapshot.FeatureSnapshot


目标：

    确认 FeatureSnapshot 只有一个来源：

        features.snapshot


    防止：

        features.engine.FeatureSnapshot

        与

        features.snapshot.FeatureSnapshot


    重复定义。


============================================================

"""


from features.engine import FeatureEngine

from features.snapshot import FeatureSnapshot





class FakeOrderBook:
    """
    最小 OrderBook Mock


    只提供 FeatureEngine 当前需要的方法。

    """



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

        return 1000



    def ask_volume(self):

        return 800



    def imbalance(self):

        return 0.1111





def test_feature_engine_can_initialize():


    engine = FeatureEngine(

        FakeOrderBook()

    )


    assert engine is not None





def test_feature_engine_returns_snapshot():


    engine = FeatureEngine(

        FakeOrderBook()

    )


    snapshot = engine.update(

        timestamp=100

    )


    assert isinstance(

        snapshot,

        FeatureSnapshot

    )





def test_snapshot_mapping():


    engine = FeatureEngine(

        FakeOrderBook()

    )


    snapshot = engine.update(

        timestamp=100

    )



    assert snapshot.best_bid == 7571000000000


    assert snapshot.best_ask == 7571250000000


    assert snapshot.spread == 250000000


    assert snapshot.mid_price == 7571.125


    assert snapshot.micro_price == 7571.13


    assert snapshot.bid_volume == 1000


    assert snapshot.ask_volume == 800


    assert snapshot.obi == 0.1111


    assert snapshot.timestamp == 100





def test_snapshot_single_source_contract():


    snapshot = FeatureSnapshot()


    module_name = (

        snapshot.__class__.__module__

    )


    assert module_name == (

        "features.snapshot"

    )





def test_feature_engine_latest_snapshot():


    engine = FeatureEngine(

        FakeOrderBook()

    )


    assert engine.get_latest() is None



    snapshot = engine.update(

        timestamp=200

    )


    latest = engine.get_latest()



    assert latest is snapshot