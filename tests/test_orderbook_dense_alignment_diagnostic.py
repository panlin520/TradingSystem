"""
tests/test_orderbook_dense_alignment_diagnostic.py


============================================================
Dense Ground Truth Alignment Diagnostic
============================================================


目的：

调查 Dense Ground Truth 第一个 mismatch：

    checkpoint = 486

    ts_recv =
        1781530200070792146


重点检查：

    MBO
    MBP-10

在失败位置附近的：

    ts_recv
    ts_event
    sequence
    action
    side
    flags
    F_LAST


============================================================


本测试：

    不修改OrderBook

    不判断盘口正确/错误

只调查：

    ts_recv边界

VS

    CME Event / F_LAST边界


============================================================
"""


from pathlib import Path

import databento as db
import pytest



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


MBP10_FILE = (
    PROJECT_ROOT
    /
    "data"
    /
    "ESU6_2026-06-15_MBP10.dbn.zst"
)



# ============================================================
# Failure Point
# ============================================================


FAIL_TS_RECV = (
    1781530200070792146
)


# 前后观察窗口
#
# 5毫秒
DIAGNOSTIC_WINDOW_NS = (
    5_000_000
)



# ============================================================
# Databento Flags
# ============================================================


F_LAST = 128

F_SNAPSHOT = 32



# ============================================================
# Safe Attr
# ============================================================


def get_attr(
    obj,
    name,
    default=None,
):
    """
    安全读取DBN字段。
    """


    try:

        return getattr(
            obj,
            name,
        )

    except Exception:

        return default



# ============================================================
# Flag Formatter
# ============================================================


def format_flags(
    value
):
    """
    显示关键flags。
    """


    if value is None:

        return "None"


    value = int(
        value
    )


    names = []


    if (
        value
        &
        F_LAST
    ):

        names.append(
            "LAST"
        )


    if (
        value
        &
        F_SNAPSHOT
    ):

        names.append(
            "SNAPSHOT"
        )


    if not names:

        return str(
            value
        )


    return (
        f"{value} "
        f"({'|'.join(names)})"
    )



# ============================================================
# Read MBO Around Failure
# ============================================================


