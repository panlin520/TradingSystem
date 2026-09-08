"""
tests/test_real_es_mbo_semantics.py

============================================================
Real ESU6 Databento MBO Semantics Audit
============================================================

目标：

    使用真实：

        ESU6_2026-06-15_MBO.dbn.zst

    审计 CME / Databento MBO 真实事件语义。

============================================================

重点检查：

    1. Action 分布

        A
        M
        C
        R
        T
        F
        N


    2. Cancel 真实行为

        当前订单 old_size
        C event.size

        分类：

            FULL_CANCEL

                C.size == old_size

            PARTIAL_CANCEL_CANDIDATE

                0 < C.size < old_size

            OVERSIZED_CANCEL

                C.size > old_size

            MISSING_ORDER

                C引用的order_id当前不存在


    3. Modify 真实行为

        old_price
        old_size
        old_side

            ↓

        new_price
        new_size
        new_side

        分类：

            SIZE_INCREASE
            SIZE_DECREASE
            SAME_SIZE

            PRICE_MOVE
            SAME_PRICE

            SIDE_CHANGE


    4. Trade

        T.side:

            B
            A
            None


    5. F_LAST

        flags & 128


    6. Sequence

        只观察：

            sequence decrease

        不假设 sequence 必须全局单调。

============================================================

IMPORTANT

    本文件：

        不修改：

            data/databento_feed.py
            core/event.py
            orderbook/*
            features/*

        不调用冻结Builder修改盘口。

        只对真实MBO事件做独立Shadow Audit。

============================================================

为什么不用当前OrderBook作为Cancel Ground Truth：

    当前我们正在调查：

        C.size < old_size

    到底在真实ESU6中是否存在。

    如果直接使用当前冻结OrderBook：

        C会直接删除order

    那么测试本身会受到待调查实现影响。

    因此：

        本测试维护独立shadow_orders。

============================================================

运行：

    默认扫描：

        1,000,000 events

    PowerShell：

        python -m pytest tests/test_real_es_mbo_semantics.py -v -s


    扫完整文件：

        $env:MBO_AUDIT_MAX_EVENTS="0"
        python -m pytest tests/test_real_es_mbo_semantics.py -v -s


    指定数量：

        $env:MBO_AUDIT_MAX_EVENTS="5000000"
        python -m pytest tests/test_real_es_mbo_semantics.py -v -s

============================================================
"""

from __future__ import annotations

import os

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import pytest

from core.event import (
    MarketEvent,
    OrderAction,
    OrderSide,
)

from data.databento_feed import DatabentoFeed


# ============================================================
# Configuration
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MBO_FILE = (
    PROJECT_ROOT
    / "data"
    / "ESU6_2026-06-15_MBO.dbn.zst"
)

MBO_FILE = Path(
    os.getenv(
        "MBO_AUDIT_FILE",
        str(DEFAULT_MBO_FILE),
    )
)

# 0 = 扫描完整文件
MAX_EVENTS = int(
    os.getenv(
        "MBO_AUDIT_MAX_EVENTS",
        "1000000",
    )
)

F_LAST = 128

MAX_EXAMPLES = 20


# ============================================================
# Shadow Order
# ============================================================


@dataclass
class ShadowOrder:
    """
    独立于生产OrderBook的审计订单。

    这里只保存：

        order_id
        side
        price
        size

    用于在M/C之前读取旧状态。
    """

    order_id: int
    side: Optional[OrderSide]
    price: Optional[int]
    size: int


# ============================================================
# Audit Result
# ============================================================


