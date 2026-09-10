"""
tests/test_strategy_exit_semantics.py

============================================================
Strategy EXIT Semantics Contract
============================================================

验证：

1. HOLD + ENTRY 仍然无效
2. HOLD + EXIT 是合法策略退出意图
3. LONG + HOLD EXIT -> SELL EXIT
4. SHORT + HOLD EXIT -> BUY EXIT
5. FLAT + HOLD EXIT -> no trade
6. EXIT 优先于 ENTRY
7. 显式 BUY/SELL EXIT 继续保持原方向

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
)

from strategy.context import (
    StrategyContext,
    PositionContext,
)





def make_context(
    side="FLAT",
    quantity=0,
):

    return StrategyContext(

        symbol="ESU6",

        position=PositionContext(

            symbol="ESU6",

            quantity=quantity,

            side=side,

        ),

    )





def make_hold_exit(
    score=1.5,
    confidence=0.8,
):

    return Signal(

        side=SignalSide.HOLD,

        signal_type=SignalType.EXIT,

        category=StrategyCategory.EXIT,

        size=1,

        confidence=confidence,

        score=score,

        reason="exit current position",

        strategy="exit_strategy",

    )





def test_hold_entry_is_invalid():

    signal = Signal(

        side=SignalSide.HOLD,

        signal_type=SignalType.ENTRY,

        size=1,

    )


    assert signal.is_valid() is False





def test_hold_exit_is_valid():

    signal = make_hold_exit()


    assert signal.is_valid() is True

    assert signal.is_exit() is True





def test_hold_exit_long_resolves_to_sell():

    engine = CompositeSignalEngine()

    context = make_context(

        side="LONG",

        quantity=2,

    )


    result = engine.combine(

        [make_hold_exit()],

        context,

    )


    assert result.is_trade() is True

    assert result.is_exit() is True

    assert result.side == SignalSide.SELL

    assert result.signal_type == SignalType.EXIT





def test_hold_exit_short_resolves_to_buy():

    engine = CompositeSignalEngine()

    context = make_context(

        side="SHORT",

        quantity=2,

    )


    result = engine.combine(

        [make_hold_exit()],

        context,

    )


    assert result.is_trade() is True

    assert result.is_exit() is True

    assert result.side == SignalSide.BUY

    assert result.signal_type == SignalType.EXIT





def test_hold_exit_flat_returns_no_trade():

    engine = CompositeSignalEngine()

    context = make_context(

        side="FLAT",

        quantity=0,

    )


    result = engine.combine(

        [make_hold_exit()],

        context,

    )


    assert result.is_trade() is False

    assert result.side == SignalSide.HOLD

    assert result.signal_type == SignalType.NONE





def test_hold_exit_without_context_returns_no_trade():

    engine = CompositeSignalEngine()


    result = engine.combine(

        [make_hold_exit()],

        context=None,

    )


    assert result.is_trade() is False





def test_exit_priority_over_entry_with_hold_exit():

    engine = CompositeSignalEngine()

    context = make_context(

        side="LONG",

        quantity=1,

    )


    entry = Signal(

        side=SignalSide.BUY,

        signal_type=SignalType.ENTRY,

        category=StrategyCategory.MEAN_REVERSION,

        confidence=0.95,

        score=2.0,

        strategy="entry_strategy",

    )


    exit_signal = make_hold_exit(

        score=1.5,

        confidence=0.8,

    )


    result = engine.combine(

        [
            entry,
            exit_signal,
        ],

        context,

    )


    assert result.is_trade() is True

    assert result.signal_type == SignalType.EXIT

    assert result.side == SignalSide.SELL





def test_explicit_buy_exit_keeps_buy_direction():

    engine = CompositeSignalEngine()

    signal = Signal(

        side=SignalSide.BUY,

        signal_type=SignalType.EXIT,

        category=StrategyCategory.EXIT,

        confidence=0.8,

        score=1.5,

    )


    result = engine.combine(

        [signal],

        make_context(
            side="LONG",
            quantity=1,
        ),

    )


    assert result.is_trade() is True

    assert result.signal_type == SignalType.EXIT

    assert result.side == SignalSide.BUY





def test_explicit_sell_exit_keeps_sell_direction():

    engine = CompositeSignalEngine()

    signal = Signal(

        side=SignalSide.SELL,

        signal_type=SignalType.EXIT,

        category=StrategyCategory.EXIT,

        confidence=0.8,

        score=1.5,

    )


    result = engine.combine(

        [signal],

        make_context(
            side="SHORT",
            quantity=1,
        ),

    )


    assert result.is_trade() is True

    assert result.signal_type == SignalType.EXIT

    assert result.side == SignalSide.SELL





def test_hold_exit_zero_size_is_invalid():

    signal = Signal(

        side=SignalSide.HOLD,

        signal_type=SignalType.EXIT,

        size=0,

    )


    assert signal.is_valid() is False
