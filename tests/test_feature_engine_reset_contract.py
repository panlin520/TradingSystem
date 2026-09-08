"""
tests/test_feature_engine_reset_contract.py

============================================================
FeatureEngine Reset Lifecycle Contract
============================================================

目标：

    验证：

        FeatureEngine.reset()
            ↓
        FeatureSnapshot reset
        FlowFeatures reset
        RegimeFeatures reset
        Trade feature state reset
        events_processed reset

============================================================

特别重要：

    本测试不修改：

        core/*
        data/*
        orderbook/*

    只验证features生命周期。

============================================================
"""

from __future__ import annotations

import pytest

from core.event import (
    MarketEvent,
    OrderAction,
    OrderSide,
)

from features.feature_engine import FeatureEngine
from features.snapshot import FeatureSnapshot


# ============================================================
# Event Factory
# ============================================================


def make_event(
    *,
    sequence,
    action,
    side=None,
    order_id=None,
    price=None,
    size=None,
    flags=128,
    symbol="ESU6",
):
    return MarketEvent(
        ts_event=sequence,
        ts_recv=sequence,
        sequence=sequence,
        action=action,
        side=side,
        order_id=order_id,
        price=price,
        size=size,
        symbol=symbol,
        channel_id=0,
        publisher_id=1,
        instrument_id=1,
        flags=flags,
    )


# ============================================================
# Dummy OrderBook
# ============================================================


class FakeOrderBook:
    """
    只用于FeatureEngine reset测试。

    不替代真实OrderBook Ground Truth。
    """

    def __init__(self):
        self._best_bid = 100
        self._best_ask = 102
        self.bids = {}
        self.asks = {}
        self.orders = {}

    def best_bid(self):
        return self._best_bid

    def best_ask(self):
        return self._best_ask

    def bid_volume(self):
        return 10

    def ask_volume(self):
        return 10

    def spread(self):
        return (
            self._best_ask
            -
            self._best_bid
        )

    def mid_price(self):
        return (
            self._best_bid
            +
            self._best_ask
        ) / 2

    def micro_price(self):
        return (
            self._best_bid
            +
            self._best_ask
        ) / 2


# ============================================================
# Helpers
# ============================================================


def make_engine():
    """
    创建FeatureEngine。

    兼容当前构造函数：
        FeatureEngine(orderbook=...)
    """

    book = FakeOrderBook()

    engine = FeatureEngine(
        orderbook=book
    )

    return (
        engine,
        book,
    )


def populate_flow_state(
    engine,
):
    """
    直接向FlowFeatures喂事件，
    确保Shadow Orders产生真实状态。
    """

    snapshot = engine.snapshot

    snapshot = engine.flow_features.update(
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1001,
            price=100,
            size=10,
        ),
        snapshot,
    )

    snapshot = engine.flow_features.update(
        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=1002,
            price=102,
            size=8,
        ),
        snapshot,
    )

    snapshot = engine.flow_features.update(
        make_event(
            sequence=3,
            action=OrderAction.MODIFY,
            side=OrderSide.BID,
            order_id=1001,
            price=100,
            size=15,
        ),
        snapshot,
    )

    engine.snapshot = snapshot