class AuditResult:
    """
    保存整个真实MBO审计结果。
    """

    def __init__(self):

        # ====================================================
        # 总事件
        # ====================================================

        self.total_events = 0

        self.action_counts = Counter()

        # ====================================================
        # Shadow Book
        # ====================================================

        self.orders: Dict[
            int,
            ShadowOrder,
        ] = {}

        self.max_active_orders = 0

        # ====================================================
        # Add
        # ====================================================

        self.add_missing_order_id = 0

        self.add_reused_order_id = 0

        # ====================================================
        # Modify
        # ====================================================

        self.modify_total = 0

        self.modify_found_order = 0

        self.modify_missing_order = 0

        self.modify_size_increase = 0

        self.modify_size_decrease = 0

        self.modify_size_same = 0

        self.modify_price_move = 0

        self.modify_price_same = 0

        self.modify_side_change = 0

        self.modify_side_same = 0

        self.modify_size_increase_volume = 0

        self.modify_size_decrease_volume = 0

        # ====================================================
        # Cancel
        # ====================================================

        self.cancel_total = 0

        self.cancel_found_order = 0

        self.cancel_missing_order = 0

        self.cancel_full = 0

        self.cancel_partial_candidate = 0

        self.cancel_oversized = 0

        self.cancel_zero_size = 0

        self.cancel_unknown_size = 0

        self.cancel_partial_volume = 0

        # ====================================================
        # Cancel follow-up
        # ====================================================

        # 用于判断：
        #
        # 一个 C.size < old_size 的订单，
        # 后面是否再次被 M/C/F 引用。
        #
        # 如果存在：
        #
        # 这是“该订单在C后仍存活”的强证据。

        self.pending_partial_cancel = {}

        self.partial_followup_modify = 0

        self.partial_followup_cancel = 0

        self.partial_followup_fill = 0

        self.partial_followup_other = 0

        self.partial_followup_readd = 0

        # ====================================================
        # Trade
        # ====================================================

        self.trade_total = 0

        self.trade_bid_side = 0

        self.trade_ask_side = 0

        self.trade_none_side = 0

        self.trade_other_side = 0

        self.trade_volume = 0

        self.trade_bid_volume = 0

        self.trade_ask_volume = 0

        self.trade_none_volume = 0

        # ====================================================
        # Fill
        # ====================================================

        self.fill_total = 0

        self.fill_found_order = 0

        self.fill_missing_order = 0

        # ====================================================
        # Reset
        # ====================================================

        self.reset_total = 0

        # ====================================================
        # F_LAST
        # ====================================================

        self.f_last_count = 0

        self.not_f_last_count = 0

        # ====================================================
        # Sequence
        # ====================================================

        self.sequence_first = None

        self.sequence_last = None

        self.sequence_decrease_count = 0

        self.sequence_equal_count = 0

        self.sequence_increase_count = 0

        self.sequence_max_backward_jump = 0

        # ====================================================
        # Examples
        # ====================================================

        self.partial_cancel_examples = []

        self.full_cancel_examples = []

        self.oversized_cancel_examples = []

        self.missing_cancel_examples = []

        self.modify_increase_examples = []

        self.modify_decrease_examples = []

        self.modify_price_move_examples = []

        self.modify_side_change_examples = []

        self.partial_followup_examples = []

        self.sequence_decrease_examples = []


# ============================================================
# Helpers
# ============================================================


def safe_int(
    value,
    default=0,
):
    """
    None安全整数转换。
    """

    if value is None:
        return default

    try:
        return int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


def side_name(
    side,
):
    """
    输出side可读值。
    """

    if side is None:
        return None

    try:
        return side.value

    except Exception:
        return str(
            side
        )


def action_name(
    action,
):
    """
    输出action可读值。
    """

    try:
        return action.value

    except Exception:
        return str(
            action
        )


def append_example(
    container,
    value,
):
    """
    限制诊断样本数量，
    防止完整日扫描占用大量内存。
    """

    if len(
        container
    ) < MAX_EXAMPLES:

        container.append(
            value
        )


# ============================================================
# Sequence Audit
# ============================================================


def audit_sequence(
    result: AuditResult,
    event: MarketEvent,
):
    """
    只观察sequence。

    IMPORTANT：

        sequence不作为本测试排序依据。

    我们完全保留Feed原始输入顺序。
    """

    sequence = safe_int(
        event.sequence,
        0,
    )

    if result.sequence_first is None:

        result.sequence_first = sequence

        result.sequence_last = sequence

        return

    previous = result.sequence_last

    if sequence > previous:

        result.sequence_increase_count += 1

    elif sequence == previous:

        result.sequence_equal_count += 1

    else:

        result.sequence_decrease_count += 1

        backward_jump = (
            previous
            -
            sequence
        )

        result.sequence_max_backward_jump = max(
            result.sequence_max_backward_jump,
            backward_jump,
        )

        append_example(
            result.sequence_decrease_examples,
            {
                "event_number":
                    result.total_events,

                "previous_sequence":
                    previous,

                "current_sequence":
                    sequence,

                "backward_jump":
                    backward_jump,

                "action":
                    action_name(
                        event.action
                    ),

                "order_id":
                    event.order_id,

                "instrument_id":
                    event.instrument_id,

                "channel_id":
                    event.channel_id,
            },
        )

    result.sequence_last = sequence


# ============================================================
# F_LAST Audit
# ============================================================


def audit_f_last(
    result: AuditResult,
    event: MarketEvent,
):
    """
    F_LAST = bit 7 = 128
    """

    flags = safe_int(
        event.flags,
        0,
    )

    if (
        flags
        &
        F_LAST
    ):

        result.f_last_count += 1

    else:

        result.not_f_last_count += 1


# ============================================================
# Partial Cancel Follow-up
# ============================================================


