"""
tests/test_full_runtime_engine.py


============================================================
Full Runtime Engine Integration Test
============================================================


目标：

使用真实：

    ESU6_2026-06-15_MBO.dbn.zst


验证：

    DatabentoFeed

        ↓

    TradingEngine

        ↓

    OrderBookBuilder

        ↓

    Strategy

        ↓

    Signal

        ↓

    RiskManagerV2

        ↓

    Order

        ↓

    ExecutionEngine

        ↓

    Fill

        ↓

    Portfolio

        ↓

    Position / PnL


============================================================
测试原则
============================================================


1.

不修改：

    core/engine.py
    data/databento_feed.py
    orderbook/*
    risk/*
    execution/*
    portfolio/*
    order/*


2.

使用真实：

    DatabentoFeed
    OrderBookBuilder
    RiskManagerV2
    ExecutionEngine
    Portfolio


3.

Strategy 使用测试专用 Strategy。

目的不是验证策略 alpha。

而是：

    强制产生一次 Signal

从而检查：

    Signal
        ↓
    Risk
        ↓
    Order
        ↓
    Execution
        ↓
    Fill
        ↓
    Portfolio


4.

真实 Runtime Contract 不使用 Adapter。

如果当前模块之间接口不兼容：

    Test 必须失败。

然后根据真实错误修正正式模块。


============================================================
"""



from pathlib import Path



import pytest



from core.engine import (
    EngineMode,
    TradingEngine,
)



from data.databento_feed import (
    DatabentoFeed,
)



from orderbook.builder import (
    OrderBookBuilder,
)



from signals.signal import (
    Signal,
    SignalSide,
)



from risk.risk_manager_v2 import (
    RiskManagerV2,
)



from execution.execution_engine import (
    ExecutionEngine,
    ExecutionMode,
)



from portfolio.portfolio import (
    Portfolio,
)





# ============================================================
# Project Paths
# ============================================================


PROJECT_ROOT = (

    Path(__file__)

    .resolve()

    .parent

    .parent

)



MBO_FILE = (

    PROJECT_ROOT

    /

    "data"

    /

    "ESU6_2026-06-15_MBO.dbn.zst"

)



SYMBOL = "ESU6"





# ============================================================
# Runtime Configuration
# ============================================================


EVENT_LIMIT = 20_000



F_LAST = 128





# ============================================================
# Limited Feed
# ============================================================


class LimitedFeed:
    """
    给真实 DatabentoFeed 添加事件数量限制。


    TradingEngine.run():

        for event in self.feed


    所以这里只负责包装 iterable。


    不改变：

        event
        sequence
        flags
        order
    """



    def __init__(

        self,

        feed,

        limit,

    ):


        self.feed = feed

        self.limit = limit



    def __iter__(

        self

    ):


        count = 0


        for event in self.feed:


            if (

                count

                >=

                self.limit

            ):

                break


            yield event


            count += 1





# ============================================================
# One Shot Strategy
# ============================================================


class OneShotStrategy:
    """
    Runtime 集成测试 Strategy。


    目的：

        在第一个 Engine Stable Event

        生成一次 BUY Signal。


    后续：

        永远返回 None。


    这不是策略逻辑测试。


    只用于强制触发：

        Strategy
            ↓
        Signal
            ↓
        Risk
            ↓
        Order
            ↓
        Execution
            ↓
        Fill
            ↓
        Portfolio
    """



    def __init__(

        self

    ):


        self.started = 0

        self.stopped = 0



        self.market_event_count = 0

        self.generate_signal_count = 0



        self.generated = False



        self.last_event = None

        self.last_state = None





    # ========================================================
    # Start
    # ========================================================


    def on_start(

        self,

        state

    ):


        self.started += 1





    # ========================================================
    # Stop
    # ========================================================


    def on_stop(

        self,

        state

    ):


        self.stopped += 1





    # ========================================================
    # Stable Market Event
    # ========================================================


    def on_market_event(

        self,

        event,

        state

    ):


        self.market_event_count += 1


        self.last_event = event

        self.last_state = state





    # ========================================================
    # Generate Signal
    # ========================================================


    def generate_signal(

        self,

        event,

        state

    ):


        self.generate_signal_count += 1



        if self.generated:

            return None



        self.generated = True



        return Signal(

            symbol=SYMBOL,

            side=SignalSide.BUY,

            quantity=1,

            strategy="full_runtime_test",

            confidence=1.0,

        )





# ============================================================
# Scan Real Feed
# ============================================================


def scan_real_feed(

    limit

):
    """
    独立扫描真实 MBO。


    统计：

        total
        F_LAST


    不经过 TradingEngine。


    用于建立测试 Reference。
    """



    feed = DatabentoFeed(

        file_path=str(

            MBO_FILE

        ),

        symbol=SYMBOL,

    )



    total = 0

    last_count = 0



    for event in feed:


        if (

            total

            >=

            limit

        ):

            break



        flags = int(

            getattr(

                event,

                "flags",

                0

            )

            or

            0

        )



        if (

            flags

            &

            F_LAST

        ):


            last_count += 1



        total += 1



    return {

        "total":

            total,


        "last_count":

            last_count,

    }





