"""
tests/test_orderbook_edge_cases.py


============================================================
OrderBook Edge Cases Test
============================================================


目的：

验证 OrderBook 在边界条件下是否保持内部状态一致。


重点不是测试：

    “代码能不能运行”

而是测试：

    “异常或复杂操作之后，
     OrderBook 的最终状态是否仍然正确”


============================================================


测试范围：

1. 空盘口状态

2. RESET

3. MODIFY 改价格

4. MODIFY 改 Side

5. MODIFY 同时改价格 + Side

6. Cancel 不存在订单

7. Modify 不存在订单

8. 重复 order_id

9. PriceLevel 清理

10. 全局 OrderBook Invariant


============================================================
"""


import pytest


from core.event import (
    MarketEvent,
    OrderAction,
    OrderSide,
)


from orderbook.builder import (
    OrderBookBuilder,
)


# ============================================================
# 测试价格
# ============================================================


BID_1 = 7550000000000

BID_2 = 7550250000000

BID_3 = 7550500000000


ASK_1 = 7551000000000

ASK_2 = 7551250000000

ASK_3 = 7551500000000



# ============================================================
# 创建 MarketEvent
# ============================================================


def create_event(
    action,
    order_id=None,
    side=None,
    price=None,
    size=None,
    sequence=1,
):
    """
    创建测试 MarketEvent。
    """

    return MarketEvent(

        ts_event=sequence,

        ts_recv=sequence,

        sequence=sequence,

        action=action,

        side=side,

        order_id=order_id,

        price=price,

        size=size,

        symbol="ESU6",

        channel_id=None,

        publisher_id=None,

        instrument_id=None,

        flags=None,

    )



# ============================================================
# 辅助：
# 验证整个 OrderBook 内部结构一致
# ============================================================


def assert_book_invariant(book):
    """
    验证 L3 OrderBook 核心不变量。


    每一个：

        book.orders

    中的订单必须：

        1.
        出现在正确 Side

        2.
        出现在正确 PriceLevel

        3.
        PriceLevel 中保存的对象
        必须就是全局 orders 中的同一个对象


    同时：

        PriceLevel.volume

    必须等于该 Level 所有 Order.size 总和。
    """


    # ========================================================
    # 1.
    # 从全局 orders -> PriceLevel 检查
    # ========================================================

    for order_id, order in book.orders.items():

        if order.side == OrderSide.BID:

            levels = book.bids

        else:

            levels = book.asks


        assert (
            order.price in levels
        ), (
            f"Order {order_id} price level missing: "
            f"side={order.side}, "
            f"price={order.price}"
        )


        level = levels[
            order.price
        ]


        assert (
            order_id in level.orders
        ), (
            f"Order {order_id} exists in book.orders "
            f"but missing from PriceLevel"
        )


        assert (
            level.orders[order_id]
            is
            order
        ), (
            f"Order {order_id} object mismatch "
            f"between book.orders and PriceLevel"
        )


    # ========================================================
    # 2.
    # 从 Bid PriceLevel -> 全局 orders 检查
    # ========================================================

    for price, level in book.bids.items():

        calculated_volume = 0


        assert (
            not level.empty()
        ), (
            f"Empty Bid PriceLevel should not remain: "
            f"{price}"
        )


        for order_id, order in level.orders.items():

            assert (
                order_id in book.orders
            ), (
                f"Bid level contains stale order "
                f"{order_id}"
            )


            assert (
                book.orders[order_id]
                is
                order
            )


            assert (
                order.side
                ==
                OrderSide.BID
            )


            assert (
                order.price
                ==
                price
            )


            calculated_volume += (
                order.size
            )


        assert (
            level.volume
            ==
            calculated_volume
        ), (
            f"Bid volume mismatch at {price}: "
            f"level.volume={level.volume}, "
            f"calculated={calculated_volume}"
        )


    # ========================================================
    # 3.
    # 从 Ask PriceLevel -> 全局 orders 检查
    # ========================================================

    for price, level in book.asks.items():

        calculated_volume = 0


        assert (
            not level.empty()
        ), (
            f"Empty Ask PriceLevel should not remain: "
            f"{price}"
        )


        for order_id, order in level.orders.items():

            assert (
                order_id in book.orders
            ), (
                f"Ask level contains stale order "
                f"{order_id}"
            )


            assert (
                book.orders[order_id]
                is
                order
            )


            assert (
                order.side
                ==
                OrderSide.ASK
            )


            assert (
                order.price
                ==
                price
            )


            calculated_volume += (
                order.size
            )


        assert (
            level.volume
            ==
            calculated_volume
        ), (
            f"Ask volume mismatch at {price}: "
            f"level.volume={level.volume}, "
            f"calculated={calculated_volume}"
        )