def audit_partial_followup(
    result: AuditResult,
    event: MarketEvent,
):
    """
    检查之前出现的：

        C.size < old_size

    对应order_id是否再次被后续事件引用。

    这对判断真实C语义非常重要。
    """

    order_id = event.order_id

    if order_id is None:

        return

    if order_id not in (
        result.pending_partial_cancel
    ):

        return

    previous = (
        result.pending_partial_cancel[
            order_id
        ]
    )

    # 当前这个事件本身就是
    # 创建pending记录的那条C，
    # 不算follow-up。

    if (
        previous[
            "event_number"
        ]
        ==
        result.total_events
    ):

        return

    action = action_name(
        event.action
    )

    example = {
        "original_cancel":
            previous,

        "followup_event_number":
            result.total_events,

        "followup_action":
            action,

        "followup_size":
            event.size,

        "followup_price":
            event.price,

        "followup_side":
            side_name(
                event.side
            ),
    }

    if event.action == OrderAction.MODIFY:

        result.partial_followup_modify += 1

    elif event.action == OrderAction.CANCEL:

        result.partial_followup_cancel += 1

    elif event.action == OrderAction.FILL:

        result.partial_followup_fill += 1

    elif event.action == OrderAction.ADD:

        result.partial_followup_readd += 1

    else:

        result.partial_followup_other += 1

    append_example(
        result.partial_followup_examples,
        example,
    )

    # 只记录第一次follow-up，
    # 防止同一个candidate反复计数。

    result.pending_partial_cancel.pop(
        order_id,
        None,
    )


# ============================================================
# ADD
# ============================================================


def audit_add(
    result: AuditResult,
    event: MarketEvent,
):
    """
    Shadow ADD。
    """

    order_id = event.order_id

    if order_id is None:

        result.add_missing_order_id += 1

        return

    if order_id in result.orders:

        result.add_reused_order_id += 1

    size = safe_int(
        event.size,
        0,
    )

    result.orders[
        order_id
    ] = ShadowOrder(
        order_id=order_id,
        side=event.side,
        price=event.price,
        size=size,
    )

    result.max_active_orders = max(
        result.max_active_orders,
        len(
            result.orders
        ),
    )


# ============================================================
# MODIFY
# ============================================================


def audit_modify(
    result: AuditResult,
    event: MarketEvent,
):
    """
    审计真实M事件。

    Ground Truth候选语义：

        event.size = 新size

    我们重点统计：

        old -> new
    """

    result.modify_total += 1

    order_id = event.order_id

    if (
        order_id is None
        or
        order_id not in result.orders
    ):

        result.modify_missing_order += 1

        return

    result.modify_found_order += 1

    order = result.orders[
        order_id
    ]

    old_size = order.size

    old_price = order.price

    old_side = order.side

    new_size = (
        safe_int(
            event.size,
            old_size,
        )
        if event.size is not None
        else old_size
    )

    new_price = (
        event.price
        if event.price is not None
        else old_price
    )

    new_side = (
        event.side
        if event.side is not None
        else old_side
    )

    # ========================================================
    # Size
    # ========================================================

    if new_size > old_size:

        result.modify_size_increase += 1

        delta = (
            new_size
            -
            old_size
        )

        result.modify_size_increase_volume += (
            delta
        )

        append_example(
            result.modify_increase_examples,
            {
                "event_number":
                    result.total_events,

                "sequence":
                    event.sequence,

                "order_id":
                    order_id,

                "side":
                    side_name(
                        old_side
                    ),

                "price":
                    old_price,

                "old_size":
                    old_size,

                "event_size":
                    event.size,

                "new_size":
                    new_size,

                "delta":
                    delta,
            },
        )

    elif new_size < old_size:

        result.modify_size_decrease += 1

        delta = (
            old_size
            -
            new_size
        )

        result.modify_size_decrease_volume += (
            delta
        )

        append_example(
            result.modify_decrease_examples,
            {
                "event_number":
                    result.total_events,

                "sequence":
                    event.sequence,

                "order_id":
                    order_id,

                "side":
                    side_name(
                        old_side
                    ),

                "price":
                    old_price,

                "old_size":
                    old_size,

                "event_size":
                    event.size,

                "new_size":
                    new_size,

                "removed_delta":
                    delta,
            },
        )

    else:

        result.modify_size_same += 1

    # ========================================================
    # Price
    # ========================================================

    if new_price != old_price:

        result.modify_price_move += 1

        append_example(
            result.modify_price_move_examples,
            {
                "event_number":
                    result.total_events,

                "sequence":
                    event.sequence,

                "order_id":
                    order_id,

                "side":
                    side_name(
                        old_side
                    ),

                "old_price":
                    old_price,

                "new_price":
                    new_price,

                "old_size":
                    old_size,

                "new_size":
                    new_size,
            },
        )

    else:

        result.modify_price_same += 1

    # ========================================================
    # Side
    # ========================================================

    if new_side != old_side:

        result.modify_side_change += 1

        append_example(
            result.modify_side_change_examples,
            {
                "event_number":
                    result.total_events,

                "sequence":
                    event.sequence,

                "order_id":
                    order_id,

                "old_side":
                    side_name(
                        old_side
                    ),

                "new_side":
                    side_name(
                        new_side
                    ),

                "price":
                    new_price,

                "size":
                    new_size,
            },
        )

    else:

        result.modify_side_same += 1

    # ========================================================
    # Shadow update
    # ========================================================

    order.size = new_size

    order.price = new_price

    order.side = new_side


