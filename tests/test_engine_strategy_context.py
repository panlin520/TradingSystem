"""
tests/test_engine_strategy_context.py


============================================================
Engine Strategy Context Runtime Contract Test
============================================================


验证：

    TradingEngine

        ↓

    F_LAST Boundary

        ↓

    StrategyContextRuntime

        ↓

    SystemState.strategy_context

        ↓

    Strategy.on_market_event(event, state)


重点确认：

    1. 非 F_LAST 不生成 StrategyContext

    2. F_LAST 才生成 StrategyContext

    3. TradingEngine.risk 显式传入 StrategyContextRuntime

    4. Strategy 在原接口 on_market_event(event, state)
       中可以读取 state.strategy_context

    5. 不修改 Strategy 调用接口


============================================================
"""


from core.engine import (
    TradingEngine,
    EngineMode,
)

from features.snapshot import FeatureSnapshot

from runtime.strategy_context_runtime import (
    StrategyContextRuntime,
)

from strategy.context import StrategyContext





# ============================================================
# Fake Market Event
# ============================================================


class FakeEvent:
    """
    Engine 当前测试所需最小 MarketEvent。

    正式 Engine 当前读取：

        ts_event
        flags
    """

    def __init__(
        self,
        ts_event=100,
        flags=128,
    ):

        self.ts_event = ts_event

        self.flags = flags





# ============================================================
# Fake OrderBook
# ============================================================


class FakeOrderBook:
    """
    对齐 ContextBuilder 当前使用的正式 OrderBook 接口：

        on_event(event)

        best_bid()

        best_ask()

        bid_volume()

        ask_volume()

        orders
    """

    def __init__(self):

        self.orders = {
            1: object(),
            2: object(),
        }

        self.event_count = 0


    def on_event(
        self,
        event
    ):

        self.event_count += 1


    def best_bid(self):

        return 7571000000000


    def best_ask(self):

        return 7571250000000


    def bid_volume(self):

        return 120


    def ask_volume(self):

        return 100





# ============================================================
# Fake Feature Runtime
# ============================================================


class FakeFeatureRuntime:
    """
    对齐 FeatureRuntime.update(timestamp=None) 接口。

    这里不测试 FeatureEngine 本身；
    只为 Engine -> StrategyContext 提供真实形状的 FeatureSnapshot。
    """

    def __init__(self):

        self.latest_snapshot = None

        self.update_count = 0


    def update(
        self,
        timestamp=None
    ):

        self.update_count += 1


        self.latest_snapshot = FeatureSnapshot(

            timestamp=timestamp or 0,

            sequence=self.update_count,

            symbol="ESU6",

            best_bid=7571000000000,

            best_ask=7571250000000,

            spread=250000000,

            mid_price=7571.125,

            micro_price=7571.13,

            bid_volume=120,

            ask_volume=100,

            obi=0.0909,

        )


        return self.latest_snapshot





# ============================================================
# Fake Portfolio
# ============================================================


class FakePosition:

    def __init__(self):

        self.quantity = 2

        self.side = "LONG"

        self.avg_price = 7570.0





class FakePortfolio:

    def __init__(self):

        self.position = FakePosition()


    def get_position(
        self,
        symbol
    ):

        return self.position





# ============================================================
# Fake Risk
# ============================================================


class FakeKillSwitch:

    def __init__(
        self,
        triggered=False
    ):

        self.triggered = triggered


    def is_triggered(self):

        return self.triggered





class FakeRiskManager:
    """
    对齐 StrategyContext 当前读取的 Risk 接口：

        risk_manager.kill_switch.is_triggered()
    """

    def __init__(
        self,
        triggered=False
    ):

        self.kill_switch = FakeKillSwitch(
            triggered=triggered
        )





# ============================================================
# StrategyContextRuntime Spy
# ============================================================


class SpyStrategyContextRuntime(
    StrategyContextRuntime
):
    """
    使用正式 StrategyContextRuntime 实现，
    仅记录 Engine 实际传入的参数。
    """

    def __init__(self):

        super().__init__()

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


        return super().build(

            state=state,

            risk_manager=risk_manager,

        )





# ============================================================
# Fake Strategy
# ============================================================