# ============================================================
# 1.
# 空盘口
# ============================================================


def test_empty_book_state():
    """
    新建 OrderBookBuilder 后：

        bids
        asks
        orders

    都应该为空。

    所有依赖 Bid / Ask 的价格指标
    都应该安全返回 None。
    """


    builder = OrderBookBuilder()

    book = builder.get_book()


    assert (
        len(book.bids)
        ==
        0
    )


    assert (
        len(book.asks)
        ==
        0
    )


    assert (
        len(book.orders)
        ==
        0
    )


    assert (
        book.best_bid()
        is
        None
    )


    assert (
        book.best_ask()
        is
        None
    )


    assert (
        book.mid_price()
        is
        None
    )


    assert (
        book.spread()
        is
        None
    )


    assert (
        book.micro_price()
        is
        None
    )


    assert (
        book.imbalance()
        is
        None
    )


    assert (
        book.bid_volume()
        ==
        0
    )


    assert (
        book.ask_volume()
        ==
        0
    )


    assert_book_invariant(
        book
    )



# ============================================================
# 2.
# RESET
# ============================================================


def test_reset_clears_entire_book():
    """
    RESET 后必须清空：

        bids
        asks
        orders

    同时：

        trade_count
        trade_volume

    也按照当前 OrderBook.clear() 设计归零。
    """


    builder = OrderBookBuilder()


    # Bid

    builder.on_event(

        create_event(

            action=OrderAction.ADD,

            order_id=1001,

            side=OrderSide.BID,

            price=BID_1,

            size=10,

            sequence=1,

        )

    )


    # Ask

    builder.on_event(

        create_event(

            action=OrderAction.ADD,

            order_id=1002,

            side=OrderSide.ASK,

            price=ASK_1,

            size=20,

            sequence=2,

        )

    )


    # Trade统计

    builder.on_event(

        create_event(

            action=OrderAction.TRADE,

            order_id=1002,

            side=OrderSide.ASK,

            price=ASK_1,

            size=5,

            sequence=3,

        )

    )


    book = builder.get_book()


    assert (
        len(book.orders)
        ==
        2
    )


    assert (
        book.trade_count
        ==
        1
    )


    assert (
        book.trade_volume
        ==
        5
    )


    # ========================================================
    # RESET
    # ========================================================

    builder.on_event(

        create_event(

            action=OrderAction.RESET,

            sequence=4,

        )

    )


    book = builder.get_book()


    assert (
        len(book.bids)
        ==
        0
    )


    assert (
        len(book.asks)
        ==
        0
    )


    assert (
        len(book.orders)
        ==
        0
    )


    assert (
        book.bid_volume()
        ==
        0
    )


    assert (
        book.ask_volume()
        ==
        0
    )


    assert (
        book.best_bid()
        is
        None
    )


    assert (
        book.best_ask()
        is
        None
    )


    assert (
        book.mid_price()
        is
        None
    )


    assert (
        book.spread()
        is
        None
    )


    assert (
        book.trade_count
        ==
        0
    )


    assert (
        book.trade_volume
        ==
        0
    )


    assert_book_invariant(
        book
    )



# ============================================================
# 3.
# MODIFY 改价格
# ============================================================