# ============================================================
# Test 1
# Real MBO File
# ============================================================


def test_full_runtime_real_mbo_file_exists():
    """
    Full Runtime Test 必须使用真实 MBO。
    """



    assert (

        MBO_FILE.exists()

    ), (

        f"MBO file missing: "

        f"{MBO_FILE}"

    )





# ============================================================
# Test 2
# Real Feed F_LAST
# ============================================================


def test_full_runtime_real_feed_contains_f_last():
    """
    确认当前测试区间内存在稳定边界 F_LAST。
    """



    stats = (

        scan_real_feed(

            EVENT_LIMIT

        )

    )



    print()



    print(

        "=" * 100

    )



    print(

        "FULL RUNTIME REAL FEED"

    )



    print(

        "=" * 100

    )



    print(

        "events:",

        stats["total"]

    )



    print(

        "F_LAST:",

        stats["last_count"]

    )



    print(

        "=" * 100

    )



    assert (

        stats["total"]

        ==

        EVENT_LIMIT

    )



    assert (

        stats["last_count"]

        >

        0

    )





# ============================================================
# Test 3
# Engine Construction
# ============================================================


def test_full_runtime_engine_construction():
    """
    验证所有真实组件可以构造。
    """



    portfolio = Portfolio(

        initial_capital=100000

    )



    execution = ExecutionEngine(

        mode=ExecutionMode.BACKTEST,

    )



    risk = RiskManagerV2()



    orderbook = OrderBookBuilder()



    strategy = OneShotStrategy()



    engine = TradingEngine(

        mode=EngineMode.BACKTEST,

        feed=None,

        orderbook=orderbook,

        strategy=strategy,

        risk=risk,

        execution=execution,

        portfolio=portfolio,

    )



    assert engine is not None



    assert (

        engine.orderbook

        is

        orderbook

    )



    assert (

        engine.strategy

        is

        strategy

    )



    assert (

        engine.risk

        is

        risk

    )



    assert (

        engine.execution

        is

        execution

    )



    assert (

        engine.portfolio

        is

        portfolio

    )



    assert (

        engine.state.orderbook

        is

        orderbook

    )



    assert (

        engine.state.portfolio

        is

        portfolio

    )





# ============================================================
# Test 4
# FULL REAL RUNTIME
# ============================================================


