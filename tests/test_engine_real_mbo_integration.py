"""
tests/test_engine_real_mbo_integration.py


============================================================
TradingEngine Real Databento MBO Integration Test
============================================================


目的：

使用真实：

    ESU6_2026-06-15_MBO.dbn.zst

验证完整链路：

    Raw Databento MBO
        ↓
    DatabentoFeed
        ↓
    TradingEngine
        ↓
    OrderBookBuilder
        ↓
    Strategy
        ↓
    Risk
        ↓
    Execution


============================================================
本测试验证
============================================================


1. Engine处理所有raw MarketEvent：

       processed_events
       ==
       实际feed事件数量


2. OrderBookBuilder处理所有raw MarketEvent。


3. Strategy只在：

       event.flags & F_LAST

   成立时调用。


4. Risk只在F_LAST调用。


5. Execution只在F_LAST调用。


6. Strategy / Risk / Execution：

       调用次数
       ==
       实际F_LAST数量


7. N + F_LAST：

       必须能够触发稳定状态dispatch。


8. Engine Replay后的OrderBook：

       与独立Direct Replay

   最终完全一致。


9. 比较：

       best bid
       best ask
       bid volume
       ask volume
       active order count

       Top 10：
           price
           size
           count


============================================================
测试规模
============================================================


默认：

    前250,000条真实MBO records


这是前面已经做过raw/feed flags parity的同一规模。


============================================================
重要
============================================================


本测试：

    不修改：
        core/engine.py
        data/databento_feed.py
        orderbook/*


只验证真实集成链。


============================================================
"""


from heapq import (
    nlargest,
    nsmallest,
)

from pathlib import Path


import pytest


from core.engine import (
    EngineMode,
    TradingEngine,
)


from core.event import (
    OrderAction,
)


from data.databento_feed import (
    DatabentoFeed,
)


from orderbook.builder import (
    OrderBookBuilder,
)



# ============================================================
# Paths
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
# Configuration
# ============================================================


EVENT_LIMIT = 250_000


DEPTH = 10


F_LAST = 128



# ============================================================
# Limited Feed
# ============================================================


class LimitedFeed:
    """
    给真实 DatabentoFeed 加事件数量限制。


    TradingEngine.run()要求：

        for event in self.feed


    所以这里做一个简单Iterable包装。
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
# Recording Strategy
# ============================================================


class RecordingStrategy:
    """
    记录Engine实际dispatch到Strategy的稳定事件。
    """


    def __init__(
        self
    ):

        self.started = 0

        self.stopped = 0

        self.events = []

        self.none_last_count = 0


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


        flags = int(
            event.flags
            or
            0
        )


        if (
            event.action
            ==
            OrderAction.NONE
            and
            (
                flags
                &
                F_LAST
            )
        ):


            self.none_last_count += 1



# ============================================================
# Recording Risk
# ============================================================


class RecordingRisk:
    """
    记录Risk调用。
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
# Recording Execution
# ============================================================


