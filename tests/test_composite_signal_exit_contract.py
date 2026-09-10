"""
tests/test_composite_signal_exit_contract.py

============================================================
Composite Signal EXIT Contract Test
============================================================

验证：

    strategy.signal.Signal(EXIT)
            ↓
    CompositeSignalEngine.combine(...)
            ↓
    CompositeSignal(EXIT)

核心约束：

    EXIT 输入经过 CompositeSignalEngine 后，
    signal_type 必须继续保持 EXIT。

============================================================
"""

from strategy.signal import (
    Signal,
    SignalSide,
    SignalType,
    StrategyCategory,
)

from strategy.composite_signal import (
    CompositeSignalEngine,
    CompositeSignal,
)


class FakeContext:
    """
    CompositeSignalEngine.combine() 当前只需要：

        context.can_trade()

    EXIT 在 combine() 中优先于 entry permission，
    但提供此接口保持契约完整。
    """

    def can_trade(self):

        return True


def test_single_buy_exit_preserves_exit_type():

    engine = CompositeSignalEngine(
        min_confidence=0.6,
        min_score=1.0,
    )

    signal = Signal(
        side=SignalSide.BUY,
        signal_type=SignalType.EXIT,
        category=StrategyCategory.EXIT,
        confidence=0.90,
        score=1.5,
        reason="exit long",
        strategy="exit_strategy",
    )

    result = engine.combine(
        [signal],
        FakeContext(),
    )

    assert isinstance(
        result,
        CompositeSignal,
    )

    assert result.is_trade() is True

    assert result.is_exit() is True

    assert result.is_entry() is False

    assert result.signal_type == SignalType.EXIT

    assert result.side == SignalSide.BUY


def test_single_sell_exit_preserves_exit_type():

    engine = CompositeSignalEngine(
        min_confidence=0.6,
        min_score=1.0,
    )

    signal = Signal(
        side=SignalSide.SELL,
        signal_type=SignalType.EXIT,
        category=StrategyCategory.EXIT,
        confidence=0.90,
        score=1.5,
        reason="exit short",
        strategy="exit_strategy",
    )

    result = engine.combine(
        [signal],
        FakeContext(),
    )

    assert result.is_trade() is True

    assert result.is_exit() is True

    assert result.is_entry() is False

    assert result.signal_type == SignalType.EXIT

    assert result.side == SignalSide.SELL


def test_multiple_exit_signals_preserve_exit_type():

    engine = CompositeSignalEngine(
        min_confidence=0.6,
        min_score=1.0,
    )

    signals = [
        Signal(
            side=SignalSide.BUY,
            signal_type=SignalType.EXIT,
            category=StrategyCategory.EXIT,
            confidence=0.80,
            score=0.8,
            reason="exit-1",
            strategy="exit_strategy_1",
        ),
        Signal(
            side=SignalSide.BUY,
            signal_type=SignalType.EXIT,
            category=StrategyCategory.EXIT,
            confidence=0.90,
            score=0.9,
            reason="exit-2",
            strategy="exit_strategy_2",
        ),
    ]

    result = engine.combine(
        signals,
        FakeContext(),
    )

    assert result.is_trade() is True

    assert result.signal_type == SignalType.EXIT

    assert result.side == SignalSide.BUY

    assert result.is_exit() is True


def test_exit_has_priority_over_entry():

    engine = CompositeSignalEngine(
        min_confidence=0.6,
        min_score=1.0,
    )

    signals = [
        Signal(
            side=SignalSide.SELL,
            signal_type=SignalType.ENTRY,
            category=StrategyCategory.MEAN_REVERSION,
            confidence=0.95,
            score=2.0,
            reason="entry signal",
            strategy="entry_strategy",
        ),
        Signal(
            side=SignalSide.BUY,
            signal_type=SignalType.EXIT,
            category=StrategyCategory.EXIT,
            confidence=0.90,
            score=1.5,
            reason="exit signal",
            strategy="exit_strategy",
        ),
    ]

    result = engine.combine(
        signals,
        FakeContext(),
    )

    assert result.is_trade() is True

    assert result.signal_type == SignalType.EXIT

    assert result.side == SignalSide.BUY
