"""
tests/test_orderbook_ground_truth_dense_window.py


============================================================
OrderBook Dense-Window Official Ground Truth Test
F_LAST Aware Version
============================================================


目的：

验证一个高密度行情窗口内：

    Databento MBO
        ↓
    DatabentoFeed
        ↓
    OrderBookBuilder
        ↓
    OrderBook

与：

    Databento 官方 MBP-10

在“完整 market event 边界”上的盘口状态是否持续一致。


============================================================
为什么不能比较所有 ts_recv group
============================================================


前一个 Dense 测试发现：

    sequence = 5166966
    ts_recv  = 1781530200070792146

对应：

    44 条 MBO record


其中：

    T
    F
    C
    M

全部处理完成以后：

    最后一条 MBO flags = 0


也就是说：

    这个 market event 尚未到达 F_LAST。


真正的完成边界出现在下一条：

    sequence = 5166967

    action = N
    flags  = F_LAST


因此：

    不允许在 5166966 的中间状态
    强行拿我们的完整 Book
    与 MBP-10 中间状态比较。


============================================================
本测试的新规则
============================================================


对于每一个 MBP-10 ts_recv group：

首先要求：

    官方 MBP-10 group 最后一条 record
    带 F_LAST


然后让 MBO Replay 到：

    event.ts_recv <= checkpoint_ts_recv


再要求：

    这个 ts_recv 下
    MBO 最后一条 record
    也带 F_LAST


只有：

    Official MBP-10 final record = F_LAST
    AND
    MBO final record             = F_LAST

才进行：

    Top 10 Bid
    Top 10 Ask

严格 Ground Truth 对比。


否则：

    SKIP

而不是：

    FAIL


============================================================
测试窗口
============================================================


    2026-06-15 13:30:00 UTC

到：

    2026-06-15 13:40:00 UTC


============================================================
比较内容
============================================================


每个有效 checkpoint：

Bid depth 0 ~ 9：

    price
    size
    order count


Ask depth 0 ~ 9：

    price
    size
    order count


每个 checkpoint：

    10
    ×
    2 sides
    ×
    3 fields

    =

    60 strict comparisons


============================================================
重要
============================================================


本测试：

    不修改：

        orderbook/order.py
        orderbook/level.py
        orderbook/book.py
        orderbook/builder.py


只验证：

    完整 event boundary 上的真实盘口状态。


============================================================
"""


from datetime import (
    datetime,
    timezone,
)

from heapq import (
    nlargest,
    nsmallest,
)

from pathlib import Path


import databento as db
import pytest


from data.databento_feed import (
    DatabentoFeed,
)