class RecordingExecution:
    """
    记录Execution调用。
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
# Count Real F_LAST
# ============================================================


def scan_real_feed_stats(
    limit
):
    """
    独立扫描真实DatabentoFeed。


    只统计：

        total events
        F_LAST
        N + F_LAST


    不经过TradingEngine。
    """


    feed = DatabentoFeed(

        file_path=str(
            MBO_FILE
        ),

        symbol=SYMBOL,

    )


    total = 0

    last_count = 0

    none_last_count = 0


    for event in feed:


        if (
            total
            >=
            limit
        ):

            break


        flags = int(
            event.flags
            or
            0
        )


        if (
            flags
            &
            F_LAST
        ):


            last_count += 1


            if (
                event.action
                ==
                OrderAction.NONE
            ):

                none_last_count += 1


        total += 1


    return {

        "total":
            total,

        "last_count":
            last_count,

        "none_last_count":
            none_last_count,

    }



# ============================================================
# Extract Top10
# ============================================================


def extract_top10(
    book
):
    """
    从OrderBook读取Top10。
    """


    bid_prices = nlargest(

        DEPTH,

        book.bids.keys(),

    )


    ask_prices = nsmallest(

        DEPTH,

        book.asks.keys(),

    )


    bids = []

    asks = []


    for depth, price in enumerate(
        bid_prices
    ):


        level = (
            book.bids[
                price
            ]
        )


        bids.append(
            {
                "depth":
                    depth,

                "price":
                    price,

                "size":
                    level.volume,

                "count":
                    level.order_count(),
            }
        )


    for depth, price in enumerate(
        ask_prices
    ):


        level = (
            book.asks[
                price
            ]
        )


        asks.append(
            {
                "depth":
                    depth,

                "price":
                    price,

                "size":
                    level.volume,

                "count":
                    level.order_count(),
            }
        )


    return {

        "bids":
            bids,

        "asks":
            asks,

    }



# ============================================================
# Direct Replay
# ============================================================


def build_direct_reference(
    limit
):
    """
    不经过TradingEngine。


    直接：

        DatabentoFeed
            ↓
        OrderBookBuilder


    建立独立Reference。


    目的：

    检查Engine没有：

        漏record
        重复record
        改变record顺序
    """


    feed = DatabentoFeed(

        file_path=str(
            MBO_FILE
        ),

        symbol=SYMBOL,

    )


    builder = (
        OrderBookBuilder()
    )


    count = 0


    for event in feed:


        if (
            count
            >=
            limit
        ):

            break


        builder.on_event(
            event
        )


        count += 1


    return (

        builder,

        count,

    )



# ============================================================
# Test 1
# Files
# ============================================================


def test_real_engine_integration_file_exists():
    """
    真实MBO文件必须存在。
    """


    assert (
        MBO_FILE.exists()
    ), (
        f"MBO file missing: "
        f"{MBO_FILE}"
    )



# ============================================================
# Test 2
# Real feed contains F_LAST
# ============================================================


def test_real_feed_contains_f_last():
    """
    前250k真实数据中必须存在F_LAST。
    """


    stats = (
        scan_real_feed_stats(
            EVENT_LIMIT
        )
    )


    print()

    print(
        "=" * 100
    )

    print(
        "REAL MBO F_LAST DISTRIBUTION"
    )

    print(
        "=" * 100
    )


    print(
        "events:",
        stats[
            "total"
        ]
    )


    print(
        "F_LAST:",
        stats[
            "last_count"
        ]
    )


    print(
        "N + F_LAST:",
        stats[
            "none_last_count"
        ]
    )


    assert (
        stats[
            "total"
        ]
        ==
        EVENT_LIMIT
    )


    assert (
        stats[
            "last_count"
        ]
        >
        0
    )



# ============================================================
# Test 3
# Real Engine F_LAST dispatch
# ============================================================


def test_engine_real_mbo_f_last_dispatch():
    """
    核心真实集成测试。


    使用真实DatabentoFeed。


    验证：

        processed_events
        OrderBook replay
        Strategy dispatch
        Risk dispatch
        Execution dispatch

    全部符合F_LAST规则。
    """


    # ========================================================
    # Independent expected stats
    # ========================================================

    expected = (
        scan_real_feed_stats(
            EVENT_LIMIT
        )
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
    # Real OrderBookBuilder
    # ========================================================

    builder = (
        OrderBookBuilder()
    )


    # ========================================================
    # Upper layers
    # ========================================================

    strategy = (
        RecordingStrategy()
    )


    risk = (
        RecordingRisk()
    )


    execution = (
        RecordingExecution()
    )


    # ========================================================
    # Real TradingEngine
    # ========================================================

    engine = TradingEngine(

        mode=EngineMode.BACKTEST,

        feed=feed,

        orderbook=builder,

        strategy=strategy,

        risk=risk,

        execution=execution,

        portfolio=None,

    )


    # ========================================================
    # Run
    # ========================================================

    engine.run()


    # ========================================================
    # Basic Lifecycle
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
    # Every raw record processed
    # ========================================================

    assert (
        engine.processed_events
        ==
        EVENT_LIMIT
    ), (
        f"processed_events mismatch | "
        f"engine={engine.processed_events} "
        f"expected={EVENT_LIMIT}"
    )


    # ========================================================
    # Builder event counter
    # ========================================================

    assert (
        builder.event_count
        ==
        EVENT_LIMIT
    ), (
        f"OrderBookBuilder event_count mismatch | "
        f"builder={builder.event_count} "
        f"expected={EVENT_LIMIT}"
    )


    # ========================================================
    # Strategy = F_LAST
    # ========================================================

    assert (
        len(
            strategy.events
        )
        ==
        expected[
            "last_count"
        ]
    ), (
        "Strategy dispatch count mismatch | "
        f"strategy={len(strategy.events)} "
        f"F_LAST={expected['last_count']}"
    )


    # ========================================================
    # Risk = F_LAST
    # ========================================================

    assert (
        len(
            risk.events
        )
        ==
        expected[
            "last_count"
        ]
    ), (
        "Risk dispatch count mismatch | "
        f"risk={len(risk.events)} "
        f"F_LAST={expected['last_count']}"
    )


    # ========================================================
    # Execution = F_LAST
    # ========================================================

    assert (
        len(
            execution.events
        )
        ==
        expected[
            "last_count"
        ]
    ), (
        "Execution dispatch count mismatch | "
        f"execution={len(execution.events)} "
        f"F_LAST={expected['last_count']}"
    )


    # ========================================================
    # Every Strategy event must actually be F_LAST
    # ========================================================

    for index, event in enumerate(
        strategy.events
    ):


        flags = int(
            event.flags
            or
            0
        )


        assert (
            flags
            &
            F_LAST
        ), (
            f"Strategy received non-F_LAST event | "
            f"index={index} "
            f"sequence={event.sequence} "
            f"flags={flags}"
        )


    # ========================================================
    # N + F_LAST parity
    # ========================================================

    assert (
        strategy.none_last_count
        ==
        expected[
            "none_last_count"
        ]
    ), (
        "N + F_LAST dispatch mismatch | "
        f"strategy={strategy.none_last_count} "
        f"expected={expected['none_last_count']}"
    )


    # ========================================================
    # Summary
    # ========================================================

    book = (
        builder.get_book()
    )


    print()

    print(
        "=" * 100
    )

    print(
        "REAL MBO -> ENGINE F_LAST INTEGRATION PASSED"
    )

    print(
        "=" * 100
    )


    print(
        "raw events:",
        EVENT_LIMIT
    )


    print(
        "engine processed_events:",
        engine.processed_events
    )


    print(
        "builder event_count:",
        builder.event_count
    )


    print()

    print(
        "F_LAST records:",
        expected[
            "last_count"
        ]
    )


    print(
        "Strategy calls:",
        len(
            strategy.events
        )
    )


    print(
        "Risk calls:",
        len(
            risk.events
        )
    )


    print(
        "Execution calls:",
        len(
            execution.events
        )
    )


    print()

    print(
        "N + F_LAST:",
        expected[
            "none_last_count"
        ]
    )


    print()

    print(
        "active orders:",
        len(
            book.orders
        )
    )


    print(
        "bid levels:",
        len(
            book.bids
        )
    )


    print(
        "ask levels:",
        len(
            book.asks
        )
    )


    print(
        "best bid:",
        book.best_bid()
    )


    print(
        "best ask:",
        book.best_ask()
    )



# ============================================================
# Test 4
# Engine Book vs Direct Replay
# ============================================================


def test_engine_book_matches_direct_replay():
    """
    这是第二个关键测试。


    同样的250,000条真实MBO：


        路径A：

            DatabentoFeed
                ↓
            TradingEngine
                ↓
            OrderBookBuilder


        路径B：

            DatabentoFeed
                ↓
            OrderBookBuilder


    两者最终Book必须完全一致。


    这证明Engine的F_LAST gating：

        只影响上层dispatch

    而没有改变：

        OrderBook raw replay。
    """


    # ========================================================
    # Engine Path
    # ========================================================

    engine_builder = (
        OrderBookBuilder()
    )


    engine_feed = LimitedFeed(

        feed=DatabentoFeed(

            file_path=str(
                MBO_FILE
            ),

            symbol=SYMBOL,

        ),

        limit=EVENT_LIMIT,

    )


    engine = TradingEngine(

        mode=EngineMode.BACKTEST,

        feed=engine_feed,

        orderbook=engine_builder,

        strategy=None,

        risk=None,

        execution=None,

        portfolio=None,

    )


    engine.run()


    engine_book = (
        engine_builder.get_book()
    )


    # ========================================================
    # Direct Path
    # ========================================================

    direct_builder, direct_count = (
        build_direct_reference(
            EVENT_LIMIT
        )
    )


    direct_book = (
        direct_builder.get_book()
    )


    # ========================================================
    # Count
    # ========================================================

    assert (
        direct_count
        ==
        EVENT_LIMIT
    )


    assert (
        engine.processed_events
        ==
        direct_count
    )


    assert (
        engine_builder.event_count
        ==
        direct_builder.event_count
    )


    # ========================================================
    # Core Book State
    # ========================================================

    assert (
        engine_book.best_bid()
        ==
        direct_book.best_bid()
    )


    assert (
        engine_book.best_ask()
        ==
        direct_book.best_ask()
    )


    assert (
        engine_book.bid_volume()
        ==
        direct_book.bid_volume()
    )


    assert (
        engine_book.ask_volume()
        ==
        direct_book.ask_volume()
    )


    assert (
        len(
            engine_book.orders
        )
        ==
        len(
            direct_book.orders
        )
    )


    assert (
        len(
            engine_book.bids
        )
        ==
        len(
            direct_book.bids
        )
    )


    assert (
        len(
            engine_book.asks
        )
        ==
        len(
            direct_book.asks
        )
    )


    # ========================================================
    # Top10
    # ========================================================

    engine_top10 = (
        extract_top10(
            engine_book
        )
    )


    direct_top10 = (
        extract_top10(
            direct_book
        )
    )


    assert (
        engine_top10
        ==
        direct_top10
    ), (
        "Engine replay Top10 differs "
        "from direct OrderBookBuilder replay."
    )


    # ========================================================
    # Every active order
    #
    # Compare exact:
    #
    #   ID
    #   side
    #   price
    #   size
    #
    # ========================================================

    assert (
        set(
            engine_book.orders.keys()
        )
        ==
        set(
            direct_book.orders.keys()
        )
    )


    for order_id, engine_order in (
        engine_book.orders.items()
    ):


        direct_order = (
            direct_book.orders[
                order_id
            ]
        )


        assert (
            engine_order.side
            ==
            direct_order.side
        )


        assert (
            engine_order.price
            ==
            direct_order.price
        )


        assert (
            engine_order.size
            ==
            direct_order.size
        )


    print()

    print(
        "=" * 100
    )

    print(
        "ENGINE BOOK == DIRECT REPLAY PASSED"
    )

    print(
        "=" * 100
    )


    print(
        "events:",
        EVENT_LIMIT
    )


    print(
        "active orders:",
        len(
            engine_book.orders
        )
    )


    print(
        "bid levels:",
        len(
            engine_book.bids
        )
    )


    print(
        "ask levels:",
        len(
            engine_book.asks
        )
    )


    print(
        "best bid:",
        engine_book.best_bid()
    )


    print(
        "best ask:",
        engine_book.best_ask()
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