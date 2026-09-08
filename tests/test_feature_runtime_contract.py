"""
tests/test_feature_runtime_contract.py

============================================================
Feature Runtime Contract Tests
============================================================

目标：

    验证当前 Feature 子系统真实运行时契约。

测试范围：

    FeatureSnapshot
    OrderBookFeatures
    TradeFeatures
    FlowFeatures
    RegimeFeatures
    FeatureEngine

============================================================

本测试暂时不接：

    - Databento DBN
    - Frozen OrderBook真实重放
    - StrategyManager
    - Risk
    - Execution
    - Portfolio

============================================================

核心原则：

    先验证模块自己的接口是否闭合。

    如果测试失败：

        优先修 Feature 层。

    不允许为了 Feature 测试去修改：

        orderbook/*
        data/*
        core/engine.py

============================================================
"""

from enum import Enum

import pytest

from features.snapshot import FeatureSnapshot
from features.orderbook_features import OrderBookFeatures
from features.trade_features import TradeFeatures
from features.flow_features import FlowFeatures
from features.regime_features import (
    RegimeFeatures,
    TrendRegime,
    VolatilityRegime,
    LiquidityRegime,
)
from features.feature_engine import FeatureEngine


# ============================================================
# Fake Infrastructure
# ============================================================


class FakeAction(Enum):
    ADD = "A"
    MODIFY = "M"
    CANCEL = "C"
    RESET = "R"
    TRADE = "T"
    FILL = "F"
    NONE = "N"


class FakeSide(Enum):
    BID = "B"
    ASK = "A"


class FakeEvent:
    """
    最小 MarketEvent 模拟对象。
    """

    def __init__(
        self,
        *,
        action,
        side=FakeSide.BID,
        price=100,
        size=1,
        order_id=None,
        sequence=1,
        timestamp=1,
    ):
        self.action = action
        self.side = side
        self.price = price
        self.size = size
        self.order_id = order_id
        self.sequence = sequence
        self.timestamp = timestamp


class FakeLevel:
    """
    模拟 PriceLevel。

    OrderBookFeatures._depth() 当前读取：

        level.volume
    """

    def __init__(
        self,
        volume
    ):
        self.volume = volume


class FakeOrderBook:
    """
    使用当前冻结 OrderBook 的公开访问风格：

        best_bid()
        best_ask()
        bid_volume()
        ask_volume()

    bids / asks:

        price -> level
    """

    def __init__(
        self,
        *,
        best_bid=100,
        best_ask=102,
        bid_levels=None,
        ask_levels=None,
    ):
        self._best_bid = best_bid
        self._best_ask = best_ask

        if bid_levels is None:
            bid_levels = {
                100: 10,
                99: 20,
                98: 30,
            }

        if ask_levels is None:
            ask_levels = {
                102: 15,
                103: 25,
                104: 35,
            }

        self.bids = {
            price: FakeLevel(volume)
            for price, volume in bid_levels.items()
        }

        self.asks = {
            price: FakeLevel(volume)
            for price, volume in ask_levels.items()
        }

    def best_bid(self):
        return self._best_bid

    def best_ask(self):
        return self._best_ask

    def spread(self):
        if (
            self._best_bid is None
            or
            self._best_ask is None
        ):
            return None

        return (
            self._best_ask
            -
            self._best_bid
        )

    def mid_price(self):
        if (
            self._best_bid is None
            or
            self._best_ask is None
        ):
            return None

        return (
            self._best_bid
            +
            self._best_ask
        ) / 2

    def bid_volume(self):
        return sum(
            level.volume
            for level in self.bids.values()
        )

    def ask_volume(self):
        return sum(
            level.volume
            for level in self.asks.values()
        )

    def micro_price(self):
        bid = self.best_bid()
        ask = self.best_ask()

        bid_volume = self.bid_volume()
        ask_volume = self.ask_volume()

        total = (
            bid_volume
            +
            ask_volume
        )

        if (
            bid is None
            or
            ask is None
        ):
            return None

        if total == 0:
            return (
                bid
                +
                ask
            ) / 2

        return (
            ask * bid_volume
            +
            bid * ask_volume
        ) / total

    def imbalance(self):
        bid = self.bid_volume()
        ask = self.ask_volume()

        total = bid + ask

        if total == 0:
            return 0.0

        return (
            bid
            -
            ask
        ) / total


# ============================================================
# FeatureSnapshot
# ============================================================


def test_feature_snapshot_can_initialize():
    """
    FeatureSnapshot必须可以无参数初始化。
    """

    snapshot = FeatureSnapshot()

    assert snapshot.timestamp == 0
    assert snapshot.sequence == 0
    assert snapshot.symbol == ""

    assert snapshot.best_bid is None
    assert snapshot.best_ask is None

    assert snapshot.bid_volume == 0
    assert snapshot.ask_volume == 0

    assert snapshot.trade_count == 0
    assert snapshot.trade_volume == 0

    assert snapshot.ofi == 0.0


