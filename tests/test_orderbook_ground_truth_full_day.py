"""
tests/test_orderbook_ground_truth_full_day.py


============================================================
OrderBook Full-Day Official Ground Truth Test
============================================================


目的：

把已经通过的：

    Snapshot Ground Truth
    Multi-Checkpoint Ground Truth

进一步升级为：

    Full-Day Ground Truth


验证完整：

    2026-06-15

期间我们的：

    Databento MBO
        |
        v
    DatabentoFeed
        |
        v
    OrderBookBuilder
        |
        v
    L3 OrderBook

聚合得到的：

    Top 10 Bid
    Top 10 Ask

是否持续与：

    Databento 官方 MBP-10

一致。


============================================================


比较内容：

每一个 checkpoint：

Bid 0 ~ 9：

    price
    size
    order count


Ask 0 ~ 9：

    price
    size
    order count


也就是说：

每 checkpoint 共严格验证：

    10 Bid prices
    10 Bid sizes
    10 Bid counts

    10 Ask prices
    10 Ask sizes
    10 Ask counts


总计：

    60 个字段 / checkpoint


============================================================


Checkpoint 设计：

默认：

    100 个 checkpoint


不是按：

    record index

而是按照：

    MBP-10 整个文件 ts_recv 时间范围

均匀采样。


对于每个目标时间：

    找到第一个：

        ts_recv >= target_time

    的 MBP-10 ts_recv group。


然后使用：

    该 ts_recv group 的最后一条 MBP-10 record


作为官方最终状态。


============================================================


重要：

为什么必须使用：

    ts_recv group 的最后一条 record？


因为同一个：

    ts_recv

可能包含多条状态更新。


我们的 MBO Replay 在 checkpoint 时会处理：

    所有 event.ts_recv <= checkpoint_ts_recv


因此官方侧也必须使用：

    该 ts_recv group 最后的状态。


否则可能出现：

    MBO 已经处理完整 group

但：

    MBP-10 仍然是 group 中间状态


从而制造假的 mismatch。


============================================================


Replay原则：

MBO 只连续读取一次。


不是：

    checkpoint 1
        从头 Replay

    checkpoint 2
        再从头 Replay


而是：

    Snapshot
        |
        v
    checkpoint 1
        |
        v
    继续 Replay
        |
        v
    checkpoint 2
        |
        v
    继续 Replay
        |
        v
    ...
        |
        v
    Full Day


这样真正验证：

    长时间连续状态是否漂移。


============================================================
"""


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
# Configuration
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
# Full-Day checkpoint数量
#
# 100：
#
#     已经足够覆盖整天大量不同市场状态。
#
# 后面如果需要更强验证，
# 可以改成：
#
#     250
#     500
#     1000
#
# ============================================================


CHECKPOINT_COUNT = 100



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
# Extract Official Top 10
# ============================================================


def extract_official_top10(
    record
):
    """
    从官方 MBP-10 record 提取：

        Bid Top 10
        Ask Top 10
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
    从我们的 L3 OrderBook 聚合前10档。


    Bid：

        price 高 -> 低


    Ask：

        price 低 -> 高
    """


    # ========================================================
    # Bid
    # ========================================================

    bid_prices = sorted(

        book.bids.keys(),

        reverse=True,

    )[
        :DEPTH
    ]


    # ========================================================
    # Ask
    # ========================================================

    ask_prices = sorted(

        book.asks.keys()

    )[
        :DEPTH
    ]


    bids = []

    asks = []


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
# Discover MBP-10 Time Range
# ============================================================


def discover_mbp10_time_range():
    """
    扫描官方 MBP-10：

    获取：

        first ts_recv
        last ts_recv


    注意：

    这里只读取官方数据。

    不涉及我们的 OrderBook。
    """


    store = db.DBNStore.from_file(
        MBP10_FILE
    )


    first_ts_recv = None

    last_ts_recv = None

    record_count = 0


    for record in store:


        ts_recv = get_attr(
            record,
            "ts_recv",
        )


        if ts_recv is None:

            continue


        if first_ts_recv is None:

            first_ts_recv = (
                ts_recv
            )


        last_ts_recv = (
            ts_recv
        )


        record_count += 1


    if first_ts_recv is None:

        raise RuntimeError(
            "MBP-10 contains no valid records."
        )


    return {

        "first_ts_recv":
            first_ts_recv,

        "last_ts_recv":
            last_ts_recv,

        "record_count":
            record_count,

    }



# ============================================================
# Generate Target Times
# ============================================================


