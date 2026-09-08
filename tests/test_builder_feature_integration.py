"""
tests/test_builder_feature_integration.py

============================================================
MarketEvent -> Builder -> OrderBook -> FeatureEngine
Integration Tests
============================================================

目标：

    验证真实系统链路：

        core.event.MarketEvent
                ↓
        orderbook.builder.OrderBookBuilder
                ↓
        orderbook.book.OrderBook
                ↓
        features.feature_engine.FeatureEngine
                ↓
        features.snapshot.FeatureSnapshot

============================================================

本测试使用真实：

    - MarketEvent
    - OrderAction
    - OrderSide
    - OrderBookBuilder
    - OrderBook
    - Order
    - PriceLevel
    - FeatureEngine
    - FeatureSnapshot

============================================================

重要原则：

    冻结层：

        core/event.py
        orderbook/order.py
        orderbook/level.py
        orderbook/book.py
        orderbook/builder.py

    本测试：

        只调用
        不修改

============================================================

事件处理顺序必须是：

    MarketEvent

        ↓

    builder.on_event(event)

        ↓

    OrderBook 已经完成当前事件更新

        ↓

    feature_engine.on_event(event)

        ↓

    FeatureSnapshot读取稳定后的Book

============================================================

验证内容：

    1. ADD Bid
    2. ADD Ask
    3. 多订单 / 多档盘口
    4. MODIFY
    5. CANCEL
    6. RESET
    7. TRADE
    8. FILL
    9. NONE
    10. Sequence
    11. Raw ES价格单位
    12. Builder统计
    13. Feature统计
    14. 连续事件Pipeline
    15. RESET后重新建Book

============================================================
"""

import pytest

from core.event import (
    MarketEvent,
    OrderAction,
    OrderSide,
)

from orderbook.book import OrderBook
from orderbook.builder import OrderBookBuilder

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
    ts_event=None,
    ts_recv=None,
    symbol="ESU6",
    channel_id=0,
    publisher_id=1,
    instrument_id=1,
    flags=0,
):
    """
    创建真实 core.event.MarketEvent。

    所有测试统一通过这里创建事件。

    这样可以确保测试使用的是系统真实事件模型，
    而不是Fake Event。
    """

    if ts_event is None:
        ts_event = sequence

    if ts_recv is None:
        ts_recv = ts_event

    return MarketEvent(
        ts_event=ts_event,
        ts_recv=ts_recv,
        sequence=sequence,
        action=action,
        side=side,
        order_id=order_id,
        price=price,
        size=size,
        symbol=symbol,
        channel_id=channel_id,
        publisher_id=publisher_id,
        instrument_id=instrument_id,
        flags=flags,
    )


# ============================================================
# Pipeline Factory
# ============================================================


def make_pipeline():
    """
    创建真实：

        OrderBook
            ↓
        OrderBookBuilder
            ↓
        FeatureEngine
    """

    book = OrderBook()

    builder = OrderBookBuilder(
        book=book
    )

    feature_engine = FeatureEngine(
        orderbook=book
    )

    return (
        book,
        builder,
        feature_engine,
    )


# ============================================================
# Apply Event
# ============================================================


def apply_event(
    builder,
    feature_engine,
    event
):
    """
    系统正确事件顺序：

        1. Builder先更新Book
        2. FeatureEngine再读取Book

    返回：

        FeatureSnapshot
    """

    builder.on_event(
        event
    )

    snapshot = feature_engine.on_event(
        event
    )

    return snapshot


# ============================================================
# Basic Initialization
# ============================================================


