"""
tests/test_orderbook_l3_snapshot_ground_truth.py


============================================================
Official Databento L3 MBO Snapshot Ground Truth
============================================================


目的：

验证我们 OrderBook 内部的：

    order_id
    side
    price
    size

以及：

    每个 price level 的 FIFO / queue priority

是否与：

    Databento 官方 MBO Snapshot

完全一致。


============================================================


官方依据：

Databento Historical MBO：

    每个 UTC 工作日 00:00:00

包含官方合成的：

    MBO Snapshot


单个 instrument Snapshot：

    R
    ↓
    A
    A
    A
    ...
    ↓
    LAST


官方明确说明：

    Snapshot 中的记录保留：

        price-level priority order

因此：

    同一价格档 Snapshot A record 的发布顺序

就是：

        FIFO / queue priority


============================================================


我们现在验证：


1. Snapshot完整性

    R开始

    Snapshot flags存在


2. Active Orders

    raw snapshot order count
        ==
    book.orders count


3. 每个订单：

    order_id
    side
    price
    size


4. 每个价格档：

    raw official FIFO order_id sequence
        ==
    PriceLevel FIFO order_id sequence


5. 所有 Bid / Ask price level


============================================================


这不是：

    MBP-10聚合检查


而是：

    完整L3订单级检查。


============================================================
"""


from collections import defaultdict
from pathlib import Path

import databento as db
import pytest


from data.databento_feed import (
    DatabentoFeed,
)


from orderbook.builder import (
    OrderBookBuilder,
)


