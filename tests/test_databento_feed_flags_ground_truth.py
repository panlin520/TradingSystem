"""
tests/test_databento_feed_flags_ground_truth.py


============================================================
DatabentoFeed Flags Ground Truth
============================================================

目的：

验证：

    Raw Databento DBN
        ↓
    data/databento_feed.py
        ↓
    MarketEvent

过程中：

    flags

尤其：

    F_LAST = 128

是否被完整、逐记录、无损保留。


============================================================
为什么现在必须测试
============================================================

Dense Ground Truth 已经证明：

    OrderBook 只能在 F_LAST 边界读取稳定状态。

因此如果：

    DatabentoFeed

错误地：

    丢失 flags
    修改 flags
    忽略 N + F_LAST

那么后面的：

    Engine
    Feature
    Strategy

都会错误判断 market-event boundary。


============================================================
本测试验证
============================================================

1. Snapshot flags 保留

2. Raw DBN vs MarketEvent：
       ts_recv
       ts_event
       sequence
       action
       side
       order_id
       price
       size
       flags
       instrument_id
       publisher_id
       channel_id

   逐条一致

3. F_LAST bit：
       raw.flags & 128
   必须与：
       event.flags & 128
   完全一致

4. 专门检查之前 Dense failure：

       sequence = 5166966

   应该：

       所有记录均 !F_LAST

5. 下一 sequence：

       sequence = 5166967

   应该包含：

       action = N
       F_LAST = True

这证明：

    N + F_LAST

可以穿过 DatabentoFeed，
供 Engine 使用。


============================================================
重要
============================================================

本测试不修改：

    core/event.py
    data/databento_feed.py
    orderbook/*

只验证现有实现。
"""


from pathlib import Path

import databento as db
import pytest


from core.event import (
    OrderAction,
    OrderSide,
)


