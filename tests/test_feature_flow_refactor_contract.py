"""
tests/test_feature_flow_refactor_contract.py

============================================================
Feature Flow Engine Refactor Contract
============================================================

目标：

    为 Feature Flow Engine 重构建立新的明确契约。

============================================================

真实 ESU6 全日审计已经确认：

    Total MBO:
        10,417,106

    Cancel:
        4,111,285

        所有真实C：
            C.size == current order size

        Partial C:
            0

    Modify:
        1,145,108

        Size Increase:
            93,343

        Size Decrease:
            190,731

        Price Move:
            1,051,814

        Side Change:
            0

============================================================

因此新的 FlowFeatures 必须：

    1. 自己维护轻量 Shadow Order State

        order_id
        side
        price
        size

    2. A：

        记录真实新增流动性

    3. C：

        记录真实移除流动性

    4. M Size Increase：

        old_size=10
        new_size=15

        added += 5

    5. M Size Decrease：

        old_size=10
        new_size=6

        removed += 4

    6. M Price Move：

        Bid 100 @ 10
            ↓
        Bid 101 @ 10

        old price:
            removed += 10

        new price:
            added += 10

    7. signed directional flow：

        Bid Add       = positive
        Bid Remove    = negative

        Ask Add       = negative
        Ask Remove    = positive

    8. OFI：

        必须是方向性的 signed flow metric。

        不能继续把：

            total added - total removed

        直接称为 directional OFI。

    9. liquidity_balance：

        保留：

            (added - removed)
            /
            (added + removed)

        但它必须与 OFI 分离。

    10. RESET：

        清空 Shadow Order State。

============================================================

冻结层：

    data/*
    core/*
    orderbook/*

本测试不修改冻结层。

============================================================
"""

import pytest

from core.event import (
    MarketEvent,
    OrderAction,
    OrderSide,
)

from features.flow_features import FlowFeatures
from features.snapshot import FeatureSnapshot


# ============================================================
# Event Factory
# ============================================================


def make_event(
    *,
    sequence,
    action,
    side=None,
    order_id=None,
    price=None,
    size=None,
    flags=128,
    symbol="ESU6",
):
    """
    创建真实 MarketEvent。
    """

    return MarketEvent(
        ts_event=sequence,
        ts_recv=sequence,
        sequence=sequence,
        action=action,
        side=side,
        order_id=order_id,
        price=price,
        size=size,
        symbol=symbol,
        channel_id=0,
        publisher_id=1,
        instrument_id=1,
        flags=flags,
    )


# ============================================================
# Helpers
# ============================================================


def make_flow():
    """
    创建新的FlowFeatures。
    """

    return FlowFeatures()


def make_snapshot():
    """
    创建新的FeatureSnapshot。
    """

    return FeatureSnapshot()


def apply(
    flow,
    snapshot,
    event,
):
    """
    调用FlowFeatures。
    """

    return flow.update(
        event,
        snapshot,
    )


# ============================================================
# Snapshot Contract
# ============================================================


def test_snapshot_has_new_flow_fields():
    """
    重构后的Snapshot必须明确区分：

        liquidity balance
        directional OFI
        signed raw flow
    """

    snapshot = FeatureSnapshot()

    assert hasattr(
        snapshot,
        "liquidity_balance"
    )

    assert hasattr(
        snapshot,
        "signed_order_flow"
    )

    assert hasattr(
        snapshot,
        "bid_added_volume"
    )

    assert hasattr(
        snapshot,
        "bid_removed_volume"
    )

    assert hasattr(
        snapshot,
        "ask_added_volume"
    )

    assert hasattr(
        snapshot,
        "ask_removed_volume"
    )

    assert hasattr(
        snapshot,
        "modify_added_volume"
    )

    assert hasattr(
        snapshot,
        "modify_removed_volume"
    )

    assert hasattr(
        snapshot,
        "price_move_count"
    )

    assert hasattr(
        snapshot,
        "price_move_added_volume"
    )

    assert hasattr(
        snapshot,
        "price_move_removed_volume"
    )