# ============================================================
# CANCEL
# ============================================================


def audit_cancel(
    result: AuditResult,
    event: MarketEvent,
):
    """
    这是本测试最重要的部分。

    在处理C之前读取：

        old_size

    然后比较：

        C.size

    注意：

        这里不使用生产OrderBook.cancel_order()。
    """

    result.cancel_total += 1

    order_id = event.order_id

    if (
        order_id is None
        or
        order_id not in result.orders
    ):

        result.cancel_missing_order += 1

        append_example(
            result.missing_cancel_examples,
            {
                "event_number":
                    result.total_events,

                "sequence":
                    event.sequence,

                "order_id":
                    order_id,

                "event_size":
                    event.size,

                "price":
                    event.price,

                "side":
                    side_name(
                        event.side
                    ),
            },
        )

        return

    result.cancel_found_order += 1

    order = result.orders[
        order_id
    ]

    old_size = order.size

    cancel_size = event.size

    # ========================================================
    # Unknown C.size
    # ========================================================

    if cancel_size is None:

        result.cancel_unknown_size += 1

        result.orders.pop(
            order_id,
            None,
        )

        return

    cancel_size = safe_int(
        cancel_size,
        0,
    )

    # ========================================================
    # Zero C
    # ========================================================

    if cancel_size == 0:

        result.cancel_zero_size += 1

        # 不自行猜测。
        #
        # 为保持审计继续，
        # 当前shadow把订单删除。
        result.orders.pop(
            order_id,
            None,
        )

        return

    # ========================================================
    # Exact Full Cancel
    # ========================================================

    if cancel_size == old_size:

        result.cancel_full += 1

        append_example(
            result.full_cancel_examples,
            {
                "event_number":
                    result.total_events,

                "sequence":
                    event.sequence,

                "order_id":
                    order_id,

                "side":
                    side_name(
                        order.side
                    ),

                "price":
                    order.price,

                "old_size":
                    old_size,

                "cancel_size":
                    cancel_size,
            },
        )

        result.orders.pop(
            order_id,
            None,
        )

        return

    # ========================================================
    # Candidate Partial Cancel
    # ========================================================

    if (
        0
        <
        cancel_size
        <
        old_size
    ):

        result.cancel_partial_candidate += 1

        result.cancel_partial_volume += (
            cancel_size
        )

        example = {
            "event_number":
                result.total_events,

            "sequence":
                event.sequence,

            "order_id":
                order_id,

            "side":
                side_name(
                    order.side
                ),

            "price":
                order.price,

            "old_size":
                old_size,

            "cancel_size":
                cancel_size,

            "candidate_remaining":
                (
                    old_size
                    -
                    cancel_size
                ),
        }

        append_example(
            result.partial_cancel_examples,
            example,
        )

        # ----------------------------------------------------
        # 保存candidate，后续观察该order_id
        # 是否继续出现M/C/F。
        # ----------------------------------------------------

        result.pending_partial_cancel[
            order_id
        ] = example

        # ----------------------------------------------------
        # Shadow使用partial-cancel假设继续。
        #
        # 这样可以观察：
        # 如果后续再次出现同order_id，
        # 是否与remaining状态连贯。
        # ----------------------------------------------------

        order.size = (
            old_size
            -
            cancel_size
        )

        return

    # ========================================================
    # Oversized
    # ========================================================

    if cancel_size > old_size:

        result.cancel_oversized += 1

        append_example(
            result.oversized_cancel_examples,
            {
                "event_number":
                    result.total_events,

                "sequence":
                    event.sequence,

                "order_id":
                    order_id,

                "side":
                    side_name(
                        order.side
                    ),

                "price":
                    order.price,

                "old_size":
                    old_size,

                "cancel_size":
                    cancel_size,
            },
        )

        result.orders.pop(
            order_id,
            None,
        )


# ============================================================
# TRADE
# ============================================================


def audit_trade(
    result: AuditResult,
    event: MarketEvent,
):
    """
    统计真实T side。
    """

    result.trade_total += 1

    size = safe_int(
        event.size,
        0,
    )

    result.trade_volume += (
        size
    )

    if event.side == OrderSide.BID:

        result.trade_bid_side += 1

        result.trade_bid_volume += (
            size
        )

    elif event.side == OrderSide.ASK:

        result.trade_ask_side += 1

        result.trade_ask_volume += (
            size
        )

    elif event.side is None:

        result.trade_none_side += 1

        result.trade_none_volume += (
            size
        )

    else:

        result.trade_other_side += 1


