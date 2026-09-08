"""
tests/test_real_orderbook_feature_integration.py

============================================================
Real OrderBook -> FeatureEngine Integration Tests
============================================================

目标：

    使用真实冻结 OrderBook：

        orderbook.order.Order
                ↓
        orderbook.level.PriceLevel
                ↓
        orderbook.book.OrderBook
                ↓
        features.FeatureEngine
                ↓
        FeatureSnapshot

============================================================

重要：

    本测试直接调用真实冻结 OrderBook。

    允许：

        - 创建 OrderBook
        - 创建 Order
        - add_order()
        - cancel_order()
        - clear()
        - best_bid()
        - best_ask()
        - bid_volume()
        - ask_volume()
        - 读取 bids / asks

    禁止：

        - 修改 orderbook/*
        - 修改冻结接口
        - 为 FeatureEngine 改动 OrderBook

============================================================

本测试验证：

    1. 真实 OrderBook 可以被 FeatureEngine 读取
    2. Best Bid / Ask 正确传入 FeatureSnapshot
    3. Spread / Mid Price 正确
    4. 全盘口 Bid / Ask Volume 正确
    5. Depth 5 / Depth 10 正确
    6. OBI 正确
    7. Micro Price 正确
    8. Cancel 后 FeatureSnapshot 正确变化
    9. Clear / RESET 后 FeatureEngine 不崩溃
    10. 多次 Feature 更新保持真实盘口同步

============================================================

本测试暂时不负责：

    - DBNFeed
    - OrderBookBuilder
    - 真实 Databento Replay
    - Strategy
    - Risk
    - Execution
    - Portfolio

============================================================
"""

from enum import Enum

import pytest

from core.event import OrderSide

from orderbook.order import Order
from orderbook.book import OrderBook

from features.feature_engine import FeatureEngine
from features.snapshot import FeatureSnapshot


# ============================================================
# Minimal Feature Event
# ============================================================


class TestAction(Enum):
    """
    FeatureEngine需要读取：

        event.action.value

    这里只为驱动 FeatureEngine。

    OrderBook 本身使用的是真实 OrderBook。
    """

    ADD = "A"
    MODIFY = "M"
    CANCEL = "C"
    RESET = "R"
    TRADE = "T"
    FILL = "F"
    NONE = "N"


class TestEvent:
    """
    FeatureEngine最小事件对象。

    这里只负责给：

        FlowFeatures
        TradeFeatures
        FeatureEngine metadata

    提供必要字段。

    不负责重建 OrderBook。
    """

    def __init__(
        self,
        *,
        action=TestAction.NONE,
        side=OrderSide.BID,
        price=0,
        size=0,
        timestamp=0,
        sequence=0,
        symbol="ESU6",
    ):

        self.action = action
        self.side = side
        self.price = price
        self.size = size
        self.timestamp = timestamp
        self.sequence = sequence
        self.symbol = symbol


# ============================================================
# Helpers
# ============================================================


def make_order(
    *,
    order_id,
    side,
    price,
    size,
    sequence,
    ts_event=None,
):
    """
    创建真实 orderbook.order.Order。
    """

    if ts_event is None:
        ts_event = sequence

    return Order(
        order_id=order_id,
        side=side,
        price=price,
        size=size,
        sequence=sequence,
        ts_event=ts_event,
    )


def add_order(
    book,
    *,
    order_id,
    side,
    price,
    size,
    sequence,
):
    """
    向真实冻结 OrderBook 添加真实 Order。
    """

    order = make_order(
        order_id=order_id,
        side=side,
        price=price,
        size=size,
        sequence=sequence,
    )

    book.add_order(
        order
    )

    return order


def feature_event(
    *,
    sequence=1,
    action=TestAction.NONE,
    side=OrderSide.BID,
    price=0,
    size=0,
):
    """
    创建用于触发 FeatureEngine 的最小事件。
    """

    return TestEvent(
        action=action,
        side=side,
        price=price,
        size=size,
        timestamp=sequence,
        sequence=sequence,
        symbol="ESU6",
    )


# ============================================================
# Real OrderBook Basic Contract
# ============================================================