def test_modify_price_moves_order_to_new_level():
    """
    Bid：

        BID_1
        size=10

    Modify：

        BID_1
          ↓
        BID_2

    验证：

        旧 Level 删除

        新 Level 创建

        order索引正确

        best_bid更新
    """


    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            action=OrderAction.ADD,

            order_id=2001,

            side=OrderSide.BID,

            price=BID_1,

            size=10,

            sequence=1,

        )

    )


    builder.on_event(

        create_event(

            action=OrderAction.MODIFY,

            order_id=2001,

            side=OrderSide.BID,

            price=BID_2,

            size=10,

            sequence=2,

        )

    )


    book = builder.get_book()


    assert (
        BID_1
        not in
        book.bids
    )


    assert (
        BID_2
        in
        book.bids
    )


    assert (
        book.orders[2001].price
        ==
        BID_2
    )


    assert (
        book.orders[2001].side
        ==
        OrderSide.BID
    )


    assert (
        book.bid_volume()
        ==
        10
    )


    assert (
        book.best_bid()
        ==
        BID_2
    )


    assert_book_invariant(
        book
    )



# ============================================================
# 4.
# MODIFY 改 Side
# ============================================================


def test_modify_side_moves_bid_to_ask():
    """
    同一个订单：

        BID
         ↓
        ASK

    验证：

        不允许同时残留在 Bid 和 Ask。
    """


    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            action=OrderAction.ADD,

            order_id=3001,

            side=OrderSide.BID,

            price=BID_1,

            size=7,

            sequence=1,

        )

    )


    builder.on_event(

        create_event(

            action=OrderAction.MODIFY,

            order_id=3001,

            side=OrderSide.ASK,

            price=BID_1,

            size=7,

            sequence=2,

        )

    )


    book = builder.get_book()


    assert (
        BID_1
        not in
        book.bids
    )


    assert (
        BID_1
        in
        book.asks
    )


    assert (
        book.orders[3001].side
        ==
        OrderSide.ASK
    )


    assert (
        book.bid_volume()
        ==
        0
    )


    assert (
        book.ask_volume()
        ==
        7
    )


    assert (
        len(book.orders)
        ==
        1
    )


    assert_book_invariant(
        book
    )



# ============================================================
# 5.
# MODIFY 同时改 Side + Price
# ============================================================


def test_modify_price_and_side_together():
    """
    原：

        BID BID_1

    修改：

        ASK ASK_2


    验证完整迁移。
    """


    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            action=OrderAction.ADD,

            order_id=4001,

            side=OrderSide.BID,

            price=BID_1,

            size=12,

            sequence=1,

        )

    )


    builder.on_event(

        create_event(

            action=OrderAction.MODIFY,

            order_id=4001,

            side=OrderSide.ASK,

            price=ASK_2,

            size=18,

            sequence=2,

        )

    )


    book = builder.get_book()


    assert (
        BID_1
        not in
        book.bids
    )


    assert (
        ASK_2
        in
        book.asks
    )


    assert (
        book.orders[4001].side
        ==
        OrderSide.ASK
    )


    assert (
        book.orders[4001].price
        ==
        ASK_2
    )


    assert (
        book.orders[4001].size
        ==
        18
    )


    assert (
        book.bid_volume()
        ==
        0
    )


    assert (
        book.ask_volume()
        ==
        18
    )


    assert (
        book.best_ask()
        ==
        ASK_2
    )


    assert_book_invariant(
        book
    )



# ============================================================
# 6.
# Cancel 不存在订单
# ============================================================