# ============================================================
# FILL
# ============================================================


def audit_fill(
    result: AuditResult,
    event: MarketEvent,
):
    """
    Fill不主动改变shadow订单。

    这里只统计：

        F引用的order_id
        是否仍在shadow中。
    """

    result.fill_total += 1

    order_id = event.order_id

    if (
        order_id is not None
        and
        order_id in result.orders
    ):

        result.fill_found_order += 1

    else:

        result.fill_missing_order += 1


# ============================================================
# RESET
# ============================================================


def audit_reset(
    result: AuditResult,
):
    """
    Reset是state boundary。
    """

    result.reset_total += 1

    result.orders.clear()

    result.pending_partial_cancel.clear()


# ============================================================
# Audit Event
# ============================================================


def audit_event(
    result: AuditResult,
    event: MarketEvent,
):
    """
    处理一个真实MarketEvent。
    """

    result.total_events += 1

    # ========================================================
    # 基础统计
    # ========================================================

    action = action_name(
        event.action
    )

    result.action_counts[
        action
    ] += 1

    audit_sequence(
        result,
        event,
    )

    audit_f_last(
        result,
        event,
    )

    # ========================================================
    # 先检查candidate partial cancel后续引用
    # ========================================================

    audit_partial_followup(
        result,
        event,
    )

    # ========================================================
    # Action
    # ========================================================

    if event.action == OrderAction.ADD:

        audit_add(
            result,
            event,
        )

    elif event.action == OrderAction.MODIFY:

        audit_modify(
            result,
            event,
        )

    elif event.action == OrderAction.CANCEL:

        audit_cancel(
            result,
            event,
        )

    elif event.action == OrderAction.TRADE:

        audit_trade(
            result,
            event,
        )

    elif event.action == OrderAction.FILL:

        audit_fill(
            result,
            event,
        )

    elif event.action == OrderAction.RESET:

        audit_reset(
            result,
        )

    elif event.action == OrderAction.NONE:

        pass


# ============================================================
# Full Audit
# ============================================================


def run_real_mbo_audit():
    """
    扫描真实ESU6 MBO。
    """

    assert MBO_FILE.exists(), (
        "\n"
        "MBO文件不存在：\n"
        f"{MBO_FILE}\n"
    )

    feed = DatabentoFeed(
        file_path=str(
            MBO_FILE
        ),
        symbol="ESU6",
    )

    result = AuditResult()

    print(
        "\n"
        "============================================================"
    )

    print(
        "REAL ESU6 MBO SEMANTICS AUDIT"
    )

    print(
        "============================================================"
    )

    print(
        "File:",
        MBO_FILE
    )

    print(
        "Max Events:",
        (
            "FULL FILE"
            if MAX_EVENTS == 0
            else f"{MAX_EVENTS:,}"
        )
    )

    print(
        "============================================================"
    )

    for event in feed:

        audit_event(
            result,
            event,
        )

        # ====================================================
        # Progress
        # ====================================================

        if (
            result.total_events
            %
            500_000
            ==
            0
        ):

            print(
                f"Processed: "
                f"{result.total_events:,}"
            )

        # ====================================================
        # Limit
        # ====================================================

        if (
            MAX_EVENTS
            >
            0
            and
            result.total_events
            >=
            MAX_EVENTS
        ):

            break

    return result


# ============================================================
# Percentage
# ============================================================


def percent(
    value,
    total,
):
    """
    百分比格式。
    """

    if total == 0:

        return "0.0000%"

    return (
        f"{value / total * 100:.4f}%"
    )


# ============================================================
# Print Examples
# ============================================================


def print_examples(
    title,
    examples,
):
    """
    打印诊断样本。
    """

    print(
        "\n"
        f"{title}:"
    )

    if not examples:

        print(
            "    NONE"
        )

        return

    for index, example in enumerate(
        examples,
        start=1,
    ):

        print(
            f"    [{index}] "
            f"{example}"
        )


# ============================================================
# Print Audit Report
# ============================================================


