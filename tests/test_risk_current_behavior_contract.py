"""
tests/test_risk_current_behavior_contract.py

============================================================
Current Risk Subsystem Behavior Contract
============================================================

目的：

    在正式重构 Risk 之前，
    完整记录当前 risk/* 的真实运行行为。

============================================================

IMPORTANT

本文件不是“理想 Risk 设计”测试。

它验证的是：

    当前代码实际上怎么运行。

因此部分测试会明确记录当前存在的问题，例如：

    - RiskManager 不调用 Signal.is_valid()
    - HOLD Signal 当前可能被批准
    - size <= 0 当前可能被批准
    - BUY / SELL 方向没有参与 position limit 计算
    - opposite-side fill 不会减仓/反手
    - max_total_position 没有执行
    - max_exposure 没有执行
    - max_consecutive_losses 没有执行
    - allow_overnight 没有执行
    - RiskManager.reset() 只 reset KillSwitch

这些测试通过：

    不代表这些行为是正确的。

只代表：

    我们已经准确知道旧 Risk 当前在做什么。

正式重构之后：

    这些“旧行为契约”中的错误行为测试
    将被新的 Risk Contract 替代。

============================================================

本测试只调用：

    risk/position.py
    risk/limits.py
    risk/kill_switch.py
    risk/risk_manager.py
    strategy/signal.py

不修改：

    data/*
    core/*
    orderbook/*
    features/*
    strategy/*
    portfolio/*

============================================================
"""

import pytest

from strategy.signal import (
    Signal,
    SignalSide,
)

from risk.position import (
    Position,
    PositionSide,
)

from risk.limits import RiskLimits

from risk.kill_switch import (
    KillSwitch,
    KillSwitchState,
)

from risk.risk_manager import RiskManager


# ============================================================
# Helpers
# ============================================================


def make_signal(
    *,
    side=SignalSide.BUY,
    size=1,
    price=100,
):
    """
    创建最小真实 Signal。
    """

    return Signal(
        side=side,
        size=size,
        price=price,
    )


def make_manager(
    **limit_overrides,
):
    """
    创建带自定义 RiskLimits 的 RiskManager。
    """

    limits = RiskLimits(
        **limit_overrides
    )

    return RiskManager(
        limits=limits
    )


# ============================================================
# 1. RiskLimits
# ============================================================


def test_risk_limits_default_values():
    """
    锁定当前默认限制。
    """

    limits = RiskLimits()

    assert limits.max_position == 10
    assert limits.max_total_position == 20
    assert limits.max_open_orders == 10
    assert limits.max_daily_loss == 1000.0
    assert limits.max_exposure == 100000.0
    assert limits.max_consecutive_losses == 5
    assert limits.max_order_size == 5
    assert limits.allow_overnight is False


def test_risk_limits_snapshot():
    """
    snapshot() 应完整返回当前限制。
    """

    limits = RiskLimits()

    snapshot = limits.snapshot()

    assert snapshot[
        "max_position"
    ] == 10

    assert snapshot[
        "max_total_position"
    ] == 20

    assert snapshot[
        "max_open_orders"
    ] == 10

    assert snapshot[
        "max_daily_loss"
    ] == 1000.0

    assert snapshot[
        "max_exposure"
    ] == 100000.0

    assert snapshot[
        "max_consecutive_losses"
    ] == 5

    assert snapshot[
        "max_order_size"
    ] == 5

    assert snapshot[
        "allow_overnight"
    ] is False


# ============================================================
# 2. Position Current Behavior
# ============================================================


def test_risk_position_initial_state():
    """
    Position 默认状态。
    """

    position = Position(
        symbol="ESU6"
    )

    assert position.symbol == "ESU6"
    assert position.side == PositionSide.FLAT
    assert position.quantity == 0
    assert position.average_price == 0.0
    assert position.realized_pnl == 0.0
    assert position.market_price is None

    assert position.is_flat() is True


def test_risk_position_open_long():
    """
    当前 Position.open() 可以建立 LONG。
    """

    position = Position(
        symbol="ESU6"
    )

    position.open(
        PositionSide.LONG,
        2,
        100.0,
    )

    assert position.side == PositionSide.LONG
    assert position.quantity == 2
    assert position.average_price == 100.0
    assert position.is_flat() is False