def populate_snapshot_state(
    engine,
):
    """
    手动污染Snapshot，
    用于验证reset是否彻底恢复默认值。
    """

    snapshot = engine.snapshot

    snapshot.timestamp = 123456789
    snapshot.sequence = 999
    snapshot.symbol = "ESU6"

    snapshot.best_bid = 100
    snapshot.best_ask = 102
    snapshot.spread = 2

    snapshot.mid_price = 101.0
    snapshot.micro_price = 101.25
    snapshot.micro_price_delta = 0.25

    snapshot.bid_volume = 100
    snapshot.ask_volume = 80

    snapshot.bid_depth_5 = 50
    snapshot.ask_depth_5 = 40

    snapshot.bid_depth_10 = 100
    snapshot.ask_depth_10 = 80

    snapshot.obi = 0.25

    snapshot.last_trade_price = 101
    snapshot.last_trade_size = 5

    snapshot.trade_count = 10
    snapshot.trade_volume = 50

    snapshot.aggressive_buy_volume = 30
    snapshot.aggressive_sell_volume = 20
    snapshot.trade_imbalance = 0.2

    snapshot.add_volume = 100
    snapshot.cancel_volume = 50
    snapshot.modify_volume = 25

    snapshot.bid_added_volume = 60
    snapshot.bid_removed_volume = 10

    snapshot.ask_added_volume = 40
    snapshot.ask_removed_volume = 20

    snapshot.modify_added_volume = 15
    snapshot.modify_removed_volume = 5

    snapshot.price_move_count = 7
    snapshot.price_move_added_volume = 30
    snapshot.price_move_removed_volume = 25

    snapshot.signed_order_flow = 30
    snapshot.ofi = 0.3

    snapshot.liquidity_added = 150
    snapshot.liquidity_removed = 75
    snapshot.liquidity_balance = 0.333333

    snapshot.queue_pressure = 0.4
    snapshot.replenishment = 12

    snapshot.spread_regime = "WIDE"
    snapshot.volatility_regime = "HIGH"

    snapshot.extra[
        "test_state"
    ] = 123


def populate_regime_state(
    engine,
):
    """
    如果当前FeatureEngine已经集成RegimeFeatures，
    则污染其内部状态。

    如果还没有regime_features属性，
    当前测试会明确暴露这个生命周期缺口。
    """

    assert hasattr(
        engine,
        "regime_features"
    ), (
        "FeatureEngine当前没有regime_features属性；"
        "如果目标生命周期要求RegimeFeatures reset，"
        "需要正式集成RegimeFeatures。"
    )

    regime = engine.regime_features

    # ========================================================
    # History
    # ========================================================

    if hasattr(
        regime,
        "mid_prices"
    ):
        regime.mid_prices.extend(
            [
                100.0,
                101.0,
                102.0,
            ]
        )

    if hasattr(
        regime,
        "returns"
    ):
        regime.returns.extend(
            [
                1.0,
                1.0,
            ]
        )

    # ========================================================
    # Scores
    # ========================================================

    if hasattr(
        regime,
        "trend_score"
    ):
        regime.trend_score = 0.75

    if hasattr(
        regime,
        "volatility_score"
    ):
        regime.volatility_score = 0.80

    if hasattr(
        regime,
        "liquidity_score"
    ):
        regime.liquidity_score = 0.60

    # ========================================================
    # Enum states
    #
    # 不硬编码Enum类型，
    # 只保证当前状态不再是初始值即可。
    # ========================================================

    for name in (
        "trend",
        "volatility",
        "liquidity",
    ):
        if not hasattr(
            regime,
            name
        ):
            continue

        current = getattr(
            regime,
            name
        )

        enum_type = type(
            current
        )

        members = list(
            enum_type
        )

        for member in members:
            if member != current:
                setattr(
                    regime,
                    name,
                    member
                )
                break


# ============================================================
# Initial State
# ============================================================


def test_feature_engine_initial_snapshot_is_clean():
    engine, _ = make_engine()

    assert isinstance(
        engine.snapshot,
        FeatureSnapshot
    )

    assert engine.events_processed == 0

    assert engine.flow_features.active_order_count() == 0


# ============================================================
# Flow Can Hold State Before Reset
# ============================================================


def test_flow_shadow_has_state_before_reset():
    engine, _ = make_engine()

    populate_flow_state(
        engine
    )

    assert engine.flow_features.active_order_count() == 2

    assert engine.flow_features.get_order_state(
        1001
    ) is not None

    assert engine.flow_features.get_order_state(
        1002
    ) is not None


# ============================================================
# Snapshot Is Replaced
# ============================================================