class FakeStrategy:
    """
    保持 Engine 当前正式 Strategy Market Hook：

        on_market_event(event, state)

    不增加 context 参数。
    """

    def __init__(self):

        self.market_event_count = 0

        self.last_event = None

        self.last_state = None

        self.context_seen = None


    def on_market_event(
        self,
        event,
        state,
    ):

        self.market_event_count += 1

        self.last_event = event

        self.last_state = state

        self.context_seen = state.strategy_context





# ============================================================
# Engine Factory
# ============================================================


def create_engine(
    risk=None,
    strategy=None,
    strategy_context_runtime=None,
):

    if risk is None:

        risk = FakeRiskManager()


    if strategy is None:

        strategy = FakeStrategy()


    if strategy_context_runtime is None:

        strategy_context_runtime = (
            SpyStrategyContextRuntime()
        )


    engine = TradingEngine(

        mode=EngineMode.BACKTEST,

        orderbook=FakeOrderBook(),

        strategy=strategy,

        risk=risk,

        portfolio=FakePortfolio(),

        feature_runtime=FakeFeatureRuntime(),

        strategy_context_runtime=(
            strategy_context_runtime
        ),

    )


    return (
        engine,
        strategy,
        risk,
        strategy_context_runtime,
    )





# ============================================================
# Tests
# ============================================================


def test_engine_can_initialize_strategy_context_runtime():


    (
        engine,
        _,
        _,
        runtime,
    ) = create_engine()


    assert engine.strategy_context_runtime is runtime


    assert engine.state.strategy_context is None





def test_non_f_last_does_not_build_strategy_context():


    (
        engine,
        strategy,
        _,
        runtime,
    ) = create_engine()


    engine.start()


    engine.on_event(

        FakeEvent(

            ts_event=100,

            flags=0,

        )

    )


    # Raw path 已运行
    assert engine.processed_events == 1


    # 但没有越过 F_LAST boundary
    assert engine.stable_events == 0


    assert runtime.build_count == 0


    assert engine.state.strategy_context is None


    assert strategy.market_event_count == 0





def test_f_last_builds_strategy_context():


    (
        engine,
        _,
        _,
        runtime,
    ) = create_engine()


    engine.start()


    engine.on_event(

        FakeEvent(

            ts_event=100,

            flags=128,

        )

    )


    assert engine.stable_events == 1


    assert runtime.build_count == 1


    assert isinstance(

        engine.state.strategy_context,

        StrategyContext,

    )


    assert (
        engine.state.strategy_context.symbol
        ==
        "ESU6"
    )


    assert (
        engine.state.strategy_context.orderbook.best_bid
        ==
        7571000000000
    )


    assert (
        engine.state.strategy_context.features.mid_price
        ==
        7571.125
    )





def test_engine_passes_its_risk_to_strategy_context_runtime():


    risk = FakeRiskManager(

        triggered=True

    )


    runtime = SpyStrategyContextRuntime()


    (
        engine,
        _,
        _,
        _,
    ) = create_engine(

        risk=risk,

        strategy_context_runtime=runtime,

    )


    engine.start()


    engine.on_event(

        FakeEvent(

            flags=128

        )

    )


    assert runtime.last_state is engine.state


    assert runtime.last_risk_manager is engine.risk


    assert runtime.last_risk_manager is risk


    assert (
        engine.state.strategy_context.risk.kill_switch
        is True
    )


    assert (
        engine.state.strategy_context.risk.allowed
        is False
    )





def test_strategy_reads_context_through_existing_event_state_interface():


    strategy = FakeStrategy()


    (
        engine,
        _,
        _,
        runtime,
    ) = create_engine(

        strategy=strategy

    )


    engine.start()


    event = FakeEvent(

        ts_event=200,

        flags=128,

    )


    engine.on_event(

        event

    )


    # Strategy Market Hook 仍然是：
    #
    #     on_market_event(event, state)
    #
    # Context 通过 state 提供。

    assert strategy.market_event_count == 1


    assert strategy.last_event is event


    assert strategy.last_state is engine.state


    assert strategy.context_seen is (
        engine.state.strategy_context
    )


    assert isinstance(

        strategy.context_seen,

        StrategyContext,

    )


    # Context 必须先于 Strategy Hook 构建
    assert runtime.build_count == 1


    assert (
        strategy.context_seen.timestamp
        ==
        200
    )