def load_mbo_window():
    """
    读取失败点前后MBO raw records。
    """


    start = (
        FAIL_TS_RECV
        -
        DIAGNOSTIC_WINDOW_NS
    )


    end = (
        FAIL_TS_RECV
        +
        DIAGNOSTIC_WINDOW_NS
    )


    store = db.DBNStore.from_file(
        MBO_FILE
    )


    rows = []


    for record in store:


        ts_recv = get_attr(
            record,
            "ts_recv",
        )


        if ts_recv is None:

            continue


        if (
            ts_recv
            <
            start
        ):

            continue


        if (
            ts_recv
            >
            end
        ):

            break


        rows.append(
            {
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

                "side":
                    get_attr(
                        record,
                        "side",
                    ),

                "order_id":
                    get_attr(
                        record,
                        "order_id",
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
                    int(
                        get_attr(
                            record,
                            "flags",
                            0,
                        )
                    ),
            }
        )


    return rows



# ============================================================
# Read MBP10 Around Failure
# ============================================================


def load_mbp10_window():
    """
    读取失败点前后官方MBP-10。
    """


    start = (
        FAIL_TS_RECV
        -
        DIAGNOSTIC_WINDOW_NS
    )


    end = (
        FAIL_TS_RECV
        +
        DIAGNOSTIC_WINDOW_NS
    )


    store = db.DBNStore.from_file(
        MBP10_FILE
    )


    rows = []


    for record in store:


        ts_recv = get_attr(
            record,
            "ts_recv",
        )


        if ts_recv is None:

            continue


        if (
            ts_recv
            <
            start
        ):

            continue


        if (
            ts_recv
            >
            end
        ):

            break


        rows.append(
            {
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
                    int(
                        get_attr(
                            record,
                            "flags",
                            0,
                        )
                    ),

                "bid":
                    get_attr(
                        record,
                        "bid_px_00",
                    ),

                "ask":
                    get_attr(
                        record,
                        "ask_px_00",
                    ),

                "bid_size":
                    get_attr(
                        record,
                        "bid_sz_00",
                    ),

                "ask_size":
                    get_attr(
                        record,
                        "ask_sz_00",
                    ),

                "bid_count":
                    get_attr(
                        record,
                        "bid_ct_00",
                    ),

                "ask_count":
                    get_attr(
                        record,
                        "ask_ct_00",
                    ),
            }
        )


    return rows



# ============================================================
# Print MBO
# ============================================================


def print_mbo(
    rows
):
    """
    打印MBO。
    """


    print()

    print(
        "=" * 150
    )

    print(
        "RAW MBO AROUND FAILURE"
    )

    print(
        "=" * 150
    )


    print(
        f"{'INDEX':<7}"
        f"{'DELTA_NS':<14}"
        f"{'TS_RECV':<22}"
        f"{'SEQUENCE':<12}"
        f"{'ACTION':<8}"
        f"{'SIDE':<6}"
        f"{'PRICE':<18}"
        f"{'SIZE':<8}"
        f"{'FLAGS':<18}"
        f"{'ORDER_ID':<18}"
    )


    print(
        "-" * 150
    )


    for index, row in enumerate(
        rows
    ):


        delta = (
            row[
                "ts_recv"
            ]
            -
            FAIL_TS_RECV
        )


        marker = (
            " <--"
            if row[
                "ts_recv"
            ]
            ==
            FAIL_TS_RECV
            else ""
        )


        print(

            f"{index:<7}"

            f"{delta:<14}"

            f"{row['ts_recv']:<22}"

            f"{str(row['sequence']):<12}"

            f"{str(row['action']):<8}"

            f"{str(row['side']):<6}"

            f"{str(row['price']):<18}"

            f"{str(row['size']):<8}"

            f"{format_flags(row['flags']):<18}"

            f"{str(row['order_id']):<18}"

            f"{marker}"

        )



# ============================================================
# Print MBP
# ============================================================


def print_mbp10(
    rows
):
    """
    打印官方MBP-10。
    """


    print()

    print(
        "=" * 175
    )

    print(
        "OFFICIAL MBP-10 AROUND FAILURE"
    )

    print(
        "=" * 175
    )


    print(
        f"{'INDEX':<7}"
        f"{'DELTA_NS':<14}"
        f"{'TS_RECV':<22}"
        f"{'SEQ':<11}"
        f"{'ACT':<6}"
        f"{'SIDE':<6}"
        f"{'FLAGS':<17}"
        f"{'BID':<18}"
        f"{'BIDSZ':<8}"
        f"{'BIDCT':<8}"
        f"{'ASK':<18}"
        f"{'ASKSZ':<8}"
        f"{'ASKCT':<8}"
    )


    print(
        "-" * 175
    )


    for index, row in enumerate(
        rows
    ):


        delta = (
            row[
                "ts_recv"
            ]
            -
            FAIL_TS_RECV
        )


        marker = (
            " <-- FAILURE CHECKPOINT"
            if row[
                "ts_recv"
            ]
            ==
            FAIL_TS_RECV
            else ""
        )


        print(

            f"{index:<7}"

            f"{delta:<14}"

            f"{row['ts_recv']:<22}"

            f"{str(row['sequence']):<11}"

            f"{str(row['action']):<6}"

            f"{str(row['side']):<6}"

            f"{format_flags(row['flags']):<17}"

            f"{str(row['bid']):<18}"

            f"{str(row['bid_size']):<8}"

            f"{str(row['bid_count']):<8}"

            f"{str(row['ask']):<18}"

            f"{str(row['ask_size']):<8}"

            f"{str(row['ask_count']):<8}"

            f"{marker}"

        )



# ============================================================
# Exact Failure Record
# ============================================================


def print_failure_record_details(
    mbp_rows
):
    """
    找到失败ts_recv对应的MBP记录。
    """


    matching = [

        row

        for row in mbp_rows

        if (
            row[
                "ts_recv"
            ]
            ==
            FAIL_TS_RECV
        )

    ]


    print()

    print(
        "=" * 100
    )

    print(
        "FAILURE CHECKPOINT DETAILS"
    )

    print(
        "=" * 100
    )


    print(
        "records with exact ts_recv:",
        len(
            matching
        )
    )


    for index, row in enumerate(
        matching
    ):


        print()

        print(
            "record:",
            index
        )


        print(
            "ts_recv:",
            row[
                "ts_recv"
            ]
        )


        print(
            "ts_event:",
            row[
                "ts_event"
            ]
        )


        print(
            "sequence:",
            row[
                "sequence"
            ]
        )


        print(
            "action:",
            row[
                "action"
            ]
        )


        print(
            "side:",
            row[
                "side"
            ]
        )


        print(
            "flags:",
            format_flags(
                row[
                    "flags"
                ]
            )
        )


        print(
            "best bid:",
            row[
                "bid"
            ],
            "size=",
            row[
                "bid_size"
            ],
            "count=",
            row[
                "bid_count"
            ],
        )


        print(
            "best ask:",
            row[
                "ask"
            ],
            "size=",
            row[
                "ask_size"
            ],
            "count=",
            row[
                "ask_count"
            ],
        )



# ============================================================
# Sequence Matching
# ============================================================


def print_sequence_relationship(
    mbo_rows,
    mbp_rows,
):
    """
    比较MBP sequence是否在附近MBO出现。
    """


    mbo_sequences = {}


    for row in mbo_rows:


        sequence = (
            row[
                "sequence"
            ]
        )


        mbo_sequences.setdefault(
            sequence,
            []
        ).append(
            row
        )


    print()

    print(
        "=" * 120
    )

    print(
        "MBP-10 -> MBO SEQUENCE RELATIONSHIP"
    )

    print(
        "=" * 120
    )


    relevant_mbp = [

        row

        for row in mbp_rows

        if abs(
            row[
                "ts_recv"
            ]
            -
            FAIL_TS_RECV
        )
        <=
        1_000_000

    ]


    for mbp in relevant_mbp:


        sequence = (
            mbp[
                "sequence"
            ]
        )


        matching_mbo = (
            mbo_sequences.get(
                sequence,
                []
            )
        )


        print()

        print(
            "MBP:",
            "ts_recv=",
            mbp[
                "ts_recv"
            ],
            "sequence=",
            sequence,
            "action=",
            mbp[
                "action"
            ],
            "flags=",
            format_flags(
                mbp[
                    "flags"
                ]
            ),
        )


        print(
            "matching MBO records:",
            len(
                matching_mbo
            )
        )


        for mbo in matching_mbo:


            print(

                "    MBO",

                "ts_recv=",
                mbo[
                    "ts_recv"
                ],

                "action=",
                mbo[
                    "action"
                ],

                "side=",
                mbo[
                    "side"
                ],

                "price=",
                mbo[
                    "price"
                ],

                "size=",
                mbo[
                    "size"
                ],

                "flags=",
                format_flags(
                    mbo[
                        "flags"
                    ]
                ),

            )



# ============================================================
# Test
# ============================================================


def test_dense_failure_alignment_diagnostic():
    """
    只做诊断。

    没有盘口PASS/FAIL断言。
    """


    mbo_rows = (
        load_mbo_window()
    )


    mbp_rows = (
        load_mbp10_window()
    )


    assert (
        len(
            mbo_rows
        )
        >
        0
    )


    assert (
        len(
            mbp_rows
        )
        >
        0
    )


    print()

    print(
        "Failure ts_recv:",
        FAIL_TS_RECV
    )


    print(
        "MBO records in window:",
        len(
            mbo_rows
        )
    )


    print(
        "MBP10 records in window:",
        len(
            mbp_rows
        )
    )


    print_mbo(
        mbo_rows
    )


    print_mbp10(
        mbp_rows
    )


    print_failure_record_details(
        mbp_rows
    )


    print_sequence_relationship(

        mbo_rows,

        mbp_rows,

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