"""
tests/test_feature_mbo_semantics.py

============================================================
Databento MBO Feature Semantics Contract
============================================================

目标：

    从“接口正确”进入“市场语义正确”。

    本测试直接验证：

        Databento MBO Ground Truth
                ↓
        MarketEvent
                ↓
        OrderBookBuilder
                ↓
        OrderBook
                ↓
        FeatureEngine
                ↓
        FeatureSnapshot

============================================================

Ground Truth
============================================================

1. Trade Side

    T + side=B

        表示 Buy Aggressor

    T + side=A

        表示 Sell Aggressor


2. Cancel

    C.size

        表示本次取消的数量。

    因此：

        old_size = 10
        C.size   = 4

    正确结果：

        remaining_size = 6


3. Modify

    M.size

        表示修改后的新 size。

    不是：

        liquidity delta


    例如：

        old = 10
        new = 15

    event.size:

        15

    真实 liquidity delta:

        +5


    old = 10
    new = 6

    event.size:

        6

    真实 liquidity delta:

        -4


4. Modify Price

    Modify可能改变：

        price
        size


    例如：

        Bid 100 @ 10

            ↓ M

        Bid 101 @ 10

    从订单流角度：

        old price 100:

            remove 10

        new price 101:

            add 10


5. F_LAST

    F_LAST = 128

    同一个publisher event可能被规范化为多条MBO records。

    Book可以逐条更新。

    但是稳定Book状态：

        只应该在 F_LAST 后检查。

============================================================

IMPORTANT
============================================================

这不是“让现有实现全部通过”的测试。

这是 Ground Truth Test。

如果出现失败：

    不允许：

        为了测试变绿
        修改Ground Truth断言。

    应该：

        判断当前实现是否真的违反MBO语义。

============================================================

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
# Constants
# ============================================================


F_LAST = 128


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
    flags=F_LAST,
    ts_event=None,
    ts_recv=None,
    symbol="ESU6",
    channel_id=0,
    publisher_id=1,
    instrument_id=1,
):
    """
    创建真实 MarketEvent。
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
# Pipeline
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
# Apply
# ============================================================


def apply_event(
    builder,
    feature_engine,
    event,
):
    """
    正常系统顺序：

        Event
            ↓
        Builder
            ↓
        Book
            ↓
        Feature
    """

    builder.on_event(
        event
    )

    snapshot = feature_engine.on_event(
        event
    )

    return snapshot


# ============================================================
# F_LAST Helper
# ============================================================


def is_f_last(
    event,
):
    """
    Databento：

        F_LAST = 1 << 7
               = 128
    """

    return bool(
        (
            event.flags
            or 0
        )
        &
        F_LAST
    )


# ============================================================
# 1. F_LAST Constant
# ============================================================


def test_f_last_constant():
    """
    F_LAST固定为128。
    """

    assert F_LAST == 128

    assert F_LAST == (
        1 << 7
    )


# ============================================================
# 2. F_LAST Detection
# ============================================================


def test_f_last_detection():
    """
    flags中包含128：

        True

    不包含：

        False
    """

    not_last = make_event(
        sequence=1,
        action=OrderAction.NONE,
        flags=0,
    )

    last = make_event(
        sequence=2,
        action=OrderAction.NONE,
        flags=128,
    )

    assert is_f_last(
        not_last
    ) is False

    assert is_f_last(
        last
    ) is True


# ============================================================
# 3. Multi-record Publisher Event
# ============================================================