def print_report(
    result: AuditResult,
):
    """
    打印完整审计报告。
    """

    print(
        "\n"
        "\n"
        "============================================================"
    )

    print(
        "REAL ESU6 MBO AUDIT RESULT"
    )

    print(
        "============================================================"
    )

    print(
        f"Total Events: "
        f"{result.total_events:,}"
    )

    print(
        f"Active Shadow Orders: "
        f"{len(result.orders):,}"
    )

    print(
        f"Max Active Orders: "
        f"{result.max_active_orders:,}"
    )

    # ========================================================
    # Actions
    # ========================================================

    print(
        "\n"
        "------------------------------------------------------------"
    )

    print(
        "ACTION COUNTS"
    )

    print(
        "------------------------------------------------------------"
    )

    for action in (
        "A",
        "M",
        "C",
        "R",
        "T",
        "F",
        "N",
    ):

        count = result.action_counts[
            action
        ]

        print(
            f"{action}: "
            f"{count:,} "
            f"({percent(count, result.total_events)})"
        )

    # ========================================================
    # Cancel
    # ========================================================

    print(
        "\n"
        "------------------------------------------------------------"
    )

    print(
        "CANCEL AUDIT"
    )

    print(
        "------------------------------------------------------------"
    )

    print(
        f"Cancel Total: "
        f"{result.cancel_total:,}"
    )

    print(
        f"Found Existing Order: "
        f"{result.cancel_found_order:,}"
    )

    print(
        f"Missing Order: "
        f"{result.cancel_missing_order:,}"
    )

    print(
        f"Full Cancel "
        f"(C.size == old_size): "
        f"{result.cancel_full:,}"
    )

    print(
        f"Partial Cancel Candidate "
        f"(0 < C.size < old_size): "
        f"{result.cancel_partial_candidate:,}"
    )

    print(
        f"Partial Candidate Rate: "
        f"{percent(
            result.cancel_partial_candidate,
            result.cancel_found_order
        )}"
    )

    print(
        f"Partial Cancel Volume: "
        f"{result.cancel_partial_volume:,}"
    )

    print(
        f"Oversized Cancel "
        f"(C.size > old_size): "
        f"{result.cancel_oversized:,}"
    )

    print(
        f"Zero-size Cancel: "
        f"{result.cancel_zero_size:,}"
    )

    print(
        f"Unknown-size Cancel: "
        f"{result.cancel_unknown_size:,}"
    )

    # ========================================================
    # Partial followup
    # ========================================================

    print(
        "\n"
        "Partial Cancel Follow-up:"
    )

    print(
        f"    Followed by MODIFY: "
        f"{result.partial_followup_modify:,}"
    )

    print(
        f"    Followed by CANCEL: "
        f"{result.partial_followup_cancel:,}"
    )

    print(
        f"    Followed by FILL: "
        f"{result.partial_followup_fill:,}"
    )

    print(
        f"    Followed by ADD: "
        f"{result.partial_followup_readd:,}"
    )

    print(
        f"    Followed by Other: "
        f"{result.partial_followup_other:,}"
    )

    print(
        f"    Still Pending at End: "
        f"{len(result.pending_partial_cancel):,}"
    )

    # ========================================================
    # Modify
    # ========================================================

    print(
        "\n"
        "------------------------------------------------------------"
    )

    print(
        "MODIFY AUDIT"
    )

    print(
        "------------------------------------------------------------"
    )

    print(
        f"Modify Total: "
        f"{result.modify_total:,}"
    )

    print(
        f"Found Existing Order: "
        f"{result.modify_found_order:,}"
    )

    print(
        f"Missing Order: "
        f"{result.modify_missing_order:,}"
    )

    print(
        f"Size Increase: "
        f"{result.modify_size_increase:,}"
    )

    print(
        f"Size Increase Volume: "
        f"{result.modify_size_increase_volume:,}"
    )

    print(
        f"Size Decrease: "
        f"{result.modify_size_decrease:,}"
    )

    print(
        f"Size Decrease Volume: "
        f"{result.modify_size_decrease_volume:,}"
    )

    print(
        f"Same Size: "
        f"{result.modify_size_same:,}"
    )

    print(
        f"Price Move: "
        f"{result.modify_price_move:,}"
    )

    print(
        f"Same Price: "
        f"{result.modify_price_same:,}"
    )

    print(
        f"Side Change: "
        f"{result.modify_side_change:,}"
    )

    print(
        f"Same Side: "
        f"{result.modify_side_same:,}"
    )

    # ========================================================
    # Trade
    # ========================================================

    print(
        "\n"
        "------------------------------------------------------------"
    )

    print(
        "TRADE SIDE AUDIT"
    )

    print(
        "------------------------------------------------------------"
    )

    print(
        f"Trade Total: "
        f"{result.trade_total:,}"
    )

    print(
        f"T.side=B: "
        f"{result.trade_bid_side:,} "
        f"({percent(
            result.trade_bid_side,
            result.trade_total
        )})"
    )

    print(
        f"T.side=A: "
        f"{result.trade_ask_side:,} "
        f"({percent(
            result.trade_ask_side,
            result.trade_total
        )})"
    )

    print(
        f"T.side=None: "
        f"{result.trade_none_side:,} "
        f"({percent(
            result.trade_none_side,
            result.trade_total
        )})"
    )

    print(
        f"T.side=Other: "
        f"{result.trade_other_side:,}"
    )

    print(
        f"Trade Volume: "
        f"{result.trade_volume:,}"
    )

    print(
        f"Bid-side Trade Volume: "
        f"{result.trade_bid_volume:,}"
    )

    print(
        f"Ask-side Trade Volume: "
        f"{result.trade_ask_volume:,}"
    )

    print(
        f"None-side Trade Volume: "
        f"{result.trade_none_volume:,}"
    )

    # ========================================================
    # Fill
    # ========================================================

    print(
        "\n"
        "------------------------------------------------------------"
    )

    print(
        "FILL AUDIT"
    )

    print(
        "------------------------------------------------------------"
    )

    print(
        f"Fill Total: "
        f"{result.fill_total:,}"
    )

    print(
        f"Fill Existing Order: "
        f"{result.fill_found_order:,}"
    )

    print(
        f"Fill Missing Order: "
        f"{result.fill_missing_order:,}"
    )

    # ========================================================
    # F_LAST
    # ========================================================

    print(
        "\n"
        "------------------------------------------------------------"
    )

    print(
        "F_LAST AUDIT"
    )

    print(
        "------------------------------------------------------------"
    )

    print(
        f"F_LAST: "
        f"{result.f_last_count:,} "
        f"({percent(
            result.f_last_count,
            result.total_events
        )})"
    )

    print(
        f"Not F_LAST: "
        f"{result.not_f_last_count:,} "
        f"({percent(
            result.not_f_last_count,
            result.total_events
        )})"
    )

    # ========================================================
    # Sequence
    # ========================================================

    print(
        "\n"
        "------------------------------------------------------------"
    )

    print(
        "SEQUENCE AUDIT"
    )

    print(
        "------------------------------------------------------------"
    )

    print(
        f"First Sequence: "
        f"{result.sequence_first}"
    )

    print(
        f"Last Sequence: "
        f"{result.sequence_last}"
    )

    print(
        f"Sequence Increase: "
        f"{result.sequence_increase_count:,}"
    )

    print(
        f"Sequence Equal: "
        f"{result.sequence_equal_count:,}"
    )

    print(
        f"Sequence Decrease: "
        f"{result.sequence_decrease_count:,}"
    )

    print(
        f"Maximum Backward Jump: "
        f"{result.sequence_max_backward_jump:,}"
    )

    # ========================================================
    # Examples
    # ========================================================

    print(
        "\n"
        "============================================================"
    )

    print(
        "DIAGNOSTIC EXAMPLES"
    )

    print(
        "============================================================"
    )

    print_examples(
        "Partial Cancel Candidates",
        result.partial_cancel_examples,
    )

    print_examples(
        "Partial Cancel Follow-up",
        result.partial_followup_examples,
    )

    print_examples(
        "Oversized Cancels",
        result.oversized_cancel_examples,
    )

    print_examples(
        "Missing Cancels",
        result.missing_cancel_examples,
    )

    print_examples(
        "Modify Size Increase",
        result.modify_increase_examples,
    )

    print_examples(
        "Modify Size Decrease",
        result.modify_decrease_examples,
    )

    print_examples(
        "Modify Price Move",
        result.modify_price_move_examples,
    )

    print_examples(
        "Modify Side Change",
        result.modify_side_change_examples,
    )

    print_examples(
        "Sequence Decrease",
        result.sequence_decrease_examples,
    )

    print(
        "\n"
        "============================================================"
    )


