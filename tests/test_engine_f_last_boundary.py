"""
tests/test_engine_f_last_boundary.py


============================================================
TradingEngine F_LAST Boundary Test
============================================================


目的：

验证当前 TradingEngine 是否正确区分：

    record-level processing

和：

    stable market-event dispatch


正确原则：

每条 MarketEvent：

    Clock            -> 更新
    State            -> 更新
    OrderBookBuilder -> 更新


但是：

    Strategy
    Risk
    Execution

不能在每条MBO record后都读取盘口。


只有：

    event.flags & F_LAST

成立时：

    Strategy
    Risk
    Execution

才允许收到“稳定盘口边界”事件。


============================================================
为什么必须这样
============================================================


我们已经用 Databento 官方数据确认：

sequence = 5166966

    44 条 MBO records
    F_LAST = 0

然后：

sequence = 5166967

    action = N
    flags  = 128
    F_LAST = True


因此：

5166966 内部的 44 条 record

属于：

    尚未完成的 market event


而：

5166967 的 N + F_LAST

才表示：

    完整 market-event boundary。


============================================================
本测试分两类
============================================================


A. 当前 Engine 基础行为：

    - stopped时忽略event
    - OrderBook每条record都处理
    - processed_events每条都增加


B. F_LAST稳定状态规则：

    - !F_LAST：
        Strategy不调用
        Risk不调用
        Execution不调用

    - F_LAST：
        Strategy调用一次
        Risk调用一次
        Execution调用一次


============================================================
注意
============================================================

如果当前 engine.py 还没有实现 F_LAST gating，

那么：

    F_LAST相关测试应该 FAIL。

这是预期结果。

不要为了让测试通过而修改测试。

测试的目的就是确认 Engine 当前是否存在架构问题。
"""


from dataclasses import dataclass

import pytest


from core.engine import (
    TradingEngine,
    EngineMode,
)


from core.event import (
    MarketEvent,
    OrderAction,
)



# ============================================================
# Databento Flag
# ============================================================


F_LAST = 128



# ============================================================
# Test Doubles
# ============================================================


class RecordingOrderBook:
    """
    模拟 OrderBookBuilder。

    Engine 当前调用：

        self.orderbook.on_event(event)

    因此这里只记录事件。
    """


    def __init__(
        self
    ):

        self.events = []


    def on_event(
        self,
        event
    ):

        self.events.append(
            event
        )



class RecordingStrategy:
    """
    模拟 Strategy。
    """


    def __init__(
        self
    ):

        self.started = 0

        self.stopped = 0

        self.events = []


    def on_start(
        self,
        state
    ):

        self.started += 1


    def on_stop(
        self,
        state
    ):

        self.stopped += 1


    def on_market_event(
        self,
        event,
        state
    ):

        self.events.append(
            event
        )



class RecordingRisk:
    """
    模拟 Risk。
    """


    def __init__(
        self
    ):

        self.events = []


    def on_event(
        self,
        event,
        state
    ):

        self.events.append(
            event
        )



class RecordingExecution:
    """
    模拟 Execution。
    """


    def __init__(
        self
    ):

        self.events = []


    def on_event(
        self,
        event,
        state
    ):

        self.events.append(
            event
        )



# ============================================================
# Event Factory
# ============================================================


def make_event(
    *,
    sequence,
    flags,
    action=OrderAction.NONE,
    ts_event=None,
    ts_recv=None,
):
    """
    创建最小合法 MarketEvent。


    当前测试不需要真实订单簿字段，
    因此：

        side
        order_id
        price
        size

    使用 None。
    """


    if ts_event is None:

        ts_event = (
            1_000_000_000
            +
            sequence
        )


    if ts_recv is None:

        ts_recv = (
            2_000_000_000
            +
            sequence
        )


    return MarketEvent(

        ts_event=ts_event,

        ts_recv=ts_recv,

        sequence=sequence,

        action=action,

        side=None,

        order_id=None,

        price=None,

        size=None,

        symbol="ESU6",

        channel_id=0,

        publisher_id=1,

        instrument_id=42140870,

        flags=flags,

    )



# ============================================================
# Engine Factory
# ============================================================


def make_engine():
    """
    创建带全部 recording doubles 的 Engine。
    """


    orderbook = (
        RecordingOrderBook()
    )


    strategy = (
        RecordingStrategy()
    )


    risk = (
        RecordingRisk()
    )


    execution = (
        RecordingExecution()
    )


    engine = TradingEngine(

        mode=EngineMode.BACKTEST,

        feed=None,

        orderbook=orderbook,

        strategy=strategy,

        risk=risk,

        execution=execution,

        portfolio=None,

    )


    return {

        "engine":
            engine,

        "orderbook":
            orderbook,

        "strategy":
            strategy,

        "risk":
            risk,

        "execution":
            execution,

    }



# ============================================================
# Test 1
# Engine ignores events while stopped
# ============================================================