def test_risk_position_add_same_direction():
    """
    当前 add() 只按数量和价格计算平均价格。

    它自己并不知道成交方向。
    """

    position = Position(
        symbol="ESU6"
    )

    position.open(
        PositionSide.LONG,
        2,
        100.0,
    )

    position.add(
        2,
        102.0,
    )

    assert position.side == PositionSide.LONG
    assert position.quantity == 4

    assert position.average_price == pytest.approx(
        101.0
    )


def test_risk_position_reduce_long_current_pnl_units():
    """
    当前 risk.Position.reduce()：

        PnL = price difference * quantity

    没有乘 ES point value = 50。

    这里只记录当前行为。
    """

    position = Position(
        symbol="ESU6"
    )

    position.open(
        PositionSide.LONG,
        2,
        100.0,
    )

    position.reduce(
        1,
        102.0,
    )

    assert position.quantity == 1
    assert position.realized_pnl == pytest.approx(
        2.0
    )


def test_risk_position_unrealized_pnl_current_units():
    """
    当前 Risk Position Unrealized PnL
    同样没有 point value。
    """

    position = Position(
        symbol="ESU6"
    )

    position.open(
        PositionSide.LONG,
        2,
        100.0,
    )

    position.update_market_price(
        103.0
    )

    assert position.unrealized_pnl() == pytest.approx(
        6.0
    )


def test_risk_position_exposure_current_formula():
    """
    当前 exposure：

        quantity * market_price

    没有：

        ES multiplier
        contract point value

    这里只记录当前实现。
    """

    position = Position(
        symbol="ESU6"
    )

    position.open(
        PositionSide.LONG,
        2,
        5000.0,
    )

    position.update_market_price(
        5000.0
    )

    assert position.exposure() == pytest.approx(
        10000.0
    )


# ============================================================
# 3. Kill Switch
# ============================================================


def test_kill_switch_initial_state():
    """
    KillSwitch 默认 NORMAL。
    """

    kill_switch = KillSwitch()

    assert (
        kill_switch.state
        ==
        KillSwitchState.NORMAL
    )

    assert kill_switch.is_triggered() is False
    assert kill_switch.check() is True


def test_kill_switch_trigger():
    """
    trigger 后禁止交易。
    """

    kill_switch = KillSwitch()

    kill_switch.trigger(
        "manual test"
    )

    assert (
        kill_switch.state
        ==
        KillSwitchState.TRIGGERED
    )

    assert kill_switch.is_triggered() is True
    assert kill_switch.check() is False

    assert kill_switch.reason == "manual test"
    assert kill_switch.trigger_time is not None

    assert len(
        kill_switch.history
    ) == 1


def test_kill_switch_second_trigger_is_ignored():
    """
    当前实现：

        已经 TRIGGERED 后再次 trigger()

    不改变第一次 reason，
    不增加 history。
    """

    kill_switch = KillSwitch()

    kill_switch.trigger(
        "first"
    )

    first_time = (
        kill_switch.trigger_time
    )

    kill_switch.trigger(
        "second"
    )

    assert kill_switch.reason == "first"

    assert (
        kill_switch.trigger_time
        ==
        first_time
    )

    assert len(
        kill_switch.history
    ) == 1


def test_kill_switch_reset_preserves_history():
    """
    当前 reset：

        恢复 NORMAL
        清 reason

    但不会删除 history。
    """

    kill_switch = KillSwitch()

    kill_switch.trigger(
        "test"
    )

    kill_switch.reset()

    assert (
        kill_switch.state
        ==
        KillSwitchState.NORMAL
    )

    assert kill_switch.reason is None
    assert kill_switch.check() is True

    assert len(
        kill_switch.history
    ) == 1


# ============================================================
# 4. RiskManager Initialization
# ============================================================


def test_risk_manager_initial_state():
    """
    当前 RiskManager 初始状态。
    """

    manager = RiskManager()

    assert isinstance(
        manager.limits,
        RiskLimits
    )

    assert isinstance(
        manager.kill_switch,
        KillSwitch
    )

    assert manager.positions == {}
    assert manager.open_orders == 0
    assert manager.daily_pnl == 0.0


def test_get_position_creates_and_caches_position():
    """
    当前 RiskManager 自己拥有 Position。
    """

    manager = RiskManager()

    first = manager.get_position(
        "ESU6"
    )

    second = manager.get_position(
        "ESU6"
    )

    assert isinstance(
        first,
        Position
    )

    assert first is second

    assert (
        manager.positions[
            "ESU6"
        ]
        is first
    )