def test_real_orderbook_can_initialize():
    """
    确认测试使用的是真实 OrderBook。
    """

    book = OrderBook()

    assert isinstance(
        book,
        OrderBook
    )

    assert book.best_bid() is None
    assert book.best_ask() is None

    assert book.bid_volume() == 0
    assert book.ask_volume() == 0

    assert len(
        book.orders
    ) == 0


# ============================================================
# Real Order -> Real PriceLevel
# ============================================================


def test_real_orderbook_add_orders():
    """
    直接向真实OrderBook加入：

        Bid 100 @ 10
        Ask 102 @ 20

    验证真实PriceLevel已经建立。
    """

    book = OrderBook()

    add_order(
        book,
        order_id=1,
        side=OrderSide.BID,
        price=100,
        size=10,
        sequence=1,
    )

    add_order(
        book,
        order_id=2,
        side=OrderSide.ASK,
        price=102,
        size=20,
        sequence=2,
    )

    assert book.best_bid() == 100
    assert book.best_ask() == 102

    assert book.bid_volume() == 10
    assert book.ask_volume() == 20

    assert 100 in book.bids
    assert 102 in book.asks

    assert book.bids[
        100
    ].volume == 10

    assert book.asks[
        102
    ].volume == 20

    assert len(
        book.orders
    ) == 2


# ============================================================
# Real Book -> FeatureEngine
# ============================================================


def test_real_orderbook_feature_engine_basic():
    """
    核心测试：

        Real Order
            ↓
        Real PriceLevel
            ↓
        Real OrderBook
            ↓
        FeatureEngine
            ↓
        FeatureSnapshot
    """

    book = OrderBook()

    add_order(
        book,
        order_id=1,
        side=OrderSide.BID,
        price=100,
        size=100,
        sequence=1,
    )

    add_order(
        book,
        order_id=2,
        side=OrderSide.ASK,
        price=102,
        size=50,
        sequence=2,
    )

    engine = FeatureEngine(
        orderbook=book
    )

    snapshot = engine.on_event(
        feature_event(
            sequence=3
        )
    )

    assert isinstance(
        snapshot,
        FeatureSnapshot
    )

    assert snapshot.best_bid == 100
    assert snapshot.best_ask == 102

    assert snapshot.spread == 2
    assert snapshot.mid_price == 101.0

    assert snapshot.bid_volume == 100
    assert snapshot.ask_volume == 50


# ============================================================
# OBI
# ============================================================


def test_real_orderbook_feature_obi():
    """
    OBI：

        Bid = 150
        Ask = 50

        OBI =
            (150 - 50)
            /
            (150 + 50)

            = 0.5
    """

    book = OrderBook()

    add_order(
        book,
        order_id=1,
        side=OrderSide.BID,
        price=100,
        size=150,
        sequence=1,
    )

    add_order(
        book,
        order_id=2,
        side=OrderSide.ASK,
        price=102,
        size=50,
        sequence=2,
    )

    engine = FeatureEngine(
        orderbook=book
    )

    snapshot = engine.on_event(
        feature_event(
            sequence=3
        )
    )

    assert snapshot.obi == pytest.approx(
        0.5
    )

    assert snapshot.queue_pressure == pytest.approx(
        0.5
    )


# ============================================================
# Micro Price
# ============================================================


def test_real_orderbook_feature_micro_price():
    """
    当前 OrderBookFeatures Micro Price：

        Ask * BidVolume
        +
        Bid * AskVolume
        ------------------
        BidVolume + AskVolume

    Bid:

        100
        volume = 100

    Ask:

        102
        volume = 50

    expected:

        (102*100 + 100*50) / 150
    """

    book = OrderBook()

    add_order(
        book,
        order_id=1,
        side=OrderSide.BID,
        price=100,
        size=100,
        sequence=1,
    )

    add_order(
        book,
        order_id=2,
        side=OrderSide.ASK,
        price=102,
        size=50,
        sequence=2,
    )

    engine = FeatureEngine(
        orderbook=book
    )

    snapshot = engine.on_event(
        feature_event(
            sequence=3
        )
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
        101.0
    )


# ============================================================
# Multi-Level Depth
# ============================================================