# ============================================================
# Pytest Fixture
# ============================================================


@pytest.fixture(
    scope="module"
)
def real_mbo_audit():
    """
    整个测试模块只扫描一次DBN。

    否则每个test重新扫一遍100万事件，
    会非常慢。
    """

    result = run_real_mbo_audit()

    print_report(
        result
    )

    return result


# ============================================================
# Test 1
# ============================================================


def test_real_mbo_file_exists():
    """
    数据文件必须存在。
    """

    assert MBO_FILE.exists()

    assert MBO_FILE.is_file()


# ============================================================
# Test 2
# ============================================================


def test_real_mbo_events_are_read(
    real_mbo_audit,
):
    """
    必须真的读取到事件。
    """

    assert (
        real_mbo_audit.total_events
        >
        0
    )


# ============================================================
# Test 3
# ============================================================


def test_real_mbo_contains_book_actions(
    real_mbo_audit,
):
    """
    必须存在真实盘口事件。
    """

    assert (
        real_mbo_audit.action_counts[
            "A"
        ]
        >
        0
    )

    assert (
        real_mbo_audit.action_counts[
            "M"
        ]
        >
        0
    )

    assert (
        real_mbo_audit.action_counts[
            "C"
        ]
        >
        0
    )


# ============================================================
# Test 4
# ============================================================


def test_real_mbo_contains_trades(
    real_mbo_audit,
):
    """
    必须存在真实Trade。
    """

    assert (
        real_mbo_audit.trade_total
        >
        0
    )


# ============================================================
# Test 5
# ============================================================


def test_real_mbo_contains_f_last(
    real_mbo_audit,
):
    """
    必须观察到真实F_LAST。
    """

    assert (
        real_mbo_audit.f_last_count
        >
        0
    )


