"""
tests/test_orderbook_ground_truth.py


============================================================
OrderBook Official Ground Truth Test
============================================================


目的：

验证我们从：

    Databento MBO

重建得到的 L3 OrderBook，是否与：

    Databento 官方 MBP-10

在同一个 Snapshot 时间点得到完全一致的前 10 档盘口。


============================================================


数据：


MBO：

    data/ESU6_2026-06-15_MBO.dbn.zst


官方 Ground Truth：

    data/ESU6_2026-06-15_MBP10.dbn.zst


instrument：

    ESU6


============================================================


已确认：


MBO first ts_recv:

    1781481600000000000


MBP-10 first ts_recv:

    1781481600000000000


两者：

    delta = 0 ns


instrument_id：

    MBO   = 42140870

    MBP10 = 42140870


因此：

    两个数据文件属于同一个 instrument
    并且拥有相同的 Snapshot 时间锚点。


============================================================


Ground Truth 比较内容：


Bid：

    price
    size
    order count


Ask：

    price
    size
    order count


共：

    10 Bid Levels

    10 Ask Levels


即比较：

    bid_px_00 ... bid_px_09
    bid_sz_00 ... bid_sz_09
    bid_ct_00 ... bid_ct_09

    ask_px_00 ... ask_px_09
    ask_sz_00 ... ask_sz_09
    ask_ct_00 ... ask_ct_09


============================================================


核心原则：


不能：

    MBO 第 N 条

直接比较：

    MBP10 第 N 条


因为：

    MBO 与 MBP-10 schema 的记录数量不同。


这里使用：

    ts_recv Snapshot Anchor


具体方法：


1.

读取官方 MBP-10 第一条 Snapshot。


2.

取得：

    first_mbp10.ts_recv


3.

从 MBO 开始 Replay。


4.

处理所有：

    event.ts_recv == snapshot_ts_recv


的 MBO Snapshot 事件。


5.

遇到：

    event.ts_recv > snapshot_ts_recv

立即停止。


6.

此时我们的 OrderBook 应该代表：

    00:00:00 Snapshot 完成后的 L3 状态。


7.

将它聚合成 Top 10。


8.

和官方 MBP-10 第一条记录逐档比较。


============================================================
"""


from pathlib import Path

import pytest
import databento as db


from data.databento_feed import (
    DatabentoFeed,
)


from orderbook.builder import (
    OrderBookBuilder,
)


