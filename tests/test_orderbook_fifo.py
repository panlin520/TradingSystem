"""
tests/test_orderbook_fifo.py


============================================================
OrderBook FIFO Test
============================================================


目的：

验证 L3 OrderBook PriceLevel FIFO。


测试：

Order

    |

    v


PriceLevel


    |

    v


FIFO Queue



============================================================

"""


from orderbook.order import Order
from orderbook.level import PriceLevel


from core.event import OrderSide



# ============================================================
# 创建测试订单
# ============================================================


def create_order(
    order_id,
    size,
    sequence
):

    """
    创建测试订单。

    """

    return Order(

        order_id=order_id,

        side=OrderSide.BID,

        price=100,

        size=size,

        sequence=sequence,

        ts_event=sequence

    )



# ============================================================
# FIFO 插入测试
# ============================================================


def test_fifo_order_insert():

    level = PriceLevel(
        price=100
    )


    order_a = create_order(
        1,
        10,
        1
    )


    order_b = create_order(
        2,
        20,
        2
    )


    order_c = create_order(
        3,
        30,
        3
    )


    level.add_order(order_a)

    level.add_order(order_b)

    level.add_order(order_c)



    assert level.volume == 60


    assert (
        level.first_order().order_id
        ==
        1
    )


    assert (
        level.last_order().order_id
        ==
        3
    )


    assert (
        level.order_count()
        ==
        3
    )



# ============================================================
# 删除订单测试
# ============================================================


def test_fifo_remove_order():

    level = PriceLevel(
        price=100
    )


    level.add_order(
        create_order(
            1,
            10,
            1
        )
    )


    level.add_order(
        create_order(
            2,
            20,
            2
        )
    )


    level.add_order(
        create_order(
            3,
            30,
            3
        )
    )



    removed = level.remove_order(
        2
    )



    assert removed.order_id == 2


    assert level.volume == 40


    assert (
        level.first_order().order_id
        ==
        1
    )


    assert (
        level.last_order().order_id
        ==
        3
    )


    assert (
        level.order_count()
        ==
        2
    )



# ============================================================
# Modify测试
# ============================================================


def test_fifo_modify_order():

    level = PriceLevel(
        price=100
    )


    level.add_order(

        create_order(
            1,
            10,
            1
        )

    )



    assert level.volume == 10



    level.modify_order(

        1,

        25

    )


    assert (
        level.get_order(1).size
        ==
        25
    )


    assert level.volume == 25



# ============================================================
# Queue Position测试
# ============================================================


def test_fifo_queue_position():

    level = PriceLevel(
        price=100
    )


    level.add_order(
        create_order(
            1,
            10,
            1
        )
    )


    level.add_order(
        create_order(
            2,
            20,
            2
        )
    )


    level.add_order(
        create_order(
            3,
            30,
            3
        )
    )



    assert (
        level.queue_position(1)
        ==
        0
    )


    assert (
        level.queue_position(2)
        ==
        1
    )


    assert (
        level.queue_position(3)
        ==
        2
    )



# ============================================================
# 空队列测试
# ============================================================


def test_fifo_empty():

    level = PriceLevel(
        price=100
    )


    assert (
        level.volume
        ==
        0
    )


    assert (
        level.first_order()
        is
        None
    )


    assert (
        level.last_order()
        is
        None
    )


    assert (
        level.empty()
        is
        True
    )