def generate_target_times(
    first_ts_recv,
    last_ts_recv,
):
    """
    在整个 MBP-10 时间范围中：

    均匀生成 CHECKPOINT_COUNT 个目标时间。


    第一 checkpoint：

        first_ts_recv


    最后一 checkpoint：

        last_ts_recv
    """


    if CHECKPOINT_COUNT <= 1:

        return [
            first_ts_recv
        ]


    total_range = (
        last_ts_recv
        -
        first_ts_recv
    )


    targets = []


    for index in range(
        CHECKPOINT_COUNT
    ):


        ratio = (
            index
            /
            (
                CHECKPOINT_COUNT
                -
                1
            )
        )


        target = (

            first_ts_recv

            +

            int(
                total_range
                *
                ratio
            )

        )


        targets.append(
            target
        )


    return targets



# ============================================================
# Load Official Full-Day Checkpoints
# ============================================================


def load_official_full_day_checkpoints():
    """
    根据整天时间范围选择官方 checkpoint。


    规则：

    对每个 target_time：

        找到第一个：

            ts_recv >= target_time

        的 ts_recv group。


    然后取：

        该 group 最后一条 MBP-10 record。


    ========================================================

    为避免加载所有 MBP-10 到内存：

    使用流式扫描。

    ========================================================
    """


    time_range = (
        discover_mbp10_time_range()
    )


    first_ts_recv = (
        time_range[
            "first_ts_recv"
        ]
    )


    last_ts_recv = (
        time_range[
            "last_ts_recv"
        ]
    )


    targets = generate_target_times(

        first_ts_recv,

        last_ts_recv,

    )


    store = db.DBNStore.from_file(
        MBP10_FILE
    )


    checkpoints = []


    target_index = 0


    current_ts_recv = None

    current_last_record = None


    # ========================================================
    # Finalize one ts_recv group
    # ========================================================

    def finalize_group(
        group_ts_recv,
        record,
    ):
        """
        如果当前 group 已经覆盖一个或多个 target，
        则使用该 group 最后的 record
        作为官方 checkpoint。
        """


        nonlocal target_index


        if record is None:

            return


        while (
            target_index
            <
            len(targets)
        ):


            target_time = (
                targets[
                    target_index
                ]
            )


            if (
                group_ts_recv
                <
                target_time
            ):

                break


            checkpoints.append(
                {
                    "checkpoint_index":
                        target_index,

                    "target_ts_recv":
                        target_time,

                    "ts_recv":
                        group_ts_recv,

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

                    "instrument_id":
                        get_attr(
                            record,
                            "instrument_id",
                        ),

                    "record":
                        record,

                    "top10":
                        extract_official_top10(
                            record
                        ),
                }
            )


            target_index += 1


    # ========================================================
    # Stream Official MBP-10
    # ========================================================

    for record in store:


        ts_recv = get_attr(
            record,
            "ts_recv",
        )


        if ts_recv is None:

            continue


        # ====================================================
        # First Record
        # ====================================================

        if current_ts_recv is None:


            current_ts_recv = (
                ts_recv
            )


            current_last_record = (
                record
            )


            continue


        # ====================================================
        # Same ts_recv Group
        # ====================================================

        if (
            ts_recv
            ==
            current_ts_recv
        ):


            current_last_record = (
                record
            )


            continue


        # ====================================================
        # Previous Group Ends
        # ====================================================

        finalize_group(

            current_ts_recv,

            current_last_record,

        )


        # ====================================================
        # 所有 checkpoint 已找到
        # ====================================================

        if (
            target_index
            >=
            len(targets)
        ):

            break


        # ====================================================
        # Start New Group
        # ====================================================

        current_ts_recv = (
            ts_recv
        )


        current_last_record = (
            record
        )


    else:

        # ====================================================
        # 文件自然结束
        # ====================================================

        if (
            current_ts_recv
            is not None
        ):


            finalize_group(

                current_ts_recv,

                current_last_record,

            )


    # ========================================================
    # 最后一 target 可能正好等于最后 group。
    #
    # 如果因为浮点分配 / group边界导致少一个，
    # 最后的官方 group补齐。
    # ========================================================

    if (
        target_index
        <
        len(targets)
        and
        current_last_record
        is not None
    ):


        while (
            target_index
            <
            len(targets)
        ):


            checkpoints.append(
                {
                    "checkpoint_index":
                        target_index,

                    "target_ts_recv":
                        targets[
                            target_index
                        ],

                    "ts_recv":
                        current_ts_recv,

                    "ts_event":
                        get_attr(
                            current_last_record,
                            "ts_event",
                        ),

                    "sequence":
                        get_attr(
                            current_last_record,
                            "sequence",
                        ),

                    "instrument_id":
                        get_attr(
                            current_last_record,
                            "instrument_id",
                        ),

                    "record":
                        current_last_record,

                    "top10":
                        extract_official_top10(
                            current_last_record
                        ),
                }
            )


            target_index += 1


    return {

        "time_range":
            time_range,

        "targets":
            targets,

        "checkpoints":
            checkpoints,

    }



