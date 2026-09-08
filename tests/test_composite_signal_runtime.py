"""
tests/test_composite_signal_runtime.py

============================================================
Composite Signal Runtime Contract Tests
============================================================

目标：

    验证：

        Strategy Signal
              ↓
        CompositeSignalEngine
              ↓
        CompositeSignal
              ↓
        StrategyManager

    整条多策略信号融合链路的运行时契约。

============================================================

本测试重点验证：

    1. CompositeSignalEngine 可以正常初始化
    2. combine() 接受 strategy.signal.Signal
    3. 空信号不会产生交易
    4. 单个 BUY 信号可以被处理
    5. 单个 SELL 信号可以被处理
    6. 多个同向信号可以融合
    7. BUY / SELL 冲突可以处理
    8. 返回对象符合 CompositeSignal 契约
    9. StrategyManager → CompositeSignalEngine 可以完整运行
    10. Manager 统计正常

============================================================

本测试不负责：

    - OrderBook
    - Databento
    - Feature Engine
    - Execution
    - Portfolio
    - Risk执行
    - 策略盈利能力

============================================================
"""

import pytest

from strategy.context import (
    StrategyContext,
    OrderBookContext,
    FeatureContext,
    RegimeContext,
    PositionContext,
    RiskContext,
)

from strategy.signal import (
    Signal,
    SignalSide,
    SignalType,
    StrategyCategory,
)

from strategy.composite_signal import (
    CompositeSignal,
    CompositeSignalEngine,
)

from strategy.strategy_manager import (
    StrategyManager,
)


# ============================================================
# Helpers
# ============================================================


def make_context(
    *,
    timestamp=1,
    symbol="ESU6",
    allowed=True,
    kill_switch=False,
):
    """
    创建最小标准 StrategyContext。

    Composite Signal测试本身不依赖真实盘口。
    """

    return StrategyContext(
        timestamp=timestamp,
        symbol=symbol,

        orderbook=OrderBookContext(
            best_bid=99.75,
            best_ask=100.25,
            bid_size=100,
            ask_size=100,
            spread=0.50,
            depth={},
            active_orders=1000,
        ),

        features=FeatureContext(
            mid_price=100.0,
            micro_price=100.0,
            obi=0.0,
            queue_imbalance=0.0,
            ofi=0.0,
            trade_volume=100,
            aggressive_buy_volume=50,
            aggressive_sell_volume=50,
            trade_imbalance=0.0,
            volatility=0.25,
        ),

        regime=RegimeContext(
            name="TEST",
            trending=False,
            ranging=True,
            high_volatility=False,
            liquidity_event=False,
        ),

        position=PositionContext(
            symbol=symbol,
            quantity=0,
            side="FLAT",
            unrealized_pnl=0.0,
            realized_pnl=0.0,
        ),

        risk=RiskContext(
            allowed=allowed,
            kill_switch=kill_switch,
            current_exposure=0.0,
            max_exposure=10.0,
        ),
    )


def make_signal(
    *,
    side,
    category,
    confidence=0.90,
    score=1.50,
    strategy="test_strategy",
    reason="test signal",
):
    """
    创建标准 strategy.signal.Signal。
    """

    return Signal(
        side=side,
        signal_type=SignalType.ENTRY,
        category=category,
        confidence=float(confidence),
        score=float(score),
        timestamp=1,
        strategy=strategy,
        reason=reason,
        metadata={
            "score": float(score),
        },
    )


def assert_composite_contract(
    result
):
    """
    StrategyManager 当前要求 Composite结果：

        - 是 CompositeSignal
        - 提供 is_trade()
        - 提供 confidence
        - 提供 score

    这里将其固定为正式运行时契约。
    """

    assert isinstance(
        result,
        CompositeSignal
    )

    assert hasattr(
        result,
        "is_trade"
    )

    assert callable(
        result.is_trade
    )

    assert hasattr(
        result,
        "confidence"
    )

    assert hasattr(
        result,
        "score"
    )


# ============================================================
# Import / Initialization
# ============================================================


def test_composite_engine_can_initialize():
    """
    CompositeSignalEngine必须可以直接初始化。
    """

    engine = CompositeSignalEngine()

    assert engine is not None


def test_composite_signal_can_initialize():
    """
    CompositeSignal必须可以直接创建默认对象。
    """

    result = CompositeSignal()

    assert_composite_contract(
        result
    )

    assert result.is_trade() is False


# ============================================================
# Empty Signal
# ============================================================


def test_composite_empty_signals():
    """
    没有任何策略信号时：

        combine([])
            ↓
        CompositeSignal
            ↓
        No Trade

    不允许返回一个有效交易信号。
    """

    engine = CompositeSignalEngine()

    context = make_context()

    result = engine.combine(
        [],
        context
    )

    assert_composite_contract(
        result
    )

    assert result.is_trade() is False


# ============================================================
# Single BUY
# ============================================================