# ============================================================
# ADD Bid
# ============================================================


def test_bid_add_flow():
    """
    Bid Add：

        liquidity_added += 10
        bid_added += 10

        directional signed flow += 10
    """

    flow = make_flow()
    snapshot = make_snapshot()

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    assert snapshot.add_volume == 10

    assert snapshot.liquidity_added == 10
    assert snapshot.liquidity_removed == 0

    assert snapshot.bid_added_volume == 10
    assert snapshot.bid_removed_volume == 0

    assert snapshot.ask_added_volume == 0
    assert snapshot.ask_removed_volume == 0

    assert snapshot.signed_order_flow == 10

    assert snapshot.ofi == pytest.approx(
        1.0
    )

    assert snapshot.liquidity_balance == pytest.approx(
        1.0
    )


# ============================================================
# ADD Ask
# ============================================================


def test_ask_add_flow():
    """
    Ask Add：

        liquidity_added += 10
        ask_added += 10

        directional signed flow -= 10
    """

    flow = make_flow()
    snapshot = make_snapshot()

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=1,
            price=102,
            size=10,
        ),
    )

    assert snapshot.liquidity_added == 10

    assert snapshot.ask_added_volume == 10

    assert snapshot.signed_order_flow == -10

    assert snapshot.ofi == pytest.approx(
        -1.0
    )

    # Add/Remove balance仍然是+1，
    # 但方向OFI为-1。
    #
    # 这正是两个指标必须拆开的原因。

    assert snapshot.liquidity_balance == pytest.approx(
        1.0
    )


# ============================================================
# Symmetric Add
# ============================================================


def test_symmetric_bid_ask_add_has_zero_directional_ofi():
    """
    Bid +10
    Ask +10

    方向完全对称。

    正确：

        signed_order_flow = 0
        OFI = 0

    旧实现：

        OFI = +1

    是错误语义。
    """

    flow = make_flow()
    snapshot = make_snapshot()

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=2,
            price=102,
            size=10,
        ),
    )

    assert snapshot.bid_added_volume == 10
    assert snapshot.ask_added_volume == 10

    assert snapshot.liquidity_added == 20

    assert snapshot.signed_order_flow == 0

    assert snapshot.ofi == pytest.approx(
        0.0
    )

    assert snapshot.liquidity_balance == pytest.approx(
        1.0
    )


# ============================================================
# CANCEL Bid
# ============================================================


def test_bid_cancel_flow():
    """
    Bid Add 10
        ↓
    Bid Cancel 10

    Bid Remove：

        directional -= 10

    累计signed：

        +10 - 10 = 0
    """

    flow = make_flow()
    snapshot = make_snapshot()

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.CANCEL,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    assert snapshot.cancel_volume == 10

    assert snapshot.liquidity_added == 10
    assert snapshot.liquidity_removed == 10

    assert snapshot.bid_added_volume == 10
    assert snapshot.bid_removed_volume == 10

    assert snapshot.signed_order_flow == 0

    assert snapshot.ofi == pytest.approx(
        0.0
    )

    assert snapshot.liquidity_balance == pytest.approx(
        0.0
    )


# ============================================================
# CANCEL Ask
# ============================================================


def test_ask_cancel_is_positive_directional_flow():
    """
    Ask Remove：

        Ask liquidity减少

    对买方方向是正贡献。

        signed += removed Ask volume
    """

    flow = make_flow()
    snapshot = make_snapshot()

    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=1,
            price=102,
            size=10,
        ),
    )

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.CANCEL,
            side=OrderSide.ASK,
            order_id=1,
            price=102,
            size=10,
        ),
    )

    assert snapshot.ask_added_volume == 10
    assert snapshot.ask_removed_volume == 10

    assert snapshot.signed_order_flow == 0


# ============================================================
# Modify Increase Bid
# ============================================================


