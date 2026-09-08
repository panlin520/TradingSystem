"""
tests/test_ground_truth_alignment.py


============================================================
Ground Truth Alignment Diagnostic
============================================================


目的：

    对齐：

        ESU6 MBO

    和：

        Databento 官方 MBP-10


本测试暂时不判断：

    OrderBook 是否正确。


只负责确认：

    1. 两个文件是否能够正常读取

    2. 两边数据起点

    3. ts_recv

    4. ts_event

    5. sequence

    6. flags

    7. instrument_id

    8. MBO action / side

    9. MBP-10 官方 BBO


============================================================


重要：

不能使用：

    第 N 条 MBO

直接对应：

    第 N 条 MBP-10


必须通过时间轴对齐。


第一阶段主要观察：

    ts_recv


辅助观察：

    ts_event
    sequence
    flags
    instrument_id


============================================================
"""


from pathlib import Path

import pytest
import databento as db


from data.databento_feed import DatabentoFeed



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


# 打印前多少条记录
PRINT_LIMIT = 20



# ============================================================
# Formatting
# ============================================================


def format_ns_timestamp(
    value
):
    """
    把纳秒 Unix timestamp 转成便于观察的字符串。

    如果转换失败，保留原值。
    """

    if value is None:

        return None


    try:

        import pandas as pd

        return str(
            pd.Timestamp(
                value,
                unit="ns",
                tz="UTC",
            )
        )

    except Exception:

        return str(
            value
        )



# ============================================================
# Safe attribute helper
# ============================================================


def get_attr(
    obj,
    name,
    default=None,
):
    """
    安全读取 Databento record 属性。

    诊断程序不能因为某个 schema
    缺一个非核心字段直接中断。
    """

    try:

        return getattr(
            obj,
            name
        )

    except Exception:

        return default



# ============================================================
# Print divider
# ============================================================


def print_divider(
    title
):
    """
    打印测试区块。
    """

    print()

    print(
        "=" * 100
    )

    print(
        title
    )

    print(
        "=" * 100
    )



# ============================================================
# MBO Diagnostic
# ============================================================


def read_mbo_head(
    limit
):
    """
    使用当前工程真实 DatabentoFeed
    读取 MBO 前 limit 条 MarketEvent。
    """

    feed = DatabentoFeed(

        file_path=str(
            MBO_FILE
        ),

        symbol=SYMBOL,

    )


    rows = []


    for index, event in enumerate(
        feed
    ):

        rows.append(
            {
                "index":
                    index,

                "ts_recv":
                    event.ts_recv,

                "ts_recv_text":
                    format_ns_timestamp(
                        event.ts_recv
                    ),

                "ts_event":
                    event.ts_event,

                "ts_event_text":
                    format_ns_timestamp(
                        event.ts_event
                    ),

                "sequence":
                    event.sequence,

                "action":
                    (
                        event.action.value
                        if event.action is not None
                        else None
                    ),

                "side":
                    (
                        event.side.value
                        if event.side is not None
                        else None
                    ),

                "order_id":
                    event.order_id,

                "price":
                    event.price,

                "size":
                    event.size,

                "flags":
                    event.flags,

                "instrument_id":
                    event.instrument_id,

                "channel_id":
                    event.channel_id,

                "publisher_id":
                    event.publisher_id,
            }
        )


        if len(rows) >= limit:

            break


    return rows



# ============================================================
# MBP-10 Diagnostic
# ============================================================