def test_book_stable_boundary_after_f_last():
    """
    模拟一个publisher event包含两条record。

    Record 1：

        ADD Bid
        flags = 0

    Record 2：

        ADD Ask
        flags = F_LAST

    Builder必须逐条更新。

    但真正稳定状态是在第二条以后。
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

    # ======================================================
    # Record 1
    # ======================================================

    first = make_event(
        sequence=1,
        action=OrderAction.ADD,
        side=OrderSide.BID,
        order_id=1,
        price=100,
        size=10,
        flags=0,
    )

    snapshot_1 = apply_event(
        builder,
        feature_engine,
        first,
    )

    assert is_f_last(
        first
    ) is False

    # 中间状态
    assert book.best_bid() == 100

    assert book.best_ask() is None

    assert snapshot_1.best_bid == 100

    assert snapshot_1.best_ask is None

    # ======================================================
    # Record 2
    # ======================================================

    second = make_event(
        sequence=2,
        action=OrderAction.ADD,
        side=OrderSide.ASK,
        order_id=2,
        price=102,
        size=20,
        flags=F_LAST,
    )

    snapshot_2 = apply_event(
        builder,
        feature_engine,
        second,
    )

    assert is_f_last(
        second
    ) is True

    # ======================================================
    # F_LAST之后才是稳定状态
    # ======================================================

    assert book.best_bid() == 100

    assert book.best_ask() == 102

    assert snapshot_2.best_bid == 100

    assert snapshot_2.best_ask == 102

    assert snapshot_2.mid_price == pytest.approx(
        101.0
    )


# ============================================================
# 4. Trade Bid Side = Buy Aggressor
# ============================================================


def test_trade_bid_side_is_buy_aggressor():
    """
    Databento MBO：

        action = T
        side   = B

    表示：

        Buy Aggressor
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

    event = make_event(
        sequence=1,
        action=OrderAction.TRADE,
        side=OrderSide.BID,
        order_id=None,
        price=100,
        size=5,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        event,
    )

    assert snapshot.trade_count == 1

    assert snapshot.trade_volume == 5

    assert snapshot.aggressive_buy_volume == 5

    assert snapshot.aggressive_sell_volume == 0

    assert snapshot.trade_imbalance == pytest.approx(
        1.0
    )


# ============================================================
# 5. Trade Ask Side = Sell Aggressor
# ============================================================


def test_trade_ask_side_is_sell_aggressor():
    """
    Databento MBO：

        action = T
        side   = A

    表示：

        Sell Aggressor
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

    event = make_event(
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
        event,
    )

    assert snapshot.trade_count == 1

    assert snapshot.trade_volume == 7

    assert snapshot.aggressive_buy_volume == 0

    assert snapshot.aggressive_sell_volume == 7

    assert snapshot.trade_imbalance == pytest.approx(
        -1.0
    )


# ============================================================
# 6. Trade None Side
# ============================================================


def test_trade_none_side_has_no_aggressor_direction():
    """
    Databento允许Trade side=None。

    此时：

        成交量仍然存在

    但是：

        不能凭空猜BUY/SELL。
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

    event = make_event(
        sequence=1,
        action=OrderAction.TRADE,
        side=None,
        order_id=None,
        price=100,
        size=8,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        event,
    )

    assert snapshot.trade_count == 1

    assert snapshot.trade_volume == 8

    assert snapshot.aggressive_buy_volume == 0

    assert snapshot.aggressive_sell_volume == 0

    assert snapshot.trade_imbalance == pytest.approx(
        0.0
    )


# ============================================================
# 7. Fill Must Not Duplicate Trade
# ============================================================


def test_fill_does_not_duplicate_trade_statistics():
    """
    Databento MBO：

        T = aggressing trade
        F = resting order fill detail

    当前系统设计：

        Trade用于成交统计

        Fill不能再次增加：
            trade_count
            trade_volume
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

    trade = make_event(
        sequence=1,
        action=OrderAction.TRADE,
        side=OrderSide.BID,
        order_id=None,
        price=100,
        size=5,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        trade,
    )

    assert snapshot.trade_count == 1

    assert snapshot.trade_volume == 5

    fill = make_event(
        sequence=2,
        action=OrderAction.FILL,
        side=OrderSide.ASK,
        order_id=123,
        price=100,
        size=5,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        fill,
    )

    assert snapshot.trade_count == 1

    assert snapshot.trade_volume == 5

    assert book.trade_count == 1

    assert book.trade_volume == 5


# ============================================================
# 8. Full Cancel
# ============================================================


def test_full_cancel_ground_truth():
    """
    ADD：

        10 contracts

    C：

        size = 10

    Ground Truth：

        remaining = 0

        order应删除。
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

    add = make_event(
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
        add,
    )

    assert 1001 in book.orders

    assert book.orders[
        1001
    ].size == 10

    cancel = make_event(
        sequence=2,
        action=OrderAction.CANCEL,
        side=OrderSide.BID,
        order_id=1001,
        price=100,
        size=10,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        cancel,
    )

    assert 1001 not in book.orders

    assert book.bid_volume() == 0

    assert snapshot.cancel_volume == 10

    assert snapshot.liquidity_removed == 10


# ============================================================
# 9. Partial Cancel
# ============================================================