from core.event import (
    OrderAction,
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


MBP10_FILE = (
    PROJECT_ROOT
    /
    "data"
    /
    "ESU6_2026-06-15_MBP10.dbn.zst"
)


SYMBOL = "ESU6"


DEPTH = 10



# ============================================================
# Helpers
# ============================================================


def get_attr(
    obj,
    name,
    default=None,
):
    """
    安全读取 Databento record 属性。
    """

    try:

        return getattr(
            obj,
            name
        )

    except Exception:

        return default



# ============================================================
# Official MBP-10
# ============================================================


def load_first_official_mbp10():
    """
    读取 Databento 官方 MBP-10 第一条记录。


    该记录已经确认：

        ts_recv
        =
        2026-06-15 00:00:00 UTC


    并包含完整：

        bid 0..9
        ask 0..9

    Snapshot 状态。
    """


    store = db.DBNStore.from_file(
        MBP10_FILE
    )


    for record in store:

        return record


    raise RuntimeError(
        "MBP-10 file contains no records."
    )



# ============================================================
# Official Top 10
# ============================================================


def extract_official_top10(
    record
):
    """
    从官方 MBP-10 record 提取：

        Bid Top 10

        Ask Top 10


    返回格式：

    {
        "bids": [
            {
                "price": ...,
                "size": ...,
                "count": ...
            },
            ...
        ],

        "asks": [...]
    }
    """


    bids = []

    asks = []


    for depth in range(
        DEPTH
    ):


        suffix = (
            f"{depth:02d}"
        )


        # ====================================================
        # Bid
        # ====================================================

        bid_price = get_attr(
            record,
            f"bid_px_{suffix}"
        )


        bid_size = get_attr(
            record,
            f"bid_sz_{suffix}"
        )


        bid_count = get_attr(
            record,
            f"bid_ct_{suffix}"
        )


        bids.append(
            {
                "depth":
                    depth,

                "price":
                    bid_price,

                "size":
                    bid_size,

                "count":
                    bid_count,
            }
        )


        # ====================================================
        # Ask
        # ====================================================

        ask_price = get_attr(
            record,
            f"ask_px_{suffix}"
        )


        ask_size = get_attr(
            record,
            f"ask_sz_{suffix}"
        )


        ask_count = get_attr(
            record,
            f"ask_ct_{suffix}"
        )


        asks.append(
            {
                "depth":
                    depth,

                "price":
                    ask_price,

                "size":
                    ask_size,

                "count":
                    ask_count,
            }
        )


    return {
        "bids":
            bids,

        "asks":
            asks,
    }



# ============================================================
# Replay MBO Snapshot
# ============================================================


def rebuild_mbo_snapshot(
    snapshot_ts_recv
):
    """
    使用正式：

        DatabentoFeed
        +
        OrderBookBuilder

    重建 MBO Snapshot。


    只处理：

        ts_recv <= snapshot_ts_recv


    实际当前数据：

        Snapshot记录全部拥有：

        ts_recv
        =
        1781481600000000000


    当遇到：

        event.ts_recv > snapshot_ts_recv

    表示已经进入 Snapshot 后的正常实时历史事件。

    此时停止。
    """


    feed = DatabentoFeed(

        file_path=str(
            MBO_FILE
        ),

        symbol=SYMBOL,

    )


    builder = OrderBookBuilder()


    processed = 0

    snapshot_events = 0

    first_action = None

    first_instrument_id = None


    for event in feed:


        # ====================================================
        # 第一个Event
        # ====================================================

        if first_action is None:

            first_action = (
                event.action
            )


            first_instrument_id = (
                event.instrument_id
            )


        # ====================================================
        # Snapshot结束
        # ====================================================

        if (
            event.ts_recv
            >
            snapshot_ts_recv
        ):

            break


        # ====================================================
        # Snapshot之前理论上不存在
        # ====================================================

        if (
            event.ts_recv
            <
            snapshot_ts_recv
        ):

            continue


        # ====================================================
        # Snapshot Event
        # ====================================================

        builder.on_event(
            event
        )


        processed += 1

        snapshot_events += 1


    return {

        "builder":
            builder,

        "book":
            builder.get_book(),

        "processed":
            processed,

        "snapshot_events":
            snapshot_events,

        "first_action":
            first_action,

        "instrument_id":
            first_instrument_id,

    }



# ============================================================
# Aggregate Our Top 10
# ============================================================


def extract_our_top10(
    book
):
    """
    将我们的 L3 OrderBook 聚合成 Top 10。


    Bid：

        price 从高到低


    Ask：

        price 从低到高


    每档统计：

        price

        total size

        order count
    """


    # ========================================================
    # Bid Prices
    # ========================================================

    bid_prices = sorted(

        book.bids.keys(),

        reverse=True,

    )[
        :DEPTH
    ]


    # ========================================================
    # Ask Prices
    # ========================================================

    ask_prices = sorted(

        book.asks.keys()

    )[
        :DEPTH
    ]


    bids = []

    asks = []


    # ========================================================
    # Bids
    # ========================================================

    for depth, price in enumerate(
        bid_prices
    ):


        level = book.bids[
            price
        ]


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


    # ========================================================
    # Asks
    # ========================================================

    for depth, price in enumerate(
        ask_prices
    ):


        level = book.asks[
            price
        ]


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
# Print Comparison
# ============================================================


def print_side_comparison(
    title,
    ours,
    official,
):
    """
    打印逐档对照结果。
    """


    print()

    print(
        "=" * 120
    )

    print(
        title
    )

    print(
        "=" * 120
    )


    print(
        f"{'DEPTH':<8}"
        f"{'OUR PRICE':<20}"
        f"{'OFFICIAL PRICE':<20}"
        f"{'OUR SIZE':<12}"
        f"{'OFF SIZE':<12}"
        f"{'OUR COUNT':<12}"
        f"{'OFF COUNT':<12}"
        f"{'STATUS':<10}"
    )


    print(
        "-" * 120
    )


    for depth in range(
        DEPTH
    ):


        our_level = (
            ours[depth]
            if depth < len(ours)
            else None
        )


        official_level = (
            official[depth]
            if depth < len(official)
            else None
        )


        our_price = (
            our_level["price"]
            if our_level
            else None
        )


        our_size = (
            our_level["size"]
            if our_level
            else None
        )


        our_count = (
            our_level["count"]
            if our_level
            else None
        )


        official_price = (
            official_level["price"]
            if official_level
            else None
        )


        official_size = (
            official_level["size"]
            if official_level
            else None
        )


        official_count = (
            official_level["count"]
            if official_level
            else None
        )


        match = (

            our_price
            ==
            official_price

            and

            our_size
            ==
            official_size

            and

            our_count
            ==
            official_count

        )


        status = (
            "MATCH"
            if match
            else "MISMATCH"
        )


        print(

            f"{depth:<8}"

            f"{str(our_price):<20}"

            f"{str(official_price):<20}"

            f"{str(our_size):<12}"

            f"{str(official_size):<12}"

            f"{str(our_count):<12}"

            f"{str(official_count):<12}"

            f"{status:<10}"

        )



# ============================================================
# Detailed Assertion
# ============================================================


def assert_side_matches(
    side_name,
    ours,
    official,
):
    """
    对单边 Top10 做严格逐档检查。
    """


    assert (
        len(ours)
        >=
        DEPTH
    ), (
        f"{side_name}: "
        f"Our book contains only "
        f"{len(ours)} levels, expected at least {DEPTH}."
    )


    assert (
        len(official)
        >=
        DEPTH
    )


    for depth in range(
        DEPTH
    ):


        our_level = ours[
            depth
        ]


        official_level = official[
            depth
        ]


        # ====================================================
        # Price
        # ====================================================

        assert (
            our_level["price"]
            ==
            official_level["price"]
        ), (
            f"{side_name} depth {depth} PRICE mismatch: "
            f"ours={our_level['price']}, "
            f"official={official_level['price']}"
        )


        # ====================================================
        # Size
        # ====================================================

        assert (
            our_level["size"]
            ==
            official_level["size"]
        ), (
            f"{side_name} depth {depth} SIZE mismatch: "
            f"price={our_level['price']}, "
            f"ours={our_level['size']}, "
            f"official={official_level['size']}"
        )


        # ====================================================
        # Order Count
        # ====================================================

        assert (
            our_level["count"]
            ==
            official_level["count"]
        ), (
            f"{side_name} depth {depth} COUNT mismatch: "
            f"price={our_level['price']}, "
            f"ours={our_level['count']}, "
            f"official={official_level['count']}"
        )



# ============================================================
# Test 1
# Input Files
# ============================================================


def test_ground_truth_files_exist():
    """
    Ground Truth 所需两个文件必须存在。
    """


    assert (
        MBO_FILE.exists()
    ), (
        f"MBO file not found: "
        f"{MBO_FILE}"
    )


    assert (
        MBP10_FILE.exists()
    ), (
        f"MBP10 file not found: "
        f"{MBP10_FILE}"
    )



# ============================================================
# Test 2
# Snapshot Anchor
# ============================================================


def test_ground_truth_snapshot_anchor():
    """
    验证官方 MBP-10 Snapshot 锚点
    和 MBO 文件起点一致。
    """


    official = (
        load_first_official_mbp10()
    )


    official_ts_recv = (
        get_attr(
            official,
            "ts_recv"
        )
    )


    official_instrument = (
        get_attr(
            official,
            "instrument_id"
        )
    )


    replay = rebuild_mbo_snapshot(
        official_ts_recv
    )


    print()

    print(
        "=" * 80
    )

    print(
        "SNAPSHOT ANCHOR"
    )

    print(
        "=" * 80
    )


    print(
        "official ts_recv:",
        official_ts_recv
    )


    print(
        "official instrument_id:",
        official_instrument
    )


    print(
        "MBO instrument_id:",
        replay["instrument_id"]
    )


    print(
        "MBO snapshot events:",
        replay["snapshot_events"]
    )


    print(
        "MBO first action:",
        replay["first_action"]
    )


    assert (
        replay["instrument_id"]
        ==
        official_instrument
    )


    assert (
        replay["snapshot_events"]
        >
        0
    )


    # ========================================================
    # 当前MBO Snapshot应该从Reset开始
    # ========================================================

    assert (
        replay["first_action"]
        ==
        OrderAction.RESET
    )



# ============================================================
# Test 3
# Official BBO
# ============================================================


def test_ground_truth_best_bid_ask():
    """
    第一层验证：

        Best Bid
        Best Ask

    必须和官方 MBP-10 Snapshot 完全一致。
    """


    official_record = (
        load_first_official_mbp10()
    )


    snapshot_ts_recv = (
        get_attr(
            official_record,
            "ts_recv"
        )
    )


    replay = rebuild_mbo_snapshot(
        snapshot_ts_recv
    )


    book = replay[
        "book"
    ]


    official_bid = (
        get_attr(
            official_record,
            "bid_px_00"
        )
    )


    official_ask = (
        get_attr(
            official_record,
            "ask_px_00"
        )
    )


    print()

    print(
        "=" * 80
    )

    print(
        "BEST BID / ASK GROUND TRUTH"
    )

    print(
        "=" * 80
    )


    print(
        "ours best_bid    :",
        book.best_bid()
    )


    print(
        "official best_bid:",
        official_bid
    )


    print(
        "ours best_ask    :",
        book.best_ask()
    )


    print(
        "official best_ask:",
        official_ask
    )


    assert (
        book.best_bid()
        ==
        official_bid
    )


    assert (
        book.best_ask()
        ==
        official_ask
    )



# ============================================================
# Test 4
# Full Top-10 Official Ground Truth
# ============================================================


def test_orderbook_official_mbp10_ground_truth():
    """
    核心 Ground Truth 测试。


    比较：

        我们由 MBO 重建的 L3 OrderBook

    和：

        Databento 官方 MBP-10 Snapshot


    逐档比较：

        Bid 0..9
        Ask 0..9


    每档比较：

        price
        size
        order count
    """


    # ========================================================
    # Official
    # ========================================================

    official_record = (
        load_first_official_mbp10()
    )


    snapshot_ts_recv = (
        get_attr(
            official_record,
            "ts_recv"
        )
    )


    official = (
        extract_official_top10(
            official_record
        )
    )


    # ========================================================
    # Our MBO Reconstruction
    # ========================================================

    replay = rebuild_mbo_snapshot(
        snapshot_ts_recv
    )


    book = replay[
        "book"
    ]


    ours = extract_our_top10(
        book
    )


    # ========================================================
    # Diagnostic Summary
    # ========================================================

    print()

    print(
        "=" * 120
    )

    print(
        "OFFICIAL MBP-10 GROUND TRUTH"
    )

    print(
        "=" * 120
    )


    print(
        "snapshot ts_recv:",
        snapshot_ts_recv
    )


    print(
        "MBO snapshot events:",
        replay["snapshot_events"]
    )


    print(
        "our active orders:",
        len(book.orders)
    )


    print(
        "our bid levels:",
        len(book.bids)
    )


    print(
        "our ask levels:",
        len(book.asks)
    )


    # ========================================================
    # Print Full Comparison Before Assertion
    # ========================================================

    print_side_comparison(

        "BID TOP 10",

        ours["bids"],

        official["bids"],

    )


    print_side_comparison(

        "ASK TOP 10",

        ours["asks"],

        official["asks"],

    )


    # ========================================================
    # Strict Ground Truth Assertion
    # ========================================================

    assert_side_matches(

        "BID",

        ours["bids"],

        official["bids"],

    )


    assert_side_matches(

        "ASK",

        ours["asks"],

        official["asks"],

    )


    print()

    print(
        "=" * 120
    )

    print(
        "OFFICIAL MBP-10 GROUND TRUTH PASSED"
    )

    print(
        "=" * 120
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