# ============================================================
# 5. Basic Signal Approval
# ============================================================


def test_normal_signal_is_approved():
    """
    普通信号当前可以通过。
    """

    manager = RiskManager()

    approved, reason = (
        manager.check_signal(
            make_signal(
                side=SignalSide.BUY,
                size=1,
            ),
            "ESU6",
        )
    )

    assert approved is True
    assert reason == "Approved"


# ============================================================
# 6. Order Size Limit
# ============================================================


def test_order_size_equal_limit_is_approved():
    """
    当前条件：

        signal.size > max_order_size

    因此刚好等于 limit 可以通过。
    """

    manager = make_manager(
        max_order_size=5
    )

    approved, reason = (
        manager.check_signal(
            make_signal(
                size=5
            ),
            "ESU6",
        )
    )

    assert approved is True
    assert reason == "Approved"


def test_order_size_above_limit_is_rejected():
    """
    超过 max_order_size 被拒绝。
    """

    manager = make_manager(
        max_order_size=5
    )

    approved, reason = (
        manager.check_signal(
            make_signal(
                size=6
            ),
            "ESU6",
        )
    )

    assert approved is False

    assert reason == (
        "Order size exceeds limit"
    )


# ============================================================
# 7. Open Orders Limit
# ============================================================


def test_open_orders_below_limit_is_approved():
    """
    open_orders < limit 可以通过。
    """

    manager = make_manager(
        max_open_orders=10
    )

    manager.open_orders = 9

    approved, reason = (
        manager.check_signal(
            make_signal(),
            "ESU6",
        )
    )

    assert approved is True
    assert reason == "Approved"


def test_open_orders_equal_limit_is_rejected():
    """
    当前条件：

        open_orders >= max_open_orders

    等于 limit 就拒绝。
    """

    manager = make_manager(
        max_open_orders=10
    )

    manager.open_orders = 10

    approved, reason = (
        manager.check_signal(
            make_signal(),
            "ESU6",
        )
    )

    assert approved is False

    assert reason == (
        "Too many open orders"
    )


# ============================================================
# 8. Daily Loss
# ============================================================


def test_daily_loss_exact_limit_is_still_approved():
    """
    当前代码使用：

        daily_pnl < -max_daily_loss

    不是 <=。

    因此刚好 -1000 时仍然批准。
    """

    manager = make_manager(
        max_daily_loss=1000.0
    )

    manager.daily_pnl = -1000.0

    approved, reason = (
        manager.check_signal(
            make_signal(),
            "ESU6",
        )
    )

    assert approved is True
    assert reason == "Approved"


def test_daily_loss_below_limit_is_rejected():
    """
    只有低于 -limit 才拒绝。
    """

    manager = make_manager(
        max_daily_loss=1000.0
    )

    manager.daily_pnl = -1000.01

    approved, reason = (
        manager.check_signal(
            make_signal(),
            "ESU6",
        )
    )

    assert approved is False

    assert reason == (
        "Daily loss limit exceeded"
    )


def test_update_pnl_is_cumulative():
    """
    update_pnl 当前直接累计。
    """

    manager = RiskManager()

    manager.update_pnl(
        -100.0
    )

    manager.update_pnl(
        25.0
    )

    assert manager.daily_pnl == pytest.approx(
        -75.0
    )


# ============================================================
# 9. Kill Switch Through RiskManager
# ============================================================


def test_risk_manager_emergency_stop_blocks_signal():
    """
    emergency_stop -> KillSwitch -> reject。
    """

    manager = RiskManager()

    manager.emergency_stop(
        "manual emergency"
    )

    approved, reason = (
        manager.check_signal(
            make_signal(),
            "ESU6",
        )
    )

    assert approved is False

    assert reason == (
        "Kill Switch Triggered"
    )


# ============================================================
# 10. CURRENT BUG:
#     Signal Validation Is Not Called
# ============================================================


