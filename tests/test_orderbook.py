"""
tests/test_orderbook.py


============================================================
OrderBook Unit Test
============================================================


测试：

    L3 OrderBook


目标：

确认：

    Order

    PriceLevel

    OrderBook

    OrderBookBuilder


逻辑正确。


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
# 创建测试事件
# ============================================================


def create_event(
    action,
    order_id=1,
    side="B",
    price=6959750000000,
    size=10,
    sequence=1
):
    """
    创建模拟 MarketEvent。


    模拟 Databento MBO。
    """


    return MarketEvent(

        ts_event=sequence,

        ts_recv=sequence,

        sequence=sequence,

        action=action,

        side=(

            OrderSide.BID

            if side == "B"

            else OrderSide.ASK

        ),

        order_id=order_id,

        price=price,

        size=size,

        symbol="ESU6",

        channel_id=1,

        publisher_id=1,

        instrument_id=1,

        flags=0,

    )



# ============================================================
# Test Add
# ============================================================


def test_add_order():

    """
    测试新增订单。


    Databento:

        A
    """


    builder = OrderBookBuilder()


    event = create_event(

        OrderAction.ADD,

        order_id=100,

        side="B",

        price=6959750000000,

        size=5,

        sequence=1

    )


    builder.on_event(
        event
    )


    book = builder.get_book()


    assert (
        book.best_bid()
        ==
        6959750000000
    )


    assert (
        book.bid_volume()
        ==
        5
    )


    assert (
        len(book.orders)
        ==
        1
    )



# ============================================================
# Test Modify
# ============================================================


def test_modify_order():

    """
    测试修改订单。


    M
    """


    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            OrderAction.ADD,

            order_id=1,

            size=10,

            sequence=1

        )

    )


    builder.on_event(

        create_event(

            OrderAction.MODIFY,

            order_id=1,

            size=4,

            sequence=2

        )

    )


    book = builder.get_book()


    assert (
        book.bid_volume()
        ==
        4
    )



# ============================================================
# Test Cancel
# ============================================================


def test_cancel_order():

    """
    测试撤单。


    C
    """


    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            OrderAction.ADD,

            order_id=10,

            size=8,

            sequence=1

        )

    )


    builder.on_event(

        create_event(

            OrderAction.CANCEL,

            order_id=10,

            sequence=2

        )

    )


    book = builder.get_book()


    assert (
        len(book.orders)
        ==
        0
    )


    assert (
        book.best_bid()
        is None
    )



# ============================================================
# Test Bid Ask
# ============================================================


def test_best_bid_ask():

    """
    测试盘口价格。
    """


    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            OrderAction.ADD,

            order_id=1,

            side="B",

            price=6959750000000,

            size=10,

            sequence=1

        )

    )


    builder.on_event(

        create_event(

            OrderAction.ADD,

            order_id=2,

            side="A",

            price=6960000000000,

            size=20,

            sequence=2

        )

    )


    book = builder.get_book()


    assert (
        book.best_bid()
        ==
        6959750000000
    )


    assert (
        book.best_ask()
        ==
        6960000000000
    )


    assert (
        book.spread()
        ==
        250000000
    )



# ============================================================
# Test Mid Price
# ============================================================


def test_mid_price():

    """
    测试 Mid。


    注意：

    Bid 和 Ask 是两个不同的真实 L3 订单，
    因此必须使用不同 order_id。
    """


    builder = OrderBookBuilder()


    # ========================================================
    # Bid
    # ========================================================

    builder.on_event(

        create_event(

            OrderAction.ADD,

            order_id=1,

            side="B",

            price=100,

            size=10,

            sequence=1

        )

    )


    # ========================================================
    # Ask
    #
    # 必须使用不同 order_id
    # ========================================================

    builder.on_event(

        create_event(

            OrderAction.ADD,

            order_id=2,

            side="A",

            price=110,

            size=10,

            sequence=2

        )

    )


    book = builder.get_book()


    assert (
        book.mid_price()
        ==
        105
    )



# ============================================================
# Test FIFO
# ============================================================


def test_fifo_queue():

    """
    测试同价格 FIFO。
    """


    builder = OrderBookBuilder()


    builder.on_event(

        create_event(

            OrderAction.ADD,

            order_id=1,

            price=100,

            size=1,

            sequence=1

        )

    )


    builder.on_event(

        create_event(

            OrderAction.ADD,

            order_id=2,

            price=100,

            size=1,

            sequence=2

        )

    )


    book = builder.get_book()


    level = book.bids[
        100
    ]


    orders = list(
        level.orders.keys()
    )


    assert orders == [

        1,

        2

    ]



# ============================================================
# Test Imbalance
# ============================================================


def test_imbalance():

    """
    测试盘口不平衡。


    Bid:

        volume = 100


    Ask:

        volume = 50


    因此：

        Bid > Ask


    预期：

        imbalance > 0


    注意：

    Bid 和 Ask 必须使用不同 order_id。
    """


    builder = OrderBookBuilder()


    # ========================================================
    # Bid
    # ========================================================

    builder.on_event(

        create_event(

            OrderAction.ADD,

            order_id=1,

            side="B",

            size=100,

            sequence=1

        )

    )


    # ========================================================
    # Ask
    #
    # 必须使用不同 order_id
    # ========================================================

    builder.on_event(

        create_event(

            OrderAction.ADD,

            order_id=2,

            side="A",

            price=6960000000000,

            size=50,

            sequence=2

        )

    )


    book = builder.get_book()


    value = book.imbalance()


    assert (
        value
        >
        0
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