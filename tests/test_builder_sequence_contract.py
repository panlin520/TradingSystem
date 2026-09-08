"""
tests/test_builder_sequence_contract.py

============================================================
OrderBookBuilder Sequence Contract Tests
============================================================

目标：

    专项验证冻结 OrderBookBuilder
    对 Databento sequence 的真实处理行为。

============================================================

IMPORTANT / UNRESOLVED

此前观察到：

    sequence:

        10
        11
         9

    当前本地 Builder 没有抛出 RuntimeError。

这件事不能直接认定为：

    - 正确
    - 错误
    - 设计如此

必须通过独立测试确认真实行为。

============================================================

本测试原则：

    1. 不修改冻结 Builder
    2. 不修改冻结 OrderBook
    3. 不修改 MarketEvent
    4. 只记录当前真实契约
    5. 不为了让测试通过而改变生产代码

============================================================

验证：

    - 正常递增 sequence
    - 相同 sequence
    - sequence 倒退
    - 大幅倒退
    - RESET 前后 sequence
    - NONE / ADD 都参与 sequence
    - 倒退事件是否仍修改 Book
    - last_sequence 最终状态
    - event_count / action_count 状态

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


# ============================================================
# Event Factory
# ============================================================


def make_event(
    *,
    sequence,
    action=OrderAction.NONE,
    side=None,
    order_id=None,
    price=None,
    size=None,
    ts_event=None,
    ts_recv=None,
    symbol="ESU6",
    flags=0,
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
        channel_id=0,
        publisher_id=1,
        instrument_id=1,
        flags=flags,
    )


# ============================================================
# Builder Factory
# ============================================================


def make_builder():
    """
    创建真实冻结 OrderBook + OrderBookBuilder。
    """

    book = OrderBook()

    builder = OrderBookBuilder(
        book=book
    )

    return (
        book,
        builder,
    )


# ============================================================
# Initial State
# ============================================================


def test_sequence_initial_state():
    """
    Builder初始化：

        last_sequence = None
    """

    book, builder = make_builder()

    assert builder.last_sequence is None

    assert builder.event_count == 0


# ============================================================
# First Sequence
# ============================================================


def test_first_sequence_is_recorded():
    """
    第一个sequence应进入Builder状态。
    """

    book, builder = make_builder()

    builder.on_event(
        make_event(
            sequence=10,
        )
    )

    assert builder.last_sequence == 10

    assert builder.event_count == 1


# ============================================================
# Increasing Sequence
# ============================================================


def test_increasing_sequence():
    """
    正常递增：

        10
        11
        12

    必须正常处理。
    """

    book, builder = make_builder()

    for sequence in (
        10,
        11,
        12,
    ):

        builder.on_event(
            make_event(
                sequence=sequence,
            )
        )

    assert builder.last_sequence == 12

    assert builder.event_count == 3


# ============================================================
# Same Sequence
# ============================================================


def test_equal_sequence_behavior():
    """
    验证：

        10
        10

    当前 Builder 是否允许相同 sequence。

    这里不预设异常。
    """

    book, builder = make_builder()

    builder.on_event(
        make_event(
            sequence=10,
        )
    )

    builder.on_event(
        make_event(
            sequence=10,
        )
    )

    assert builder.event_count == 2

    assert builder.last_sequence == 10


# ============================================================
# Backward Sequence
# ============================================================


def test_backward_sequence_observed_behavior():
    """
    核心专项测试：

        10
        11
         9

    根据前一轮真实运行观察：

        当前本地 Builder
        没有抛 RuntimeError。

    本测试记录这个当前事实。
    """

    book, builder = make_builder()

    builder.on_event(
        make_event(
            sequence=10,
        )
    )

    builder.on_event(
        make_event(
            sequence=11,
        )
    )

    # --------------------------------------------------------
    # 当前观察到：
    #
    # 这里不会抛异常。
    # --------------------------------------------------------

    builder.on_event(
        make_event(
            sequence=9,
        )
    )

    assert builder.event_count == 3


# ============================================================
# What Happens To last_sequence?
# ============================================================


def test_backward_sequence_last_sequence_behavior():
    """
    验证乱序之后：

        last_sequence

    到底保持11，
    还是退回9。

    这是当前最关键的行为之一。
    """

    book, builder = make_builder()

    builder.on_event(
        make_event(
            sequence=10,
        )
    )

    builder.on_event(
        make_event(
            sequence=11,
        )
    )

    builder.on_event(
        make_event(
            sequence=9,
        )
    )

    # ======================================================
    # IMPORTANT
    #
    # 当前测试暂时不写：
    #
    #     assert builder.last_sequence == ?
    #
    # 因为这正是我们需要从本地真实实现确认的东西。
    #
    # 这里只确认它仍是整数状态。
    # ======================================================

    assert isinstance(
        builder.last_sequence,
        int
    )


# ============================================================
# Large Backward Jump
# ============================================================


def test_large_backward_sequence_behavior():
    """
    验证大幅倒退：

        1000
        1001
          10

    是否与小幅倒退行为一致。
    """

    book, builder = make_builder()

    builder.on_event(
        make_event(
            sequence=1000,
        )
    )

    builder.on_event(
        make_event(
            sequence=1001,
        )
    )

    builder.on_event(
        make_event(
            sequence=10,
        )
    )

    assert builder.event_count == 3


# ============================================================
# Backward ADD Event
# ============================================================


def test_backward_add_event_book_behavior():
    """
    这是非常重要的一项：

    如果 sequence 倒退的事件仍然被接受，

    那么它是否仍会真正修改OrderBook？

    流程：

        sequence 10:
            ADD Bid 100

        sequence 11:
            ADD Ask 102

        sequence 9:
            ADD Bid 101

    如果第三个事件被真正应用：

        Best Bid会从100变成101。
    """

    book, builder = make_builder()

    builder.on_event(
        make_event(
            sequence=10,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        )
    )

    builder.on_event(
        make_event(
            sequence=11,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=2,
            price=102,
            size=10,
        )
    )

    assert book.best_bid() == 100

    assert book.best_ask() == 102

    builder.on_event(
        make_event(
            sequence=9,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=3,
            price=101,
            size=5,
        )
    )

    # --------------------------------------------------------
    # 不预设最终Best Bid。
    #
    # 只确认Builder仍处于有效状态，
    # 后面通过专门输出测试查看真实结果。
    # --------------------------------------------------------

    assert builder.event_count == 3

    assert isinstance(
        book.orders,
        dict
    )


# ============================================================
# RESET Sequence
# ============================================================


def test_sequence_across_reset():
    """
    验证RESET是否会影响：

        builder.last_sequence

    示例：

        100 ADD
        101 RESET
        102 ADD
    """

    book, builder = make_builder()

    builder.on_event(
        make_event(
            sequence=100,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        )
    )

    builder.on_event(
        make_event(
            sequence=101,
            action=OrderAction.RESET,
            side=None,
            order_id=None,
            price=None,
            size=0,
        )
    )

    assert len(
        book.orders
    ) == 0

    builder.on_event(
        make_event(
            sequence=102,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=2,
            price=101,
            size=10,
        )
    )

    assert builder.event_count == 3

    assert book.best_bid() == 101


# ============================================================
# RESET Then Lower Sequence
# ============================================================


def test_lower_sequence_after_reset_behavior():
    """
    验证：

        sequence 100
        sequence 101 RESET
        sequence 1

    RESET是否意味着sequence边界重置？

    当前不预设结论。
    """

    book, builder = make_builder()

    builder.on_event(
        make_event(
            sequence=100,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        )
    )

    builder.on_event(
        make_event(
            sequence=101,
            action=OrderAction.RESET,
            side=None,
            order_id=None,
            price=None,
            size=0,
        )
    )

    builder.on_event(
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=2,
            price=200,
            size=10,
        )
    )

    assert builder.event_count == 3


# ============================================================
# Action Counts
# ============================================================


def test_sequence_events_still_counted():
    """
    即使出现低sequence事件，

    验证：

        event_count
        action_count

    是否仍然增加。
    """

    book, builder = make_builder()

    builder.on_event(
        make_event(
            sequence=10,
            action=OrderAction.NONE,
        )
    )

    builder.on_event(
        make_event(
            sequence=11,
            action=OrderAction.NONE,
        )
    )

    builder.on_event(
        make_event(
            sequence=9,
            action=OrderAction.NONE,
        )
    )

    assert builder.event_count == 3

    assert builder.action_count[
        "N"
    ] == 3


# ============================================================
# Diagnostic Output
# ============================================================


def test_sequence_diagnostic_output():
    """
    专门打印真实行为。

    使用pytest -s时可以直接看到结果。

    这里不是功能断言，
    而是为了把冻结Builder当前行为完整记录出来。
    """

    book, builder = make_builder()

    # ======================================================
    # 10
    # ======================================================

    builder.on_event(
        make_event(
            sequence=10,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        )
    )

    print(
        "\n"
        "========================================"
    )

    print(
        "After sequence 10:"
    )

    print(
        "last_sequence =",
        builder.last_sequence
    )

    print(
        "best_bid =",
        book.best_bid()
    )

    # ======================================================
    # 11
    # ======================================================

    builder.on_event(
        make_event(
            sequence=11,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=2,
            price=102,
            size=10,
        )
    )

    print(
        "\nAfter sequence 11:"
    )

    print(
        "last_sequence =",
        builder.last_sequence
    )

    print(
        "best_bid =",
        book.best_bid()
    )

    print(
        "best_ask =",
        book.best_ask()
    )

    # ======================================================
    # 9
    # ======================================================

    builder.on_event(
        make_event(
            sequence=9,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=3,
            price=101,
            size=5,
        )
    )

    print(
        "\nAfter backward sequence 9:"
    )

    print(
        "last_sequence =",
        builder.last_sequence
    )

    print(
        "best_bid =",
        book.best_bid()
    )

    print(
        "best_ask =",
        book.best_ask()
    )

    print(
        "orders =",
        len(
            book.orders
        )
    )

    print(
        "event_count =",
        builder.event_count
    )

    print(
        "action_count =",
        builder.action_count
    )

    print(
        "========================================"
    )

    assert builder.event_count == 3