def test_composite_single_buy_signal():
    """
    单个高置信度BUY信号必须能够进入Composite Engine。

    本测试重点不是规定最终评分公式，
    而是验证：

        Signal
          ↓
        combine()
          ↓
        CompositeSignal

    不发生接口错误。
    """

    engine = CompositeSignalEngine()

    context = make_context()

    signal = make_signal(
        side=SignalSide.BUY,
        category=StrategyCategory.MEAN_REVERSION,
        confidence=1.0,
        score=2.0,
        strategy="mean_reversion",
    )

    result = engine.combine(
        [signal],
        context
    )

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert result.confidence > 0.0
    assert result.score > 0.0


# ============================================================
# Single SELL
# ============================================================


def test_composite_single_sell_signal():
    """
    单个高置信度SELL信号。
    """

    engine = CompositeSignalEngine()

    context = make_context()

    signal = make_signal(
        side=SignalSide.SELL,
        category=StrategyCategory.MOMENTUM,
        confidence=1.0,
        score=2.0,
        strategy="momentum_breakout",
    )

    result = engine.combine(
        [signal],
        context
    )

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert result.confidence > 0.0
    assert result.score > 0.0


# ============================================================
# Multiple BUY
# ============================================================


def test_composite_multiple_buy_signals():
    """
    多个策略同时BUY。

    Mean Reversion
           BUY

    Momentum
           BUY

    Liquidity
           BUY

            ↓

    Composite Signal
    """

    engine = CompositeSignalEngine()

    context = make_context()

    signals = [
        make_signal(
            side=SignalSide.BUY,
            category=StrategyCategory.MEAN_REVERSION,
            confidence=0.90,
            score=1.20,
            strategy="mean_reversion",
        ),

        make_signal(
            side=SignalSide.BUY,
            category=StrategyCategory.MOMENTUM,
            confidence=0.85,
            score=1.30,
            strategy="momentum_breakout",
        ),

        make_signal(
            side=SignalSide.BUY,
            category=StrategyCategory.LIQUIDITY,
            confidence=0.80,
            score=1.10,
            strategy="liquidity_vacuum",
        ),
    ]

    result = engine.combine(
        signals,
        context
    )

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert result.confidence > 0.0
    assert result.score > 0.0


# ============================================================
# Multiple SELL
# ============================================================


def test_composite_multiple_sell_signals():
    """
    多个策略同时SELL。
    """

    engine = CompositeSignalEngine()

    context = make_context()

    signals = [
        make_signal(
            side=SignalSide.SELL,
            category=StrategyCategory.MEAN_REVERSION,
            confidence=0.90,
            score=1.20,
            strategy="mean_reversion",
        ),

        make_signal(
            side=SignalSide.SELL,
            category=StrategyCategory.MOMENTUM,
            confidence=0.85,
            score=1.30,
            strategy="momentum_breakout",
        ),

        make_signal(
            side=SignalSide.SELL,
            category=StrategyCategory.ABSORPTION,
            confidence=0.80,
            score=1.10,
            strategy="absorption_refill",
        ),
    ]

    result = engine.combine(
        signals,
        context
    )

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert result.confidence > 0.0
    assert result.score > 0.0


# ============================================================
# BUY / SELL Conflict
# ============================================================


def test_composite_equal_conflict():
    """
    完全对称冲突：

        BUY
        SELL

    confidence相同
    score相同

    不应该形成明确交易方向。

    预期：

        No Trade
    """

    engine = CompositeSignalEngine()

    context = make_context()

    signals = [
        make_signal(
            side=SignalSide.BUY,
            category=StrategyCategory.MOMENTUM,
            confidence=0.90,
            score=1.50,
            strategy="buy_strategy",
        ),

        make_signal(
            side=SignalSide.SELL,
            category=StrategyCategory.MOMENTUM,
            confidence=0.90,
            score=1.50,
            strategy="sell_strategy",
        ),
    ]

    result = engine.combine(
        signals,
        context
    )

    assert_composite_contract(
        result
    )

    assert result.is_trade() is False


# ============================================================
# Weak Signal
# ============================================================


def test_composite_weak_signal_does_not_crash():
    """
    很弱的Signal必须能够正常处理。

    是否交易由当前Composite阈值决定，
    但绝对不能：

        - AttributeError
        - TypeError
        - Enum错误
        - Signal接口错误
    """

    engine = CompositeSignalEngine()

    context = make_context()

    signal = make_signal(
        side=SignalSide.BUY,
        category=StrategyCategory.MEAN_REVERSION,
        confidence=0.01,
        score=0.01,
        strategy="weak_signal",
    )

    result = engine.combine(
        [signal],
        context
    )

    assert_composite_contract(
        result
    )


# ============================================================
# Different Strategy Categories
# ============================================================