# ============================================================
# Test 6
# ============================================================


def test_trade_side_distribution_is_observable(
    real_mbo_audit,
):
    """
    这里只要求真实T side数据可观察。

    不强行要求B/A比例。
    """

    observed = (
        real_mbo_audit.trade_bid_side
        +
        real_mbo_audit.trade_ask_side
        +
        real_mbo_audit.trade_none_side
        +
        real_mbo_audit.trade_other_side
    )

    assert observed == (
        real_mbo_audit.trade_total
    )


# ============================================================
# Test 7
# ============================================================


def test_modify_classification_is_complete(
    real_mbo_audit,
):
    """
    对存在旧订单状态的Modify：

        increase
        decrease
        same

    三种分类总和必须完整。
    """

    classified = (
        real_mbo_audit.modify_size_increase
        +
        real_mbo_audit.modify_size_decrease
        +
        real_mbo_audit.modify_size_same
    )

    assert classified == (
        real_mbo_audit.modify_found_order
    )


# ============================================================
# Test 8
# ============================================================


def test_modify_price_classification_is_complete(
    real_mbo_audit,
):
    """
    Price：

        move
        same

    必须完整。
    """

    classified = (
        real_mbo_audit.modify_price_move
        +
        real_mbo_audit.modify_price_same
    )

    assert classified == (
        real_mbo_audit.modify_found_order
    )


# ============================================================
# Test 9
# ============================================================


def test_cancel_classification_is_complete(
    real_mbo_audit,
):
    """
    对成功找到旧订单的C：

        full
        partial candidate
        oversized
        zero
        unknown

    分类总和必须完整。
    """

    classified = (
        real_mbo_audit.cancel_full
        +
        real_mbo_audit.cancel_partial_candidate
        +
        real_mbo_audit.cancel_oversized
        +
        real_mbo_audit.cancel_zero_size
        +
        real_mbo_audit.cancel_unknown_size
    )

    assert classified == (
        real_mbo_audit.cancel_found_order
    )


# ============================================================
# Test 10
# ============================================================


def test_print_critical_semantic_conclusion(
    real_mbo_audit,
):
    """
    最重要的结论测试。

    这里不强制：

        partial C必须存在

    也不强制：

        partial C必须不存在

    因为我们现在正是在真实数据中调查它。

    使用 -s 查看结论。
    """

    result = real_mbo_audit

    print(
        "\n"
        "\n"
        "============================================================"
    )

    print(
        "CRITICAL SEMANTIC CONCLUSION"
    )

    print(
        "============================================================"
    )

    # ========================================================
    # Cancel
    # ========================================================

    if (
        result.cancel_partial_candidate
        >
        0
    ):

        print(
            "\n"
            "[CANCEL]"
        )

        print(
            "REAL ESU6 DATA CONTAINS:"
        )

        print(
            "    0 < C.size < old_size"
        )

        print(
            "Count:",
            result.cancel_partial_candidate
        )

        followups = (
            result.partial_followup_modify
            +
            result.partial_followup_cancel
            +
            result.partial_followup_fill
        )

        print(
            "Subsequent M/C/F references "
            "to candidate orders:",
            followups
        )

        if followups > 0:

            print(
                "\n"
                "IMPORTANT:"
            )

            print(
                "Candidate partial-C orders "
                "were referenced again later."
            )

            print(
                "This is strong evidence that "
                "C did not always mean "
                "'delete entire order'."
            )

        print(
            "\n"
            "Frozen OrderBook.cancel_order() "
            "requires dedicated Ground Truth review."
        )

    else:

        print(
            "\n"
            "[CANCEL]"
        )

        print(
            "No 0 < C.size < old_size "
            "candidate observed "
            "in the scanned range."
        )

        print(
            "Do NOT conclude impossible yet "
            "unless the full DBN file was scanned."
        )

    # ========================================================
    # Modify
    # ========================================================

    print(
        "\n"
        "[MODIFY]"
    )

    print(
        "Size Increase:",
        result.modify_size_increase
    )

    print(
        "Size Decrease:",
        result.modify_size_decrease
    )

    print(
        "Price Move:",
        result.modify_price_move
    )

    print(
        "Side Change:",
        result.modify_side_change
    )

    if (
        result.modify_size_increase
        >
        0
        or
        result.modify_size_decrease
        >
        0
        or
        result.modify_price_move
        >
        0
    ):

        print(
            "\n"
            "Feature Flow must preserve "
            "pre-modify state to calculate "
            "true liquidity delta."
        )

    # ========================================================
    # OFI implication
    # ========================================================

    print(
        "\n"
        "[FEATURE / OFI]"
    )

    print(
        "Current Feature Flow cannot derive "
        "complete signed order flow "
        "from M.size alone."
    )

    print(
        "============================================================"
    )

    assert (
        result.total_events
        >
        0
    )