def test_builder_feature_pipeline_can_initialize():
    """
    整条真实Pipeline必须可以初始化。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    assert isinstance(
        book,
        OrderBook
    )

    assert isinstance(
        builder,
        OrderBookBuilder
    )

    assert isinstance(
        feature_engine,
        FeatureEngine
    )

    assert builder.get_book() is book

    assert feature_engine.orderbook is book

    assert book.best_bid() is None

    assert book.best_ask() is None


# ============================================================
# ADD BID
# ============================================================


def test_add_bid_builder_to_feature():
    """
    A Bid：

        MarketEvent
            ↓
        Builder
            ↓
        OrderBook
            ↓
        FeatureEngine
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    event = make_event(
        sequence=1,
        action=OrderAction.ADD,
        side=OrderSide.BID,
        order_id=1001,
        price=100,
        size=10,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        event
    )

    # --------------------------------------------------------
    # Real OrderBook
    # --------------------------------------------------------

    assert 1001 in book.orders

    assert book.best_bid() == 100

    assert book.best_ask() is None

    assert book.bid_volume() == 10

    assert book.ask_volume() == 0

    # --------------------------------------------------------
    # FeatureSnapshot
    # --------------------------------------------------------

    assert isinstance(
        snapshot,
        FeatureSnapshot
    )

    assert snapshot.best_bid == 100

    assert snapshot.best_ask is None

    assert snapshot.bid_volume == 10

    assert snapshot.ask_volume == 0

    assert snapshot.add_volume == 10

    assert snapshot.liquidity_added == 10


# ============================================================
# ADD BID + ASK
# ============================================================


def test_add_bid_ask_builder_to_feature():
    """
    建立完整Top Of Book。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    bid_event = make_event(
        sequence=1,
        action=OrderAction.ADD,
        side=OrderSide.BID,
        order_id=1001,
        price=100,
        size=100,
    )

    ask_event = make_event(
        sequence=2,
        action=OrderAction.ADD,
        side=OrderSide.ASK,
        order_id=2001,
        price=102,
        size=50,
    )

    apply_event(
        builder,
        feature_engine,
        bid_event
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        ask_event
    )

    assert book.best_bid() == 100

    assert book.best_ask() == 102

    assert snapshot.best_bid == 100

    assert snapshot.best_ask == 102

    assert snapshot.spread == 2

    assert snapshot.mid_price == pytest.approx(
        101.0
    )

    assert snapshot.bid_volume == 100

    assert snapshot.ask_volume == 50

    expected_obi = (
        100 - 50
    ) / (
        100 + 50
    )

    assert snapshot.obi == pytest.approx(
        expected_obi
    )

    assert snapshot.queue_pressure == pytest.approx(
        expected_obi
    )


# ============================================================
# Micro Price
# ============================================================


def test_builder_feature_micro_price():
    """
    验证Builder建立的真实Book
    能被FeatureEngine正确计算Micro Price。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=100,
        )
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=2,
            price=102,
            size=50,
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
# Multiple Price Levels
# ============================================================


def test_multiple_levels_builder_to_feature():
    """
    Builder建立真实多档盘口：

    Bid:
        100 10
         99 20
         98 30

    Ask:
        102 15
        103 25
        104 35
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    events = [
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),

        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=2,
            price=99,
            size=20,
        ),

        make_event(
            sequence=3,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=3,
            price=98,
            size=30,
        ),

        make_event(
            sequence=4,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=4,
            price=102,
            size=15,
        ),

        make_event(
            sequence=5,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=5,
            price=103,
            size=25,
        ),

        make_event(
            sequence=6,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=6,
            price=104,
            size=35,
        ),
    ]

    snapshot = None

    for event in events:

        snapshot = apply_event(
            builder,
            feature_engine,
            event
        )

    assert snapshot is not None

    assert book.best_bid() == 100

    assert book.best_ask() == 102

    assert book.bid_volume() == 60

    assert book.ask_volume() == 75

    assert snapshot.bid_volume == 60

    assert snapshot.ask_volume == 75

    assert snapshot.bid_depth_5 == 60

    assert snapshot.ask_depth_5 == 75

    assert snapshot.bid_depth_10 == 60

    assert snapshot.ask_depth_10 == 75


# ============================================================
# Same Price FIFO Aggregation
# ============================================================


def test_same_price_orders_builder_to_feature():
    """
    同一个价格加入多个真实L3订单。

    Bid 100：

        order 1 = 10
        order 2 = 20
        order 3 = 30

    Feature必须看到总量60。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    events = [
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),

        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=2,
            price=100,
            size=20,
        ),

        make_event(
            sequence=3,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=3,
            price=100,
            size=30,
        ),

        make_event(
            sequence=4,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=4,
            price=102,
            size=40,
        ),
    ]

    snapshot = None

    for event in events:

        snapshot = apply_event(
            builder,
            feature_engine,
            event
        )

    assert snapshot is not None

    assert len(
        book.orders
    ) == 4

    assert book.bids[
        100
    ].volume == 60

    assert snapshot.bid_volume == 60

    assert snapshot.ask_volume == 40


