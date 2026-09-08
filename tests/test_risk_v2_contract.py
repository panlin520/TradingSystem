"""
tests/test_risk_v2_contract.py

============================================================
Risk Manager V2 Contract Test
============================================================

目的：

验证新的 RiskManagerV2 行为。


覆盖：

    - 初始化
    - RiskDecision
    - Kill Switch
    - Position Limit
    - Total Position Limit
    - Exposure Limit
    - Signal approve/reject
    - Fill update
    - Reset
    - Snapshot


注意：

这是 V2 新行为测试。

不继承旧：

    test_risk_current_behavior_contract.py


============================================================
"""


import pytest


from dataclasses import dataclass



from risk.risk_manager_v2 import (
    RiskManagerV2,
    RiskDecision,
)


from risk.limits import RiskLimits

from risk.exposure import ExposureEngine

from risk.kill_switch import KillSwitch




# ============================================================
# Fake Signal
# ============================================================


@dataclass
class FakeSignal:

    symbol: str = "ESU6"

    side: str = "BUY"

    quantity: int = 1






# ============================================================
# Fake Portfolio
# ============================================================


class FakePosition:


    def __init__(
        self,
        quantity=0,
        side=None,
    ):

        self.quantity = quantity

        self.side = side






class FakePortfolio:


    def __init__(self):

        self.positions = {}



    def get_position(
        self,
        symbol,
    ):

        return self.positions.get(
            symbol,
            FakePosition()
        )






# ============================================================
# Fixtures
# ============================================================


@pytest.fixture

def risk_manager():

    limits = RiskLimits(

        max_position=5,

        max_total_position=10,

        max_exposure=1000,

    )

    portfolio = FakePortfolio()

    return RiskManagerV2(
        limits=limits,
        exposure_engine=ExposureEngine(
            portfolio
        ),
        kill_switch=KillSwitch(),
    )






@pytest.fixture
def portfolio():

    return FakePortfolio()






# ============================================================
# Basic
# ============================================================


def test_risk_v2_initial_state(
    risk_manager,
):


    snap = risk_manager.snapshot()


    assert snap["checks"] == 0

    assert snap["approved"] == 0

    assert snap["rejected"] == 0




def test_risk_decision_bool():

    d1 = RiskDecision(

        approved=True,

        reason="ok"

    )


    d2 = RiskDecision(

        approved=False,

        reason="deny"

    )


    assert bool(d1) is True

    assert bool(d2) is False







# ============================================================
# Normal approve
# ============================================================


def test_normal_signal_is_approved(
    risk_manager,
    portfolio,
):


    signal = FakeSignal(

        symbol="ESU6",

        side="BUY",

        quantity=1,

    )


    result = risk_manager.check_signal(

        signal,

        portfolio,

    )


    assert result.approved is True

    assert result.reason == "Approved"








# ============================================================
# Position Limit
# ============================================================


def test_position_limit_reject(
    risk_manager,
    portfolio,
):


    signal = FakeSignal(

        symbol="ESU6",

        side="BUY",

        quantity=6,

    )


    result = risk_manager.check_signal(

        signal,

        portfolio,

    )


    assert result.approved is False


    assert (
        "Position"
        in result.reason
    )







# ============================================================
# Total Position Limit
# ============================================================


def test_total_position_limit_reject(
    risk_manager,
    portfolio,
):


    signal = FakeSignal(

        symbol="ESU6",

        side="BUY",

        quantity=10,

    )


    result = risk_manager.check_signal(

        signal,

        portfolio,

    )


    assert result.approved is False







# ============================================================
# Exposure Limit
# ============================================================


def test_exposure_limit_reject(
    risk_manager,
    portfolio,
):


    risk_manager.limits.max_exposure = 1


    signal = FakeSignal(

        symbol="ESU6",

        side="BUY",

        quantity=1,

    )


    result = risk_manager.check_signal(

        signal,

        portfolio,

    )


    assert result.approved is False


    assert (
        "Exposure"
        in result.reason
    )







# ============================================================
# Kill Switch
# ============================================================


def test_kill_switch_blocks_signal(
    risk_manager,
    portfolio,
):


    risk_manager.kill_switch.trigger(
        "manual"
    )


    signal = FakeSignal()


    result = risk_manager.check_signal(

        signal,

        portfolio,

    )


    assert result.approved is False


    assert (
        "Kill"
        in result.reason
    )








# ============================================================
# Invalid Signal
# ============================================================


def test_zero_quantity_reject(
    risk_manager,
    portfolio,
):


    signal = FakeSignal(

        quantity=0

    )


    result = risk_manager.check_signal(

        signal,

        portfolio,

    )


    assert result.approved is False






def test_missing_symbol_reject(
    risk_manager,
    portfolio,
):


    signal = FakeSignal(

        symbol=None

    )


    result = risk_manager.check_signal(

        signal,

        portfolio,

    )


    assert result.approved is False







# ============================================================
# Reset
# ============================================================


def test_reset(
    risk_manager,
    portfolio,
):


    risk_manager.check_signal(

        FakeSignal(),

        portfolio,

    )


    risk_manager.reset()


    snap = risk_manager.snapshot()


    assert snap["checks"] == 0

    assert snap["approved"] == 0

    assert snap["rejected"] == 0







# ============================================================
# Fill update
# ============================================================


def test_on_fill_calls_exposure_update(
    risk_manager,
    portfolio,
):


    result = risk_manager.on_fill(

        {

            "symbol": "ESU6",

            "quantity": 1,

        },

        portfolio,

    )


    assert result is not None






# ============================================================
# Snapshot
# ============================================================


def test_snapshot_contract(
    risk_manager,
):


    snap = risk_manager.snapshot()


    assert "checks" in snap

    assert "approved" in snap

    assert "rejected" in snap

    assert "kill_switch" in snap






# ============================================================
# Diagnostic
# ============================================================


def test_risk_v2_diagnostic(
    risk_manager,
    portfolio,
):


    result = risk_manager.check_signal(

        FakeSignal(
            quantity=1
        ),

        portfolio,

    )


    snap = risk_manager.snapshot()



    print(
        "\n"
        "=" * 60
    )

    print(
        "RISK V2 DIAGNOSTIC"
    )

    print(
        "=" * 60
    )


    print(
        "approved =",
        result.approved
    )


    print(
        "reason   =",
        result.reason
    )


    print(
        "snapshot =",
        snap
    )


    print(
        "=" * 60
    )



    assert result.approved is True