def test_cancel_nonexistent_order_does_not_corrupt_book():
    """
    Cancel 一个不存在的 order_id：

    不应该：

        抛异常

        删除其他订单

        改变 volume

        改变 best bid / ask
    """


    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            action=OrderAction.ADD,

            order_id=5001,

            side=OrderSide.BID,

            price=BID_1,

            size=10,

            sequence=1,

        )

    )


    builder.on_event(

        create_event(

            action=OrderAction.CANCEL,

            order_id=999999,

            sequence=2,

        )

    )


    book = builder.get_book()


    assert (
        len(book.orders)
        ==
        1
    )


    assert (
        5001
        in
        book.orders
    )


    assert (
        book.bid_volume()
        ==
        10
    )


    assert (
        book.best_bid()
        ==
        BID_1
    )


    assert_book_invariant(
        book
    )



# ============================================================
# 7.
# Modify 不存在订单
# ============================================================


def test_modify_nonexistent_order_does_not_corrupt_book():
    """
    Modify 不存在 order_id：

    当前 OrderBook.modify_order()
    应直接 return。

    盘口不能变化。
    """


    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            action=OrderAction.ADD,

            order_id=6001,

            side=OrderSide.ASK,

            price=ASK_1,

            size=20,

            sequence=1,

        )

    )


    builder.on_event(

        create_event(

            action=OrderAction.MODIFY,

            order_id=999999,

            side=OrderSide.ASK,

            price=ASK_2,

            size=999,

            sequence=2,

        )

    )


    book = builder.get_book()


    assert (
        len(book.orders)
        ==
        1
    )


    assert (
        6001
        in
        book.orders
    )


    assert (
        book.ask_volume()
        ==
        20
    )


    assert (
        book.best_ask()
        ==
        ASK_1
    )


    assert_book_invariant(
        book
    )



# ============================================================
# 8.
# Cancel 后空 PriceLevel 必须删除
# ============================================================


def test_cancel_last_order_removes_price_level():
    """
    一个价格只有一个订单。

    Cancel 后：

        Order 删除

        PriceLevel 也必须删除。
    """


    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            action=OrderAction.ADD,

            order_id=7001,

            side=OrderSide.BID,

            price=BID_1,

            size=5,

            sequence=1,

        )

    )


    assert (
        BID_1
        in
        builder.get_book().bids
    )


    builder.on_event(

        create_event(

            action=OrderAction.CANCEL,

            order_id=7001,

            sequence=2,

        )

    )


    book = builder.get_book()


    assert (
        BID_1
        not in
        book.bids
    )


    assert (
        len(book.orders)
        ==
        0
    )


    assert (
        book.best_bid()
        is
        None
    )


    assert_book_invariant(
        book
    )



# ============================================================
# 9.
# MODIFY 离开旧 Level 后
# 旧空 Level 必须删除
# ============================================================


def test_modify_last_order_removes_old_price_level():
    """
    BID_1 只有一个订单。

    Modify 到 BID_2 后：

        BID_1 PriceLevel 必须消失。
    """


    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            action=OrderAction.ADD,

            order_id=8001,

            side=OrderSide.BID,

            price=BID_1,

            size=10,

            sequence=1,

        )

    )


    builder.on_event(

        create_event(

            action=OrderAction.MODIFY,

            order_id=8001,

            side=OrderSide.BID,

            price=BID_2,

            size=10,

            sequence=2,

        )

    )


    book = builder.get_book()


    assert (
        BID_1
        not in
        book.bids
    )


    assert (
        BID_2
        in
        book.bids
    )


    assert_book_invariant(
        book
    )



# ============================================================
# 10.
# 多价格层 Best Bid / Ask
# ============================================================


