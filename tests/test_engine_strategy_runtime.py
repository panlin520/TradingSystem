"""
tests/test_engine_strategy_runtime.py

============================================================
Engine Strategy Runtime Integration Contract Test
============================================================

验证：

    MarketEvent
        ↓
    F_LAST
        ↓
    StrategyContextRuntime
        ↓
    state.strategy_context
        ↓
    StrategyRuntime.update(state)
        ↓
    Runtime Signal
        ↓
    Engine._process_signal()

并确认：

    - 非 F_LAST 不调用 StrategyRuntime
    - StrategyRuntime 生命周期由 Engine 调度
    - StrategyRuntime 优先于 legacy generate_signal()
    - 旧 Strategy Market Hook 保持兼容

============================================================
"""


from core.engine import (
    TradingEngine,
    EngineMode,
)

from signals.signal import (
    Signal,
    SignalSide,
)





class FakeEvent:

    def __init__(
        self,
        ts_event=100,
        flags=128,
    ):

        self.ts_event = ts_event

        self.flags = flags





class FakeOrderBook:

    def __init__(self):

        self.event_count = 0


    def on_event(
        self,
        event,
    ):

        self.event_count += 1





class FakeStrategyContext:

    def __init__(
        self,
        symbol="ESU6",
        timestamp=100,
    ):

        self.symbol = symbol

        self.timestamp = timestamp





class FakeStrategyContextRuntime:

    def __init__(self):

        self.build_count = 0

        self.last_state = None

        self.last_risk_manager = None


    def build(
        self,
        state,
        risk_manager=None,
    ):

        self.build_count += 1

        self.last_state = state

        self.last_risk_manager = risk_manager


        return FakeStrategyContext(
            symbol="ESU6",
            timestamp=state.last_event.ts_event,
        )





class FakeStrategyRuntime:

    def __init__(
        self,
        signal=None,
    ):

        self.signal = signal

        self.started = False

        self.stopped = False

        self.update_count = 0

        self.last_state = None

        self.context_seen = None


    def start(self):

        self.started = True


    def stop(self):

        self.stopped = True


    def update(
        self,
        state,
    ):

        self.update_count += 1

        self.last_state = state

        self.context_seen = (
            state.strategy_context
        )

        return self.signal





class FakeLegacyStrategy:

    def __init__(self):

        self.started = False

        self.stopped = False

        self.market_event_count = 0

        self.generate_count = 0


    def on_start(
        self,
        state,
    ):

        self.started = True


    def on_stop(
        self,
        state,
    ):

        self.stopped = True


    def on_market_event(
        self,
        event,
        state,
    ):

        self.market_event_count += 1


    def generate_signal(
        self,
        event,
        state,
    ):

        self.generate_count += 1


        return Signal(
            symbol="ESU6",
            side=SignalSide.SELL,
            quantity=99,
            strategy="legacy",
        )





def create_runtime_signal():

    return Signal(
        symbol="ESU6",
        side=SignalSide.BUY,
        quantity=2,
        strategy="strategy_runtime",
        confidence=0.90,
    )





def create_engine(
    strategy_runtime=None,
    strategy=None,
):

    context_runtime = (
        FakeStrategyContextRuntime()
    )


    engine = TradingEngine(

        mode=EngineMode.BACKTEST,

        orderbook=FakeOrderBook(),

        strategy=strategy,

        strategy_context_runtime=(
            context_runtime
        ),

        strategy_runtime=(
            strategy_runtime
        ),

    )


    return (
        engine,
        context_runtime,
    )





def test_engine_can_initialize_strategy_runtime():

    runtime = FakeStrategyRuntime()


    engine, _ = create_engine(
        strategy_runtime=runtime
    )


    assert engine.strategy_runtime is runtime





def test_engine_start_stop_strategy_runtime_lifecycle():

    runtime = FakeStrategyRuntime()


    engine, _ = create_engine(
        strategy_runtime=runtime
    )


    engine.start()


    assert runtime.started is True


    engine.stop()


    assert runtime.stopped is True





def test_non_f_last_does_not_call_strategy_runtime():

    runtime = FakeStrategyRuntime(
        signal=create_runtime_signal()
    )


    engine, context_runtime = create_engine(
        strategy_runtime=runtime
    )


    engine.start()


    engine.on_event(

        FakeEvent(
            ts_event=100,
            flags=0,
        )

    )


    assert engine.processed_events == 1

    assert engine.stable_events == 0

    assert context_runtime.build_count == 0

    assert runtime.update_count == 0

    assert engine.state.strategy_context is None

    assert engine.signal_count == 0





def test_f_last_builds_context_before_strategy_runtime():

    runtime = FakeStrategyRuntime(
        signal=create_runtime_signal()
    )


    engine, context_runtime = create_engine(
        strategy_runtime=runtime
    )


    engine.start()


    event = FakeEvent(
        ts_event=200,
        flags=128,
    )


    engine.on_event(
        event
    )


    assert engine.stable_events == 1

    assert context_runtime.build_count == 1

    assert runtime.update_count == 1

    assert runtime.last_state is engine.state

    assert runtime.context_seen is (
        engine.state.strategy_context
    )

    assert runtime.context_seen is not None

    assert runtime.context_seen.timestamp == 200





def test_strategy_runtime_signal_enters_engine_pipeline():

    signal = create_runtime_signal()

    runtime = FakeStrategyRuntime(
        signal=signal
    )


    engine, _ = create_engine(
        strategy_runtime=runtime
    )


    engine.start()


    engine.on_event(
        FakeEvent(
            flags=128
        )
    )


    assert engine.signal_count == 1

    assert engine.last_signal is signal

    assert engine.signals == [
        signal
    ]


    # _process_signal() 在没有 Risk / Execution 时
    # 仍会完成 Runtime Signal → Order 转换。
    assert engine.order_count == 1

    assert engine.last_order.symbol == "ESU6"

    assert engine.last_order.quantity == 2

    assert engine.last_order.side.value == "BUY"





def test_strategy_runtime_has_priority_over_legacy_generate_signal():

    runtime_signal = create_runtime_signal()

    runtime = FakeStrategyRuntime(
        signal=runtime_signal
    )

    legacy = FakeLegacyStrategy()


    engine, _ = create_engine(

        strategy_runtime=runtime,

        strategy=legacy,

    )


    engine.start()


    engine.on_event(
        FakeEvent(
            flags=128
        )
    )


    # Legacy market hook 继续兼容
    assert legacy.market_event_count == 1


    # 但正式 StrategyRuntime 存在时，
    # 不再调用 legacy generate_signal()
    assert legacy.generate_count == 0


    assert engine.last_signal is runtime_signal

    assert engine.last_signal.quantity == 2





def test_legacy_generate_signal_still_works_without_strategy_runtime():

    legacy = FakeLegacyStrategy()


    engine, _ = create_engine(

        strategy_runtime=None,

        strategy=legacy,

    )


    engine.start()


    engine.on_event(
        FakeEvent(
            flags=128
        )
    )


    assert legacy.market_event_count == 1

    assert legacy.generate_count == 1

    assert engine.signal_count == 1

    assert engine.last_signal.strategy == "legacy"

    assert engine.last_signal.quantity == 99





def test_engine_starts_and_stops_both_runtime_and_legacy_strategy():

    runtime = FakeStrategyRuntime()

    legacy = FakeLegacyStrategy()


    engine, _ = create_engine(

        strategy_runtime=runtime,

        strategy=legacy,

    )


    engine.start()


    assert runtime.started is True

    assert legacy.started is True


    engine.stop()


    assert runtime.stopped is True

    assert legacy.stopped is True