@pytest.mark.parametrize(
    "category",
    [
        StrategyCategory.MEAN_REVERSION,
        StrategyCategory.MOMENTUM,
        StrategyCategory.LIQUIDITY,
        StrategyCategory.ABSORPTION,
    ]
)
def test_composite_accepts_all_strategy_categories(
    category
):
    """
    Composite Engine必须接受四大策略分类。
    """

    engine = CompositeSignalEngine()

    context = make_context()

    signal = make_signal(
        side=SignalSide.BUY,
        category=category,
        confidence=1.0,
        score=2.0,
    )

    result = engine.combine(
        [signal],
        context
    )

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True


# ============================================================
# Fake Strategy
# ============================================================


class FixedSignalStrategy:
    """
    用于测试 StrategyManager。

    每次 on_context 都返回固定Signal。
    """

    def __init__(
        self,
        signal
    ):
        self.signal = signal
        self.started = False

    def on_start(self):
        self.started = True

    def on_stop(self):
        self.started = False

    def on_context(
        self,
        context
    ):
        return self.signal


class NoSignalStrategy:
    """
    永远不产生Signal。
    """

    def __init__(self):
        self.started = False

    def on_start(self):
        self.started = True

    def on_stop(self):
        self.started = False

    def on_context(
        self,
        context
    ):
        return None


# ============================================================
# StrategyManager Empty
# ============================================================


def test_strategy_manager_empty_runtime():
    """
    StrategyManager没有任何策略时：

        on_context()
            ↓
        CompositeSignal
            ↓
        No Trade
    """

    manager = StrategyManager()

    context = make_context()

    result = manager.on_context(
        context
    )

    assert_composite_contract(
        result
    )

    assert result.is_trade() is False

    assert manager.total_events == 1
    assert manager.signal_count == 0


# ============================================================
# StrategyManager Single BUY
# ============================================================


def test_strategy_manager_single_buy_runtime():
    """
    StrategyManager
          ↓
    Strategy
          ↓
    Signal BUY
          ↓
    CompositeSignalEngine
          ↓
    CompositeSignal
    """

    signal = make_signal(
        side=SignalSide.BUY,
        category=StrategyCategory.MEAN_REVERSION,
        confidence=1.0,
        score=2.0,
        strategy="mean_reversion",
    )

    strategy = FixedSignalStrategy(
        signal
    )

    manager = StrategyManager()

    manager.register(
        strategy
    )

    context = make_context()

    result = manager.on_context(
        context
    )

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert manager.total_events == 1
    assert manager.signal_count == 1


# ============================================================
# StrategyManager Multiple Signals
# ============================================================


def test_strategy_manager_multiple_buy_runtime():
    """
    验证多个Strategy通过Manager进入Composite。
    """

    strategy_1 = FixedSignalStrategy(
        make_signal(
            side=SignalSide.BUY,
            category=StrategyCategory.MEAN_REVERSION,
            confidence=0.90,
            score=1.20,
            strategy="mean_reversion",
        )
    )

    strategy_2 = FixedSignalStrategy(
        make_signal(
            side=SignalSide.BUY,
            category=StrategyCategory.MOMENTUM,
            confidence=0.90,
            score=1.20,
            strategy="momentum_breakout",
        )
    )

    manager = StrategyManager()

    manager.register(
        strategy_1
    )

    manager.register(
        strategy_2
    )

    context = make_context()

    result = manager.on_context(
        context
    )

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert manager.total_events == 1
    assert manager.signal_count == 1


# ============================================================
# StrategyManager No Signal
# ============================================================


def test_strategy_manager_no_signal_runtime():
    """
    Strategy存在，但不产生Signal。
    """

    manager = StrategyManager()

    manager.register(
        NoSignalStrategy()
    )

    context = make_context()

    result = manager.on_context(
        context
    )

    assert_composite_contract(
        result
    )

    assert result.is_trade() is False

    assert manager.total_events == 1
    assert manager.signal_count == 0


# ============================================================
# StrategyManager Lifecycle
# ============================================================


def test_strategy_manager_lifecycle():
    """
    验证Manager启动和停止Strategy。
    """

    strategy = NoSignalStrategy()

    manager = StrategyManager()

    manager.register(
        strategy
    )

    assert strategy.started is False

    manager.on_start()

    assert strategy.started is True

    manager.on_stop()

    assert strategy.started is False


# ============================================================
# StrategyManager Stats
# ============================================================


def test_strategy_manager_stats_runtime():
    """
    验证Manager统计接口。
    """

    manager = StrategyManager()

    manager.register(
        NoSignalStrategy()
    )

    context = make_context()

    manager.on_context(
        context
    )

    manager.on_context(
        context
    )

    stats = manager.stats()

    assert isinstance(
        stats,
        dict
    )

    assert stats[
        "events"
    ] == 2

    assert stats[
        "signals"
    ] == 0

    assert stats[
        "strategies"
    ] == 1

    assert stats[
        "exit_strategies"
    ] == 0