def test_best_bid_ask_with_multiple_levels():
    """
    验证：

        Best Bid = 最大 Bid

        Best Ask = 最小 Ask
    """


    builder = OrderBookBuilder()


    # ========================================================
    # Bids
    # ========================================================

    builder.on_event(

        create_event(

            OrderAction.ADD,
            9001,
            OrderSide.BID,
            BID_1,
            10,
            1,

        )

    )


    builder.on_event(

        create_event(

            OrderAction.ADD,
            9002,
            OrderSide.BID,
            BID_3,
            20,
            2,

        )

    )


    builder.on_event(

        create_event(

            OrderAction.ADD,
            9003,
            OrderSide.BID,
            BID_2,
            30,
            3,

        )

    )


    # ========================================================
    # Asks
    # ========================================================

    builder.on_event(

        create_event(

            OrderAction.ADD,
            9101,
            OrderSide.ASK,
            ASK_3,
            10,
            4,

        )

    )


    builder.on_event(

        create_event(

            OrderAction.ADD,
            9102,
            OrderSide.ASK,
            ASK_1,
            20,
            5,

        )

    )


    builder.on_event(

        create_event(

            OrderAction.ADD,
            9103,
            OrderSide.ASK,
            ASK_2,
            30,
            6,

        )

    )


    book = builder.get_book()


    assert (
        book.best_bid()
        ==
        BID_3
    )


    assert (
        book.best_ask()
        ==
        ASK_1
    )


    assert (
        book.bid_volume()
        ==
        60
    )


    assert (
        book.ask_volume()
        ==
        60
    )


    assert_book_invariant(
        book
    )



# ============================================================
# 11.
# Mid / Spread
# ============================================================


def test_mid_and_spread():
    """
    验证基础价格状态。
    """


    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            OrderAction.ADD,
            10001,
            OrderSide.BID,
            BID_3,
            10,
            1,

        )

    )


    builder.on_event(

        create_event(

            OrderAction.ADD,
            10002,
            OrderSide.ASK,
            ASK_1,
            10,
            2,

        )

    )


    book = builder.get_book()


    expected_mid = (
        BID_3
        +
        ASK_1
    ) / 2


    expected_spread = (
        ASK_1
        -
        BID_3
    )


    assert (
        book.mid_price()
        ==
        expected_mid
    )


    assert (
        book.spread()
        ==
        expected_spread
    )


    assert_book_invariant(
        book
    )



# ============================================================
# 12.
# 多订单 Cancel 中间订单
# ============================================================


def test_cancel_one_order_keeps_other_orders_consistent():
    """
    同一 PriceLevel：

        order1
        order2
        order3

    Cancel order2 后：

        order1
        order3

    必须仍然存在。
    """


    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            OrderAction.ADD,
            11001,
            OrderSide.BID,
            BID_1,
            10,
            1,

        )

    )


    builder.on_event(

        create_event(

            OrderAction.ADD,
            11002,
            OrderSide.BID,
            BID_1,
            20,
            2,

        )

    )


    builder.on_event(

        create_event(

            OrderAction.ADD,
            11003,
            OrderSide.BID,
            BID_1,
            30,
            3,

        )

    )


    builder.on_event(

        create_event(

            action=OrderAction.CANCEL,

            order_id=11002,

            sequence=4,

        )

    )


    book = builder.get_book()


    level = book.bids[
        BID_1
    ]


    assert (
        list(level.orders.keys())
        ==
        [
            11001,
            11003,
        ]
    )


    assert (
        level.volume
        ==
        40
    )


    assert (
        book.bid_volume()
        ==
        40
    )


    assert (
        len(book.orders)
        ==
        2
    )


    assert_book_invariant(
        book
    )



# ============================================================
# 13.
# MODIFY size 后内部 volume 一致
# ============================================================


def test_modify_size_keeps_volume_consistent():
    """
    同 PriceLevel 中：

        order1 = 10
        order2 = 20

    修改：

        order1 = 50

    最终：

        volume = 70
    """


    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            OrderAction.ADD,
            12001,
            OrderSide.ASK,
            ASK_1,
            10,
            1,

        )

    )


    builder.on_event(

        create_event(

            OrderAction.ADD,
            12002,
            OrderSide.ASK,
            ASK_1,
            20,
            2,

        )

    )


    builder.on_event(

        create_event(

            OrderAction.MODIFY,
            12001,
            OrderSide.ASK,
            ASK_1,
            50,
            3,

        )

    )


    book = builder.get_book()


    assert (
        book.asks[ASK_1].volume
        ==
        70
    )


    assert (
        book.ask_volume()
        ==
        70
    )


    assert (
        book.orders[12001].size
        ==
        50
    )


    assert_book_invariant(
        book
    )



