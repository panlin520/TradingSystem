"""
测试策略系统加载

验证：

BaseStrategy
        |
        |
StrategyManager
        |
        |
四大战略

"""


import pytest


from strategy.base_strategy import BaseStrategy

from strategy.strategy_manager import StrategyManager

from strategy.context import StrategyContext


from strategy.strategies.mean_reversion import (
    MeanReversionStrategy
)

from strategy.strategies.momentum_breakout import (
    MomentumBreakoutStrategy
)

from strategy.strategies.liquidity_vacuum import (
    LiquidityVacuumStrategy
)

from strategy.strategies.absorption_refill import (
    AbsorptionRefillStrategy
)




# ============================================================
# 四大策略列表
# ============================================================


STRATEGIES = [

    MeanReversionStrategy,

    MomentumBreakoutStrategy,

    LiquidityVacuumStrategy,

    AbsorptionRefillStrategy,

]



# ============================================================
# Test 1
# BaseStrategy继承
# ============================================================


def test_strategy_inherit_base():

    for cls in STRATEGIES:

        assert issubclass(
            cls,
            BaseStrategy
        ), (
            f"{cls.__name__} "
            "does not inherit BaseStrategy"
        )



# ============================================================
# Test 2
# 可以实例化
# ============================================================


def test_strategy_can_initialize():

    for cls in STRATEGIES:

        strategy = cls()

        assert strategy is not None



# ============================================================
# Test 3
# Manager加载
# ============================================================


def test_strategy_manager_registers_all():


    manager = StrategyManager()


    for cls in STRATEGIES:

        strategy = cls()

        manager.register(
            strategy
        )


    assert len(
        manager.strategies
    ) == 4



# ============================================================
# Test 4
# Strategy接口
# ============================================================


def test_strategy_has_context_handler():


    for cls in STRATEGIES:

        strategy = cls()


        assert hasattr(
            strategy,
            "on_context"
        ), (
            f"{cls.__name__} "
            "missing on_context()"
        )



# ============================================================
# Test 5
# Context可以传入
# ============================================================


def test_context_object_exists():

    ctx = StrategyContext()


    assert ctx is not None