def test_feature_snapshot_copy_is_independent():
    """
    copy()必须产生独立对象。
    """

    snapshot = FeatureSnapshot(
        mid_price=100.0,
        trade_volume=10,
    )

    copied = snapshot.copy()

    assert copied is not snapshot

    assert copied.mid_price == 100.0
    assert copied.trade_volume == 10

    copied.trade_volume = 99

    assert snapshot.trade_volume == 10


def test_feature_snapshot_to_dict():
    """
    to_dict()必须返回普通dict。
    """

    snapshot = FeatureSnapshot(
        symbol="ESU6",
        mid_price=100.0,
        ofi=0.25,
    )

    data = snapshot.to_dict()

    assert isinstance(
        data,
        dict
    )

    assert data[
        "symbol"
    ] == "ESU6"

    assert data[
        "mid_price"
    ] == 100.0

    assert data[
        "ofi"
    ] == 0.25


# ============================================================
# OrderBookFeatures
# ============================================================


def test_orderbook_features_has_calculate_contract():
    """
    当前 OrderBookFeatures 正式入口：

        calculate(book, snapshot)

    不是：

        update(...)
    """

    features = OrderBookFeatures()

    assert hasattr(
        features,
        "calculate"
    )

    assert callable(
        features.calculate
    )


def test_orderbook_features_calculate():
    """
    验证盘口基础特征。
    """

    book = FakeOrderBook(
        best_bid=100,
        best_ask=102,
        bid_levels={
            100: 10,
            99: 20,
            98: 30,
        },
        ask_levels={
            102: 15,
            103: 25,
            104: 35,
        },
    )

    features = OrderBookFeatures()

    snapshot = features.calculate(
        book
    )

    assert isinstance(
        snapshot,
        FeatureSnapshot
    )

    assert snapshot.best_bid == 100
    assert snapshot.best_ask == 102

    assert snapshot.spread == 2

    assert snapshot.mid_price == 101.0

    assert snapshot.bid_volume == 60
    assert snapshot.ask_volume == 75

    assert snapshot.bid_depth_5 == 60
    assert snapshot.ask_depth_5 == 75

    assert snapshot.bid_depth_10 == 60
    assert snapshot.ask_depth_10 == 75

    expected_obi = (
        60 - 75
    ) / (
        60 + 75
    )

    assert snapshot.obi == pytest.approx(
        expected_obi
    )

    assert snapshot.queue_pressure == pytest.approx(
        expected_obi
    )


def test_orderbook_micro_price():
    """
    Micro Price:

        (Ask * BidVolume + Bid * AskVolume)
        /
        (BidVolume + AskVolume)
    """

    book = FakeOrderBook(
        best_bid=100,
        best_ask=102,
        bid_levels={
            100: 100,
        },
        ask_levels={
            102: 50,
        },
    )

    features = OrderBookFeatures()

    snapshot = features.calculate(
        book
    )

    expected = (
        102 * 100
        +
        100 * 50
    ) / 150

    assert snapshot.micro_price == pytest.approx(
        expected
    )

    assert snapshot.micro_price_delta == pytest.approx(
        expected
        -
        snapshot.mid_price
    )


# ============================================================
# TradeFeatures
# ============================================================


def test_trade_features_non_trade_ignored():
    """
    非成交事件不能增加成交统计。
    """

    features = TradeFeatures()

    snapshot = FeatureSnapshot()

    event = FakeEvent(
        action=FakeAction.ADD,
        side=FakeSide.BID,
        price=100,
        size=10,
    )

    result = features.update(
        event,
        snapshot
    )

    assert result is snapshot

    assert snapshot.trade_count == 0
    assert snapshot.trade_volume == 0


def test_trade_features_buy_trade():
    """
    当前 TradeFeatures 根据 event.side
    判断主动方向。

    B -> BUY
    """

    features = TradeFeatures()

    snapshot = FeatureSnapshot()

    event = FakeEvent(
        action=FakeAction.TRADE,
        side=FakeSide.BID,
        price=101,
        size=5,
    )

    result = features.update(
        event,
        snapshot
    )

    assert result is snapshot

    assert snapshot.last_trade_price == 101
    assert snapshot.last_trade_size == 5

    assert snapshot.trade_count == 1
    assert snapshot.trade_volume == 5

    assert snapshot.aggressive_buy_volume == 5
    assert snapshot.aggressive_sell_volume == 0

    assert snapshot.trade_imbalance == pytest.approx(
        1.0
    )