# ============================================================
# MODIFY
# ============================================================


def test_modify_builder_to_feature():
    """
    验证真实：

        MarketEvent(M)
            ↓
        Builder._modify()
            ↓
        OrderBook.modify_order()
            ↓
        PriceLevel
            ↓
        FeatureEngine

    初始：

        Bid 100 @ 10

    Modify：

        Bid 100 @ 25

    预期：

        Bid Volume = 25

    注意：

        这项测试非常重要。

        如果这里出现TypeError，
        说明当前本地冻结文件之间
        存在真实接口版本不一致。

        此时不要直接修改冻结代码。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    add_event = make_event(
        sequence=1,
        action=OrderAction.ADD,
        side=OrderSide.BID,
        order_id=1001,
        price=100,
        size=10,
    )

    apply_event(
        builder,
        feature_engine,
        add_event
    )

    modify_event = make_event(
        sequence=2,
        action=OrderAction.MODIFY,
        side=OrderSide.BID,
        order_id=1001,
        price=100,
        size=25,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        modify_event
    )

    assert 1001 in book.orders

    assert book.orders[
        1001
    ].size == 25

    assert book.bid_volume() == 25

    assert snapshot.bid_volume == 25

    assert snapshot.modify_volume == 25


# ============================================================
# CANCEL
# ============================================================


def test_cancel_builder_to_feature():
    """
    C：

        Builder删除真实订单
            ↓
        Feature读取新的Book状态
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        )
    )

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=2,
            price=100,
            size=20,
        )
    )

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=3,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=3,
            price=102,
            size=30,
        )
    )

    cancel_event = make_event(
        sequence=4,
        action=OrderAction.CANCEL,
        side=OrderSide.BID,
        order_id=1,
        price=100,
        size=10,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        cancel_event
    )

    assert 1 not in book.orders

    assert 2 in book.orders

    assert book.bid_volume() == 20

    assert snapshot.bid_volume == 20

    assert snapshot.cancel_volume == 10

    assert snapshot.liquidity_removed == 10


# ============================================================
# Best Bid Change After Cancel
# ============================================================


