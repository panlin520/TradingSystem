"""
tests/test_feature_runtime.py


============================================================
Feature Runtime Contract Test
============================================================


验证：

    FeatureEngine

        ↓

    FeatureRuntime

        ↓

    FeatureSnapshot



目标：

    确认 Runtime 层可以正确管理 Feature 生命周期。



============================================================

"""


from features.engine import FeatureEngine

from features.snapshot import FeatureSnapshot

from runtime.feature_runtime import FeatureRuntime





class FakeOrderBook:
    """
    最小 OrderBook Mock。


    FeatureEngine 当前依赖：

        best_bid()

        best_ask()

        spread()

        mid_price()

        micro_price()

        bid_volume()

        ask_volume()

        imbalance()



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

        return 1200



    def ask_volume(self):

        return 900



    def imbalance(self):

        return 0.1428





def create_runtime():

    """
    创建测试Runtime。

    """

    orderbook = FakeOrderBook()


    engine = FeatureEngine(

        orderbook

    )


    runtime = FeatureRuntime(

        engine

    )


    return runtime





def test_feature_runtime_can_initialize():


    runtime = create_runtime()


    assert runtime is not None


    assert runtime.get_latest() is None





def test_feature_runtime_update_returns_snapshot():


    runtime = create_runtime()


    snapshot = runtime.update(

        timestamp=100

    )


    assert isinstance(

        snapshot,

        FeatureSnapshot

    )





def test_feature_runtime_stores_latest_snapshot():


    runtime = create_runtime()


    snapshot = runtime.update(

        timestamp=200

    )


    latest = runtime.get_latest()



    assert latest is snapshot





def test_feature_runtime_snapshot_mapping():


    runtime = create_runtime()


    snapshot = runtime.update(

        timestamp=300

    )


    assert snapshot.best_bid == 7571000000000


    assert snapshot.best_ask == 7571250000000


    assert snapshot.mid_price == 7571.125


    assert snapshot.micro_price == 7571.13


    assert snapshot.bid_volume == 1200


    assert snapshot.ask_volume == 900


    assert snapshot.obi == 0.1428


    assert snapshot.timestamp == 300





def test_feature_runtime_has_snapshot():


    runtime = create_runtime()


    assert runtime.has_snapshot() is False



    runtime.update(

        timestamp=400

    )


    assert runtime.has_snapshot() is True





def test_feature_runtime_reset():


    runtime = create_runtime()


    runtime.update(

        timestamp=500

    )


    assert runtime.has_snapshot() is True



    runtime.reset()



    assert runtime.has_snapshot() is False


    assert runtime.get_latest() is None





def test_feature_runtime_to_dict():


    runtime = create_runtime()


    assert runtime.to_dict() == {}



    runtime.update(

        timestamp=600

    )


    data = runtime.to_dict()



    assert data["best_bid"] == 7571000000000


    assert data["best_ask"] == 7571250000000


    assert data["timestamp"] == 600