def test_partial_cancel_is_feature_shadow_compatibility_not_book_ground_truth():
    """
    IMPORTANT SEMANTIC CONTRACT

    当前冻结 OrderBook 的 CANCEL 语义：

        C -> full delete

    依据当前 ESU6_2026-06-15 完整 MBO Ground Truth：

        Cancel total             = 4,111,285
        Found Existing           = 4,111,285
        Full C.size == old_size  = 4,111,285
        Partial                  = 0

    因此：

        partial C 不是当前这份 ESU6 数据的 Book Ground Truth。

    但是：

        FlowFeatures 的独立 Shadow Order State

    为了模块健壮性，仍然支持 synthetic partial cancel：

        ADD 10
        C 4
        shadow remaining = 6

    本测试只验证 Feature Shadow 的兼容能力。

    不要求冻结 OrderBook 支持 partial C。
    不修改 orderbook/*。
    """

    feature_engine = FeatureEngine(
        orderbook=None
    )

    add = make_event(
        sequence=1,
        action=OrderAction.ADD,
        side=OrderSide.BID,
        order_id=1001,
        price=100,
        size=10,
    )

    feature_engine.snapshot = (
        feature_engine.flow_features.update(
            add,
            feature_engine.snapshot,
        )
    )

    state = (
        feature_engine.flow_features.get_order_state(
            1001
        )
    )

    assert state is not None
    assert state.size == 10

    cancel = make_event(
        sequence=2,
        action=OrderAction.CANCEL,
        side=OrderSide.BID,
        order_id=1001,
        price=100,
        size=4,
    )

    feature_engine.snapshot = (
        feature_engine.flow_features.update(
            cancel,
            feature_engine.snapshot,
        )
    )

    state = (
        feature_engine.flow_features.get_order_state(
            1001
        )
    )

    # ======================================================
    # Feature Shadow Compatibility
    # ======================================================

    assert state is not None
    assert state.size == 6

    assert (
        feature_engine.snapshot.cancel_volume
        ==
        4
    )

    assert (
        feature_engine.snapshot.liquidity_removed
        ==
        4
    )

    assert (
        feature_engine.snapshot.bid_removed_volume
        ==
        4
    )

    # Bid Remove = negative directional flow
    assert (
        feature_engine.snapshot.signed_order_flow
        ==
        6
    )

    # ADD +10, REMOVE -4
    #
    # directional:
    #     positive = Bid Add = 10
    #     negative = Bid Remove = 4
    #
    # OFI = (10 - 4) / (10 + 4)
    assert (
        feature_engine.snapshot.ofi
        ==
        pytest.approx(
            6 / 14
        )
    )


# ============================================================
# 10. Modify Increase
# ============================================================


def test_modify_increase_uses_new_size_not_delta():
    """
    Databento Modify：

        old size = 10
        M.size   = 15

    M.size = 新size

    不是：

        +15

    真实变化：

        +5
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

    add = make_event(
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
        add,
    )

    old_size = book.orders[
        1001
    ].size

    assert old_size == 10

    modify = make_event(
        sequence=2,
        action=OrderAction.MODIFY,
        side=OrderSide.BID,
        order_id=1001,
        price=100,
        size=15,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        modify,
    )

    new_size = book.orders[
        1001
    ].size

    true_delta = (
        new_size
        -
        old_size
    )

    # ======================================================
    # Databento M semantics
    # ======================================================

    assert modify.size == 15

    assert new_size == 15

    assert true_delta == 5

    assert book.bid_volume() == 15

    # ======================================================
    # 当前modify_volume字段记录原始M.size
    #
    # 这不是liquidity delta。
    # ======================================================

    assert snapshot.modify_volume == 15


# ============================================================
# 11. Modify Decrease
# ============================================================


def test_modify_decrease_uses_new_size_not_delta():
    """
    Databento：

        old = 10
        M.size = 6

    正确：

        new size = 6

    liquidity delta：

        -4
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1001,
            price=100,
            size=10,
        ),
    )

    old_size = book.orders[
        1001
    ].size

    modify = make_event(
        sequence=2,
        action=OrderAction.MODIFY,
        side=OrderSide.BID,
        order_id=1001,
        price=100,
        size=6,
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        modify,
    )

    new_size = book.orders[
        1001
    ].size

    true_delta = (
        new_size
        -
        old_size
    )

    assert modify.size == 6

    assert new_size == 6

    assert true_delta == -4

    assert book.bid_volume() == 6

    assert snapshot.modify_volume == 6


# ============================================================
# 12. Modify Increase Liquidity Delta
# ============================================================