def test_modify_bid_size_increase_uses_delta():
    """
    Real ES Ground Truth：

        Bid 100 @ 10

            ↓ M

        Bid 100 @ 15

    M.size：

        15

    真实新增：

        +5
    """

    flow = make_flow()
    snapshot = make_snapshot()

    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.MODIFY,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=15,
        ),
    )

    # Raw M.size累计
    assert snapshot.modify_volume == 15

    # 真正M新增delta
    assert snapshot.modify_added_volume == 5

    assert snapshot.modify_removed_volume == 0

    # A 10 + M delta 5
    assert snapshot.liquidity_added == 15

    assert snapshot.liquidity_removed == 0

    assert snapshot.bid_added_volume == 15

    assert snapshot.signed_order_flow == 15


# ============================================================
# Modify Decrease Bid
# ============================================================


def test_modify_bid_size_decrease_uses_delta():
    """
    Bid：

        10 -> 6

    M.size：

        6

    真正removed：

        4
    """

    flow = make_flow()
    snapshot = make_snapshot()

    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.MODIFY,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=6,
        ),
    )

    assert snapshot.modify_volume == 6

    assert snapshot.modify_added_volume == 0

    assert snapshot.modify_removed_volume == 4

    assert snapshot.liquidity_added == 10

    assert snapshot.liquidity_removed == 4

    assert snapshot.bid_removed_volume == 4

    # +10 initial bid
    # -4 bid removal

    assert snapshot.signed_order_flow == 6


# ============================================================
# Modify Increase Ask
# ============================================================


def test_modify_ask_size_increase_is_negative_flow():
    """
    Ask挂单增加：

        bearish directional contribution
    """

    flow = make_flow()
    snapshot = make_snapshot()

    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=1,
            price=102,
            size=10,
        ),
    )

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.MODIFY,
            side=OrderSide.ASK,
            order_id=1,
            price=102,
            size=15,
        ),
    )

    assert snapshot.modify_added_volume == 5

    assert snapshot.ask_added_volume == 15

    assert snapshot.signed_order_flow == -15


# ============================================================
# Modify Decrease Ask
# ============================================================


def test_modify_ask_size_decrease_is_positive_flow_delta():
    """
    Ask：

        10 -> 6

    Ask removed 4：

        directional +4
    """

    flow = make_flow()
    snapshot = make_snapshot()

    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=1,
            price=102,
            size=10,
        ),
    )

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.MODIFY,
            side=OrderSide.ASK,
            order_id=1,
            price=102,
            size=6,
        ),
    )

    assert snapshot.modify_removed_volume == 4

    assert snapshot.ask_removed_volume == 4

    # 初始 Ask Add = -10
    # Ask Remove = +4

    assert snapshot.signed_order_flow == -6


# ============================================================
# Price Move Bid
# ============================================================


def test_bid_modify_price_move_records_remove_and_add():
    """
    Bid：

        100 @ 10
            ↓ M
        101 @ 10

    Price-level flow：

        old 100:
            removed 10

        new 101:
            added 10
    """

    flow = make_flow()
    snapshot = make_snapshot()

    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.MODIFY,
            side=OrderSide.BID,
            order_id=1,
            price=101,
            size=10,
        ),
    )

    assert snapshot.price_move_count == 1

    assert snapshot.price_move_removed_volume == 10

    assert snapshot.price_move_added_volume == 10

    # 初始ADD 10
    # Price Move re-add 10
    assert snapshot.liquidity_added == 20

    # old level remove 10
    assert snapshot.liquidity_removed == 10

    assert snapshot.bid_added_volume == 20

    assert snapshot.bid_removed_volume == 10

    # 净方向仍然+10
    assert snapshot.signed_order_flow == 10


# ============================================================
# Price Move Ask
# ============================================================