from core.event import (
    OrderAction,
    OrderSide,
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


# 官方文档：
#
# F_SNAPSHOT = 32
#
# Snapshot中还会同时存在：
#
# F_BAD_TS_RECV
#
# 当前数据中：
#
# flags = 40
#
# 即：
#
# SNAPSHOT + BAD_TS_RECV


SNAPSHOT_FLAG = 32


# Databento：
#
# F_LAST = 128


LAST_FLAG = 128



# ============================================================
# Safe Attribute
# ============================================================


def get_attr(
    obj,
    name,
    default=None,
):
    """
    安全读取 raw Databento record 属性。
    """

    try:

        return getattr(
            obj,
            name
        )

    except Exception:

        return default



# ============================================================
# Side Conversion
# ============================================================


def convert_raw_side(
    side
):
    """
    Databento raw MBO side：

        B
        A
        N

    转成系统：

        OrderSide.BID
        OrderSide.ASK
        None
    """


    if side == "B":

        return OrderSide.BID


    if side == "A":

        return OrderSide.ASK


    return None



# ============================================================
# Load Official Raw Snapshot
# ============================================================


def load_official_snapshot():
    """
    直接读取 raw DBN。

    不经过：

        DatabentoFeed
        OrderBookBuilder
        OrderBook


    因此 raw snapshot 是独立的官方基准。


    返回：

        {
            "ts_recv": ...,

            "records": [...],

            "orders": {...},

            "levels": {
                OrderSide.BID: {
                    price: [order_id, ...]
                },

                OrderSide.ASK: {
                    price: [order_id, ...]
                }
            }
        }
    """


    store = db.DBNStore.from_file(
        MBO_FILE
    )


    snapshot_ts_recv = None


    snapshot_records = []


    orders = {}


    levels = {

        OrderSide.BID:
            defaultdict(
                list
            ),

        OrderSide.ASK:
            defaultdict(
                list
            ),

    }


    reset_seen = False

    last_seen = False


    for record in store:


        action = get_attr(
            record,
            "action",
        )


        flags = int(
            get_attr(
                record,
                "flags",
                0,
            )
        )


        ts_recv = get_attr(
            record,
            "ts_recv",
        )


        # ====================================================
        # 第一个Snapshot Record
        # ====================================================

        if snapshot_ts_recv is None:


            # 必须是官方Snapshot
            if not (
                flags
                &
                SNAPSHOT_FLAG
            ):

                raise AssertionError(
                    "First MBO record is not marked "
                    "as Databento Snapshot."
                )


            snapshot_ts_recv = (
                ts_recv
            )


        # ====================================================
        # Snapshot结束
        #
        # Snapshot所有记录共享generation ts_recv。
        # ====================================================

        if (
            ts_recv
            !=
            snapshot_ts_recv
        ):

            break


        # ====================================================
        # 必须属于Snapshot
        # ====================================================

        if not (
            flags
            &
            SNAPSHOT_FLAG
        ):


            # 同一个ts_recv如果已经进入普通行情，
            # 就结束Snapshot收集。
            break


        snapshot_records.append(
            record
        )


        # ====================================================
        # RESET
        # ====================================================

        if action == "R":


            reset_seen = True

            continue


        # ====================================================
        # ADD
        # ====================================================

        if action == "A":


            raw_side = get_attr(
                record,
                "side",
            )


            side = convert_raw_side(
                raw_side
            )


            if side is None:

                continue


            order_id = int(
                get_attr(
                    record,
                    "order_id",
                )
            )


            price = int(
                get_attr(
                    record,
                    "price",
                )
            )


            size = int(
                get_attr(
                    record,
                    "size",
                )
            )


            # =================================================
            # 官方Snapshot不应该出现重复active order_id
            # =================================================

            assert (
                order_id
                not in
                orders
            ), (
                f"Duplicate order_id in official snapshot: "
                f"{order_id}"
            )


            orders[
                order_id
            ] = {
                "order_id":
                    order_id,

                "side":
                    side,

                "price":
                    price,

                "size":
                    size,
            }


            # =================================================
            # 关键：
            #
            # append顺序就是Databento官方发布顺序。
            #
            # Databento官方说明Snapshot保存了
            # price-level FIFO priority。
            # =================================================

            levels[
                side
            ][
                price
            ].append(
                order_id
            )


        # ====================================================
        # LAST
        # ====================================================

        if (
            flags
            &
            LAST_FLAG
        ):


            last_seen = True


    return {

        "ts_recv":
            snapshot_ts_recv,

        "records":
            snapshot_records,

        "orders":
            orders,

        "levels":
            levels,

        "reset_seen":
            reset_seen,

        "last_seen":
            last_seen,

    }



# ============================================================
# Rebuild Snapshot Through Production Pipeline
# ============================================================


def rebuild_snapshot(
    snapshot_ts_recv
):
    """
    使用正式生产链：

        DatabentoFeed
            ↓
        OrderBookBuilder
            ↓
        OrderBook


    处理：

        Snapshot ts_recv

    的所有事件。


    一旦：

        event.ts_recv > snapshot_ts_recv

    就停止。
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


    event_count = 0


    for event in feed:


        if (
            event.ts_recv
            >
            snapshot_ts_recv
        ):


            break


        if (
            event.ts_recv
            <
            snapshot_ts_recv
        ):


            continue


        builder.on_event(
            event
        )


        event_count += 1


    return {

        "builder":
            builder,

        "book":
            builder.get_book(),

        "event_count":
            event_count,

    }



# ============================================================
# Get Book Level
# ============================================================


def get_book_level(
    book,
    side,
    price,
):
    """
    获取我们的 PriceLevel。
    """


    if (
        side
        ==
        OrderSide.BID
    ):


        return book.bids.get(
            price
        )


    return book.asks.get(
        price
    )



# ============================================================
# Extract FIFO From PriceLevel
# ============================================================


def extract_level_fifo(
    level
):
    """
    PriceLevel 使用：

        OrderedDict

    并且：

        __iter__()

    按FIFO返回Order。


    因此这里直接记录：

        order.order_id

    的顺序。
    """


    return [

        order.order_id

        for order in level

    ]



# ============================================================
# Test 1
# File
# ============================================================


def test_l3_snapshot_file_exists():
    """
    MBO文件必须存在。
    """


    assert (
        MBO_FILE.exists()
    ), (
        f"MBO file missing: "
        f"{MBO_FILE}"
    )



# ============================================================
# Test 2
# Official Snapshot Structure
# ============================================================


def test_official_l3_snapshot_structure():
    """
    检查官方Snapshot结构。
    """


    official = (
        load_official_snapshot()
    )


    print()

    print(
        "=" * 100
    )

    print(
        "OFFICIAL L3 SNAPSHOT STRUCTURE"
    )

    print(
        "=" * 100
    )


    print(
        "ts_recv:",
        official[
            "ts_recv"
        ]
    )


    print(
        "snapshot records:",
        len(
            official[
                "records"
            ]
        )
    )


    print(
        "active orders:",
        len(
            official[
                "orders"
            ]
        )
    )


    print(
        "bid levels:",
        len(
            official[
                "levels"
            ][
                OrderSide.BID
            ]
        )
    )


    print(
        "ask levels:",
        len(
            official[
                "levels"
            ][
                OrderSide.ASK
            ]
        )
    )


    print(
        "reset seen:",
        official[
            "reset_seen"
        ]
    )


    print(
        "last seen:",
        official[
            "last_seen"
        ]
    )


    assert (
        official[
            "reset_seen"
        ]
        is True
    )


    assert (
        len(
            official[
                "orders"
            ]
        )
        >
        0
    )



# ============================================================
# Test 3
# Complete Active Order Ground Truth
# ============================================================


def test_l3_snapshot_all_active_orders():
    """
    所有官方Snapshot active orders：

        order_id
        side
        price
        size

    必须与我们的Book完全一致。
    """


    official = (
        load_official_snapshot()
    )


    replay = rebuild_snapshot(

        official[
            "ts_recv"
        ]

    )


    book = (
        replay[
            "book"
        ]
    )


    official_orders = (
        official[
            "orders"
        ]
    )


    print()

    print(
        "=" * 100
    )

    print(
        "L3 ACTIVE ORDER GROUND TRUTH"
    )

    print(
        "=" * 100
    )


    print(
        "official orders:",
        len(
            official_orders
        )
    )


    print(
        "our orders:",
        len(
            book.orders
        )
    )


    print(
        "replayed events:",
        replay[
            "event_count"
        ]
    )


    # ========================================================
    # Order数量
    # ========================================================

    assert (
        len(
            book.orders
        )
        ==
        len(
            official_orders
        )
    ), (
        "Active order count mismatch."
    )


    # ========================================================
    # 每一个official order
    # ========================================================

    for order_id, expected in (
        official_orders.items()
    ):


        assert (
            order_id
            in
            book.orders
        ), (
            f"Missing active order: "
            f"{order_id}"
        )


        actual = (
            book.orders[
                order_id
            ]
        )


        # ====================================================
        # Side
        # ====================================================

        assert (
            actual.side
            ==
            expected[
                "side"
            ]
        ), (
            f"order_id={order_id} "
            f"SIDE mismatch | "
            f"ours={actual.side} "
            f"official={expected['side']}"
        )


        # ====================================================
        # Price
        # ====================================================

        assert (
            actual.price
            ==
            expected[
                "price"
            ]
        ), (
            f"order_id={order_id} "
            f"PRICE mismatch | "
            f"ours={actual.price} "
            f"official={expected['price']}"
        )


        # ====================================================
        # Size
        # ====================================================

        assert (
            actual.size
            ==
            expected[
                "size"
            ]
        ), (
            f"order_id={order_id} "
            f"SIZE mismatch | "
            f"ours={actual.size} "
            f"official={expected['size']}"
        )


    print()

    print(
        "ALL ACTIVE ORDERS MATCH"
    )



# ============================================================
# Test 4
# Complete Price-Level Membership
# ============================================================


def test_l3_snapshot_price_level_membership():
    """
    每个官方 price level 的：

        order_id membership

    必须完全一致。


    这里暂时只比较集合。

    FIFO在下一个测试单独严格检查。
    """


    official = (
        load_official_snapshot()
    )


    replay = rebuild_snapshot(

        official[
            "ts_recv"
        ]

    )


    book = (
        replay[
            "book"
        ]
    )


    checked_levels = 0


    for side in (

        OrderSide.BID,

        OrderSide.ASK,

    ):


        official_levels = (
            official[
                "levels"
            ][
                side
            ]
        )


        for price, expected_ids in (
            official_levels.items()
        ):


            level = get_book_level(

                book,

                side,

                price,

            )


            assert (
                level
                is not None
            ), (
                f"Missing price level | "
                f"side={side} "
                f"price={price}"
            )


            actual_ids = (
                extract_level_fifo(
                    level
                )
            )


            assert (
                set(
                    actual_ids
                )
                ==
                set(
                    expected_ids
                )
            ), (
                f"Price-level membership mismatch | "
                f"side={side} "
                f"price={price}"
            )


            checked_levels += 1


    print()

    print(
        "=" * 100
    )

    print(
        "L3 PRICE LEVEL MEMBERSHIP PASSED"
    )

    print(
        "=" * 100
    )


    print(
        "checked levels:",
        checked_levels
    )



# ============================================================
# Test 5
# Complete FIFO Ground Truth
# ============================================================


def test_l3_snapshot_fifo_ground_truth():
    """
    这是本文件最重要的测试。


    对所有：

        Bid price levels
        Ask price levels

    比较：

        Databento官方Snapshot发布顺序

    VS

        我们PriceLevel内部FIFO顺序


    必须：

        order_id by order_id

    完全一致。
    """


    official = (
        load_official_snapshot()
    )


    replay = rebuild_snapshot(

        official[
            "ts_recv"
        ]

    )


    book = (
        replay[
            "book"
        ]
    )


    total_levels = 0

    total_orders = 0


    for side in (

        OrderSide.BID,

        OrderSide.ASK,

    ):


        official_levels = (
            official[
                "levels"
            ][
                side
            ]
        )


        for price, expected_fifo in (
            official_levels.items()
        ):


            level = get_book_level(

                book,

                side,

                price,

            )


            assert (
                level
                is not None
            ), (
                f"Missing price level | "
                f"side={side} "
                f"price={price}"
            )


            actual_fifo = (
                extract_level_fifo(
                    level
                )
            )


            # =================================================
            # FIFO严格比较
            # =================================================

            assert (
                actual_fifo
                ==
                expected_fifo
            ), (
                "\n"
                "L3 FIFO GROUND TRUTH FAILURE\n"
                f"side={side}\n"
                f"price={price}\n"
                f"official={expected_fifo}\n"
                f"ours={actual_fifo}"
            )


            total_levels += 1


            total_orders += len(
                expected_fifo
            )


    print()

    print(
        "=" * 100
    )

    print(
        "OFFICIAL L3 FIFO GROUND TRUTH PASSED"
    )

    print(
        "=" * 100
    )


    print(
        "price levels checked:",
        total_levels
    )


    print(
        "orders checked:",
        total_orders
    )


    print(
        "official active orders:",
        len(
            official[
                "orders"
            ]
        )
    )


    print(
        "our active orders:",
        len(
            book.orders
        )
    )



# ============================================================
# Test 6
# Aggregate Final L3 Ground Truth
# ============================================================


def test_l3_snapshot_complete_ground_truth():
    """
    最终总检查。

    验证：

        Order count
        Bid level count
        Ask level count
        Active order IDs
    """


    official = (
        load_official_snapshot()
    )


    replay = rebuild_snapshot(

        official[
            "ts_recv"
        ]

    )


    book = (
        replay[
            "book"
        ]
    )


    official_bid_levels = (
        official[
            "levels"
        ][
            OrderSide.BID
        ]
    )


    official_ask_levels = (
        official[
            "levels"
        ][
            OrderSide.ASK
        ]
    )


    # ========================================================
    # Active Orders
    # ========================================================

    assert (
        len(
            book.orders
        )
        ==
        len(
            official[
                "orders"
            ]
        )
    )


    # ========================================================
    # Bid Levels
    # ========================================================

    assert (
        len(
            book.bids
        )
        ==
        len(
            official_bid_levels
        )
    )


    # ========================================================
    # Ask Levels
    # ========================================================

    assert (
        len(
            book.asks
        )
        ==
        len(
            official_ask_levels
        )
    )


    # ========================================================
    # Exact Order-ID Set
    # ========================================================

    assert (
        set(
            book.orders.keys()
        )
        ==
        set(
            official[
                "orders"
            ].keys()
        )
    )


    print()

    print(
        "=" * 100
    )

    print(
        "COMPLETE OFFICIAL L3 SNAPSHOT GROUND TRUTH PASSED"
    )

    print(
        "=" * 100
    )


    print(
        "snapshot ts_recv:",
        official[
            "ts_recv"
        ]
    )


    print(
        "snapshot records:",
        len(
            official[
                "records"
            ]
        )
    )


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