def read_mbp10_head(
    limit
):
    """
    直接读取 Databento 官方 MBP-10。

    不经过：

        DatabentoFeed
        OrderBookBuilder
        OrderBook

    保持 Ground Truth 数据独立。
    """

    store = db.DBNStore.from_file(
        MBP10_FILE
    )


    rows = []


    for index, record in enumerate(
        store
    ):

        rows.append(
            {
                "index":
                    index,

                "ts_recv":
                    get_attr(
                        record,
                        "ts_recv",
                    ),

                "ts_recv_text":
                    format_ns_timestamp(
                        get_attr(
                            record,
                            "ts_recv",
                        )
                    ),

                "ts_event":
                    get_attr(
                        record,
                        "ts_event",
                    ),

                "ts_event_text":
                    format_ns_timestamp(
                        get_attr(
                            record,
                            "ts_event",
                        )
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

                "side":
                    get_attr(
                        record,
                        "side",
                    ),

                "depth":
                    get_attr(
                        record,
                        "depth",
                    ),

                "price":
                    get_attr(
                        record,
                        "price",
                    ),

                "size":
                    get_attr(
                        record,
                        "size",
                    ),

                "flags":
                    get_attr(
                        record,
                        "flags",
                    ),

                "instrument_id":
                    get_attr(
                        record,
                        "instrument_id",
                    ),

                "publisher_id":
                    get_attr(
                        record,
                        "publisher_id",
                    ),

                # ============================================
                # 官方 Best Bid / Ask
                # ============================================

                "best_bid":
                    get_attr(
                        record,
                        "bid_px_00",
                    ),

                "best_ask":
                    get_attr(
                        record,
                        "ask_px_00",
                    ),

                "best_bid_size":
                    get_attr(
                        record,
                        "bid_sz_00",
                    ),

                "best_ask_size":
                    get_attr(
                        record,
                        "ask_sz_00",
                    ),

                "best_bid_count":
                    get_attr(
                        record,
                        "bid_ct_00",
                    ),

                "best_ask_count":
                    get_attr(
                        record,
                        "ask_ct_00",
                    ),
            }
        )


        if len(rows) >= limit:

            break


    return rows



# ============================================================
# Print MBO
# ============================================================


def print_mbo_rows(
    rows
):
    """
    打印 MBO 起始记录。
    """

    print_divider(
        "MBO HEAD"
    )


    for row in rows:

        print()

        print(
            f"[MBO {row['index']}]"
        )

        print(
            "ts_recv      :",
            row["ts_recv"],
            row["ts_recv_text"],
        )

        print(
            "ts_event     :",
            row["ts_event"],
            row["ts_event_text"],
        )

        print(
            "sequence     :",
            row["sequence"],
        )

        print(
            "action       :",
            row["action"],
        )

        print(
            "side         :",
            row["side"],
        )

        print(
            "order_id     :",
            row["order_id"],
        )

        print(
            "price        :",
            row["price"],
        )

        print(
            "size         :",
            row["size"],
        )

        print(
            "flags        :",
            row["flags"],
        )

        print(
            "instrument_id:",
            row["instrument_id"],
        )

        print(
            "channel_id   :",
            row["channel_id"],
        )

        print(
            "publisher_id :",
            row["publisher_id"],
        )



# ============================================================
# Print MBP-10
# ============================================================


def print_mbp10_rows(
    rows
):
    """
    打印官方 MBP-10 起始记录。
    """

    print_divider(
        "OFFICIAL MBP-10 HEAD"
    )


    for row in rows:

        print()

        print(
            f"[MBP10 {row['index']}]"
        )

        print(
            "ts_recv      :",
            row["ts_recv"],
            row["ts_recv_text"],
        )

        print(
            "ts_event     :",
            row["ts_event"],
            row["ts_event_text"],
        )

        print(
            "sequence     :",
            row["sequence"],
        )

        print(
            "action       :",
            row["action"],
        )

        print(
            "side         :",
            row["side"],
        )

        print(
            "depth        :",
            row["depth"],
        )

        print(
            "price        :",
            row["price"],
        )

        print(
            "size         :",
            row["size"],
        )

        print(
            "flags        :",
            row["flags"],
        )

        print(
            "instrument_id:",
            row["instrument_id"],
        )

        print(
            "publisher_id :",
            row["publisher_id"],
        )

        print(
            "official bid :",
            row["best_bid"],
            "size=",
            row["best_bid_size"],
            "count=",
            row["best_bid_count"],
        )

        print(
            "official ask :",
            row["best_ask"],
            "size=",
            row["best_ask_size"],
            "count=",
            row["best_ask_count"],
        )



# ============================================================
# Basic alignment summary
# ============================================================


def print_alignment_summary(
    mbo_rows,
    mbp_rows,
):
    """
    打印两个文件开头的时间关系。
    """


    print_divider(
        "ALIGNMENT SUMMARY"
    )


    mbo_first = mbo_rows[0]

    mbp_first = mbp_rows[0]


    print()

    print(
        "MBO first ts_recv:"
    )

    print(
        mbo_first["ts_recv"],
        mbo_first["ts_recv_text"],
    )


    print()

    print(
        "MBP10 first ts_recv:"
    )

    print(
        mbp_first["ts_recv"],
        mbp_first["ts_recv_text"],
    )


    print()

    print(
        "ts_recv delta:"
    )

    print(
        mbp_first["ts_recv"]
        -
        mbo_first["ts_recv"],
        "ns",
    )


    print()

    print(
        "MBO first ts_event:"
    )

    print(
        mbo_first["ts_event"],
        mbo_first["ts_event_text"],
    )


    print()

    print(
        "MBP10 first ts_event:"
    )

    print(
        mbp_first["ts_event"],
        mbp_first["ts_event_text"],
    )


    print()

    print(
        "MBO instrument_id:"
    )

    print(
        mbo_first["instrument_id"]
    )


    print()

    print(
        "MBP10 instrument_id:"
    )

    print(
        mbp_first["instrument_id"]
    )


    print()

    print(
        "MBO sequence:"
    )

    print(
        mbo_first["sequence"]
    )


    print()

    print(
        "MBP10 sequence:"
    )

    print(
        mbp_first["sequence"]
    )



# ============================================================
# Test 1
# Files
# ============================================================


def test_ground_truth_files_exist():
    """
    两个 Ground Truth 输入文件必须存在。
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
        f"MBP-10 file not found: "
        f"{MBP10_FILE}"
    )



# ============================================================
# Test 2
# Inspect alignment
# ============================================================


def test_ground_truth_alignment_head():
    """
    打印两边数据开头。

    当前测试阶段只要求：

        两边都有数据

    不强行要求：

        第一条记录 timestamp 完全一致。
    """


    mbo_rows = read_mbo_head(
        PRINT_LIMIT
    )


    mbp_rows = read_mbp10_head(
        PRINT_LIMIT
    )


    assert (
        len(mbo_rows)
        >
        0
    )


    assert (
        len(mbp_rows)
        >
        0
    )


    print_mbo_rows(
        mbo_rows
    )


    print_mbp10_rows(
        mbp_rows
    )


    print_alignment_summary(
        mbo_rows,
        mbp_rows,
    )



# ============================================================
# Test 3
# Instrument
# ============================================================


def test_ground_truth_instrument_id():
    """
    检查两个文件开头是否属于同一个 instrument_id。

    如果失败：

    不修改 OrderBook。

    先分析文件 symbol resolution /
    continuous contract / instrument mapping。
    """


    mbo_rows = read_mbo_head(
        1
    )


    mbp_rows = read_mbp10_head(
        1
    )


    mbo_instrument = (
        mbo_rows[0][
            "instrument_id"
        ]
    )


    mbp_instrument = (
        mbp_rows[0][
            "instrument_id"
        ]
    )


    print_divider(
        "INSTRUMENT CHECK"
    )


    print(
        "MBO instrument_id  :",
        mbo_instrument,
    )


    print(
        "MBP10 instrument_id:",
        mbp_instrument,
    )


    assert (
        mbo_instrument
        ==
        mbp_instrument
    ), (
        "MBO and MBP-10 instrument_id "
        "do not match."
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