def test_ask_modify_price_move_records_remove_and_add():
    """
    Ask：

        102 @ 7
            ↓
        103 @ 7

    remove old Ask 7:
        +7 directional

    add new Ask 7:
        -7 directional

    净directional变化=0。
    """

    flow = make_flow()
    snapshot = make_snapshot()

    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=1,
            price=102,
            size=7,
        ),
    )

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.MODIFY,
            side=OrderSide.ASK,
            order_id=1,
            price=103,
            size=7,
        ),
    )

    assert snapshot.price_move_count == 1

    assert snapshot.price_move_removed_volume == 7

    assert snapshot.price_move_added_volume == 7

    assert snapshot.ask_added_volume == 14

    assert snapshot.ask_removed_volume == 7

    # 初始Ask add仍然保留 -7
    assert snapshot.signed_order_flow == -7


# ============================================================
# Price + Size Move
# ============================================================


def test_modify_price_and_size_change_uses_full_old_new_flow():
    """
    Real ES中这种情况真实存在。

    Bid：

        old:
            100 @ 2

        M:
            101 @ 3

    正确price-level accounting：

        old level remove:
            2

        new level add:
            3
    """

    flow = make_flow()
    snapshot = make_snapshot()

    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=2,
        ),
    )

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.MODIFY,
            side=OrderSide.BID,
            order_id=1,
            price=101,
            size=3,
        ),
    )

    assert snapshot.price_move_count == 1

    assert snapshot.price_move_removed_volume == 2

    assert snapshot.price_move_added_volume == 3

    # modify net size change:
    # +1
    assert snapshot.modify_added_volume == 1

    assert snapshot.modify_removed_volume == 0

    # Initial Add 2
    # M new level Add 3
    assert snapshot.liquidity_added == 5

    # Old level removal 2
    assert snapshot.liquidity_removed == 2

    # net directional:
    # +2 initial
    # -2 old removal
    # +3 new add
    assert snapshot.signed_order_flow == 3


# ============================================================
# Price + Size Decrease
# ============================================================


def test_modify_price_move_with_size_decrease():
    """
    Bid：

        old:
            100 @ 5

        new:
            101 @ 2

    Price migration：

        remove old 5
        add new 2

    Size delta：

        removed delta = 3
    """

    flow = make_flow()
    snapshot = make_snapshot()

    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=5,
        ),
    )

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.MODIFY,
            side=OrderSide.BID,
            order_id=1,
            price=101,
            size=2,
        ),
    )

    assert snapshot.modify_removed_volume == 3

    assert snapshot.price_move_removed_volume == 5

    assert snapshot.price_move_added_volume == 2

    assert snapshot.liquidity_added == 7

    assert snapshot.liquidity_removed == 5

    assert snapshot.signed_order_flow == 2


# ============================================================
# OFI Direction
# ============================================================


def test_directional_ofi_formula():
    """
    使用累计方向流：

        positive flow:
            Bid Add
            Ask Remove

        negative flow:
            Ask Add
            Bid Remove

    OFI：

        signed
        /
        total directional activity
    """

    flow = make_flow()
    snapshot = make_snapshot()

    # Bid Add +10
    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    # Ask Add -6
    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=2,
            price=102,
            size=6,
        ),
    )

    # signed:
    # +10 - 6 = +4
    #
    # activity:
    # 10 + 6 = 16
    #
    # OFI = 4/16 = 0.25

    assert snapshot.signed_order_flow == 4

    assert snapshot.ofi == pytest.approx(
        0.25
    )


# ============================================================
# Liquidity Balance
# ============================================================


def test_liquidity_balance_is_separate_from_ofi():
    """
    Bid +10
    Ask +10

    Added=20
    Removed=0

    liquidity_balance=+1

    但是方向完全对称：

        OFI=0
    """

    flow = make_flow()
    snapshot = make_snapshot()

    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=2,
            price=102,
            size=10,
        ),
    )

    assert snapshot.ofi == pytest.approx(
        0.0
    )

    assert snapshot.liquidity_balance == pytest.approx(
        1.0
    )


# ============================================================
# Missing Modify
# ============================================================