# ============================================================
# Strict Side Comparison
# ============================================================


def assert_side_matches(
    checkpoint_index,
    checkpoint_ts_recv,
    side_name,
    ours,
    official,
):
    """
    严格检查 Bid / Ask Top10。
    """


    assert (
        len(ours)
        >=
        DEPTH
    ), (
        f"Checkpoint={checkpoint_index} "
        f"ts_recv={checkpoint_ts_recv} "
        f"{side_name}: "
        f"our book only has "
        f"{len(ours)} levels"
    )


    assert (
        len(official)
        >=
        DEPTH
    )


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
            f"\n"
            f"FULL-DAY GROUND TRUTH FAILURE\n"
            f"checkpoint={checkpoint_index}\n"
            f"ts_recv={checkpoint_ts_recv}\n"
            f"side={side_name}\n"
            f"depth={depth}\n"
            f"field=PRICE\n"
            f"ours={our_level['price']}\n"
            f"official={official_level['price']}"
        )


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
            f"\n"
            f"FULL-DAY GROUND TRUTH FAILURE\n"
            f"checkpoint={checkpoint_index}\n"
            f"ts_recv={checkpoint_ts_recv}\n"
            f"side={side_name}\n"
            f"depth={depth}\n"
            f"field=SIZE\n"
            f"price={our_level['price']}\n"
            f"ours={our_level['size']}\n"
            f"official={official_level['size']}"
        )


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
            f"\n"
            f"FULL-DAY GROUND TRUTH FAILURE\n"
            f"checkpoint={checkpoint_index}\n"
            f"ts_recv={checkpoint_ts_recv}\n"
            f"side={side_name}\n"
            f"depth={depth}\n"
            f"field=COUNT\n"
            f"price={our_level['price']}\n"
            f"ours={our_level['count']}\n"
            f"official={official_level['count']}"
        )



# ============================================================
# Print Checkpoint
# ============================================================


def print_checkpoint(
    checkpoint,
    book,
    ours,
    official,
    mbo_events,
):
    """
    打印 checkpoint 摘要。

    为避免 100 checkpoint 输出过大，
    这里只打印：

        checkpoint
        ts_recv
        MBO events
        orders
        BBO
    """


    index = (
        checkpoint[
            "checkpoint_index"
        ]
    )


    print()


    print(
        "-" * 100
    )


    print(
        "FULL-DAY CHECKPOINT:",
        index,
        "/",
        CHECKPOINT_COUNT - 1,
    )


    print(
        "target ts_recv:",
        checkpoint[
            "target_ts_recv"
        ]
    )


    print(
        "actual ts_recv:",
        checkpoint[
            "ts_recv"
        ]
    )


    print(
        "sequence:",
        checkpoint[
            "sequence"
        ]
    )


    print(
        "MBO events:",
        mbo_events
    )


    print(
        "orders:",
        len(
            book.orders
        )
    )


    print(
        "levels:",
        "bid=",
        len(
            book.bids
        ),
        "ask=",
        len(
            book.asks
        ),
    )


    print(
        "BID:",
        "ours=",
        ours[
            "bids"
        ][0],
        "official=",
        official[
            "bids"
        ][0],
    )


    print(
        "ASK:",
        "ours=",
        ours[
            "asks"
        ][0],
        "official=",
        official[
            "asks"
        ][0],
    )



# ============================================================
# Test 1
# Files
# ============================================================


def test_full_day_ground_truth_files_exist():
    """
    两个输入文件必须存在。
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
# Full-Day Official Checkpoint Discovery
# ============================================================


def test_full_day_checkpoint_discovery():
    """
    验证：

        MBP-10 时间范围

以及：

        100 个 checkpoint