def test_trade_features_sell_trade():
    """
    A -> SELL
    """

    features = TradeFeatures()

    snapshot = FeatureSnapshot()

    event = FakeEvent(
        action=FakeAction.TRADE,
        side=FakeSide.ASK,
        price=101,
        size=7,
    )

    features.update(
        event,
        snapshot
    )

    assert snapshot.trade_count == 1
    assert snapshot.trade_volume == 7

    assert snapshot.aggressive_buy_volume == 0
    assert snapshot.aggressive_sell_volume == 7

    assert snapshot.trade_imbalance == pytest.approx(
        -1.0
    )


def test_trade_features_accumulate():
    """
    连续成交应该累计。
    """

    features = TradeFeatures()

    snapshot = FeatureSnapshot()

    features.update(
        FakeEvent(
            action=FakeAction.TRADE,
            side=FakeSide.BID,
            size=10,
        ),
        snapshot
    )

    features.update(
        FakeEvent(
            action=FakeAction.TRADE,
            side=FakeSide.ASK,
            size=5,
        ),
        snapshot
    )

    assert snapshot.trade_count == 2
    assert snapshot.trade_volume == 15

    assert snapshot.aggressive_buy_volume == 10
    assert snapshot.aggressive_sell_volume == 5

    assert snapshot.trade_imbalance == pytest.approx(
        (
            10 - 5
        )
        /
        (
            10 + 5
        )
    )


# ============================================================
# FlowFeatures
# ============================================================


def test_flow_features_add():
    """
    Add:

        add_volume += size
        liquidity_added += size
    """

    features = FlowFeatures()

    snapshot = FeatureSnapshot()

    features.update(
        FakeEvent(
            action=FakeAction.ADD,
            size=10,
        ),
        snapshot
    )

    assert snapshot.add_volume == 10
    assert snapshot.liquidity_added == 10
    assert snapshot.liquidity_removed == 0

    assert snapshot.ofi == pytest.approx(
        1.0
    )


def test_flow_features_cancel():
    """
    Cancel Contract

    新 FlowFeatures 是 L3-aware。

    CANCEL 必须先有对应的 Shadow Order：

        ADD
            order_id=1001
            side=BID
            price=100
            size=10

        CANCEL
            order_id=1001
            side=BID
            price=100
            size=4

    结果：

        cancel_volume += 4
        liquidity_removed += 4

        bid_removed_volume += 4

        shadow:
            10 -> 6

    注意：

        不允许再使用缺失order_id/side/price的
        Fake CANCEL 来伪造流动性删除。
    """

    features = FlowFeatures()

    snapshot = FeatureSnapshot()

    # ======================================================
    # ADD
    # ======================================================

    features.update(
        FakeEvent(
            action=FakeAction.ADD,
            side="B",
            order_id=1001,
            price=100,
            size=10,
        ),
        snapshot
    )

    state = features.get_order_state(
        1001
    )

    assert state is not None
    assert state.size == 10

    # ======================================================
    # CANCEL
    # ======================================================

    features.update(
        FakeEvent(
            action=FakeAction.CANCEL,
            side="B",
            order_id=1001,
            price=100,
            size=4,
        ),
        snapshot
    )

    # ======================================================
    # Raw Counters
    # ======================================================

    assert snapshot.add_volume == 10
    assert snapshot.cancel_volume == 4

    assert snapshot.liquidity_added == 10
    assert snapshot.liquidity_removed == 4

    # ======================================================
    # Directional Flow
    # ======================================================

    assert snapshot.bid_added_volume == 10
    assert snapshot.bid_removed_volume == 4

    assert snapshot.ask_added_volume == 0
    assert snapshot.ask_removed_volume == 0

    assert snapshot.signed_order_flow == 6

    assert snapshot.ofi == pytest.approx(
        6 / 14
    )

    # ======================================================
    # Shadow Order
    # ======================================================

    state = features.get_order_state(
        1001
    )

    assert state is not None
    assert state.size == 6


def test_flow_features_modify():
    """
    当前 Modify只增加modify_volume。
    """

    features = FlowFeatures()

    snapshot = FeatureSnapshot()

    features.update(
        FakeEvent(
            action=FakeAction.MODIFY,
            size=6,
        ),
        snapshot
    )

    assert snapshot.modify_volume == 6


def test_flow_reset_semantics_contract():
    """
    Ground Truth已经确认：

        R = RESET

    RESET不能被当成普通Remove事件累计size。

    当前测试预计会暴露现有FlowFeatures语义问题。
    """

    features = FlowFeatures()

    snapshot = FeatureSnapshot()

    features.update(
        FakeEvent(
            action=FakeAction.RESET,
            size=100,
        ),
        snapshot
    )

    # RESET是状态边界/盘口重置，
    # 不能简单理解为取消100手。
    assert snapshot.cancel_volume == 0

    assert snapshot.liquidity_removed == 0