def test_full_runtime_engine_real_mbo_end_to_end():
    """
    核心测试。


    真正执行：

        Real MBO
            ↓
        DatabentoFeed
            ↓
        TradingEngine
            ↓
        OrderBookBuilder
            ↓
        OneShotStrategy
            ↓
        Signal
            ↓
        RiskManagerV2
            ↓
        Order
            ↓
        ExecutionEngine
            ↓
        Fill
            ↓
        Portfolio


    注意：

    本测试不使用 Fake Risk。

    不使用 Fake Execution。

    不使用 Fake Portfolio。


    如果正式模块接口不能直接连接：

        测试必须失败。

    """



    # ========================================================
    # Independent Reference
    # ========================================================


    expected = (

        scan_real_feed(

            EVENT_LIMIT

        )

    )



    assert (

        expected["last_count"]

        >

        0

    )





    # ========================================================
    # Real Feed
    # ========================================================


    raw_feed = DatabentoFeed(

        file_path=str(

            MBO_FILE

        ),

        symbol=SYMBOL,

    )



    feed = LimitedFeed(

        feed=raw_feed,

        limit=EVENT_LIMIT,

    )





    # ========================================================
    # Real OrderBook
    # ========================================================


    orderbook = OrderBookBuilder()





    # ========================================================
    # Real Portfolio
    # ========================================================


    portfolio = Portfolio(

        initial_capital=100000

    )





    # ========================================================
    # Real Risk
    # ========================================================


    risk = RiskManagerV2()





    # ========================================================
    # Real Execution
    # ========================================================


    execution = ExecutionEngine(

        mode=ExecutionMode.BACKTEST,

    )





    # ========================================================
    # Strategy
    # ========================================================


    strategy = OneShotStrategy()





    # ========================================================
    # Trading Engine
    # ========================================================


    engine = TradingEngine(

        mode=EngineMode.BACKTEST,

        feed=feed,

        orderbook=orderbook,

        strategy=strategy,

        risk=risk,

        execution=execution,

        portfolio=portfolio,

    )





    # ========================================================
    # Run
    # ========================================================


    engine.run()





    # ========================================================
    # Engine Lifecycle
    # ========================================================


    assert (

        engine.running

        is False

    )



    assert (

        strategy.started

        ==

        1

    )



    assert (

        strategy.stopped

        ==

        1

    )





    # ========================================================
    # Raw Event Path
    # ========================================================


    assert (

        engine.processed_events

        ==

        EVENT_LIMIT

    ), (

        "Engine raw event count mismatch | "

        f"engine={engine.processed_events} "

        f"expected={EVENT_LIMIT}"

    )



    assert (

        engine.state.event_count

        ==

        EVENT_LIMIT

    ), (

        "SystemState event_count mismatch | "

        f"state={engine.state.event_count} "

        f"expected={EVENT_LIMIT}"

    )



    assert (

        orderbook.event_count

        ==

        EVENT_LIMIT

    ), (

        "OrderBookBuilder event_count mismatch | "

        f"book={orderbook.event_count} "

        f"expected={EVENT_LIMIT}"

    )





    # ========================================================
    # F_LAST Dispatch
    # ========================================================


    assert (

        strategy.market_event_count

        ==

        expected["last_count"]

    ), (

        "Strategy F_LAST dispatch mismatch | "

        f"strategy={strategy.market_event_count} "

        f"expected={expected['last_count']}"

    )



    assert (

        strategy.generate_signal_count

        ==

        expected["last_count"]

    ), (

        "Strategy generate_signal dispatch mismatch | "

        f"generate={strategy.generate_signal_count} "

        f"expected={expected['last_count']}"

    )





    # ========================================================
    # Signal
    # ========================================================


    assert (

        strategy.generated

        is True

    )



    assert (

        engine.signal_count

        ==

        1

    ), (

        "Expected exactly one strategy signal | "

        f"actual={engine.signal_count}"

    )



    assert (

        engine.last_signal

        is not None

    )



    assert (

        engine.last_signal.symbol

        ==

        SYMBOL

    )





    # ========================================================
    # Risk
    # ========================================================


    assert (

        risk.total_checks

        ==

        1

    ), (

        "Risk should check exactly one signal | "

        f"actual={risk.total_checks}"

    )



    assert (

        risk.total_approved

        ==

        1

    ), (

        "Signal should be approved by Risk | "

        f"approved={risk.total_approved} "

        f"rejected={risk.total_rejected}"

    )



    assert (

        risk.total_rejected

        ==

        0

    )



    assert (

        engine.risk_reject_count

        ==

        0

    )





    # ========================================================
    # Order
    # ========================================================


    assert (

        engine.order_count

        ==

        1

    ), (

        "Expected exactly one Order | "

        f"actual={engine.order_count}"

    )



    assert (

        engine.last_order

        is not None

    )



    assert (

        engine.last_order.symbol

        ==

        SYMBOL

    )





    # ========================================================
    # Execution
    # ========================================================


    assert (

        engine.execution_fail_count

        ==

        0

    ), (

        "Execution failed after Risk approval | "

        f"execution_failures="

        f"{engine.execution_fail_count}"

    )



    assert (

        execution.total_orders

        ==

        1

    ), (

        "ExecutionEngine should receive one order | "

        f"actual={execution.total_orders}"

    )



    assert (

        execution.total_fills

        ==

        1

    ), (

        "ExecutionEngine should create one Fill | "

        f"actual={execution.total_fills}"

    )



    assert (

        execution.volume

        ==

        1

    )





    # ========================================================
    # Engine Fill
    # ========================================================


    assert (

        engine.fill_count

        ==

        1

    ), (

        "TradingEngine should receive one Fill | "

        f"actual={engine.fill_count}"

    )



    assert (

        engine.last_fill

        is not None

    )



    assert (

        engine.last_fill.symbol

        ==

        SYMBOL

    )



    assert (

        engine.last_fill.quantity

        ==

        1

    )



    assert (

        engine.last_fill.price

        is not None

    )





    # ========================================================
    # Portfolio
    # ========================================================


    assert (

        portfolio.trade_count

        ==

        1

    ), (

        "Portfolio should receive exactly one Fill | "

        f"trade_count={portfolio.trade_count}"

    )



    assert (

        portfolio.volume

        ==

        1

    )



    assert (

        portfolio.last_fill

        is not None

    )



    position = (

        portfolio.get_position(

            SYMBOL

        )

    )



    assert (

        position.quantity

        ==

        1

    ), (

        "Portfolio Position was not updated | "

        f"quantity={position.quantity}"

    )





    # ========================================================
    # Engine Runtime Statistics
    # ========================================================


    progress = (

        engine.progress()

    )



    assert (

        progress["processed_events"]

        ==

        EVENT_LIMIT

    )



    assert (

        progress["signals"]

        ==

        1

    )



    assert (

        progress["orders"]

        ==

        1

    )



    assert (

        progress["fills"]

        ==

        1

    )



    assert (

        progress["risk_rejects"]

        ==

        0

    )



    assert (

        progress["execution_failures"]

        ==

        0

    )





# ============================================================
# Test 5
# Diagnostic
# ============================================================


def test_full_runtime_diagnostic():
    """
    简单输出测试配置。
    """



    print()



    print(

        "=" * 100

    )



    print(

        "FULL RUNTIME ENGINE DIAGNOSTIC"

    )



    print(

        "=" * 100

    )



    print(

        "symbol:",

        SYMBOL

    )



    print(

        "event_limit:",

        EVENT_LIMIT

    )



    print(

        "mbo_file:",

        MBO_FILE

    )



    print(

        "=" * 100

    )