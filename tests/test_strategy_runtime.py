"""
tests/test_strategy_runtime.py

============================================================
Strategy Runtime Contract Test
============================================================

验证：

    SystemState.strategy_context
            ↓
    StrategyRuntime
            ↓
    StrategyManager.on_context(context)
            ↓
    CompositeSignal
            ↓
    StrategySignalAdapter
            ↓
    signals.signal.Signal

============================================================
"""


import pytest


from runtime.strategy_runtime import (
    StrategyRuntime,
)

from runtime.strategy_signal_adapter import (
    StrategySignalAdapter,
)

from strategy.composite_signal import (
    CompositeSignal,
)

from strategy.signal import (
    SignalSide as StrategySignalSide,
    SignalType as StrategySignalType,
    StrategyCategory,
)

from signals.signal import (
    Signal as RuntimeSignal,
    SignalSide as RuntimeSignalSide,
    SignalType as RuntimeSignalType,
)





# ============================================================
# Fake Context / State
# ============================================================


class FakeContext:

    def __init__(
        self,
        symbol="ESU6",
        timestamp=100,
    ):

        self.symbol = symbol

        self.timestamp = timestamp





class FakeState:

    def __init__(
        self,
        context=None,
    ):

        self.strategy_context = context





# ============================================================
# Fake Strategy Manager
# ============================================================


class FakeStrategyManager:

    def __init__(
        self,
        composite_signal=None,
    ):

        self.composite_signal = (
            composite_signal
        )

        self.started = False

        self.stopped = False

        self.context_count = 0

        self.last_context = None


    def on_start(self):

        self.started = True


    def on_stop(self):

        self.stopped = True


    def on_context(
        self,
        context,
    ):

        self.context_count += 1

        self.last_context = context

        return self.composite_signal





# ============================================================
# Helpers
# ============================================================


def create_trade_composite(
    side=StrategySignalSide.BUY,
    signal_type=StrategySignalType.ENTRY,
):

    return CompositeSignal(

        side=side,

        signal_type=signal_type,

        category=StrategyCategory.MEAN_REVERSION,

        confidence=0.85,

        score=1.5,

        reasons=[
            "runtime-test",
        ],

        strategies=[
            "mean_reversion",
        ],

    )





def create_runtime(
    composite_signal=None,
    quantity=1,
):

    manager = FakeStrategyManager(
        composite_signal=composite_signal
    )


    adapter = StrategySignalAdapter(
        quantity=quantity
    )


    runtime = StrategyRuntime(

        strategy_manager=manager,

        signal_adapter=adapter,

    )


    return (
        runtime,
        manager,
        adapter,
    )





# ============================================================
# Tests
# ============================================================


def test_strategy_runtime_requires_manager():

    with pytest.raises(
        ValueError
    ):

        StrategyRuntime(

            strategy_manager=None,

            signal_adapter=StrategySignalAdapter(
                quantity=1
            ),

        )





def test_strategy_runtime_requires_signal_adapter():

    with pytest.raises(
        ValueError
    ):

        StrategyRuntime(

            strategy_manager=FakeStrategyManager(),

            signal_adapter=None,

        )





def test_strategy_runtime_can_initialize():

    (
        runtime,
        manager,
        adapter,
    ) = create_runtime()


    assert runtime.strategy_manager is manager

    assert runtime.signal_adapter is adapter

    assert runtime.running is False





def test_strategy_runtime_start_calls_manager():

    (
        runtime,
        manager,
        _,
    ) = create_runtime()


    runtime.start()


    assert runtime.running is True

    assert manager.started is True





def test_strategy_runtime_stop_calls_manager():

    (
        runtime,
        manager,
        _,
    ) = create_runtime()


    runtime.start()

    runtime.stop()


    assert runtime.running is False

    assert manager.stopped is True