def test_reset_replaces_snapshot_object():
    engine, _ = make_engine()

    old_snapshot = engine.snapshot

    populate_snapshot_state(
        engine
    )

    engine.reset()

    assert engine.snapshot is not old_snapshot

    assert isinstance(
        engine.snapshot,
        FeatureSnapshot
    )


# ============================================================
# Snapshot Defaults
# ============================================================


def test_reset_clears_snapshot_market_state():
    engine, _ = make_engine()

    populate_snapshot_state(
        engine
    )

    engine.reset()

    snapshot = engine.snapshot

    assert snapshot.timestamp == 0
    assert snapshot.sequence == 0
    assert snapshot.symbol == ""

    assert snapshot.best_bid is None
    assert snapshot.best_ask is None
    assert snapshot.spread is None

    assert snapshot.mid_price is None
    assert snapshot.micro_price is None
    assert snapshot.micro_price_delta is None

    assert snapshot.bid_volume == 0
    assert snapshot.ask_volume == 0

    assert snapshot.bid_depth_5 == 0
    assert snapshot.ask_depth_5 == 0

    assert snapshot.bid_depth_10 == 0
    assert snapshot.ask_depth_10 == 0

    assert snapshot.obi == 0.0


# ============================================================
# Trade Snapshot Reset
# ============================================================


def test_reset_clears_trade_snapshot_state():
    engine, _ = make_engine()

    populate_snapshot_state(
        engine
    )

    engine.reset()

    snapshot = engine.snapshot

    assert snapshot.last_trade_price is None
    assert snapshot.last_trade_size == 0

    assert snapshot.trade_count == 0
    assert snapshot.trade_volume == 0

    assert snapshot.aggressive_buy_volume == 0
    assert snapshot.aggressive_sell_volume == 0

    assert snapshot.trade_imbalance == 0.0


# ============================================================
# Flow Snapshot Reset
# ============================================================


def test_reset_clears_flow_snapshot_state():
    engine, _ = make_engine()

    populate_snapshot_state(
        engine
    )

    engine.reset()

    snapshot = engine.snapshot

    assert snapshot.add_volume == 0
    assert snapshot.cancel_volume == 0
    assert snapshot.modify_volume == 0

    assert snapshot.bid_added_volume == 0
    assert snapshot.bid_removed_volume == 0

    assert snapshot.ask_added_volume == 0
    assert snapshot.ask_removed_volume == 0

    assert snapshot.modify_added_volume == 0
    assert snapshot.modify_removed_volume == 0

    assert snapshot.price_move_count == 0

    assert snapshot.price_move_added_volume == 0
    assert snapshot.price_move_removed_volume == 0

    assert snapshot.signed_order_flow == 0

    assert snapshot.ofi == 0.0

    assert snapshot.liquidity_added == 0
    assert snapshot.liquidity_removed == 0

    assert snapshot.liquidity_balance == 0.0


# ============================================================
# Flow Shadow Reset
# ============================================================


def test_reset_clears_flow_shadow_orders():
    """
    这是本轮最关键测试。

    当前旧FeatureEngine.reset()
    很可能会失败在这里。
    """

    engine, _ = make_engine()

    populate_flow_state(
        engine
    )

    assert engine.flow_features.active_order_count() == 2

    engine.reset()

    assert engine.flow_features.active_order_count() == 0

    assert engine.flow_features.get_order_state(
        1001
    ) is None

    assert engine.flow_features.get_order_state(
        1002
    ) is None


# ============================================================
# Flow Diagnostics Reset
# ============================================================


def test_reset_removes_old_snapshot_extra():
    engine, _ = make_engine()

    engine.snapshot.extra[
        "flow_missing_modify_count"
    ] = 5

    engine.snapshot.extra[
        "flow_missing_cancel_count"
    ] = 3

    engine.reset()

    assert engine.snapshot.extra == {}