def test_current_behavior_hold_signal_is_approved():
    """
    CURRENT BEHAVIOR / KNOWN DEFECT

    Signal.is_valid() 对 HOLD 应为 False。

    但当前 RiskManager.check_signal()
    不调用 signal.is_valid()。

    所以 HOLD + size=1 当前仍然会被批准。

    这是旧行为基线，不是目标设计。
    """

    signal = make_signal(
        side=SignalSide.HOLD,
        size=1,
    )

    assert signal.is_valid() is False

    manager = RiskManager()

    approved, reason = (
        manager.check_signal(
            signal,
            "ESU6",
        )
    )

    assert approved is True
    assert reason == "Approved"


def test_current_behavior_zero_size_signal_is_approved():
    """
    CURRENT BEHAVIOR / KNOWN DEFECT

    size=0 的 Signal.is_valid() 为 False，
    但 RiskManager 当前仍批准。
    """

    signal = make_signal(
        side=SignalSide.BUY,
        size=0,
    )

    assert signal.is_valid() is False

    manager = RiskManager()

    approved, reason = (
        manager.check_signal(
            signal,
            "ESU6",
        )
    )

    assert approved is True
    assert reason == "Approved"


def test_current_behavior_negative_size_signal_is_approved():
    """
    CURRENT BEHAVIOR / KNOWN DEFECT

    negative size 当前没有 Risk validation。
    """

    signal = make_signal(
        side=SignalSide.BUY,
        size=-1,
    )

    assert signal.is_valid() is False

    manager = RiskManager()

    approved, reason = (
        manager.check_signal(
            signal,
            "ESU6",
        )
    )

    assert approved is True
    assert reason == "Approved"


# ============================================================
# 11. CURRENT BUG:
#     Signal Direction Ignored By Position Limit
# ============================================================


def test_current_behavior_sell_does_not_reduce_projected_long_position():
    """
    CURRENT BEHAVIOR / KNOWN DEFECT

    当前：

        LONG 5
        SELL 3

    正确目标应该：

        projected = LONG 2

    但当前 RiskManager：

        new_quantity
        =
        position.quantity + signal.size
        =
        5 + 3
        =
        8

    当 max_position=6 时：

        错误拒绝 SELL 减仓信号。
    """

    manager = make_manager(
        max_position=6,
        max_order_size=10,
    )

    position = manager.get_position(
        "ESU6"
    )

    position.open(
        PositionSide.LONG,
        5,
        100.0,
    )

    approved, reason = (
        manager.check_signal(
            make_signal(
                side=SignalSide.SELL,
                size=3,
            ),
            "ESU6",
        )
    )

    assert approved is False

    assert reason == (
        "Position limit exceeded"
    )


def test_current_behavior_buy_does_not_reduce_projected_short_position():
    """
    CURRENT BEHAVIOR / KNOWN DEFECT

        SHORT 5
        BUY 3

    当前同样计算成：

        5 + 3 = 8
    """

    manager = make_manager(
        max_position=6,
        max_order_size=10,
    )

    position = manager.get_position(
        "ESU6"
    )

    position.open(
        PositionSide.SHORT,
        5,
        100.0,
    )

    approved, reason = (
        manager.check_signal(
            make_signal(
                side=SignalSide.BUY,
                size=3,
            ),
            "ESU6",
        )
    )

    assert approved is False

    assert reason == (
        "Position limit exceeded"
    )


# ============================================================
# 12. Position Limit Current Behavior
# ============================================================


def test_current_same_direction_position_limit():
    """
    LONG 5 + BUY 2 = projected 7。

    当前简单加法在这个场景恰好正确。
    """

    manager = make_manager(
        max_position=6,
        max_order_size=10,
    )

    position = manager.get_position(
        "ESU6"
    )

    position.open(
        PositionSide.LONG,
        5,
        100.0,
    )

    approved, reason = (
        manager.check_signal(
            make_signal(
                side=SignalSide.BUY,
                size=2,
            ),
            "ESU6",
        )
    )

    assert approved is False

    assert reason == (
        "Position limit exceeded"
    )


# ============================================================
# 13. CURRENT BUG:
#     max_total_position Is Not Enforced
# ============================================================


def test_current_behavior_max_total_position_is_not_checked():
    """
    CURRENT BEHAVIOR / KNOWN DEFECT

    max_total_position 已存在于 RiskLimits，
    但 RiskManager.check_signal() 当前不检查它。

    当前：

        ESU6 = 2
        NQU6 = 2

    max_total_position = 2

    再发 BUY 1 仍然可能 Approved。
    """

    manager = make_manager(
        max_position=100,
        max_total_position=2,
        max_order_size=10,
    )

    manager.on_fill(
        "ESU6",
        PositionSide.LONG,
        2,
        100.0,
    )

    manager.on_fill(
        "NQU6",
        PositionSide.LONG,
        2,
        100.0,
    )

    approved, reason = (
        manager.check_signal(
            make_signal(
                side=SignalSide.BUY,
                size=1,
            ),
            "ESU6",
        )
    )

    assert approved is True
    assert reason == "Approved"