from orderbook.builder import (
    OrderBookBuilder,
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



# ============================================================
# Configuration
# ============================================================


DEPTH = 10


# Databento F_LAST
F_LAST = 128



# ============================================================
# Dense Window
# ============================================================


WINDOW_START = datetime(

    2026,
    6,
    15,

    13,
    30,
    0,

    tzinfo=timezone.utc,

)


WINDOW_END = datetime(

    2026,
    6,
    15,

    13,
    40,
    0,

    tzinfo=timezone.utc,

)



# ============================================================
# datetime -> nanoseconds
# ============================================================


def datetime_to_ns(
    value
):
    """
    UTC datetime -> Unix nanoseconds。
    """


    return (

        int(
            value.timestamp()
        )

        *

        1_000_000_000

    )



WINDOW_START_NS = (
    datetime_to_ns(
        WINDOW_START
    )
)


WINDOW_END_NS = (
    datetime_to_ns(
        WINDOW_END
    )
)



# ============================================================
# Safe Attribute
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
# Flag Helpers
# ============================================================


def has_last_flag(
    flags
):
    """
    判断是否带 F_LAST。
    """


    if flags is None:

        return False


    return bool(

        int(
            flags
        )

        &

        F_LAST

    )



# ============================================================
# Extract Official Top 10
# ============================================================


def extract_official_top10(
    record
):
    """
    提取官方 MBP-10。
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

        bids.append(
            {
                "depth":
                    depth,

                "price":
                    get_attr(
                        record,
                        f"bid_px_{suffix}",
                    ),

                "size":
                    get_attr(
                        record,
                        f"bid_sz_{suffix}",
                    ),

                "count":
                    get_attr(
                        record,
                        f"bid_ct_{suffix}",
                    ),
            }
        )


        # ====================================================
        # Ask
        # ====================================================

        asks.append(
            {
                "depth":
                    depth,

                "price":
                    get_attr(
                        record,
                        f"ask_px_{suffix}",
                    ),

                "size":
                    get_attr(
                        record,
                        f"ask_sz_{suffix}",
                    ),

                "count":
                    get_attr(
                        record,
                        f"ask_ct_{suffix}",
                    ),
            }
        )


    return {

        "bids":
            bids,

        "asks":
            asks,

    }



# ============================================================
# Extract Our Top 10
# ============================================================


def extract_our_top10(
    book
):
    """
    从我们的 L3 OrderBook 聚合 Top 10。


    Bid：

        price 大 -> 小


    Ask：

        price 小 -> 大
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


    # ========================================================
    # Bid
    # ========================================================

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


    # ========================================================
    # Ask
    # ========================================================

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
# Official MBP-10 Group Generator
# ============================================================


def iter_official_dense_groups():
    """
    流式读取官方 MBP-10。


    以：

        ts_recv

    分组。


    每一个 group 只保留：

        最后一条 MBP-10 record。


    为什么？

    因为：

        同一个 ts_recv

    可能存在：

        多条 MBP-10 record。


    我们关心的是：

        该 ts_recv group 的最终官方状态。


    注意：

    是否真正可用于比较：

        后面还要检查 final record 是否 F_LAST。
    """


    store = db.DBNStore.from_file(
        MBP10_FILE
    )


    current_ts_recv = None

    current_last_record = None

    current_record_count = 0


    # ========================================================
    # Internal Group Builder
    # ========================================================

    def make_group(
        ts_recv,
        record,
        record_count,
    ):


        return {

            "ts_recv":
                ts_recv,

            "ts_event":
                get_attr(
                    record,
                    "ts_event",
                ),

            "sequence":
                get_attr(
                    record,
                    "sequence",
                ),

            "action":
                get_attr(
                    record,
                    "action",
                ),

            "flags":
                int(
                    get_attr(
                        record,
                        "flags",
                        0,
                    )
                ),

            "instrument_id":
                get_attr(
                    record,
                    "instrument_id",
                ),

            "record_count":
                record_count,

            "top10":
                extract_official_top10(
                    record
                ),
        }


    # ========================================================
    # Stream
    # ========================================================

    for record in store:


        ts_recv = get_attr(
            record,
            "ts_recv",
        )


        if ts_recv is None:

            continue


        # ====================================================
        # Before Window
        # ====================================================

        if (
            ts_recv
            <
            WINDOW_START_NS
        ):

            continue


        # ====================================================
        # End Window
        # ====================================================

        if (
            ts_recv
            >=
            WINDOW_END_NS
        ):


            if (
                current_last_record
                is not None
            ):


                yield make_group(

                    current_ts_recv,

                    current_last_record,

                    current_record_count,

                )


            return


        # ====================================================
        # First Group
        # ====================================================

        if (
            current_ts_recv
            is None
        ):


            current_ts_recv = (
                ts_recv
            )


            current_last_record = (
                record
            )


            current_record_count = 1


            continue


        # ====================================================
        # Same Group
        # ====================================================

        if (
            ts_recv
            ==
            current_ts_recv
        ):


            current_last_record = (
                record
            )


            current_record_count += 1


            continue


        # ====================================================
        # Previous Group Completed
        # ====================================================

        yield make_group(

            current_ts_recv,

            current_last_record,

            current_record_count,

        )


        # ====================================================
        # Start New Group
        # ====================================================

        current_ts_recv = (
            ts_recv
        )


        current_last_record = (
            record
        )


        current_record_count = 1


    # ========================================================
    # Natural EOF
    # ========================================================

    if (
        current_last_record
        is not None
    ):


        yield make_group(

            current_ts_recv,

            current_last_record,

            current_record_count,

        )



# ============================================================
# Strict Side Comparison
# ============================================================


def compare_side(
    checkpoint_index,
    ts_recv,
    sequence,
    side_name,
    ours,
    official,
):
    """
    严格比较：

        price
        size
        count

    返回比较字段数量。
    """


    assert (
        len(
            ours
        )
        ==
        DEPTH
    ), (
        f"checkpoint={checkpoint_index} "
        f"side={side_name} "
        f"our levels={len(ours)}"
    )


    assert (
        len(
            official
        )
        ==
        DEPTH
    )


    comparisons = 0


    for depth in range(
        DEPTH
    ):


        our_level = (
            ours[
                depth
            ]
        )


        official_level = (
            official[
                depth
            ]
        )


        # ====================================================
        # Price
        # ====================================================

        assert (
            our_level[
                "price"
            ]
            ==
            official_level[
                "price"
            ]
        ), (
            "\n"
            "F_LAST DENSE GROUND TRUTH FAILURE\n"
            f"checkpoint={checkpoint_index}\n"
            f"ts_recv={ts_recv}\n"
            f"sequence={sequence}\n"
            f"side={side_name}\n"
            f"depth={depth}\n"
            f"field=PRICE\n"
            f"ours={our_level['price']}\n"
            f"official={official_level['price']}"
        )


        comparisons += 1


        # ====================================================
        # Size
        # ====================================================

        assert (
            our_level[
                "size"
            ]
            ==
            official_level[
                "size"
            ]
        ), (
            "\n"
            "F_LAST DENSE GROUND TRUTH FAILURE\n"
            f"checkpoint={checkpoint_index}\n"
            f"ts_recv={ts_recv}\n"
            f"sequence={sequence}\n"
            f"side={side_name}\n"
            f"depth={depth}\n"
            f"field=SIZE\n"
            f"price={our_level['price']}\n"
            f"ours={our_level['size']}\n"
            f"official={official_level['size']}"
        )


        comparisons += 1


        # ====================================================
        # Count
        # ====================================================

        assert (
            our_level[
                "count"
            ]
            ==
            official_level[
                "count"
            ]
        ), (
            "\n"
            "F_LAST DENSE GROUND TRUTH FAILURE\n"
            f"checkpoint={checkpoint_index}\n"
            f"ts_recv={ts_recv}\n"
            f"sequence={sequence}\n"
            f"side={side_name}\n"
            f"depth={depth}\n"
            f"field=COUNT\n"
            f"price={our_level['price']}\n"
            f"ours={our_level['count']}\n"
            f"official={official_level['count']}"
        )


        comparisons += 1


    return comparisons



# ============================================================
# Test 1
# Files
# ============================================================


def test_dense_ground_truth_files_exist():
    """
    两个 Ground Truth 文件必须存在。
    """


    assert (
        MBO_FILE.exists()
    ), (
        f"MBO file missing: "
        f"{MBO_FILE}"
    )


    assert (
        MBP10_FILE.exists()
    ), (
        f"MBP10 file missing: "
        f"{MBP10_FILE}"
    )



# ============================================================
# Test 2
# Inspect Official Groups
# ============================================================


def test_dense_window_official_group_structure():
    """
    统计Dense窗口中的：

        MBP-10 ts_recv groups

    以及：

        final record带F_LAST的group数量。
    """


    total_groups = 0

    last_groups = 0

    non_last_groups = 0


    first_group = None

    last_group = None


    for group in (
        iter_official_dense_groups()
    ):


        if first_group is None:

            first_group = (
                group
            )


        last_group = (
            group
        )


        total_groups += 1


        if has_last_flag(
            group[
                "flags"
            ]
        ):


            last_groups += 1


        else:


            non_last_groups += 1


    print()

    print(
        "=" * 100
    )

    print(
        "DENSE WINDOW OFFICIAL GROUP STRUCTURE"
    )

    print(
        "=" * 100
    )


    print(
        "window start:",
        WINDOW_START.isoformat()
    )


    print(
        "window end:",
        WINDOW_END.isoformat()
    )


    print(
        "total ts_recv groups:",
        total_groups
    )


    print(
        "final record has F_LAST:",
        last_groups
    )


    print(
        "final record without F_LAST:",
        non_last_groups
    )


    if first_group is not None:


        print(
            "first ts_recv:",
            first_group[
                "ts_recv"
            ]
        )


    if last_group is not None:


        print(
            "last ts_recv:",
            last_group[
                "ts_recv"
            ]
        )


    assert (
        total_groups
        >
        0
    )


    assert (
        last_groups
        >
        0
    )



# ============================================================
# Test 3
# F_LAST Dense Ground Truth
# ============================================================


def test_orderbook_dense_window_ground_truth():
    """
    F_LAST-aware Dense Ground Truth。


    规则：


    1.

    读取每个官方 MBP-10 ts_recv group。


    2.

    MBO Replay：

        所有 event.ts_recv <= checkpoint_ts_recv


    3.

    记录：

        该 ts_recv 下
        最后一条 MBO event


    4.

    只有当：

        Official final flags & F_LAST

    AND

        MBO final flags & F_LAST

    才进行严格比较。


    5.

    中间状态：

        SKIP

    不判定为：

        FAIL
    """


    # ========================================================
    # Production MBO Replay
    # ========================================================

    feed = DatabentoFeed(

        file_path=str(
            MBO_FILE
        ),

        symbol=SYMBOL,

    )


    builder = (
        OrderBookBuilder()
    )


    mbo_iterator = iter(
        feed
    )


    pending_event = None


    # ========================================================
    # Stats
    # ========================================================

    official_group_count = 0

    compared_checkpoint_count = 0


    skipped_official_not_last = 0

    skipped_mbo_not_last = 0

    skipped_no_exact_mbo_group = 0


    mbo_event_count = 0

    comparison_count = 0


    first_compared_ts = None

    last_compared_ts = None


    official_instrument_id = None


    # ========================================================
    # Walk Official Groups
    # ========================================================

    for checkpoint in (
        iter_official_dense_groups()
    ):


        official_group_count += 1


        checkpoint_ts = (
            checkpoint[
                "ts_recv"
            ]
        )


        checkpoint_sequence = (
            checkpoint[
                "sequence"
            ]
        )


        # ====================================================
        # Official Instrument
        # ====================================================

        current_instrument_id = (
            checkpoint[
                "instrument_id"
            ]
        )


        if official_instrument_id is None:


            official_instrument_id = (
                current_instrument_id
            )


        else:


            assert (
                current_instrument_id
                ==
                official_instrument_id
            ), (
                "Official instrument_id changed "
                "inside Dense window."
            )


        # ====================================================
        # Replay MBO up through checkpoint ts_recv
        # ====================================================

        last_mbo_event_at_checkpoint = None


        while True:


            if pending_event is None:


                try:

                    pending_event = next(
                        mbo_iterator
                    )


                except StopIteration:


                    pending_event = None

                    break


            # =================================================
            # Future MBO Event
            # =================================================

            if (
                pending_event.ts_recv
                >
                checkpoint_ts
            ):


                break


            # =================================================
            # Apply Production Event
            # =================================================

            builder.on_event(
                pending_event
            )


            mbo_event_count += 1


            # =================================================
            # Track final MBO record belonging to
            # exact same ts_recv group.
            # =================================================

            if (
                pending_event.ts_recv
                ==
                checkpoint_ts
            ):


                last_mbo_event_at_checkpoint = (
                    pending_event
                )


            pending_event = None


        # ====================================================
        # Rule 1
        #
        # Official group final record must be F_LAST.
        # ====================================================

        if not has_last_flag(
            checkpoint[
                "flags"
            ]
        ):


            skipped_official_not_last += 1

            continue


        # ====================================================
        # Rule 2
        #
        # MBO must actually contain exact same ts_recv.
        # ====================================================

        if (
            last_mbo_event_at_checkpoint
            is None
        ):


            skipped_no_exact_mbo_group += 1

            continue


        # ====================================================
        # Rule 3
        #
        # Final MBO record of this ts_recv group
        # must also carry F_LAST.
        # ====================================================

        if not has_last_flag(
            last_mbo_event_at_checkpoint.flags
        ):


            skipped_mbo_not_last += 1

            continue


        # ====================================================
        # Stable Market Event Boundary
        #
        # NOW comparison is valid.
        # ====================================================


        book = (
            builder.get_book()
        )


        assert (
            len(
                book.bids
            )
            >=
            DEPTH
        )


        assert (
            len(
                book.asks
            )
            >=
            DEPTH
        )


        ours = (
            extract_our_top10(
                book
            )
        )


        official = (
            checkpoint[
                "top10"
            ]
        )


        # ====================================================
        # BID
        # ====================================================

        comparison_count += (
            compare_side(

                compared_checkpoint_count,

                checkpoint_ts,

                checkpoint_sequence,

                "BID",

                ours[
                    "bids"
                ],

                official[
                    "bids"
                ],

            )
        )


        # ====================================================
        # ASK
        # ====================================================

        comparison_count += (
            compare_side(

                compared_checkpoint_count,

                checkpoint_ts,

                checkpoint_sequence,

                "ASK",

                ours[
                    "asks"
                ],

                official[
                    "asks"
                ],

            )
        )


        # ====================================================
        # Passed Checkpoint
        # ====================================================

        if first_compared_ts is None:


            first_compared_ts = (
                checkpoint_ts
            )


        last_compared_ts = (
            checkpoint_ts
        )


        compared_checkpoint_count += 1


        # ====================================================
        # Progress
        # ====================================================

        if (
            compared_checkpoint_count
            %
            10_000
            ==
            0
        ):


            print()

            print(
                "-" * 100
            )


            print(
                "F_LAST Dense checkpoints:",
                compared_checkpoint_count
            )


            print(
                "Official groups scanned:",
                official_group_count
            )


            print(
                "Current ts_recv:",
                checkpoint_ts
            )


            print(
                "Current sequence:",
                checkpoint_sequence
            )


            print(
                "MBO events processed:",
                mbo_event_count
            )


            print(
                "Strict comparisons:",
                comparison_count
            )


            print(
                "Skipped official !LAST:",
                skipped_official_not_last
            )


            print(
                "Skipped MBO !LAST:",
                skipped_mbo_not_last
            )


            print(
                "Skipped no exact MBO:",
                skipped_no_exact_mbo_group
            )


            print(
                "Active orders:",
                len(
                    book.orders
                )
            )


            print(
                "Best bid:",
                book.best_bid()
            )


            print(
                "Best ask:",
                book.best_ask()
            )


    # ========================================================
    # Validation
    # ========================================================

    assert (
        official_group_count
        >
        0
    )


    assert (
        compared_checkpoint_count
        >
        0
    )


    # ========================================================
    # Every compared checkpoint:
    #
    # 10 depth
    # ×
    # 2 sides
    # ×
    # 3 fields
    #
    # = 60
    # ========================================================

    expected_comparisons = (

        compared_checkpoint_count

        *

        DEPTH

        *

        2

        *

        3

    )


    assert (
        comparison_count
        ==
        expected_comparisons
    )


    # ========================================================
    # Final Book
    # ========================================================

    book = (
        builder.get_book()
    )


    # ========================================================
    # Summary
    # ========================================================

    print()

    print(
        "=" * 100
    )

    print(
        "F_LAST DENSE-WINDOW OFFICIAL GROUND TRUTH PASSED"
    )

    print(
        "=" * 100
    )


    print(
        "window:",
        WINDOW_START.isoformat(),
        "->",
        WINDOW_END.isoformat(),
    )


    print()

    print(
        "official ts_recv groups:",
        official_group_count
    )


    print(
        "valid F_LAST checkpoints:",
        compared_checkpoint_count
    )


    print()

    print(
        "skipped official final !F_LAST:",
        skipped_official_not_last
    )


    print(
        "skipped MBO final !F_LAST:",
        skipped_mbo_not_last
    )


    print(
        "skipped no exact MBO group:",
        skipped_no_exact_mbo_group
    )


    print()

    print(
        "first compared ts_recv:",
        first_compared_ts
    )


    print(
        "last compared ts_recv:",
        last_compared_ts
    )


    print()

    print(
        "strict comparisons:",
        comparison_count
    )


    print(
        "comparisons/checkpoint:",
        (
            DEPTH
            *
            2
            *
            3
        )
    )


    print()

    print(
        "MBO events processed:",
        mbo_event_count
    )


    print(
        "official instrument_id:",
        official_instrument_id
    )


    print()

    print(
        "final active orders:",
        len(
            book.orders
        )
    )


    print(
        "final bid levels:",
        len(
            book.bids
        )
    )


    print(
        "final ask levels:",
        len(
            book.asks
        )
    )


    print(
        "final best bid:",
        book.best_bid()
    )


    print(
        "final best ask:",
        book.best_ask()
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