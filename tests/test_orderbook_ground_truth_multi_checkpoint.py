"""
tests/test_orderbook_ground_truth_multi_checkpoint.py


============================================================
OrderBook Official MBP-10 Multi-Checkpoint Ground Truth
============================================================


目的：

把之前已经通过的：

    单一 Snapshot Ground Truth

升级为：

    多时间点 Ground Truth


验证：

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
          |
          v
    聚合 Top 10
          |
          v
    Databento 官方 MBP-10


============================================================


每个 checkpoint 比较：


Bid 0 ~ 9：

    price
    size
    order count


Ask 0 ~ 9：

    price
    size
    order count


============================================================


重要：

MBP-10 与 MBO：

    记录数量不相同。


因此不能：

    MBO 第 N 条
        VS
    MBP10 第 N 条


本测试使用：

    ts_recv


并且只选择：

    一个 ts_recv 时间组中的最后一条 MBP-10 record。


原因：

一个 ts_recv 时间点可能包含多个行情更新。


如果比较：

    ts_recv 相同时间组中间状态

可能造成：

    MBO 已经处理完整时间组

但：

    MBP-10 record 还是中间状态。


所以：

    官方 checkpoint

必须取：

    每个 ts_recv group 的最后状态。


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
# MBP-10 ts_recv Group Checkpoints
#
# 这里不是原始 record index。
#
# 而是：
#
#     不同 ts_recv group 的序号。
#
# 逐渐扩大距离，
# 检查 Replay 推进后的稳定性。
# ============================================================


CHECKPOINT_GROUPS = [

    0,

    100,

    500,

    1_000,

    2_500,

    5_000,

    10_000,

    25_000,

    50_000,

    100_000,

]



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
    提取 Databento 官方 MBP-10。
    """


    bids = []

    asks = []


    for depth in range(
        DEPTH
    ):


        suffix = (
            f"{depth:02d}"
        )


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
    """


    bid_prices = sorted(

        book.bids.keys(),

        reverse=True,

    )[
        :DEPTH
    ]


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
# Load Official Checkpoints
# ============================================================


def load_official_checkpoints():
    """
    从 MBP-10 中选择多个 checkpoint。


    核心规则：

    每个 checkpoint 必须是：

        某一个 ts_recv group

    的：

        最后一条 MBP-10 record。


    返回：

        [
            {
                group_index,
                ts_recv,
                sequence,
                record,
                top10
            }
        ]
    """


    wanted = set(
        CHECKPOINT_GROUPS
    )


    max_group = max(
        CHECKPOINT_GROUPS
    )


    store = db.DBNStore.from_file(
        MBP10_FILE
    )


    checkpoints = []


    current_ts_recv = None

    current_last_record = None

    group_index = -1


    # ========================================================
    # 内部函数：
    #
    # 一个 ts_recv group 结束时，
    # 判断是否需要保存。
    # ========================================================

    def finalize_group(
        index,
        record
    ):


        if record is None:

            return


        if index not in wanted:

            return


        checkpoints.append(
            {
                "group_index":
                    index,

                "ts_recv":
                    get_attr(
                        record,
                        "ts_recv",
                    ),

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


    # ========================================================
    # Stream MBP-10
    # ========================================================

    for record in store:


        ts_recv = get_attr(
            record,
            "ts_recv",
        )


        # ====================================================
        # First Record
        # ====================================================

        if current_ts_recv is None:


            current_ts_recv = ts_recv

            current_last_record = record

            group_index = 0

            continue


        # ====================================================
        # Same ts_recv Group
        # ====================================================

        if ts_recv == current_ts_recv:


            current_last_record = record

            continue


        # ====================================================
        # Previous Group Finished
        # ====================================================

        finalize_group(

            group_index,

            current_last_record,

        )


        # ====================================================
        # 如果已经超过最后目标
        # 就不需要继续扫描整个 214MB 文件。
        # ====================================================

        if group_index >= max_group:

            break


        # ====================================================
        # Start New Group
        # ====================================================

        group_index += 1

        current_ts_recv = ts_recv

        current_last_record = record


    else:

        # ====================================================
        # 文件自然结束时保存最后一个 group。
        # ====================================================

        finalize_group(

            group_index,

            current_last_record,

        )


    return checkpoints



# ============================================================
# Assert One Side
# ============================================================


def assert_side_matches(
    checkpoint_index,
    side_name,
    ours,
    official,
):
    """
    严格检查一侧 Top 10。
    """


    assert (
        len(ours)
        >=
        DEPTH
    ), (
        f"Checkpoint {checkpoint_index} "
        f"{side_name}: "
        f"our book only contains "
        f"{len(ours)} levels."
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
            f"Checkpoint {checkpoint_index} "
            f"{side_name} depth={depth} "
            f"PRICE mismatch | "
            f"ours={our_level['price']} "
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
            f"Checkpoint {checkpoint_index} "
            f"{side_name} depth={depth} "
            f"SIZE mismatch | "
            f"price={our_level['price']} "
            f"ours={our_level['size']} "
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
            f"Checkpoint {checkpoint_index} "
            f"{side_name} depth={depth} "
            f"COUNT mismatch | "
            f"price={our_level['price']} "
            f"ours={our_level['count']} "
            f"official={official_level['count']}"
        )



# ============================================================
# Print Top Level Summary
# ============================================================


def print_checkpoint_summary(
    checkpoint,
    book,
    ours,
    official,
    mbo_events,
):
    """
    每个 checkpoint 打印简洁摘要。
    """


    print()

    print(
        "=" * 100
    )


    print(
        f"GROUND TRUTH CHECKPOINT "
        f"{checkpoint['group_index']}"
    )


    print(
        "=" * 100
    )


    print(
        "ts_recv:",
        checkpoint["ts_recv"]
    )


    print(
        "ts_event:",
        checkpoint["ts_event"]
    )


    print(
        "sequence:",
        checkpoint["sequence"]
    )


    print(
        "MBO processed:",
        mbo_events
    )


    print(
        "active orders:",
        len(book.orders)
    )


    print(
        "bid levels:",
        len(book.bids)
    )


    print(
        "ask levels:",
        len(book.asks)
    )


    print()


    print(
        "Best Bid:"
    )


    print(
        "    ours    :",
        ours["bids"][0]["price"],
        "size=",
        ours["bids"][0]["size"],
        "count=",
        ours["bids"][0]["count"],
    )


    print(
        "    official:",
        official["bids"][0]["price"],
        "size=",
        official["bids"][0]["size"],
        "count=",
        official["bids"][0]["count"],
    )


    print()


    print(
        "Best Ask:"
    )


    print(
        "    ours    :",
        ours["asks"][0]["price"],
        "size=",
        ours["asks"][0]["size"],
        "count=",
        ours["asks"][0]["count"],
    )


    print(
        "    official:",
        official["asks"][0]["price"],
        "size=",
        official["asks"][0]["size"],
        "count=",
        official["asks"][0]["count"],
    )



# ============================================================
# Test Files
# ============================================================


def test_multi_checkpoint_files_exist():
    """
    Ground Truth 文件必须存在。
    """


    assert MBO_FILE.exists(), (
        f"MBO file missing: {MBO_FILE}"
    )


    assert MBP10_FILE.exists(), (
        f"MBP10 file missing: {MBP10_FILE}"
    )



# ============================================================
# Test Official Checkpoint Collection
# ============================================================


def test_official_checkpoint_collection():
    """
    确认可以从官方 MBP-10
    收集到所有目标 checkpoint。
    """


    checkpoints = (
        load_official_checkpoints()
    )


    print()

    print(
        "=" * 100
    )

    print(
        "OFFICIAL CHECKPOINTS"
    )

    print(
        "=" * 100
    )


    for checkpoint in checkpoints:


        print(

            "group=",
            checkpoint[
                "group_index"
            ],

            "ts_recv=",
            checkpoint[
                "ts_recv"
            ],

            "sequence=",
            checkpoint[
                "sequence"
            ],

        )


    assert (
        len(checkpoints)
        ==
        len(CHECKPOINT_GROUPS)
    ), (
        f"Expected {len(CHECKPOINT_GROUPS)} "
        f"checkpoints, "
        f"got {len(checkpoints)}"
    )



# ============================================================
# Main Multi-Checkpoint Ground Truth
# ============================================================


def test_orderbook_multi_checkpoint_ground_truth():
    """
    核心测试。


    一次性顺序 Replay MBO。

    不为每个 checkpoint 从头重新 Replay。


    即：

        Snapshot
           |
           v
        checkpoint 0
           |
           v
        继续 Replay
           |
           v
        checkpoint 100
           |
           v
        继续 Replay
           |
           v
        ...


    这样同时验证：

        Replay 连续状态

    而不是：

        每个 checkpoint 独立重建。
    """


    checkpoints = (
        load_official_checkpoints()
    )


    assert (
        len(checkpoints)
        ==
        len(CHECKPOINT_GROUPS)
    )


    # ========================================================
    # 官方 instrument 必须一致
    # ========================================================

    official_instrument = (
        checkpoints[0][
            "instrument_id"
        ]
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


    checkpoint_index = 0

    mbo_events = 0


    # ========================================================
    # 我们需要“看一条未来 Event”
    #
    # 因此手动使用 iterator。
    # ========================================================

    iterator = iter(
        feed
    )


    pending_event = None


    # ========================================================
    # 对每个官方 checkpoint
    # ========================================================

    for checkpoint in checkpoints:


        target_ts_recv = (
            checkpoint[
                "ts_recv"
            ]
        )


        # ====================================================
        # Replay 所有：
        #
        #     event.ts_recv <= target_ts_recv
        #
        # 的 MBO。
        # ====================================================

        while True:


            if pending_event is None:


                try:

                    pending_event = next(
                        iterator
                    )

                except StopIteration:

                    break


            # =================================================
            # 未来Event
            #
            # 留给下一个 checkpoint。
            # =================================================

            if (
                pending_event.ts_recv
                >
                target_ts_recv
            ):


                break


            # =================================================
            # 当前 checkpoint 范围内
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
        # Instrument
        # ====================================================

        assert (
            official_instrument
            is not None
        )


        # ====================================================
        # Extract Our / Official
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
        # Diagnostic
        # ====================================================

        print_checkpoint_summary(

            checkpoint,

            book,

            ours,

            official,

            mbo_events,

        )


        # ====================================================
        # Strict Comparison
        # ====================================================

        assert_side_matches(

            checkpoint[
                "group_index"
            ],

            "BID",

            ours[
                "bids"
            ],

            official[
                "bids"
            ],

        )


        assert_side_matches(

            checkpoint[
                "group_index"
            ],

            "ASK",

            ours[
                "asks"
            ],

            official[
                "asks"
            ],

        )


        checkpoint_index += 1


    # ========================================================
    # 所有 checkpoint 都必须完成
    # ========================================================

    assert (
        checkpoint_index
        ==
        len(checkpoints)
    )


    print()

    print(
        "=" * 100
    )

    print(
        "MULTI-CHECKPOINT OFFICIAL GROUND TRUTH PASSED"
    )

    print(
        "=" * 100
    )


    print(
        "checkpoints:",
        checkpoint_index
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