# ============================================================
# Regime Module Exists
# ============================================================


def test_feature_engine_has_regime_features():
    """
    如果目标Architecture已经要求：

        FeatureEngine
            ↓
        RegimeFeatures

    那么这里必须存在。
    """

    engine, _ = make_engine()

    assert hasattr(
        engine,
        "regime_features"
    )


# ============================================================
# Regime Reset API
# ============================================================


def test_regime_features_has_reset_contract():
    engine, _ = make_engine()

    assert hasattr(
        engine,
        "regime_features"
    )

    assert callable(
        getattr(
            engine.regime_features,
            "reset",
            None,
        )
    ), (
        "RegimeFeatures必须提供reset()，"
        "否则FeatureEngine无法统一清理生命周期状态。"
    )


# ============================================================
# Regime History Reset
# ============================================================


def test_reset_clears_regime_history():
    engine, _ = make_engine()

    populate_regime_state(
        engine
    )

    regime = engine.regime_features

    if hasattr(
        regime,
        "mid_prices"
    ):
        assert len(
            regime.mid_prices
        ) > 0

    if hasattr(
        regime,
        "returns"
    ):
        assert len(
            regime.returns
        ) > 0

    engine.reset()

    if hasattr(
        regime,
        "mid_prices"
    ):
        assert regime.mid_prices == []

    if hasattr(
        regime,
        "returns"
    ):
        assert regime.returns == []


# ============================================================
# Regime Scores Reset
# ============================================================


def test_reset_clears_regime_scores():
    engine, _ = make_engine()

    populate_regime_state(
        engine
    )

    regime = engine.regime_features

    engine.reset()

    if hasattr(
        regime,
        "trend_score"
    ):
        assert regime.trend_score == 0.0

    if hasattr(
        regime,
        "volatility_score"
    ):
        assert regime.volatility_score == 0.0

    if hasattr(
        regime,
        "liquidity_score"
    ):
        assert regime.liquidity_score == 0.0


# ============================================================
# events_processed
# ============================================================


def test_reset_clears_events_processed():
    engine, _ = make_engine()

    engine.events_processed = 999

    engine.reset()

    assert engine.events_processed == 0


# ============================================================
# OrderBook Reference Must Survive
# ============================================================


def test_reset_does_not_replace_orderbook_reference():
    """
    FeatureEngine.reset():

        重置Feature生命周期

    不应该：

        替换
        clear
        修改

    外部OrderBook。
    """

    engine, book = make_engine()

    original = engine.orderbook

    engine.reset()

    assert engine.orderbook is original

    assert engine.orderbook is book


# ============================================================
# Reset Is Idempotent
# ============================================================


def test_reset_is_idempotent():
    """
    连续reset不能报错。
    """

    engine, _ = make_engine()

    populate_flow_state(
        engine
    )

    engine.reset()

    engine.reset()

    engine.reset()

    assert engine.events_processed == 0

    assert engine.flow_features.active_order_count() == 0

    assert isinstance(
        engine.snapshot,
        FeatureSnapshot
    )


# ============================================================
# Engine Reusable After Reset
# ============================================================


def test_flow_engine_is_reusable_after_reset():
    """
    reset之后必须能像全新实例一样继续工作。
    """

    engine, _ = make_engine()

    populate_flow_state(
        engine
    )

    engine.reset()

    snapshot = engine.flow_features.update(
        make_event(
            sequence=100,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=9999,
            price=200,
            size=7,
        ),
        engine.snapshot,
    )

    engine.snapshot = snapshot

    assert engine.flow_features.active_order_count() == 1

    state = engine.flow_features.get_order_state(
        9999
    )

    assert state is not None

    assert state.price == 200

    assert state.size == 7

    assert engine.snapshot.bid_added_volume == 7

    assert engine.snapshot.signed_order_flow == 7

    assert engine.snapshot.ofi == pytest.approx(
        1.0
    )


