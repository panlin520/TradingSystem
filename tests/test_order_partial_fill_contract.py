"""
tests/test_order_partial_fill_contract.py

============================================================
Order Partial Fill Contract Test
============================================================

验证：

    CREATED
        ↓
    fill(partial)
        ↓
    PARTIAL_FILLED
        ↓
    fill(remaining)
        ↓
    FILLED

同时验证：

    filled_quantity
    remaining_quantity

============================================================
"""

import pytest

from order.order import (
    Order,
    OrderSide,
    OrderStatus,
)


def create_order(
    quantity=10
):

    return Order(
        symbol="ESU6",
        side=OrderSide.BUY,
        quantity=quantity,
    )


def test_order_initial_fill_state():

    order = create_order(
        quantity=10
    )

    assert order.status == OrderStatus.CREATED

    assert order.filled_quantity == 0

    assert order.remaining_quantity == 10


def test_partial_fill_sets_partial_filled_status():

    order = create_order(
        quantity=10
    )

    order.fill(
        4
    )

    assert order.status == OrderStatus.PARTIAL_FILLED

    assert order.filled_quantity == 4

    assert order.remaining_quantity == 6


def test_second_partial_fill_remains_partial_filled():

    order = create_order(
        quantity=10
    )

    order.fill(
        4
    )

    order.fill(
        3
    )

    assert order.status == OrderStatus.PARTIAL_FILLED

    assert order.filled_quantity == 7

    assert order.remaining_quantity == 3


def test_remaining_fill_sets_filled_status():

    order = create_order(
        quantity=10
    )

    order.fill(
        4
    )

    order.fill(
        6
    )

    assert order.status == OrderStatus.FILLED

    assert order.filled_quantity == 10

    assert order.remaining_quantity == 0


def test_single_full_fill_sets_filled_status():

    order = create_order(
        quantity=10
    )

    order.fill(
        10
    )

    assert order.status == OrderStatus.FILLED

    assert order.filled_quantity == 10

    assert order.remaining_quantity == 0


def test_fill_rejects_zero_quantity():

    order = create_order(
        quantity=10
    )

    with pytest.raises(
        ValueError
    ):

        order.fill(
            0
        )


def test_fill_rejects_negative_quantity():

    order = create_order(
        quantity=10
    )

    with pytest.raises(
        ValueError
    ):

        order.fill(
            -1
        )


def test_fill_rejects_quantity_above_remaining():

    order = create_order(
        quantity=10
    )

    order.fill(
        8
    )

    with pytest.raises(
        ValueError
    ):

        order.fill(
            3
        )


    assert order.status == OrderStatus.PARTIAL_FILLED

    assert order.filled_quantity == 8

    assert order.remaining_quantity == 2