def test_modify_increase_liquidity_delta_ground_truth():
    """
    CRITICAL FEATURE TEST

    ADD：

        +10 liquidity

    MODIFY：

        old 10
        new 15

    Modify真正新增：

        +5

    因此累计：

        liquidity_added = 15

    如果当前Feature仍然只有10：

        说明FlowFeatures无法计算M的真实delta。
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1001,
            price=100,
            size=10,
        ),
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=2,
            action=OrderAction.MODIFY,
            side=OrderSide.BID,
            order_id=1001,
            price=100,
            size=15,
        ),
    )

    assert book.orders[
        1001
    ].size == 15

    # ======================================================
    # Ground Truth Liquidity
    #
    # A +10
    # M +5
    #
    # total added = 15
    # ======================================================

    assert snapshot.liquidity_added == 15

    assert snapshot.liquidity_removed == 0


# ============================================================
# 13. Modify Decrease Liquidity Delta
# ============================================================


def test_modify_decrease_liquidity_delta_ground_truth():
    """
    CRITICAL FEATURE TEST

    ADD：

        +10

    MODIFY：

        10 -> 6

    真正移除：

        4

    因此：

        liquidity_added   = 10
        liquidity_removed = 4
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1001,
            price=100,
            size=10,
        ),
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=2,
            action=OrderAction.MODIFY,
            side=OrderSide.BID,
            order_id=1001,
            price=100,
            size=6,
        ),
    )

    assert book.orders[
        1001
    ].size == 6

    assert snapshot.liquidity_added == 10

    # ======================================================
    # Ground Truth:
    #
    # 10 -> 6
    #
    # removed = 4
    # ======================================================

    assert snapshot.liquidity_removed == 4


# ============================================================
# 14. Modify Price Move
# ============================================================


def test_modify_price_move_ground_truth():
    """
    ADD：

        Bid 100 @ 10

    MODIFY：

        Bid 101 @ 10

    正确Book：

        100价格层消失

        101价格层出现

        order_id保持不变
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1001,
            price=100,
            size=10,
        ),
    )

    assert 100 in book.bids

    assert book.best_bid() == 100

    snapshot = apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=2,
            action=OrderAction.MODIFY,
            side=OrderSide.BID,
            order_id=1001,
            price=101,
            size=10,
        ),
    )

    assert 1001 in book.orders

    assert book.orders[
        1001
    ].price == 101

    assert book.orders[
        1001
    ].size == 10

    assert 100 not in book.bids

    assert 101 in book.bids

    assert book.best_bid() == 101

    assert snapshot.best_bid == 101


# ============================================================
# 15. Modify Price Move Liquidity Semantics
# ============================================================


def test_modify_price_move_flow_semantics():
    """
    从Order Flow角度：

        Bid 100 @ 10
            ↓
        Bid 101 @ 10

    应理解为：

        100：

            removed 10

        101：

            added 10

    即使总Book Volume没有变化：

        price-level liquidity发生了迁移。

    当前FeatureSnapshot只有全局：

        liquidity_added
        liquidity_removed

    如果没有记录这次迁移，
    说明当前Flow模型不足以描述price-moving Modify。
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1001,
            price=100,
            size=10,
        ),
    )

    before_volume = book.bid_volume()

    snapshot = apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=2,
            action=OrderAction.MODIFY,
            side=OrderSide.BID,
            order_id=1001,
            price=101,
            size=10,
        ),
    )

    after_volume = book.bid_volume()

    # 总量不变
    assert before_volume == 10

    assert after_volume == 10

    # 价格位置已经变化
    assert 100 not in book.bids

    assert 101 in book.bids

    # ======================================================
    # Ground Truth Flow
    #
    # 初始ADD：
    #     added = 10
    #
    # Price-moving MODIFY：
    #     old level removed = 10
    #     new level added    = 10
    #
    # 所以累计至少应该能够表达：
    #
    #     added   = 20
    #     removed = 10
    #
    # 注意：
    # 这是“price-level flow accounting”，
    # 不是net book volume。
    # ======================================================

    assert snapshot.liquidity_added == 20

    assert snapshot.liquidity_removed == 10


# ============================================================
# 16. Cancel OFI Ground Truth
# ============================================================