def test_engine_ignores_event_when_not_running():
    """
    当前 engine.py：

        if not self.running:
            return

    因此停止状态下：

        Clock
        State
        OrderBook
        Strategy
        Risk
        Execution
        processed_events

    都不能前进。
    """


    ctx = (
        make_engine()
    )


    engine = (
        ctx[
            "engine"
        ]
    )


    event = make_event(

        sequence=1,

        flags=F_LAST,

    )


    engine.on_event(
        event
    )


    assert (
        engine.processed_events
        ==
        0
    )


    assert (
        len(
            ctx[
                "orderbook"
            ].events
        )
        ==
        0
    )


    assert (
        len(
            ctx[
                "strategy"
            ].events
        )
        ==
        0
    )


    assert (
        len(
            ctx[
                "risk"
            ].events
        )
        ==
        0
    )


    assert (
        len(
            ctx[
                "execution"
            ].events
        )
        ==
        0
    )



# ============================================================
# Test 2
# Start / Stop lifecycle
# ============================================================


def test_engine_strategy_lifecycle():
    """
    start / stop 应分别调用一次：

        strategy.on_start
        strategy.on_stop
    """


    ctx = (
        make_engine()
    )


    engine = (
        ctx[
            "engine"
        ]
    )


    strategy = (
        ctx[
            "strategy"
        ]
    )


    engine.start()


    assert (
        engine.running
        is True
    )


    assert (
        strategy.started
        ==
        1
    )


    engine.stop()


    assert (
        engine.running
        is False
    )


    assert (
        strategy.stopped
        ==
        1
    )



# ============================================================
# Test 3
# OrderBook must process every raw record
# ============================================================


def test_engine_orderbook_receives_non_last_records():
    """
    即使：

        F_LAST = False

    OrderBook 仍然必须处理该 raw MBO record。


    F_LAST控制的是：

        stable state publication

    不是：

        book mutation。
    """


    ctx = (
        make_engine()
    )


    engine = (
        ctx[
            "engine"
        ]
    )


    engine.start()


    event = make_event(

        sequence=5166966,

        flags=0,

        action=OrderAction.TRADE,

    )


    engine.on_event(
        event
    )


    assert (
        len(
            ctx[
                "orderbook"
            ].events
        )
        ==
        1
    )


    assert (
        ctx[
            "orderbook"
        ].events[
            0
        ]
        is
        event
    )


    assert (
        engine.processed_events
        ==
        1
    )



# ============================================================
# Test 4
# NON-LAST must NOT reach Strategy
# ============================================================


def test_engine_non_last_event_must_not_reach_strategy():
    """
    关键测试。


    !F_LAST：

        OrderBook需要更新

    但是：

        Strategy不能读取中间盘口。


    当前旧版 Engine 如果无条件：

        strategy.on_market_event(...)

    本测试应该 FAIL。
    """


    ctx = (
        make_engine()
    )


    engine = (
        ctx[
            "engine"
        ]
    )


    engine.start()


    event = make_event(

        sequence=5166966,

        flags=0,

        action=OrderAction.TRADE,

    )


    engine.on_event(
        event
    )


    assert (
        len(
            ctx[
                "orderbook"
            ].events
        )
        ==
        1
    )


    assert (
        len(
            ctx[
                "strategy"
            ].events
        )
        ==
        0
    ), (
        "Strategy received an incomplete "
        "market-event record before F_LAST."
    )



# ============================================================
# Test 5
# NON-LAST must NOT reach Risk
# ============================================================


def test_engine_non_last_event_must_not_reach_risk():
    """
    Risk同样不应该在不完整盘口状态上执行。
    """


    ctx = (
        make_engine()
    )


    engine = (
        ctx[
            "engine"
        ]
    )


    engine.start()


    event = make_event(

        sequence=5166966,

        flags=0,

    )


    engine.on_event(
        event
    )


    assert (
        len(
            ctx[
                "risk"
            ].events
        )
        ==
        0
    ), (
        "Risk received an incomplete "
        "market-event record before F_LAST."
    )



# ============================================================
# Test 6
# NON-LAST must NOT reach Execution
# ============================================================


def test_engine_non_last_event_must_not_reach_execution():
    """
    Execution也不应该在不完整盘口状态上执行。
    """


    ctx = (
        make_engine()
    )


    engine = (
        ctx[
            "engine"
        ]
    )


    engine.start()


    event = make_event(

        sequence=5166966,

        flags=0,

    )


    engine.on_event(
        event
    )


    assert (
        len(
            ctx[
                "execution"
            ].events
        )
        ==
        0
    ), (
        "Execution received an incomplete "
        "market-event record before F_LAST."
    )



# ============================================================
# Test 7
# F_LAST must reach upper layers
# ============================================================