def test_strategy_runtime_does_not_update_when_stopped():

    (
        runtime,
        manager,
        _,
    ) = create_runtime(
        composite_signal=create_trade_composite()
    )


    state = FakeState(
        FakeContext()
    )


    result = runtime.update(
        state
    )


    assert result is None

    assert manager.context_count == 0

    assert runtime.context_count == 0





def test_strategy_runtime_requires_strategy_context():

    (
        runtime,
        manager,
        _,
    ) = create_runtime(
        composite_signal=create_trade_composite()
    )


    runtime.start()


    result = runtime.update(
        FakeState(
            context=None
        )
    )


    assert result is None

    assert manager.context_count == 0

    assert runtime.context_count == 0





def test_strategy_runtime_passes_context_to_manager():

    (
        runtime,
        manager,
        _,
    ) = create_runtime(
        composite_signal=CompositeSignal()
    )


    runtime.start()


    context = FakeContext(
        symbol="ESU6",
        timestamp=123,
    )


    result = runtime.update(

        FakeState(
            context
        )

    )


    assert result is None

    assert manager.context_count == 1

    assert manager.last_context is context

    assert runtime.last_context is context

    assert runtime.context_count == 1





def test_strategy_runtime_converts_buy_entry():

    (
        runtime,
        _,
        _,
    ) = create_runtime(

        composite_signal=create_trade_composite(

            side=StrategySignalSide.BUY,

            signal_type=StrategySignalType.ENTRY,

        ),

        quantity=2,

    )


    runtime.start()


    result = runtime.update(

        FakeState(

            FakeContext(
                symbol="ESU6",
                timestamp=456,
            )

        )

    )


    assert isinstance(
        result,
        RuntimeSignal
    )


    assert result.symbol == "ESU6"

    assert result.side == RuntimeSignalSide.BUY

    assert result.quantity == 2

    assert result.signal_type == RuntimeSignalType.ENTRY


    assert runtime.composite_signal_count == 1

    assert runtime.runtime_signal_count == 1

    assert runtime.last_signal is result





def test_strategy_runtime_converts_sell_exit():

    (
        runtime,
        _,
        _,
    ) = create_runtime(

        composite_signal=create_trade_composite(

            side=StrategySignalSide.SELL,

            signal_type=StrategySignalType.EXIT,

        ),

        quantity=1,

    )


    runtime.start()


    result = runtime.update(

        FakeState(

            FakeContext(
                symbol="ESU6"
            )

        )

    )


    assert isinstance(
        result,
        RuntimeSignal
    )


    assert result.side == RuntimeSignalSide.SELL

    assert result.signal_type == RuntimeSignalType.EXIT





def test_strategy_runtime_non_trade_composite_returns_none():

    (
        runtime,
        _,
        _,
    ) = create_runtime(

        composite_signal=CompositeSignal()

    )


    runtime.start()


    result = runtime.update(

        FakeState(
            FakeContext()
        )

    )


    assert result is None

    assert runtime.context_count == 1

    assert runtime.composite_signal_count == 0

    assert runtime.runtime_signal_count == 0





def test_strategy_runtime_reset():

    (
        runtime,
        _,
        _,
    ) = create_runtime(

        composite_signal=create_trade_composite()

    )


    runtime.start()


    runtime.update(

        FakeState(
            FakeContext()
        )

    )


    assert runtime.context_count == 1

    assert runtime.runtime_signal_count == 1


    runtime.reset()


    assert runtime.context_count == 0

    assert runtime.composite_signal_count == 0

    assert runtime.runtime_signal_count == 0

    assert runtime.last_context is None

    assert runtime.last_composite_signal is None

    assert runtime.last_signal is None





def test_strategy_runtime_status():

    (
        runtime,
        _,
        _,
    ) = create_runtime(

        composite_signal=create_trade_composite()

    )


    runtime.start()


    runtime.update(

        FakeState(
            FakeContext()
        )

    )


    status = runtime.status()


    assert status["running"] is True

    assert status["contexts"] == 1

    assert status["composite_signals"] == 1

    assert status["runtime_signals"] == 1
