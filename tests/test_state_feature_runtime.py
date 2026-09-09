"""
tests/test_state_feature_runtime.py


============================================================
SystemState Feature Snapshot Contract Test
============================================================


验证：

    FeatureSnapshot

        ↓

    SystemState

        ↓

    snapshot()


目标：

    确认 SystemState 可以保存 FeatureSnapshot。


============================================================

"""


from core.state import SystemState

from features.snapshot import FeatureSnapshot





def create_snapshot():

    """
    创建测试 FeatureSnapshot。
    """

    return FeatureSnapshot(

        best_bid=7571000000000,

        best_ask=7571250000000,

        spread=250000000,

        mid_price=7571.125,

        micro_price=7571.13,

        bid_volume=1200,

        ask_volume=900,

        obi=0.1428,

        timestamp=100,

    )





def test_state_can_initialize():

    state = SystemState()


    assert state is not None


    assert state.feature_snapshot is None





def test_state_can_set_feature_snapshot():


    state = SystemState()


    snapshot = create_snapshot()



    state.set_feature_snapshot(

        snapshot

    )



    assert state.feature_snapshot is snapshot





def test_state_feature_snapshot_mapping():


    state = SystemState()


    snapshot = create_snapshot()



    state.set_feature_snapshot(

        snapshot

    )



    assert state.feature_snapshot.mid_price == 7571.125


    assert state.feature_snapshot.obi == 0.1428


    assert state.feature_snapshot.timestamp == 100





def test_state_snapshot_contains_feature():


    state = SystemState()


    snapshot = create_snapshot()



    state.set_feature_snapshot(

        snapshot

    )



    data = state.snapshot()



    assert "feature" in data


    assert data["feature"]["mid_price"] == 7571.125


    assert data["feature"]["best_bid"] == 7571000000000


    assert data["feature"]["timestamp"] == 100





def test_state_without_feature_snapshot():


    state = SystemState()



    data = state.snapshot()



    assert data["feature"] is None