def test_modify_missing_order_is_safe():
    """
    Feed正常情况下不应该发生，
    但Feature不能因为一个missing order崩溃。
    """

    flow = make_flow()
    snapshot = make_snapshot()

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.MODIFY,
            side=OrderSide.BID,
            order_id=999,
            price=100,
            size=5,
        ),
    )

    assert snapshot.modify_volume == 5

    assert (
        snapshot.extra[
            "flow_missing_modify_count"
        ]
        ==
        1
    )


# ============================================================
# Missing Cancel
# ============================================================


def test_cancel_missing_order_is_safe():
    """
    同样只记录诊断。
    """

    flow = make_flow()
    snapshot = make_snapshot()

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.CANCEL,
            side=OrderSide.BID,
            order_id=999,
            price=100,
            size=5,
        ),
    )

    assert (
        snapshot.extra[
            "flow_missing_cancel_count"
        ]
        ==
        1
    )


# ============================================================
# Generic Partial Cancel Safety
# ============================================================


def test_flow_shadow_can_handle_partial_cancel_safely():
    """
    虽然完整ESU6这一日：

        4,111,285 / 4,111,285

    都是full cancel，

    但Feature shadow不应该人为限制只能full cancel。

    ADD 10
    C 4

    Shadow应保留6。

    注意：

        这不会修改冻结OrderBook语义。
    """

    flow = make_flow()
    snapshot = make_snapshot()

    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.CANCEL,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=4,
        ),
    )

    assert snapshot.liquidity_removed == 4

    assert snapshot.bid_removed_volume == 4

    assert flow.active_order_count() == 1

    state = flow.get_order_state(
        1
    )

    assert state is not None

    assert state.size == 6


# ============================================================
# Full Cancel Shadow Removal
# ============================================================


def test_full_cancel_removes_shadow_order():
    """
    Full C以后shadow order消失。
    """

    flow = make_flow()
    snapshot = make_snapshot()

    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.CANCEL,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    assert flow.get_order_state(
        1
    ) is None

    assert flow.active_order_count() == 0


# ============================================================
# RESET
# ============================================================


def test_reset_event_clears_shadow_orders():
    """
    R：

        shadow order state清空。

    但不能把整个Book清空行为伪装成Cancel Flow。
    """

    flow = make_flow()
    snapshot = make_snapshot()

    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    assert flow.active_order_count() == 1

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.RESET,
            side=None,
            order_id=None,
            price=None,
            size=999,
        ),
    )

    assert flow.active_order_count() == 0

    # R不是C
    assert snapshot.cancel_volume == 0

    # 不能因为R.size=999就制造removed 999
    assert snapshot.liquidity_removed == 0


# ============================================================
# Explicit Reset Method
# ============================================================


def test_flow_reset_method():
    """
    FeatureEngine.reset()后必须能同时reset FlowFeatures。
    """

    flow = make_flow()
    snapshot = make_snapshot()

    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    assert flow.active_order_count() == 1

    flow.reset()

    assert flow.active_order_count() == 0


# ============================================================
# Multiple Orders
# ============================================================


def test_multiple_shadow_orders():
    """
    Shadow state按order_id独立。
    """

    flow = make_flow()
    snapshot = make_snapshot()

    for index in range(
        1,
        11,
    ):
        apply(
            flow,
            snapshot,
            make_event(
                sequence=index,
                action=OrderAction.ADD,
                side=(
                    OrderSide.BID
                    if index % 2
                    else OrderSide.ASK
                ),
                order_id=index,
                price=100 + index,
                size=index,
            ),
        )

    assert flow.active_order_count() == 10

    for index in range(
        1,
        11,
    ):
        state = flow.get_order_state(
            index
        )

        assert state is not None

        assert state.size == index


# ============================================================
# No Trade Double Count
# ============================================================


def test_trade_does_not_change_order_flow_liquidity():
    """
    T由TradeFeatures处理。

    FlowFeatures不能把T再次当：

        liquidity_removed
        signed passive flow
    """

    flow = make_flow()
    snapshot = make_snapshot()

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.TRADE,
            side=OrderSide.BID,
            order_id=None,
            price=100,
            size=5,
        ),
    )

    assert snapshot.liquidity_added == 0

    assert snapshot.liquidity_removed == 0

    assert snapshot.signed_order_flow == 0

    assert snapshot.ofi == pytest.approx(
        0.0
    )