def test_cancel_best_price_updates_feature():
    """
    删除Best Bid后：

        100 -> 99

    Feature必须同步。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    events = [
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),

        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=2,
            price=99,
            size=20,
        ),

        make_event(
            sequence=3,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=3,
            price=102,
            size=30,
        ),
    ]

    for event in events:

        apply_event(
            builder,
            feature_engine,
            event
        )

    assert book.best_bid() == 100

    cancel = make_event(
        sequence=4,
        action=OrderAction.CANCEL,
        side=OrderSide.BID,
        order_id=1,
        price=100,
        size=10,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        cancel
    )

    assert book.best_bid() == 99

    assert snapshot.best_bid == 99

    assert snapshot.best_ask == 102

    assert snapshot.spread == 3

    assert snapshot.mid_price == pytest.approx(
        100.5
    )


# ============================================================
# TRADE
# ============================================================


def test_trade_does_not_change_book_but_updates_feature():
    """
    T：

        Builder：
            不修改挂单Book
            更新Trade统计

        FeatureEngine：
            更新成交统计

    当前冻结Builder的Trade路径
    会增加book.trade_count和trade_volume。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=100,
        )
    )

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=2,
            price=102,
            size=100,
        )
    )

    before_orders = len(
        book.orders
    )

    before_bid = book.bid_volume()

    before_ask = book.ask_volume()

    trade_event = make_event(
        sequence=3,
        action=OrderAction.TRADE,
        side=OrderSide.BID,
        order_id=None,
        price=102,
        size=5,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        trade_event
    )

    # --------------------------------------------------------
    # Book挂单不变
    # --------------------------------------------------------

    assert len(
        book.orders
    ) == before_orders

    assert book.bid_volume() == before_bid

    assert book.ask_volume() == before_ask

    # --------------------------------------------------------
    # Builder成交统计
    # --------------------------------------------------------

    assert book.trade_count == 1

    assert book.trade_volume == 5

    # --------------------------------------------------------
    # Feature成交统计
    # --------------------------------------------------------

    assert snapshot.trade_count == 1

    assert snapshot.trade_volume == 5

    assert snapshot.last_trade_price == 102

    assert snapshot.last_trade_size == 5

    assert snapshot.aggressive_buy_volume == 5

    assert snapshot.aggressive_sell_volume == 0

    assert snapshot.trade_imbalance == pytest.approx(
        1.0
    )


# ============================================================
# SELL TRADE
# ============================================================


def test_sell_trade_builder_to_feature():
    """
    Ask side Trade：

        Feature当前映射为主动SELL。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    trade_event = make_event(
        sequence=1,
        action=OrderAction.TRADE,
        side=OrderSide.ASK,
        order_id=None,
        price=100,
        size=7,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        trade_event
    )

    assert book.trade_count == 1

    assert book.trade_volume == 7

    assert snapshot.trade_count == 1

    assert snapshot.trade_volume == 7

    assert snapshot.aggressive_buy_volume == 0

    assert snapshot.aggressive_sell_volume == 7

    assert snapshot.trade_imbalance == pytest.approx(
        -1.0
    )


# ============================================================
# FILL
# ============================================================


def test_fill_does_not_change_book():
    """
    F：

        当前Builder定义：
            不修改Book

        Feature TradeFeatures：
            当前只把T当成交事件

    因此F不应该增加Feature trade_count。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        )
    )

    fill_event = make_event(
        sequence=2,
        action=OrderAction.FILL,
        side=OrderSide.BID,
        order_id=1,
        price=100,
        size=5,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        fill_event
    )

    assert 1 in book.orders

    assert book.bid_volume() == 10

    assert snapshot.bid_volume == 10

    assert snapshot.trade_count == 0

    assert snapshot.trade_volume == 0


# ============================================================
# NONE
# ============================================================


def test_none_event_does_not_change_book():
    """
    N：

        Builder忽略。
        Feature可以安全读取当前状态。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        )
    )

    none_event = make_event(
        sequence=2,
        action=OrderAction.NONE,
        side=None,
        order_id=None,
        price=None,
        size=None,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        none_event
    )

    assert book.best_bid() == 100

    assert book.bid_volume() == 10

    assert snapshot.best_bid == 100

    assert snapshot.bid_volume == 10


# ============================================================
# RESET
# ============================================================


def test_reset_builder_to_feature():
    """
    R：

        MarketEvent
            ↓
        Builder
            ↓
        book.clear()
            ↓
        FeatureEngine
            ↓
        空盘口FeatureSnapshot

    同时验证：

        R不能被FlowFeatures误计为cancel volume。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        )
    )

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=2,
            price=102,
            size=20,
        )
    )

    reset_event = make_event(
        sequence=3,
        action=OrderAction.RESET,
        side=None,
        order_id=None,
        price=None,
        size=999,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        reset_event
    )

    # --------------------------------------------------------
    # Real Book cleared
    # --------------------------------------------------------

    assert len(
        book.orders
    ) == 0

    assert book.best_bid() is None

    assert book.best_ask() is None

    assert book.bid_volume() == 0

    assert book.ask_volume() == 0

    # --------------------------------------------------------
    # Feature sees empty Book
    # --------------------------------------------------------

    assert snapshot.best_bid is None

    assert snapshot.best_ask is None

    assert snapshot.mid_price is None

    assert snapshot.micro_price is None

    assert snapshot.bid_volume == 0

    assert snapshot.ask_volume == 0

    # --------------------------------------------------------
    # RESET不是cancel
    #
    # 前面没有C事件，所以必须仍然为0。
    # --------------------------------------------------------

    assert snapshot.cancel_volume == 0

    assert snapshot.liquidity_removed == 0