from data.databento_feed import (
    DatabentoFeed,
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
# Databento Flags
# ============================================================


F_LAST = 128

F_SNAPSHOT = 32

F_BAD_TS_RECV = 8



# ============================================================
# Diagnostic sequences found previously
# ============================================================


INCOMPLETE_SEQUENCE = 5166966

BOUNDARY_SEQUENCE = 5166967



# ============================================================
# General parity test size
# ============================================================


PARITY_RECORD_LIMIT = 250_000



# ============================================================
# Safe Attribute
# ============================================================


def get_attr(
    obj,
    name,
    default=None,
):
    """
    安全读取 raw Databento 字段。
    """


    try:

        return getattr(
            obj,
            name
        )

    except Exception:

        return default



# ============================================================
# Raw -> Expected Action
# ============================================================


def expected_action(
    raw_action
):
    """
    Raw Databento action
    转换成项目 OrderAction。
    """


    mapping = {

        "A":
            OrderAction.ADD,

        "M":
            OrderAction.MODIFY,

        "C":
            OrderAction.CANCEL,

        "R":
            OrderAction.RESET,

        "T":
            OrderAction.TRADE,

        "F":
            OrderAction.FILL,

        "N":
            OrderAction.NONE,

    }


    assert (
        raw_action
        in
        mapping
    ), (
        f"Unknown raw action: "
        f"{raw_action}"
    )


    return mapping[
        raw_action
    ]



# ============================================================
# Raw -> Expected Side
# ============================================================


def expected_side(
    raw_side
):
    """
    Raw Databento side：

        B -> BID
        A -> ASK
        N -> None
    """


    if raw_side == "B":

        return OrderSide.BID


    if raw_side == "A":

        return OrderSide.ASK


    return None



# ============================================================
# Raw MBO iterator
# ============================================================


def iter_raw_mbo():
    """
    直接读取官方 DBN。

    这是 DatabentoFeed 的独立 Ground Truth。
    """


    store = db.DBNStore.from_file(
        MBO_FILE
    )


    for record in store:

        yield record



# ============================================================
# Test 1
# File
# ============================================================


def test_databento_feed_flags_file_exists():
    """
    MBO Ground Truth 文件必须存在。
    """


    assert (
        MBO_FILE.exists()
    ), (
        f"MBO file missing: "
        f"{MBO_FILE}"
    )



# ============================================================
# Test 2
# Snapshot flags
# ============================================================


def test_databento_feed_snapshot_flags():
    """
    验证开头官方 MBO Snapshot 的 flags
    能正确进入 MarketEvent。


    已知：

        snapshot ts_recv
        =
        1781481600000000000


    Snapshot：

        R + A + A + ...

    应带：

        F_SNAPSHOT
        F_BAD_TS_RECV

    Snapshot 最终还应出现：

        F_LAST
    """


    raw_iterator = iter_raw_mbo()


    feed = DatabentoFeed(

        file_path=str(
            MBO_FILE
        ),

        symbol=SYMBOL,

    )


    feed_iterator = iter(
        feed
    )


    snapshot_ts_recv = None

    snapshot_records = 0

    last_seen = False


    while True:


        raw = next(
            raw_iterator
        )


        event = next(
            feed_iterator
        )


        raw_ts_recv = int(
            get_attr(
                raw,
                "ts_recv",
            )
        )


        if snapshot_ts_recv is None:

            snapshot_ts_recv = (
                raw_ts_recv
            )


        # Snapshot结束
        if (
            raw_ts_recv
            !=
            snapshot_ts_recv
        ):

            break


        raw_flags = int(
            get_attr(
                raw,
                "flags",
                0,
            )
        )


        event_flags = int(
            event.flags
            or
            0
        )


        # ====================================================
        # Exact flags parity
        # ====================================================

        assert (
            event_flags
            ==
            raw_flags
        ), (
            f"Snapshot flags mismatch | "
            f"raw={raw_flags} "
            f"event={event_flags}"
        )


        # ====================================================
        # Snapshot bit
        # ====================================================

        assert (
            raw_flags
            &
            F_SNAPSHOT
        ), (
            "Snapshot record missing "
            "F_SNAPSHOT."
        )


        # ====================================================
        # BAD_TS_RECV expected on historical snapshot
        # ====================================================

        assert (
            raw_flags
            &
            F_BAD_TS_RECV
        ), (
            "Snapshot record missing "
            "F_BAD_TS_RECV."
        )


        if (
            raw_flags
            &
            F_LAST
        ):

            last_seen = True


        snapshot_records += 1


    print()

    print(
        "=" * 100
    )

    print(
        "DATABENTO FEED SNAPSHOT FLAGS"
    )

    print(
        "=" * 100
    )


    print(
        "snapshot ts_recv:",
        snapshot_ts_recv
    )


    print(
        "snapshot records:",
        snapshot_records
    )


    print(
        "F_LAST seen:",
        last_seen
    )


    assert (
        snapshot_records
        ==
        5173
    )


    assert (
        last_seen
        is True
    )



# ============================================================
# Test 3
# Raw DBN vs Feed field parity
# ============================================================


def test_databento_feed_raw_record_parity():
    """
    前 250,000 条：

        Raw DBN
        vs
        MarketEvent

    逐字段严格比较。


    最重要的是：

        flags

    但同时验证其它关键字段，

    防止 Feed 发生：

        record skip
        record shift
        ordering mismatch
    """


    raw_iterator = iter_raw_mbo()


    feed = DatabentoFeed(

        file_path=str(
            MBO_FILE
        ),

        symbol=SYMBOL,

    )


    feed_iterator = iter(
        feed
    )


    compared = 0

    raw_last_count = 0

    feed_last_count = 0


    for index in range(
        PARITY_RECORD_LIMIT
    ):


        raw = next(
            raw_iterator
        )


        event = next(
            feed_iterator
        )


        raw_flags = int(
            get_attr(
                raw,
                "flags",
                0,
            )
        )


        event_flags = int(
            event.flags
            or
            0
        )


        # ====================================================
        # ts_recv
        # ====================================================

        assert (
            event.ts_recv
            ==
            int(
                get_attr(
                    raw,
                    "ts_recv",
                )
            )
        ), (
            f"index={index} "
            f"ts_recv mismatch"
        )


        # ====================================================
        # ts_event
        # ====================================================

        assert (
            event.ts_event
            ==
            int(
                get_attr(
                    raw,
                    "ts_event",
                )
            )
        ), (
            f"index={index} "
            f"ts_event mismatch"
        )


        # ====================================================
        # sequence
        # ====================================================

        assert (
            event.sequence
            ==
            int(
                get_attr(
                    raw,
                    "sequence",
                )
            )
        ), (
            f"index={index} "
            f"sequence mismatch"
        )


        # ====================================================
        # action
        # ====================================================

        raw_action = get_attr(
            raw,
            "action",
        )


        assert (
            event.action
            ==
            expected_action(
                raw_action
            )
        ), (
            f"index={index} "
            f"action mismatch | "
            f"raw={raw_action} "
            f"event={event.action}"
        )


        # ====================================================
        # side
        # ====================================================

        raw_side = get_attr(
            raw,
            "side",
        )


        assert (
            event.side
            ==
            expected_side(
                raw_side
            )
        ), (
            f"index={index} "
            f"side mismatch | "
            f"raw={raw_side} "
            f"event={event.side}"
        )


        # ====================================================
        # order_id
        # ====================================================

        assert (
            event.order_id
            ==
            int(
                get_attr(
                    raw,
                    "order_id",
                )
            )
        ), (
            f"index={index} "
            f"order_id mismatch"
        )


        # ====================================================
        # price
        # ====================================================

        assert (
            event.price
            ==
            int(
                get_attr(
                    raw,
                    "price",
                )
            )
        ), (
            f"index={index} "
            f"price mismatch"
        )


        # ====================================================
        # size
        # ====================================================

        assert (
            event.size
            ==
            int(
                get_attr(
                    raw,
                    "size",
                )
            )
        ), (
            f"index={index} "
            f"size mismatch"
        )


        # ====================================================
        # flags
        #
        # 这是本测试最关键的断言。
        # ====================================================

        assert (
            event_flags
            ==
            raw_flags
        ), (
            "\n"
            "FLAGS GROUND TRUTH FAILURE\n"
            f"index={index}\n"
            f"sequence={event.sequence}\n"
            f"ts_recv={event.ts_recv}\n"
            f"raw_flags={raw_flags}\n"
            f"event_flags={event_flags}"
        )


        # ====================================================
        # F_LAST bit parity
        # ====================================================

        raw_is_last = bool(
            raw_flags
            &
            F_LAST
        )


        feed_is_last = bool(
            event_flags
            &
            F_LAST
        )


        assert (
            raw_is_last
            ==
            feed_is_last
        ), (
            f"index={index} "
            f"F_LAST mismatch"
        )


        if raw_is_last:

            raw_last_count += 1


        if feed_is_last:

            feed_last_count += 1


        # ====================================================
        # instrument_id
        # ====================================================

        assert (
            event.instrument_id
            ==
            int(
                get_attr(
                    raw,
                    "instrument_id",
                )
            )
        ), (
            f"index={index} "
            f"instrument_id mismatch"
        )


        # ====================================================
        # publisher_id
        # ====================================================

        assert (
            event.publisher_id
            ==
            int(
                get_attr(
                    raw,
                    "publisher_id",
                )
            )
        ), (
            f"index={index} "
            f"publisher_id mismatch"
        )


        # ====================================================
        # channel_id
        # ====================================================

        assert (
            event.channel_id
            ==
            int(
                get_attr(
                    raw,
                    "channel_id",
                )
            )
        ), (
            f"index={index} "
            f"channel_id mismatch"
        )


        compared += 1


    print()

    print(
        "=" * 100
    )

    print(
        "RAW DBN -> DATABENTO FEED PARITY PASSED"
    )

    print(
        "=" * 100
    )


    print(
        "records compared:",
        compared
    )


    print(
        "raw F_LAST records:",
        raw_last_count
    )


    print(
        "feed F_LAST records:",
        feed_last_count
    )


    assert (
        raw_last_count
        ==
        feed_last_count
    )


    assert (
        raw_last_count
        >
        0
    )



# ============================================================
# Test 4
# Known incomplete market event
# ============================================================


def test_databento_feed_known_incomplete_sequence():
    """
    检查之前 Dense mismatch 的真实 sequence：

        5166966


    已经通过 raw DBN 诊断确认：

        该 sequence 有 44 条 MBO records

    并且：

        没有任何一条 F_LAST。


    Feed必须完整保留这一事实。
    """


    feed = DatabentoFeed(

        file_path=str(
            MBO_FILE
        ),

        symbol=SYMBOL,

    )


    records = []


    for event in feed:


        if (
            event.sequence
            <
            INCOMPLETE_SEQUENCE
        ):

            continue


        if (
            event.sequence
            >
            INCOMPLETE_SEQUENCE
        ):

            break


        records.append(
            event
        )


    print()

    print(
        "=" * 100
    )

    print(
        "KNOWN INCOMPLETE EVENT"
    )

    print(
        "=" * 100
    )


    print(
        "sequence:",
        INCOMPLETE_SEQUENCE
    )


    print(
        "records:",
        len(
            records
        )
    )


    assert (
        len(
            records
        )
        ==
        44
    )


    last_count = 0


    for event in records:


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


    print(
        "F_LAST records:",
        last_count
    )


    assert (
        last_count
        ==
        0
    )



# ============================================================
# Test 5
# N + F_LAST boundary
# ============================================================


def test_databento_feed_none_action_can_carry_f_last():
    """
    检查下一 sequence：

        5166967


    Raw诊断已经确认：

        action = N
        flags  = 128


    这是非常关键的 Engine 输入语义。


    Feed必须产生：

        OrderAction.NONE

并且：

        event.flags & F_LAST

必须为True。
    """


    feed = DatabentoFeed(

        file_path=str(
            MBO_FILE
        ),

        symbol=SYMBOL,

    )


    records = []


    for event in feed:


        if (
            event.sequence
            <
            BOUNDARY_SEQUENCE
        ):

            continue


        if (
            event.sequence
            >
            BOUNDARY_SEQUENCE
        ):

            break


        records.append(
            event
        )


    print()

    print(
        "=" * 100
    )

    print(
        "N + F_LAST EVENT BOUNDARY"
    )

    print(
        "=" * 100
    )


    print(
        "sequence:",
        BOUNDARY_SEQUENCE
    )


    print(
        "records:",
        len(
            records
        )
    )


    assert (
        len(
            records
        )
        ==
        1
    )


    event = (
        records[
            0
        ]
    )


    flags = int(
        event.flags
        or
        0
    )


    print(
        "action:",
        event.action
    )


    print(
        "flags:",
        flags
    )


    print(
        "F_LAST:",
        bool(
            flags
            &
            F_LAST
        )
    )


    assert (
        event.action
        ==
        OrderAction.NONE
    )


    assert (
        flags
        &
        F_LAST
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