# ============================================================
# 14. CURRENT BUG:
#     max_exposure Is Not Enforced
# ============================================================


def test_current_behavior_max_exposure_is_not_checked():
    """
    CURRENT BEHAVIOR / KNOWN DEFECT

    max_exposure 虽然存在，
    RiskManager 当前没有 exposure check。
    """

    manager = make_manager(
        max_position=100,
        max_order_size=10,
        max_exposure=100.0,
    )

    position = manager.get_position(
        "ESU6"
    )

    position.open(
        PositionSide.LONG,
        2,
        5000.0,
    )

    position.update_market_price(
        5000.0
    )

    assert position.exposure() == pytest.approx(
        10000.0
    )

    assert (
        position.exposure()
        >
        manager.limits.max_exposure
    )

    approved, reason = (
        manager.check_signal(
            make_signal(
                side=SignalSide.BUY,
                size=1,
            ),
            "ESU6",
        )
    )

    assert approved is True
    assert reason == "Approved"


# ============================================================
# 15. CURRENT BUG:
#     max_consecutive_losses Has No Runtime State
# ============================================================


def test_current_behavior_consecutive_loss_limit_has_no_runtime_counter():
    """
    当前 RiskLimits 有：

        max_consecutive_losses

    但是 RiskManager 没有：

        consecutive_losses

    也没有相关检查。
    """

    manager = RiskManager()

    assert (
        manager.limits.max_consecutive_losses
        ==
        5
    )

    assert not hasattr(
        manager,
        "consecutive_losses"
    )


# ============================================================
# 16. CURRENT BUG:
#     allow_overnight Is Configuration Only
# ============================================================


def test_current_behavior_allow_overnight_is_configuration_only():
    """
    当前 allow_overnight 只存在于 limits。

    RiskManager 没有 overnight/session 检查入口。
    """

    manager = RiskManager()

    assert manager.limits.allow_overnight is False

    assert not hasattr(
        manager,
        "check_overnight"
    )


# ============================================================
# 17. RiskManager.on_fill()
# ============================================================


def test_on_fill_opens_flat_position():
    """
    flat + fill 当前能够开仓。
    """

    manager = RiskManager()

    manager.on_fill(
        "ESU6",
        PositionSide.LONG,
        2,
        100.0,
    )

    position = manager.get_position(
        "ESU6"
    )

    assert position.side == PositionSide.LONG
    assert position.quantity == 2
    assert position.average_price == 100.0


def test_on_fill_same_direction_adds_position():
    """
    当前同方向 fill 可以正常加仓。
    """

    manager = RiskManager()

    manager.on_fill(
        "ESU6",
        PositionSide.LONG,
        2,
        100.0,
    )

    manager.on_fill(
        "ESU6",
        PositionSide.LONG,
        2,
        102.0,
    )

    position = manager.get_position(
        "ESU6"
    )

    assert position.side == PositionSide.LONG
    assert position.quantity == 4

    assert position.average_price == pytest.approx(
        101.0
    )


def test_current_behavior_opposite_fill_incorrectly_adds_position():
    """
    CURRENT BEHAVIOR / KNOWN DEFECT

    当前：

        LONG 2
        收到 SHORT fill 1

    RiskManager.on_fill() 不检查成交方向。

    因为 Position 非 flat：

        无条件调用 position.add()

    所以结果变成：

        LONG 3

    而不是：

        LONG 1

    这里明确锁定旧行为。
    """

    manager = RiskManager()

    manager.on_fill(
        "ESU6",
        PositionSide.LONG,
        2,
        100.0,
    )

    manager.on_fill(
        "ESU6",
        PositionSide.SHORT,
        1,
        90.0,
    )

    position = manager.get_position(
        "ESU6"
    )

    assert position.side == PositionSide.LONG

    assert position.quantity == 3

    assert position.average_price == pytest.approx(
        (
            100.0 * 2
            +
            90.0
        )
        /
        3
    )