def test_real_orderbook_feature_multilevel_depth():
    """
    使用真实PriceLevel验证Depth。

    Bid:

        100 = 10
         99 = 20
         98 = 30
         97 = 40
         96 = 50
         95 = 60

    Ask:

        102 = 15
        103 = 25
        104 = 35
        105 = 45
        106 = 55
        107 = 65

    Depth5必须只统计前5档。
    Depth10会统计全部6档。
    """

    book = OrderBook()

    bid_data = [
        (100, 10),
        (99, 20),
        (98, 30),
        (97, 40),
        (96, 50),
        (95, 60),
    ]

    ask_data = [
        (102, 15),
        (103, 25),
        (104, 35),
        (105, 45),
        (106, 55),
        (107, 65),
    ]

    sequence = 1

    for price, size in bid_data:

        add_order(
            book,
            order_id=sequence,
            side=OrderSide.BID,
            price=price,
            size=size,
            sequence=sequence,
        )

        sequence += 1

    for price, size in ask_data:

        add_order(
            book,
            order_id=sequence,
            side=OrderSide.ASK,
            price=price,
            size=size,
            sequence=sequence,
        )

        sequence += 1

    engine = FeatureEngine(
        orderbook=book
    )

    snapshot = engine.on_event(
        feature_event(
            sequence=sequence
        )
    )

    assert snapshot.best_bid == 100
    assert snapshot.best_ask == 102

    expected_bid_depth_5 = (
        10
        +
        20
        +
        30
        +
        40
        +
        50
    )

    expected_ask_depth_5 = (
        15
        +
        25
        +
        35
        +
        45
        +
        55
    )

    expected_bid_depth_10 = sum(
        size
        for _, size in bid_data
    )

    expected_ask_depth_10 = sum(
        size
        for _, size in ask_data
    )

    assert snapshot.bid_depth_5 == (
        expected_bid_depth_5
    )

    assert snapshot.ask_depth_5 == (
        expected_ask_depth_5
    )

    assert snapshot.bid_depth_10 == (
        expected_bid_depth_10
    )

    assert snapshot.ask_depth_10 == (
        expected_ask_depth_10
    )

    assert snapshot.bid_volume == (
        expected_bid_depth_10
    )

    assert snapshot.ask_volume == (
        expected_ask_depth_10
    )


# ============================================================
# Same Price Multiple Orders
# ============================================================


def test_real_orderbook_feature_same_level_multiple_orders():
    """
    同价格多个真实L3 Order：

        Bid 100:
            order 1 = 10
            order 2 = 20
            order 3 = 30

    PriceLevel.volume应该为60。

    FeatureEngine必须读取到60。
    """

    book = OrderBook()

    add_order(
        book,
        order_id=1,
        side=OrderSide.BID,
        price=100,
        size=10,
        sequence=1,
    )

    add_order(
        book,
        order_id=2,
        side=OrderSide.BID,
        price=100,
        size=20,
        sequence=2,
    )

    add_order(
        book,
        order_id=3,
        side=OrderSide.BID,
        price=100,
        size=30,
        sequence=3,
    )

    add_order(
        book,
        order_id=4,
        side=OrderSide.ASK,
        price=102,
        size=40,
        sequence=4,
    )

    assert book.bids[
        100
    ].volume == 60

    engine = FeatureEngine(
        orderbook=book
    )

    snapshot = engine.on_event(
        feature_event(
            sequence=5
        )
    )

    assert snapshot.bid_volume == 60
    assert snapshot.ask_volume == 40

    assert snapshot.bid_depth_5 == 60


# ============================================================
# Cancel -> Feature
# ============================================================


def test_real_orderbook_cancel_updates_feature():
    """
    先建立：

        Bid 100:
            order1 = 10
            order2 = 20

        Ask 102:
            order3 = 30

    然后：

        cancel_order(1)

    验证：

        Real OrderBook
            ↓
        FeatureEngine

    能看到真实盘口变化。
    """

    book = OrderBook()

    add_order(
        book,
        order_id=1,
        side=OrderSide.BID,
        price=100,
        size=10,
        sequence=1,
    )

    add_order(
        book,
        order_id=2,
        side=OrderSide.BID,
        price=100,
        size=20,
        sequence=2,
    )

    add_order(
        book,
        order_id=3,
        side=OrderSide.ASK,
        price=102,
        size=30,
        sequence=3,
    )

    engine = FeatureEngine(
        orderbook=book
    )

    before = engine.on_event(
        feature_event(
            sequence=4
        )
    )

    assert before.bid_volume == 30

    # ======================================================
    # 调用冻结OrderBook公开接口
    # ======================================================

    book.cancel_order(
        1
    )

    after = engine.on_event(
        feature_event(
            sequence=5
        )
    )

    assert book.bid_volume() == 20

    assert after.bid_volume == 20

    assert after.best_bid == 100

    assert 1 not in book.orders

    assert 2 in book.orders