# ============================================================
# RESET Then Rebuild
# ============================================================


def test_reset_then_rebuild_pipeline():
    """
    RESET后重新ADD新的盘口。

    必须不能残留旧Best Bid / Ask。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        )
    )

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=2,
            price=102,
            size=10,
        )
    )

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=3,
            action=OrderAction.RESET,
            side=None,
            order_id=None,
            price=None,
            size=0,
        )
    )

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=4,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=10,
            price=200,
            size=50,
        )
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=5,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=11,
            price=204,
            size=70,
        )
    )

    assert book.best_bid() == 200

    assert book.best_ask() == 204

    assert snapshot.best_bid == 200

    assert snapshot.best_ask == 204

    assert snapshot.spread == 4

    assert snapshot.mid_price == pytest.approx(
        202.0
    )

    assert snapshot.bid_volume == 50

    assert snapshot.ask_volume == 70


# ============================================================
# Raw ES Integer Price
# ============================================================


def test_builder_feature_raw_es_price_units():
    """
    使用真实ES Databento整数价格单位。

    7571.00：

        7_571_000_000_000

    7571.25：

        7_571_250_000_000

    Feature层必须保持原始整数单位。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    bid = 7_571_000_000_000

    ask = 7_571_250_000_000

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=bid,
            size=100,
        )
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=2,
            price=ask,
            size=100,
        )
    )

    assert snapshot.best_bid == bid

    assert snapshot.best_ask == ask

    assert snapshot.spread == (
        250_000_000
    )

    assert snapshot.mid_price == pytest.approx(
        (
            bid
            +
            ask
        ) / 2
    )

    assert snapshot.micro_price == pytest.approx(
        (
            bid
            +
            ask
        ) / 2
    )


# ============================================================
# Feature Event Metadata
# ============================================================


def test_market_event_metadata_reaches_feature_snapshot():
    """
    MarketEvent中的：

        ts_event
        sequence
        symbol

    应该进入FeatureSnapshot。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    event = make_event(
        sequence=12345,
        action=OrderAction.ADD,
        side=OrderSide.BID,
        order_id=1,
        price=100,
        size=10,
        ts_event=987654321,
        ts_recv=987654999,
        symbol="ESU6",
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        event
    )

    assert snapshot.timestamp == (
        987654321
    )

    assert snapshot.sequence == (
        12345
    )

    assert snapshot.symbol == (
        "ESU6"
    )


# ============================================================
# Builder Statistics
# ============================================================


def test_builder_statistics():
    """
    Builder必须统计真实Action数量。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    events = [
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),

        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=2,
            price=102,
            size=10,
        ),

        make_event(
            sequence=3,
            action=OrderAction.TRADE,
            side=OrderSide.BID,
            order_id=None,
            price=102,
            size=2,
        ),

        make_event(
            sequence=4,
            action=OrderAction.NONE,
            side=None,
            order_id=None,
            price=None,
            size=None,
        ),
    ]

    for event in events:

        apply_event(
            builder,
            feature_engine,
            event
        )

    assert builder.event_count == 4

    assert builder.action_count[
        "A"
    ] == 2

    assert builder.action_count[
        "T"
    ] == 1

    assert builder.action_count[
        "N"
    ] == 1

    assert builder.last_sequence == 4