# ============================================================
# Old Shadow Must Not Leak Into New Session
# ============================================================


def test_old_order_id_does_not_leak_after_reset():
    """
    Session 1：

        ADD order 1

    reset

    Session 2：

        M order 1

    正确：

        新session里order 1不存在。

    所以应该被记录成：

        flow_missing_modify_count = 1
    """

    engine, _ = make_engine()

    engine.snapshot = (
        engine.flow_features.update(
            make_event(
                sequence=1,
                action=OrderAction.ADD,
                side=OrderSide.BID,
                order_id=1,
                price=100,
                size=10,
            ),
            engine.snapshot,
        )
    )

    assert engine.flow_features.get_order_state(
        1
    ) is not None

    engine.reset()

    assert engine.flow_features.get_order_state(
        1
    ) is None

    engine.snapshot = (
        engine.flow_features.update(
            make_event(
                sequence=2,
                action=OrderAction.MODIFY,
                side=OrderSide.BID,
                order_id=1,
                price=100,
                size=20,
            ),
            engine.snapshot,
        )
    )

    assert (
        engine.snapshot.extra[
            "flow_missing_modify_count"
        ]
        ==
        1
    )

    assert engine.snapshot.modify_added_volume == 0


# ============================================================
# TradeFeatures Lifecycle
# ============================================================


def test_trade_features_lifecycle_contract():
    """
    当前TradeFeatures如果完全无内部历史状态，
    reset可以：

        1. 提供reset()空实现

    或：

        2. FeatureEngine重新创建TradeFeatures

    最终要求是：

        新session不得继承内部Trade state。

    这里检查公开对象是否能安全重建/重置。
    """

    engine, _ = make_engine()

    trade = engine.trade_features

    # 如果TradeFeatures已有reset，则应可调用。
    if callable(
        getattr(
            trade,
            "reset",
            None,
        )
    ):
        trade.reset()

    # 当前最重要的是：
    # reset之后FeatureEngine仍然必须有可用TradeFeatures。
    engine.reset()

    assert engine.trade_features is not None


# ============================================================
# Full Reset Diagnostic
# ============================================================


def test_feature_engine_reset_diagnostic():
    engine, _ = make_engine()

    populate_snapshot_state(
        engine
    )

    populate_flow_state(
        engine
    )

    engine.events_processed = 123

    flow_before = (
        engine.flow_features.active_order_count()
    )

    snapshot_before = engine.snapshot

    print(
        "\n"
        "============================================================"
    )

    print(
        "FEATURE ENGINE RESET DIAGNOSTIC"
    )

    print(
        "============================================================"
    )

    print(
        "Before reset:"
    )

    print(
        "events_processed      =",
        engine.events_processed
    )

    print(
        "flow active orders    =",
        flow_before
    )

    print(
        "signed_order_flow     =",
        engine.snapshot.signed_order_flow
    )

    print(
        "trade_volume          =",
        engine.snapshot.trade_volume
    )

    print(
        "snapshot id           =",
        id(
            snapshot_before
        )
    )

    engine.reset()

    print(
        "\nAfter reset:"
    )

    print(
        "events_processed      =",
        engine.events_processed
    )

    print(
        "flow active orders    =",
        engine.flow_features.active_order_count()
    )

    print(
        "signed_order_flow     =",
        engine.snapshot.signed_order_flow
    )

    print(
        "trade_volume          =",
        engine.snapshot.trade_volume
    )

    print(
        "snapshot id           =",
        id(
            engine.snapshot
        )
    )

    print(
        "snapshot replaced     =",
        engine.snapshot is not snapshot_before
    )

    print(
        "============================================================"
    )

    assert engine.events_processed == 0

    assert engine.flow_features.active_order_count() == 0

    assert engine.snapshot.signed_order_flow == 0

    assert engine.snapshot.trade_volume == 0

    assert engine.snapshot is not snapshot_before