# ============================================================
# FILL
# ============================================================


def test_fill_does_not_change_flow_shadow():
    """
    当前系统定义：

        F本身不修改OrderBook。

    所以Flow shadow也不根据F直接修改。
    """

    flow = make_flow()
    snapshot = make_snapshot()

    apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=1,
            price=102,
            size=10,
        ),
    )

    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.FILL,
            side=OrderSide.ASK,
            order_id=1,
            price=102,
            size=3,
        ),
    )

    state = flow.get_order_state(
        1
    )

    assert state is not None

    assert state.size == 10

    assert snapshot.liquidity_removed == 0


# ============================================================
# Copy
# ============================================================


def test_new_snapshot_fields_survive_copy():
    """
    新字段必须进入FeatureSnapshot.copy()。
    """

    snapshot = FeatureSnapshot()

    snapshot.signed_order_flow = 123
    snapshot.liquidity_balance = 0.25
    snapshot.bid_added_volume = 100
    snapshot.ask_removed_volume = 20

    copied = snapshot.copy()

    assert copied.signed_order_flow == 123

    assert copied.liquidity_balance == pytest.approx(
        0.25
    )

    assert copied.bid_added_volume == 100

    assert copied.ask_removed_volume == 20


# ============================================================
# to_dict
# ============================================================


def test_new_snapshot_fields_survive_to_dict():
    """
    CSV / Excel / Web后面都会依赖to_dict。
    """

    snapshot = FeatureSnapshot()

    snapshot.signed_order_flow = 5
    snapshot.liquidity_balance = -0.2

    data = snapshot.to_dict()

    assert (
        data[
            "signed_order_flow"
        ]
        ==
        5
    )

    assert data[
        "liquidity_balance"
    ] == pytest.approx(
        -0.2
    )


# ============================================================
# Diagnostic
# ============================================================


def test_refactor_contract_diagnostic():
    """
    打印一个完整事件序列。
    """

    flow = make_flow()
    snapshot = make_snapshot()

    # Bid +10
    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    # Ask +8
    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=2,
            price=102,
            size=8,
        ),
    )

    # Bid M 10 -> 15
    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=3,
            action=OrderAction.MODIFY,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=15,
        ),
    )

    # Ask price move 102 -> 103
    snapshot = apply(
        flow,
        snapshot,
        make_event(
            sequence=4,
            action=OrderAction.MODIFY,
            side=OrderSide.ASK,
            order_id=2,
            price=103,
            size=8,
        ),
    )

    print(
        "\n"
        "============================================================"
    )

    print(
        "FEATURE FLOW REFACTOR DIAGNOSTIC"
    )

    print(
        "============================================================"
    )

    print(
        "liquidity_added          =",
        snapshot.liquidity_added
    )

    print(
        "liquidity_removed        =",
        snapshot.liquidity_removed
    )

    print(
        "liquidity_balance        =",
        snapshot.liquidity_balance
    )

    print(
        "bid_added_volume         =",
        snapshot.bid_added_volume
    )

    print(
        "bid_removed_volume       =",
        snapshot.bid_removed_volume
    )

    print(
        "ask_added_volume         =",
        snapshot.ask_added_volume
    )

    print(
        "ask_removed_volume       =",
        snapshot.ask_removed_volume
    )

    print(
        "modify_added_volume      =",
        snapshot.modify_added_volume
    )

    print(
        "modify_removed_volume    =",
        snapshot.modify_removed_volume
    )

    print(
        "price_move_count         =",
        snapshot.price_move_count
    )

    print(
        "signed_order_flow        =",
        snapshot.signed_order_flow
    )

    print(
        "directional OFI          =",
        snapshot.ofi
    )

    print(
        "shadow active orders     =",
        flow.active_order_count()
    )

    print(
        "============================================================"
    )

    assert flow.active_order_count() == 2