# ============================================================
# Feature Statistics
# ============================================================


def test_feature_engine_statistics():
    """
    FeatureEngine必须处理同样数量事件。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    for sequence in range(
        1,
        11
    ):

        event = make_event(
            sequence=sequence,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=sequence,
            price=100 - sequence,
            size=1,
        )

        apply_event(
            builder,
            feature_engine,
            event
        )

    assert builder.event_count == 10

    assert feature_engine.events_processed == 10


# ============================================================
# Sequence Contract
# ============================================================


def test_builder_sequence_tracking_contract():
    """
    验证当前冻结 Builder 的 sequence 跟踪行为。

    注意：

        这里不假设乱序一定抛异常。

    原因：

        当前本地冻结版本是最终事实来源。

    本测试只验证：

        1. Builder能够接收sequence
        2. last_sequence会被维护
        3. 不修改OrderBook
        4. Feature链路不受影响

    是否拒绝乱序，
    应由单独的Ground Truth测试确定，
    不能在这里凭历史版本假设。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    first = make_event(
        sequence=10,
        action=OrderAction.NONE,
        side=None,
        order_id=None,
        price=None,
        size=None,
    )

    second = make_event(
        sequence=11,
        action=OrderAction.NONE,
        side=None,
        order_id=None,
        price=None,
        size=None,
    )

    third = make_event(
        sequence=9,
        action=OrderAction.NONE,
        side=None,
        order_id=None,
        price=None,
        size=None,
    )

    # ======================================================
    # 10
    # ======================================================

    snapshot_1 = apply_event(
        builder,
        feature_engine,
        first
    )

    assert builder.last_sequence == 10

    # ======================================================
    # 11
    # ======================================================

    snapshot_2 = apply_event(
        builder,
        feature_engine,
        second
    )

    assert builder.last_sequence == 11

    # ======================================================
    # 9
    #
    # 当前冻结版本实际允许该事件继续进入。
    # 不在此测试中人为要求RuntimeError。
    # ======================================================

    snapshot_3 = apply_event(
        builder,
        feature_engine,
        third
    )

    assert isinstance(
        snapshot_1,
        FeatureSnapshot
    )

    assert isinstance(
        snapshot_2,
        FeatureSnapshot
    )

    assert isinstance(
        snapshot_3,
        FeatureSnapshot
    )

    # NONE事件不能修改Book
    assert len(
        book.orders
    ) == 0

    assert book.best_bid() is None

    assert book.best_ask() is None

    # 三个事件都实际进入Builder和FeatureEngine
    assert builder.event_count == 3

    assert feature_engine.events_processed == 3


# ============================================================
# MarketEvent Helpers
# ============================================================


def test_market_event_book_update_contract():
    """
    验证真实MarketEvent辅助接口。
    """

    add = make_event(
        sequence=1,
        action=OrderAction.ADD,
        side=OrderSide.BID,
        order_id=1,
        price=100,
        size=1,
    )

    trade = make_event(
        sequence=2,
        action=OrderAction.TRADE,
        side=OrderSide.BID,
        order_id=None,
        price=100,
        size=1,
    )

    assert add.is_book_update() is True

    assert trade.is_book_update() is False

    assert add.is_trade() is False

    assert trade.is_trade() is True


# ============================================================
# Long Pipeline
# ============================================================