# ============================================================
# 14.
# 重复 Order ID
# ============================================================


def test_duplicate_order_id_must_not_corrupt_book():
    """
    极重要边界测试。


    L3核心规则：

        order_id 必须唯一。


    测试：

    先加入：

        order_id = 13001
        BID_1


    再加入：

        同一个 order_id = 13001
        BID_2


    无论系统最终选择：

        Reject
        Ignore
        Replace

    都绝对不能产生：

        book.orders 中只有一个订单

        但旧 PriceLevel 仍残留另一个同 ID 订单


    也就是说：

        Book Invariant 必须保持。


    注意：

    这个测试非常可能暴露当前 add_order()
    对重复 order_id 的一致性问题。

    如果这里失败：

        不要删除测试。

    应修复 OrderBook.add_order()。
    """


    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            OrderAction.ADD,
            13001,
            OrderSide.BID,
            BID_1,
            10,
            1,

        )

    )


    try:

        builder.on_event(

            create_event(

                OrderAction.ADD,
                13001,
                OrderSide.BID,
                BID_2,
                20,
                2,

            )

        )

    except ValueError:

        # ====================================================
        # 如果正式设计选择：
        #
        # 重复 Order ID -> Reject
        #
        # 这是允许的。
        #
        # 但原 Book 必须仍然一致。
        # ====================================================

        pass


    book = builder.get_book()


    assert_book_invariant(
        book
    )


    assert (
        len(book.orders)
        ==
        1
    )



# ============================================================
# 15.
# 最终复杂状态 Invariant
# ============================================================


def test_complex_book_global_invariant():
    """
    构造一组：

        Add
        Modify
        Cancel
        Side Change
        Price Change

    最后统一验证所有内部索引。
    """


    builder = OrderBookBuilder()


    # ========================================================
    # Initial Book
    # ========================================================

    builder.on_event(

        create_event(

            OrderAction.ADD,
            14001,
            OrderSide.BID,
            BID_1,
            10,
            1,

        )

    )


    builder.on_event(

        create_event(

            OrderAction.ADD,
            14002,
            OrderSide.BID,
            BID_1,
            20,
            2,

        )

    )


    builder.on_event(

        create_event(

            OrderAction.ADD,
            14003,
            OrderSide.BID,
            BID_2,
            30,
            3,

        )

    )


    builder.on_event(

        create_event(

            OrderAction.ADD,
            14004,
            OrderSide.ASK,
            ASK_1,
            40,
            4,

        )

    )


    builder.on_event(

        create_event(

            OrderAction.ADD,
            14005,
            OrderSide.ASK,
            ASK_2,
            50,
            5,

        )

    )


    # ========================================================
    # Modify size
    # ========================================================

    builder.on_event(

        create_event(

            OrderAction.MODIFY,
            14001,
            OrderSide.BID,
            BID_1,
            15,
            6,

        )

    )


    # ========================================================
    # Modify price
    # ========================================================

    builder.on_event(

        create_event(

            OrderAction.MODIFY,
            14003,
            OrderSide.BID,
            BID_3,
            30,
            7,

        )

    )


    # ========================================================
    # Side + price change
    # ========================================================

    builder.on_event(

        create_event(

            OrderAction.MODIFY,
            14002,
            OrderSide.ASK,
            ASK_3,
            20,
            8,

        )

    )


    # ========================================================
    # Cancel
    # ========================================================

    builder.on_event(

        create_event(

            action=OrderAction.CANCEL,

            order_id=14004,

            sequence=9,

        )

    )


    book = builder.get_book()


    assert (
        len(book.orders)
        ==
        4
    )


    assert (
        14004
        not in
        book.orders
    )


    assert_book_invariant(
        book
    )



# ============================================================
# Main
# ============================================================


if __name__ == "__main__":

    pytest.main(
        [
            "-v",
            "-s",
            __file__,
        ]
    )