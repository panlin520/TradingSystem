"""
tests/test_orderbook_trade.py


============================================================

OrderBook Trade Test

============================================================


目的：

验证 OrderBook 对成交事件以及基础盘口事件的处理。


测试链：

MarketEvent

        |

        v

OrderBookBuilder

        |

        v

OrderBook


============================================================


验证：

- Add订单
- Trade事件统计
- Fill事件行为
- Cancel订单
- Modify订单


============================================================


核心规则：


T = Trade

    - 更新 trade_count
    - 更新 trade_volume
    - 不直接修改 OrderBook


F = Fill

    - 不增加 trade_count
    - 不增加 trade_volume
    - 不直接修改 OrderBook


A / M / C / R

    - 负责真正修改订单簿状态


============================================================
"""


import pytest


from core.event import (
    MarketEvent,
    OrderAction,
    OrderSide,
)


from orderbook.builder import OrderBookBuilder




# ============================================================
# 创建测试事件
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
    创建测试用 MarketEvent。
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
# Trade事件测试
# ============================================================


def test_trade_event():
    """
    测试：

    1. Add 一个 Bid 订单
    2. 输入 Trade
    3. Trade 应增加成交统计
    4. Trade 本身不直接删除订单
    """

    builder = OrderBookBuilder()


    # ========================================================
    # Add Bid
    # ========================================================

    builder.on_event(

        create_event(

            action=OrderAction.ADD,

            order_id=1001,

            side=OrderSide.BID,

            price=7550000000000,

            size=10,

            sequence=1,

        )

    )


    book = builder.get_book()


    assert (
        book.bid_volume()
        ==
        10
    )


    assert (
        len(book.orders)
        ==
        1
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


    # ========================================================
    # Trade
    # ========================================================

    builder.on_event(

        create_event(

            action=OrderAction.TRADE,

            order_id=1001,

            side=OrderSide.BID,

            price=7550000000000,

            size=10,

            sequence=2,

        )

    )


    book = builder.get_book()


    # ========================================================
    # Trade统计
    # ========================================================

    assert (
        book.trade_count
        ==
        1
    )


    assert (
        book.trade_volume
        ==
        10
    )


    # ========================================================
    # Trade不直接修改盘口
    # ========================================================

    assert (
        len(book.orders)
        ==
        1
    )


    assert (
        book.bid_volume()
        ==
        10
    )


    assert (
        book.best_bid()
        ==
        7550000000000
    )




# ============================================================
# Fill事件测试
# ============================================================


def test_fill_event():
    """
    测试：

    1. Add 一个 Ask 订单
    2. 输入 Fill
    3. Fill 不增加 Trade 统计
    4. Fill 不直接修改盘口


    重要：

    FILL 和 TRADE 不是两次独立成交统计。

    Builder 当前设计：

        T -> 负责 trade_count / trade_volume

        F -> 只作为成交明细事件存在，
             不再次进行成交统计。
    """

    builder = OrderBookBuilder()


    # ========================================================
    # Add Ask
    # ========================================================

    builder.on_event(

        create_event(

            action=OrderAction.ADD,

            order_id=2001,

            side=OrderSide.ASK,

            price=7551000000000,

            size=5,

            sequence=1,

        )

    )


    book = builder.get_book()


    assert (
        book.ask_volume()
        ==
        5
    )


    assert (
        len(book.orders)
        ==
        1
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


    # ========================================================
    # Fill
    # ========================================================

    builder.on_event(

        create_event(

            action=OrderAction.FILL,

            order_id=2001,

            side=OrderSide.ASK,

            price=7551000000000,

            size=5,

            sequence=2,

        )

    )


    book = builder.get_book()


    # ========================================================
    # Fill不能重复增加Trade统计
    # ========================================================

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


    # ========================================================
    # Fill本身不直接修改盘口
    # ========================================================

    assert (
        len(book.orders)
        ==
        1
    )


    assert (
        book.ask_volume()
        ==
        5
    )


    assert (
        book.best_ask()
        ==
        7551000000000
    )




# ============================================================
# Trade + Fill 不重复统计
# ============================================================


def test_trade_and_fill_not_double_counted():
    """
    测试：

    同一成交逻辑中：

        TRADE
        +
        FILL

    成交次数只能统计一次。


    预期：

        trade_count = 1
        trade_volume = Trade.size

    Fill 不应再次累加。
    """

    builder = OrderBookBuilder()


    # ========================================================
    # Add resting Ask
    # ========================================================

    builder.on_event(

        create_event(

            action=OrderAction.ADD,

            order_id=2501,

            side=OrderSide.ASK,

            price=7551000000000,

            size=10,

            sequence=1,

        )

    )


    # ========================================================
    # Trade
    # ========================================================

    builder.on_event(

        create_event(

            action=OrderAction.TRADE,

            order_id=2501,

            side=OrderSide.ASK,

            price=7551000000000,

            size=4,

            sequence=2,

        )

    )


    # ========================================================
    # Fill
    # ========================================================

    builder.on_event(

        create_event(

            action=OrderAction.FILL,

            order_id=2501,

            side=OrderSide.ASK,

            price=7551000000000,

            size=4,

            sequence=3,

        )

    )


    book = builder.get_book()


    # ========================================================
    # 不能重复统计
    # ========================================================

    assert (
        book.trade_count
        ==
        1
    )


    assert (
        book.trade_volume
        ==
        4
    )


    # ========================================================
    # T / F 都不直接修改Book
    # ========================================================

    assert (
        book.ask_volume()
        ==
        10
    )


    assert (
        len(book.orders)
        ==
        1
    )




# ============================================================
# Cancel测试
# ============================================================


def test_cancel_event():
    """
    测试：

    Add Ask

        ↓

    Cancel

        ↓

    订单应该从盘口中删除。
    """

    builder = OrderBookBuilder()


    # ========================================================
    # Add
    # ========================================================

    builder.on_event(

        create_event(

            action=OrderAction.ADD,

            order_id=3001,

            side=OrderSide.ASK,

            price=7551000000000,

            size=20,

            sequence=1,

        )

    )


    book = builder.get_book()


    assert (
        book.ask_volume()
        ==
        20
    )


    assert (
        len(book.orders)
        ==
        1
    )


    assert (
        book.best_ask()
        ==
        7551000000000
    )


    # ========================================================
    # Cancel
    # ========================================================

    builder.on_event(

        create_event(

            action=OrderAction.CANCEL,

            order_id=3001,

            sequence=2,

        )

    )


    book = builder.get_book()


    assert (
        book.ask_volume()
        ==
        0
    )


    assert (
        len(book.orders)
        ==
        0
    )


    assert (
        book.best_ask()
        is
        None
    )




# ============================================================
# Modify测试
# ============================================================


def test_modify_event():
    """
    测试：

    Add：

        size = 10

    Modify：

        size = 25

    最终盘口数量应该为：

        25
    """

    builder = OrderBookBuilder()


    # ========================================================
    # Add
    # ========================================================

    builder.on_event(

        create_event(

            action=OrderAction.ADD,

            order_id=4001,

            side=OrderSide.BID,

            price=7550000000000,

            size=10,

            sequence=1,

        )

    )


    book = builder.get_book()


    assert (
        book.bid_volume()
        ==
        10
    )


    # ========================================================
    # Modify
    # ========================================================

    builder.on_event(

        create_event(

            action=OrderAction.MODIFY,

            order_id=4001,

            side=OrderSide.BID,

            price=7550000000000,

            size=25,

            sequence=2,

        )

    )


    book = builder.get_book()


    assert (
        book.bid_volume()
        ==
        25
    )


    assert (
        len(book.orders)
        ==
        1
    )


    assert (
        book.best_bid()
        ==
        7550000000000
    )




# ============================================================
# Action统计测试
# ============================================================


def test_builder_action_count():
    """
    验证 Builder 对：

        A
        T
        F
        C

    的事件数量统计。
    """

    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            action=OrderAction.ADD,

            order_id=5001,

            side=OrderSide.BID,

            price=7550000000000,

            size=10,

            sequence=1,

        )

    )


    builder.on_event(

        create_event(

            action=OrderAction.TRADE,

            order_id=5001,

            side=OrderSide.BID,

            price=7550000000000,

            size=2,

            sequence=2,

        )

    )


    builder.on_event(

        create_event(

            action=OrderAction.FILL,

            order_id=5001,

            side=OrderSide.BID,

            price=7550000000000,

            size=2,

            sequence=3,

        )

    )


    builder.on_event(

        create_event(

            action=OrderAction.CANCEL,

            order_id=5001,

            sequence=4,

        )

    )


    assert (
        builder.event_count
        ==
        4
    )


    assert (
        builder.action_count["A"]
        ==
        1
    )


    assert (
        builder.action_count["T"]
        ==
        1
    )


    assert (
        builder.action_count["F"]
        ==
        1
    )


    assert (
        builder.action_count["C"]
        ==
        1
    )


    # ========================================================
    # Trade只统计一次
    # ========================================================

    book = builder.get_book()


    assert (
        book.trade_count
        ==
        1
    )


    assert (
        book.trade_volume
        ==
        2
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