def test_builder_feature_long_runtime():
    """
    连续200个真实MarketEvent：

        ADD
        CANCEL
        TRADE
        NONE

    经过：

        Builder
            ↓
        Real Book
            ↓
        FeatureEngine

    验证运行过程中不发生接口错误。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    sequence = 0

    next_order_id = 1

    active_bid_ids = []

    # ======================================================
    # 固定Ask
    # ======================================================

    sequence += 1

    ask_event = make_event(
        sequence=sequence,
        action=OrderAction.ADD,
        side=OrderSide.ASK,
        order_id=100_000,
        price=200,
        size=100,
    )

    apply_event(
        builder,
        feature_engine,
        ask_event
    )

    # ======================================================
    # 200 Events
    # ======================================================

    for index in range(
        1,
        201
    ):

        sequence += 1

        # --------------------------------------------------
        # 每10个事件做Trade
        # --------------------------------------------------

        if index % 10 == 0:

            event = make_event(
                sequence=sequence,
                action=OrderAction.TRADE,
                side=(
                    OrderSide.BID
                    if index % 20 == 0
                    else OrderSide.ASK
                ),
                order_id=None,
                price=150,
                size=5,
            )

        # --------------------------------------------------
        # 每7个事件Cancel一个旧Bid
        # --------------------------------------------------

        elif (
            index % 7 == 0
            and
            active_bid_ids
        ):

            order_id = (
                active_bid_ids.pop(0)
            )

            order = book.orders.get(
                order_id
            )

            cancel_size = (
                order.size
                if order is not None
                else 0
            )

            cancel_price = (
                order.price
                if order is not None
                else 0
            )

            event = make_event(
                sequence=sequence,
                action=OrderAction.CANCEL,
                side=OrderSide.BID,
                order_id=order_id,
                price=cancel_price,
                size=cancel_size,
            )

        # --------------------------------------------------
        # 其他情况Add Bid
        # --------------------------------------------------

        else:

            order_id = next_order_id

            next_order_id += 1

            active_bid_ids.append(
                order_id
            )

            price = (
                100
                +
                index % 50
            )

            size = (
                1
                +
                index % 10
            )

            event = make_event(
                sequence=sequence,
                action=OrderAction.ADD,
                side=OrderSide.BID,
                order_id=order_id,
                price=price,
                size=size,
            )

        snapshot = apply_event(
            builder,
            feature_engine,
            event
        )

        assert isinstance(
            snapshot,
            FeatureSnapshot
        )

        # --------------------------------------------------
        # Feature必须始终与真实Book一致
        # --------------------------------------------------

        assert snapshot.best_bid == (
            book.best_bid()
        )

        assert snapshot.best_ask == (
            book.best_ask()
        )

        assert snapshot.bid_volume == (
            book.bid_volume()
        )

        assert snapshot.ask_volume == (
            book.ask_volume()
        )

    assert builder.event_count == 201

    assert feature_engine.events_processed == 201

    assert builder.last_sequence == sequence


# ============================================================
# Exact Book / Feature Equality
# ============================================================


def test_feature_snapshot_matches_real_book_exactly():
    """
    最终关键契约：

        FeatureSnapshot盘口字段

    必须和：

        Real OrderBook

    完全一致。
    """

    book, builder, feature_engine = (
        make_pipeline()
    )

    events = [
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=100,
        ),

        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=2,
            price=99,
            size=50,
        ),

        make_event(
            sequence=3,
            action=OrderAction.ASK
            if hasattr(
                OrderAction,
                "ASK"
            )
            else OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=3,
            price=102,
            size=80,
        ),

        make_event(
            sequence=4,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=4,
            price=103,
            size=40,
        ),
    ]

    snapshot = None

    for event in events:

        snapshot = apply_event(
            builder,
            feature_engine,
            event
        )

    assert snapshot is not None

    assert snapshot.best_bid == (
        book.best_bid()
    )

    assert snapshot.best_ask == (
        book.best_ask()
    )

    assert snapshot.spread == (
        book.spread()
    )

    assert snapshot.mid_price == (
        book.mid_price()
    )

    assert snapshot.bid_volume == (
        book.bid_volume()
    )

    assert snapshot.ask_volume == (
        book.ask_volume()
    )