# ============================================================
# 18. RiskManager.reset()
# ============================================================


def test_current_behavior_risk_manager_reset_only_resets_kill_switch():
    """
    CURRENT BEHAVIOR

    RiskManager.reset() 当前只：

        kill_switch.reset()

    不清：

        positions
        daily_pnl
        open_orders
    """

    manager = RiskManager()

    manager.on_fill(
        "ESU6",
        PositionSide.LONG,
        2,
        100.0,
    )

    manager.daily_pnl = -500.0
    manager.open_orders = 3

    manager.emergency_stop(
        "test"
    )

    manager.reset()

    assert manager.kill_switch.is_triggered() is False

    # 当前 reset 不清这些状态
    assert manager.daily_pnl == -500.0
    assert manager.open_orders == 3

    assert "ESU6" in manager.positions

    assert (
        manager.positions[
            "ESU6"
        ].quantity
        ==
        2
    )


# ============================================================
# 19. Snapshot
# ============================================================


def test_risk_manager_snapshot_current_contract():
    """
    当前 snapshot 契约。
    """

    manager = RiskManager()

    manager.on_fill(
        "ESU6",
        PositionSide.LONG,
        2,
        100.0,
    )

    manager.daily_pnl = -50.0
    manager.open_orders = 2

    snapshot = manager.snapshot()

    assert "kill_switch" in snapshot
    assert "daily_pnl" in snapshot
    assert "open_orders" in snapshot
    assert "positions" in snapshot
    assert "limits" in snapshot

    assert snapshot[
        "daily_pnl"
    ] == -50.0

    assert snapshot[
        "open_orders"
    ] == 2

    assert "ESU6" in snapshot[
        "positions"
    ]


# ============================================================
# 20. Diagnostic
# ============================================================


def test_risk_current_behavior_diagnostic():
    """
    输出当前 Risk 的几个关键问题。

    pytest -s 时查看。
    """

    manager = make_manager(
        max_position=6,
        max_total_position=4,
        max_order_size=10,
        max_exposure=100.0,
    )

    # --------------------------------------------------------
    # LONG 5
    # --------------------------------------------------------

    manager.on_fill(
        "ESU6",
        PositionSide.LONG,
        5,
        100.0,
    )

    position = manager.get_position(
        "ESU6"
    )

    position.update_market_price(
        100.0
    )

    # --------------------------------------------------------
    # SELL 3
    # --------------------------------------------------------

    sell_signal = make_signal(
        side=SignalSide.SELL,
        size=3,
    )

    sell_approved, sell_reason = (
        manager.check_signal(
            sell_signal,
            "ESU6",
        )
    )

    # --------------------------------------------------------
    # HOLD
    # --------------------------------------------------------

    hold_signal = make_signal(
        side=SignalSide.HOLD,
        size=1,
    )

    # 用空仓symbol避免position limit干扰
    hold_approved, hold_reason = (
        manager.check_signal(
            hold_signal,
            "MESU6",
        )
    )

    print(
        "\n"
        "============================================================"
    )

    print(
        "CURRENT RISK BEHAVIOR DIAGNOSTIC"
    )

    print(
        "============================================================"
    )

    print(
        "ESU6 position side       =",
        position.side.value,
    )

    print(
        "ESU6 position quantity   =",
        position.quantity,
    )

    print(
        "ESU6 risk exposure       =",
        position.exposure(),
    )

    print(
        "configured max exposure =",
        manager.limits.max_exposure,
    )

    print(
        "SELL 3 approved          =",
        sell_approved,
    )

    print(
        "SELL 3 reason            =",
        sell_reason,
    )

    print(
        "HOLD is_valid            =",
        hold_signal.is_valid(),
    )

    print(
        "HOLD approved            =",
        hold_approved,
    )

    print(
        "HOLD reason              =",
        hold_reason,
    )

    print(
        "max_total_position       =",
        manager.limits.max_total_position,
    )

    print(
        "has consecutive counter  =",
        hasattr(
            manager,
            "consecutive_losses"
        ),
    )

    print(
        "============================================================"
    )

    # ========================================================
    # 当前已知行为
    # ========================================================

    assert sell_approved is False

    assert sell_reason == (
        "Position limit exceeded"
    )

    assert hold_signal.is_valid() is False

    assert hold_approved is True

    assert hold_reason == "Approved"