是否都能正确生成。
    """


    result = (
        load_official_full_day_checkpoints()
    )


    time_range = (
        result[
            "time_range"
        ]
    )


    checkpoints = (
        result[
            "checkpoints"
        ]
    )


    print()

    print(
        "=" * 100
    )

    print(
        "FULL-DAY OFFICIAL CHECKPOINT DISCOVERY"
    )

    print(
        "=" * 100
    )


    print(
        "MBP10 first ts_recv:",
        time_range[
            "first_ts_recv"
        ]
    )


    print(
        "MBP10 last ts_recv:",
        time_range[
            "last_ts_recv"
        ]
    )


    print(
        "MBP10 records:",
        time_range[
            "record_count"
        ]
    )


    print(
        "requested checkpoints:",
        CHECKPOINT_COUNT
    )


    print(
        "collected checkpoints:",
        len(
            checkpoints
        )
    )


    assert (
        len(checkpoints)
        ==
        CHECKPOINT_COUNT
    )


    # ========================================================
    # 时间必须单调
    # ========================================================

    previous = None


    for checkpoint in checkpoints:


        current = (
            checkpoint[
                "ts_recv"
            ]
        )


        if previous is not None:


            assert (
                current
                >=
                previous
            )


        previous = current



# ============================================================
# Test 3
# Full-Day Official Ground Truth
# ============================================================


def test_orderbook_full_day_ground_truth():
    """
    全天官方 Ground Truth 核心测试。


    MBO 从头 Replay 一次。


    每到一个官方 checkpoint：

        1.
        Replay 所有：

            event.ts_recv <= checkpoint.ts_recv


        2.
        从我们的 L3 OrderBook 聚合 Top10


        3.
        对比官方 MBP-10


        4.
        Bid / Ask：

            price
            size
            count

        必须全部完全一致。
    """


    official_result = (
        load_official_full_day_checkpoints()
    )


    checkpoints = (
        official_result[
            "checkpoints"
        ]
    )


    assert (
        len(checkpoints)
        ==
        CHECKPOINT_COUNT
    )


    # ========================================================
    # Instrument
    # ========================================================

    official_instrument = (
        checkpoints[
            0
        ][
            "instrument_id"
        ]
    )


    assert (
        official_instrument
        is not None
    )


    for checkpoint in checkpoints:


        assert (
            checkpoint[
                "instrument_id"
            ]
            ==
            official_instrument
        )


    # ========================================================
    # MBO Feed
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


    iterator = iter(
        feed
    )


    pending_event = None


    mbo_events = 0

    passed_checkpoints = 0


    # ========================================================
    # Continuous Replay
    # ========================================================

    for checkpoint in checkpoints:


        target_ts_recv = (
            checkpoint[
                "ts_recv"
            ]
        )


        # ====================================================
        # Replay到当前官方checkpoint
        # ====================================================

        while True:


            if (
                pending_event
                is None
            ):


                try:

                    pending_event = next(
                        iterator
                    )

                except StopIteration:

                    pending_event = None

                    break


            # =================================================
            # 下一条Event已经超过checkpoint
            # =================================================

            if (
                pending_event.ts_recv
                >
                target_ts_recv
            ):


                break


            # =================================================
            # 应用MBO Event
            # =================================================

            builder.on_event(
                pending_event
            )


            mbo_events += 1


            pending_event = None


        # ====================================================
        # Current Book
        # ====================================================

        book = (
            builder.get_book()
        )


        # ====================================================
        # 必须至少存在10档
        # ====================================================

        assert (
            len(book.bids)
            >=
            DEPTH
        )


        assert (
            len(book.asks)
            >=
            DEPTH
        )


        # ====================================================
        # Extract
        # ====================================================

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
        # Print
        # ====================================================

        print_checkpoint(

            checkpoint,

            book,

            ours,

            official,

            mbo_events,

        )


        # ====================================================
        # BID
        # ====================================================

        assert_side_matches(

            checkpoint[
                "checkpoint_index"
            ],

            checkpoint[
                "ts_recv"
            ],

            "BID",

            ours[
                "bids"
            ],

            official[
                "bids"
            ],

        )


        # ====================================================
        # ASK
        # ====================================================

        assert_side_matches(

            checkpoint[
                "checkpoint_index"
            ],

            checkpoint[
                "ts_recv"
            ],

            "ASK",

            ours[
                "asks"
            ],

            official[
                "asks"
            ],

        )


        passed_checkpoints += 1


    # ========================================================
    # Final Summary
    # ========================================================

    print()

    print(
        "=" * 100
    )

    print(
        "FULL-DAY OFFICIAL GROUND TRUTH PASSED"
    )

    print(
        "=" * 100
    )


    print(
        "checkpoints:",
        passed_checkpoints
    )


    print(
        "depth per side:",
        DEPTH
    )


    print(
        "fields per level:",
        3
    )


    print(
        "comparisons per checkpoint:",
        (
            DEPTH
            *
            2
            *
            3
        )
    )


    print(
        "total strict comparisons:",
        (
            passed_checkpoints
            *
            DEPTH
            *
            2
            *
            3
        )
    )


    print(
        "MBO events processed:",
        mbo_events
    )


    print(
        "final active orders:",
        len(
            builder.get_book().orders
        )
    )


    print(
        "final bid levels:",
        len(
            builder.get_book().bids
        )
    )


    print(
        "final ask levels:",
        len(
            builder.get_book().asks
        )
    )


    # ========================================================
    # 必须全部checkpoint通过
    # ========================================================

    assert (
        passed_checkpoints
        ==
        CHECKPOINT_COUNT
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