def test_engine_f_last_event_reaches_upper_layers():
    """
    完整 market-event boundary：

        F_LAST=True

    应触发：

        Strategy
        Risk
        Execution

    各一次。
    """


    ctx = (
        make_engine()
    )


    engine = (
        ctx[
            "engine"
        ]
    )


    engine.start()


    event = make_event(

        sequence=5166967,

        flags=F_LAST,

        action=OrderAction.NONE,

    )


    engine.on_event(
        event
    )


    # Book也必须收到
    assert (
        len(
            ctx[
                "orderbook"
            ].events
        )
        ==
        1
    )


    # Strategy
    assert (
        len(
            ctx[
                "strategy"
            ].events
        )
        ==
        1
    )


    # Risk
    assert (
        len(
            ctx[
                "risk"
            ].events
        )
        ==
        1
    )


    # Execution
    assert (
        len(
            ctx[
                "execution"
            ].events
        )
        ==
        1
    )


    assert (
        ctx[
            "strategy"
        ].events[
            0
        ]
        is
        event
    )



# ============================================================
# Test 8
# 44 incomplete records + boundary
# ============================================================


def test_engine_incomplete_sequence_dispatches_only_once():
    """
    模拟已经从真实 Databento 数据确认的结构：


        sequence 5166966

            44 records
            flags=0


        sequence 5166967

            1 record
            action=N
            flags=128


    正确结果：


        OrderBook events:

            45


        Strategy:

            1


        Risk:

            1


        Execution:

            1


        processed_events:

            45
    """


    ctx = (
        make_engine()
    )


    engine = (
        ctx[
            "engine"
        ]
    )


    engine.start()


    # ========================================================
    # 44 incomplete records
    # ========================================================

    for index in range(
        44
    ):


        event = make_event(

            sequence=5166966,

            flags=0,

            action=OrderAction.CANCEL,

            ts_event=(
                10_000_000
                +
                index
            ),

            ts_recv=(
                20_000_000
                +
                index
            ),

        )


        engine.on_event(
            event
        )


    # ========================================================
    # Boundary:
    #
    # N + F_LAST
    # ========================================================

    boundary = make_event(

        sequence=5166967,

        flags=F_LAST,

        action=OrderAction.NONE,

        ts_event=30_000_000,

        ts_recv=40_000_000,

    )


    engine.on_event(
        boundary
    )


    # ========================================================
    # Every raw record reached Book
    # ========================================================

    assert (
        len(
            ctx[
                "orderbook"
            ].events
        )
        ==
        45
    )


    # ========================================================
    # Every raw record counted
    # ========================================================

    assert (
        engine.processed_events
        ==
        45
    )


    # ========================================================
    # Stable state dispatched once
    # ========================================================

    assert (
        len(
            ctx[
                "strategy"
            ].events
        )
        ==
        1
    ), (
        "Strategy must be dispatched exactly once "
        "for 44 incomplete records + one F_LAST boundary."
    )


    assert (
        len(
            ctx[
                "risk"
            ].events
        )
        ==
        1
    )


    assert (
        len(
            ctx[
                "execution"
            ].events
        )
        ==
        1
    )


    assert (
        ctx[
            "strategy"
        ].events[
            0
        ].sequence
        ==
        5166967
    )


    assert (
        ctx[
            "strategy"
        ].events[
            0
        ].action
        ==
        OrderAction.NONE
    )



# ============================================================
# Test 9
# Multiple completed boundaries
# ============================================================


def test_engine_dispatches_once_per_f_last_boundary():
    """
    验证多个market events：

        3 incomplete
        LAST

        2 incomplete
        LAST

        5 incomplete
        LAST


    Strategy最终：

        3次

    而不是：

        13次。
    """


    ctx = (
        make_engine()
    )


    engine = (
        ctx[
            "engine"
        ]
    )


    engine.start()


    raw_record_count = 0


    # ========================================================
    # Event group 1
    # ========================================================

    for _ in range(
        3
    ):


        engine.on_event(
            make_event(

                sequence=100,

                flags=0,

            )
        )


        raw_record_count += 1


    engine.on_event(
        make_event(

            sequence=101,

            flags=F_LAST,

        )
    )


    raw_record_count += 1


    # ========================================================
    # Event group 2
    # ========================================================

    for _ in range(
        2
    ):


        engine.on_event(
            make_event(

                sequence=102,

                flags=0,

            )
        )


        raw_record_count += 1


    engine.on_event(
        make_event(

            sequence=103,

            flags=F_LAST,

        )
    )


    raw_record_count += 1


    # ========================================================
    # Event group 3
    # ========================================================

    for _ in range(
        5
    ):


        engine.on_event(
            make_event(

                sequence=104,

                flags=0,

            )
        )


        raw_record_count += 1


    engine.on_event(
        make_event(

            sequence=105,

            flags=F_LAST,

        )
    )


    raw_record_count += 1


    # ========================================================
    # Raw processing
    # ========================================================

    assert (
        len(
            ctx[
                "orderbook"
            ].events
        )
        ==
        raw_record_count
    )


    assert (
        engine.processed_events
        ==
        raw_record_count
    )


    # ========================================================
    # Stable dispatch
    # ========================================================

    assert (
        len(
            ctx[
                "strategy"
            ].events
        )
        ==
        3
    )


    assert (
        len(
            ctx[
                "risk"
            ].events
        )
        ==
        3
    )


    assert (
        len(
            ctx[
                "execution"
            ].events
        )
        ==
        3
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