# ============================================================
# Best Price Change
# ============================================================


def test_real_orderbook_best_price_change_updates_feature():
    """
    初始：

        Bid:
            100 @ 10
             99 @ 20

        Ask:
            102 @ 30

    删除Best Bid订单后：

        Best Bid:

            100 -> 99

    FeatureSnapshot必须同步。
    """

    book = OrderBook()

    add_order(
        book,
        order_id=1,
        side=OrderSide.BID,
        price=100,
        size=10,
        sequence=1,
    )

    add_order(
        book,
        order_id=2,
        side=OrderSide.BID,
        price=99,
        size=20,
        sequence=2,
    )

    add_order(
        book,
        order_id=3,
        side=OrderSide.ASK,
        price=102,
        size=30,
        sequence=3,
    )

    engine = FeatureEngine(
        orderbook=book
    )

    first = engine.on_event(
        feature_event(
            sequence=4
        )
    )

    assert first.best_bid == 100
    assert first.mid_price == 101.0

    book.cancel_order(
        1
    )

    second = engine.on_event(
        feature_event(
            sequence=5
        )
    )

    assert second.best_bid == 99
    assert second.best_ask == 102

    assert second.spread == 3

    assert second.mid_price == pytest.approx(
        100.5
    )


# ============================================================
# Real Raw ES Price Units
# ============================================================


def test_real_orderbook_feature_raw_es_price_units():
    """
    使用和ES Databento相同类型的整数价格。

    示例：

        Bid:
            7571000000000
            = 7571.00

        Ask:
            7571250000000
            = 7571.25

    Feature层必须保持原始价格单位，
    不能偷偷除以1e9。
    """

    bid = 7_571_000_000_000

    ask = 7_571_250_000_000

    book = OrderBook()

    add_order(
        book,
        order_id=1,
        side=OrderSide.BID,
        price=bid,
        size=100,
        sequence=1,
    )

    add_order(
        book,
        order_id=2,
        side=OrderSide.ASK,
        price=ask,
        size=100,
        sequence=2,
    )

    engine = FeatureEngine(
        orderbook=book
    )

    snapshot = engine.on_event(
        feature_event(
            sequence=3
        )
    )

    assert snapshot.best_bid == bid

    assert snapshot.best_ask == ask

    assert snapshot.spread == (
        250_000_000
    )

    assert snapshot.mid_price == (
        bid
        +
        ask
    ) / 2

    assert snapshot.micro_price == pytest.approx(
        (
            bid
            +
            ask
        ) / 2
    )


# ============================================================
# Empty Real Book
# ============================================================


def test_real_empty_orderbook_feature_engine():
    """
    FeatureEngine必须能够安全读取空的真实OrderBook。
    """

    book = OrderBook()

    engine = FeatureEngine(
        orderbook=book
    )

    snapshot = engine.on_event(
        feature_event(
            sequence=1
        )
    )

    assert isinstance(
        snapshot,
        FeatureSnapshot
    )

    assert snapshot.best_bid is None

    assert snapshot.best_ask is None

    assert snapshot.mid_price is None

    assert snapshot.micro_price is None

    assert snapshot.bid_volume == 0

    assert snapshot.ask_volume == 0

    assert snapshot.obi == 0.0


# ============================================================
# Clear / RESET
# ============================================================