# ============================================================
# RegimeFeatures
# ============================================================


def test_regime_features_can_initialize():
    """
    RegimeFeatures必须能够初始化。
    """

    regime = RegimeFeatures(
        window_size=20
    )

    assert regime.trend == TrendRegime.UNKNOWN

    assert (
        regime.volatility
        ==
        VolatilityRegime.UNKNOWN
    )

    assert (
        regime.liquidity
        ==
        LiquidityRegime.UNKNOWN
    )


def test_regime_features_reads_current_orderbook_api():
    """
    当前冻结OrderBook访问方式：

        best_bid()
        best_ask()

    RegimeFeatures必须能够读取这种接口。
    """

    regime = RegimeFeatures(
        window_size=20
    )

    book = FakeOrderBook(
        best_bid=100,
        best_ask=102,
    )

    snapshot = FeatureSnapshot()

    regime.update(
        book,
        snapshot
    )

    assert len(
        regime.mid_prices
    ) == 1

    assert regime.mid_prices[
        -1
    ] == 101.0


def test_regime_features_liquidity():
    """
    使用bid_volume()/ask_volume()
    验证Liquidity状态。
    """

    regime = RegimeFeatures(
        window_size=20
    )

    book = FakeOrderBook(
        bid_levels={
            100: 300,
        },
        ask_levels={
            102: 300,
        },
    )

    snapshot = FeatureSnapshot()

    regime.update(
        book,
        snapshot
    )

    assert (
        regime.liquidity
        ==
        LiquidityRegime.NORMAL
    )

    assert regime.liquidity_score == 600


# ============================================================
# FeatureEngine
# ============================================================


def test_feature_engine_can_initialize():
    """
    模块化 FeatureEngine 必须可以初始化。
    """

    book = FakeOrderBook()

    engine = FeatureEngine(
        orderbook=book
    )

    assert engine.orderbook is book

    assert isinstance(
        engine.snapshot,
        FeatureSnapshot
    )

    assert engine.events_processed == 0


def test_feature_engine_add_event_pipeline():
    """
    最重要的运行时集成测试。

    验证：

        Event
          ↓
        FlowFeatures
          ↓
        OrderBookFeatures
          ↓
        TradeFeatures
          ↓
        FeatureSnapshot

    这条测试预计会直接暴露当前
    FeatureEngine接口冲突。
    """

    book = FakeOrderBook()

    engine = FeatureEngine(
        orderbook=book
    )

    event = FakeEvent(
        action=FakeAction.ADD,
        side=FakeSide.BID,
        price=100,
        size=10,
    )

    snapshot = engine.on_event(
        event
    )

    assert isinstance(
        snapshot,
        FeatureSnapshot
    )

    assert engine.events_processed == 1

    assert snapshot.add_volume == 10

    assert snapshot.best_bid == 100
    assert snapshot.best_ask == 102

    assert snapshot.mid_price == 101.0


def test_feature_engine_trade_event_pipeline():
    """
    验证Trade事件经过完整FeatureEngine。
    """

    book = FakeOrderBook()

    engine = FeatureEngine(
        orderbook=book
    )

    event = FakeEvent(
        action=FakeAction.TRADE,
        side=FakeSide.BID,
        price=102,
        size=5,
    )

    snapshot = engine.on_event(
        event
    )

    assert isinstance(
        snapshot,
        FeatureSnapshot
    )

    assert snapshot.trade_count == 1
    assert snapshot.trade_volume == 5

    assert snapshot.aggressive_buy_volume == 5


def test_feature_engine_snapshot_identity():
    """
    Engine应该持续维护同一个当前snapshot，
    而不是每个event无条件丢失累计状态。
    """

    book = FakeOrderBook()

    engine = FeatureEngine(
        orderbook=book
    )

    first = engine.on_event(
        FakeEvent(
            action=FakeAction.ADD,
            size=10,
        )
    )

    second = engine.on_event(
        FakeEvent(
            action=FakeAction.CANCEL,
            size=5,
        )
    )

    assert first is second

    assert second.add_volume == 10
    assert second.cancel_volume == 5


def test_feature_engine_reset():
    """
    reset()必须清空当前Feature状态和计数。
    """

    book = FakeOrderBook()

    engine = FeatureEngine(
        orderbook=book
    )

    engine.on_event(
        FakeEvent(
            action=FakeAction.ADD,
            size=10,
        )
    )

    engine.reset()

    assert engine.events_processed == 0

    assert isinstance(
        engine.snapshot,
        FeatureSnapshot
    )

    assert engine.snapshot.add_volume == 0
    assert engine.snapshot.trade_volume == 0