def test_cancel_updates_current_flow_ofi():
    """
    当前FlowFeatures定义：

        OFI =
            (added - removed)
            /
            (added + removed)

    这里先验证它自己的数学一致性。

    A:

        +10

    C:

        -4

    expected:

        (10 - 4)
        /
        (10 + 4)

        = 6/14
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

    apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1001,
            price=100,
            size=10,
        ),
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=2,
            action=OrderAction.CANCEL,
            side=OrderSide.BID,
            order_id=1001,
            price=100,
            size=4,
        ),
    )

    expected = (
        10 - 4
    ) / (
        10 + 4
    )

    assert snapshot.ofi == pytest.approx(
        expected
    )


# ============================================================
# 17. Current OFI Is Not Signed Bid/Ask OFI
# ============================================================


def test_directional_ofi_is_separate_from_liquidity_balance():
    """
    IMPORTANT

    当前正式 FlowFeatures 定义：

    directional OFI:

        Bid Add     -> positive
        Ask Remove  -> positive

        Ask Add     -> negative
        Bid Remove  -> negative

    因此：

        Bid Add 10
        Ask Add 10

    两边方向完全抵消：

        signed_order_flow = 0
        directional OFI   = 0.0

    但是从总流动性角度：

        liquidity_added   = 20
        liquidity_removed = 0

    所以：

        liquidity_balance = +1.0

    这两个指标现在必须明确分离。
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

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
        ),
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
            size=10,
        ),
    )

    # ======================================================
    # Raw Liquidity
    # ======================================================

    assert snapshot.liquidity_added == 20
    assert snapshot.liquidity_removed == 0

    # ======================================================
    # Directional Buckets
    # ======================================================

    assert snapshot.bid_added_volume == 10
    assert snapshot.ask_added_volume == 10

    assert snapshot.bid_removed_volume == 0
    assert snapshot.ask_removed_volume == 0

    # ======================================================
    # Directional Flow
    # ======================================================

    assert snapshot.signed_order_flow == 0

    assert snapshot.ofi == pytest.approx(
        0.0
    )

    # ======================================================
    # Liquidity Balance
    # ======================================================

    assert snapshot.liquidity_balance == pytest.approx(
        1.0
    )


# ============================================================
# 18. RESET Is Not Cancel
# ============================================================


def test_reset_is_not_cancel_flow():
    """
    R = Clear Book

    不能把：

        reset size

    当成：

        cancel volume
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

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
        ),
    )

    snapshot = apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=2,
            action=OrderAction.RESET,
            side=None,
            order_id=None,
            price=None,
            size=999,
        ),
    )

    assert len(
        book.orders
    ) == 0

    # RESET不能被伪造成999手Cancel
    assert snapshot.cancel_volume == 0

    assert snapshot.liquidity_removed == 0


# ============================================================
# 19. Diagnostic Summary
# ============================================================


def test_semantics_diagnostic_output():
    """
    打印当前系统关键语义。

    pytest -s 时直接查看。
    """

    (
        book,
        builder,
        feature_engine,
    ) = make_pipeline()

    # ======================================================
    # ADD
    # ======================================================

    snapshot = apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1001,
            price=100,
            size=10,
        ),
    )

    print(
        "\n"
        "============================================================"
    )

    print(
        "MBO SEMANTICS DIAGNOSTIC"
    )

    print(
        "============================================================"
    )

    print(
        "After ADD 10:"
    )

    print(
        "book size            =",
        book.orders[
            1001
        ].size
    )

    print(
        "liquidity_added      =",
        snapshot.liquidity_added
    )

    print(
        "liquidity_removed    =",
        snapshot.liquidity_removed
    )

    # ======================================================
    # MODIFY 10 -> 15
    # ======================================================

    snapshot = apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=2,
            action=OrderAction.MODIFY,
            side=OrderSide.BID,
            order_id=1001,
            price=100,
            size=15,
        ),
    )

    print(
        "\nAfter MODIFY 10 -> 15:"
    )

    print(
        "book size            =",
        book.orders[
            1001
        ].size
    )

    print(
        "modify_volume        =",
        snapshot.modify_volume
    )

    print(
        "liquidity_added      =",
        snapshot.liquidity_added
    )

    print(
        "liquidity_removed    =",
        snapshot.liquidity_removed
    )

    # ======================================================
    # TRADE B
    # ======================================================

    snapshot = apply_event(
        builder,
        feature_engine,
        make_event(
            sequence=3,
            action=OrderAction.TRADE,
            side=OrderSide.BID,
            order_id=None,
            price=101,
            size=5,
        ),
    )

    print(
        "\nAfter BUY aggressor TRADE 5:"
    )

    print(
        "trade_volume         =",
        snapshot.trade_volume
    )

    print(
        "aggressive_buy       =",
        snapshot.aggressive_buy_volume
    )

    print(
        "aggressive_sell      =",
        snapshot.aggressive_sell_volume
    )

    print(
        "trade_imbalance      =",
        snapshot.trade_imbalance
    )

    print(
        "\n"
        "============================================================"
    )

    assert isinstance(
        snapshot,
        FeatureSnapshot
    )