def test_real_orderbook_clear_feature_engine():
    """
    调用真实冻结：

        OrderBook.clear()

    模拟R = RESET后的盘口状态。

    FeatureEngine必须能够读取清空后的Book。
    """

    book = OrderBook()

    add_order(
        book,
        order_id=1,
        side=OrderSide.BID,
        price=100,
        size=10,
        sequence=1,
    )

    add_order(
        book,
        order_id=2,
        side=OrderSide.ASK,
        price=102,
        size=20,
        sequence=2,
    )

    engine = FeatureEngine(
        orderbook=book
    )

    before = engine.on_event(
        feature_event(
            sequence=3
        )
    )

    assert before.best_bid == 100
    assert before.best_ask == 102

    # ======================================================
    # Frozen OrderBook RESET interface
    # ======================================================

    book.clear()

    after = engine.on_event(
        feature_event(
            sequence=4,
            action=TestAction.RESET,
            size=999,
        )
    )

    assert book.best_bid() is None

    assert book.best_ask() is None

    assert book.bid_volume() == 0

    assert book.ask_volume() == 0

    assert len(
        book.orders
    ) == 0

    assert after.best_bid is None

    assert after.best_ask is None

    assert after.mid_price is None

    assert after.bid_volume == 0

    assert after.ask_volume == 0

    # R不能被Feature层误认为999手撤单
    assert after.cancel_volume == 0

    assert after.liquidity_removed == 0


# ============================================================
# Rebuild After Clear
# ============================================================


def test_real_orderbook_rebuild_after_clear():
    """
    RESET后重新建立盘口。

    验证FeatureEngine没有保留旧盘口价格。
    """

    book = OrderBook()

    add_order(
        book,
        order_id=1,
        side=OrderSide.BID,
        price=100,
        size=10,
        sequence=1,
    )

    add_order(
        book,
        order_id=2,
        side=OrderSide.ASK,
        price=102,
        size=10,
        sequence=2,
    )

    engine = FeatureEngine(
        orderbook=book
    )

    first = engine.on_event(
        feature_event(
            sequence=3
        )
    )

    assert first.best_bid == 100
    assert first.best_ask == 102

    # ======================================================
    # Clear
    # ======================================================

    book.clear()

    engine.on_event(
        feature_event(
            sequence=4,
            action=TestAction.RESET,
        )
    )

    # ======================================================
    # Rebuild
    # ======================================================

    add_order(
        book,
        order_id=10,
        side=OrderSide.BID,
        price=200,
        size=50,
        sequence=5,
    )

    add_order(
        book,
        order_id=11,
        side=OrderSide.ASK,
        price=204,
        size=70,
        sequence=6,
    )

    rebuilt = engine.on_event(
        feature_event(
            sequence=7
        )
    )

    assert rebuilt.best_bid == 200

    assert rebuilt.best_ask == 204

    assert rebuilt.spread == 4

    assert rebuilt.mid_price == 202.0

    assert rebuilt.bid_volume == 50

    assert rebuilt.ask_volume == 70


# ============================================================
# Long Real Book Read
# ============================================================


def test_real_orderbook_feature_repeated_runtime():
    """
    连续100次修改真实OrderBook状态并读取Feature。

    这里通过：

        cancel旧订单
        add新订单

    改变盘口。

    不调用不确定的modify_order签名，
    避免测试依赖历史版本差异。
    """

    book = OrderBook()

    # 固定Ask
    add_order(
        book,
        order_id=10_000,
        side=OrderSide.ASK,
        price=200,
        size=100,
        sequence=1,
    )

    # 初始Bid
    current_order_id = 1

    add_order(
        book,
        order_id=current_order_id,
        side=OrderSide.BID,
        price=100,
        size=100,
        sequence=2,
    )

    engine = FeatureEngine(
        orderbook=book
    )

    for index in range(
        1,
        101
    ):

        # --------------------------------------------------
        # 删除旧Best Bid
        # --------------------------------------------------

        book.cancel_order(
            current_order_id
        )

        # --------------------------------------------------
        # 插入新Best Bid
        # --------------------------------------------------

        current_order_id = (
            1000
            +
            index
        )

        bid_price = (
            100
            +
            index
        )

        add_order(
            book,
            order_id=current_order_id,
            side=OrderSide.BID,
            price=bid_price,
            size=100 + index,
            sequence=100 + index,
        )

        snapshot = engine.on_event(
            feature_event(
                sequence=1000 + index
            )
        )

        assert snapshot.best_bid == (
            bid_price
        )

        assert snapshot.best_ask == 200

        assert snapshot.bid_volume == (
            100 + index
        )

    assert engine.events_processed == 100

    assert book.best_bid() == 200

    assert book.bid_volume() == 200