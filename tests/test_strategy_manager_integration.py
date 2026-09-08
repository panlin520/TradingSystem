"""
tests/test_strategy_manager_integration.py

============================================================
Strategy Manager Integration Tests
============================================================

目标：

    验证真实策略：

        MeanReversionStrategy
        MomentumBreakoutStrategy
        LiquidityVacuumStrategy
        AbsorptionRefillStrategy

    与：

        StrategyContext
        StrategyManager
        CompositeSignalEngine
        CompositeSignal

    能够组成完整运行链路。

============================================================

Pipeline:

    StrategyContext Sequence
            |
            v
    Real Strategies
            |
            v
    StrategyManager
            |
            v
    CompositeSignalEngine
            |
            v
    CompositeSignal

============================================================

本测试验证：

    1. 四个真实策略可以注册到Manager
    2. Manager可以驱动真实策略warmup
    3. Mean Reversion通过Manager产生交易
    4. Momentum Breakout通过Manager产生交易
    5. Liquidity Vacuum通过Manager产生交易
    6. Absorption / Refill通过Manager产生交易
    7. 多策略可以同时运行
    8. 多策略长序列运行不崩溃
    9. Manager统计正确
    10. Composite结果符合契约

============================================================

本测试不负责：

    - Databento
    - OrderBook重建
    - FeatureEngine真实计算
    - Risk执行
    - Execution
    - Portfolio
    - 策略盈利能力

============================================================
"""

from strategy.context import (
    StrategyContext,
    OrderBookContext,
    FeatureContext,
    RegimeContext,
    PositionContext,
    RiskContext,
)

from strategy.composite_signal import (
    CompositeSignal,
    CompositeSignalEngine,
)

from strategy.strategy_manager import (
    StrategyManager,
)

from strategy.strategies.mean_reversion import (
    MeanReversionStrategy,
)

from strategy.strategies.momentum_breakout import (
    MomentumBreakoutStrategy,
)

from strategy.strategies.liquidity_vacuum import (
    LiquidityVacuumStrategy,
)

from strategy.strategies.absorption_refill import (
    AbsorptionRefillStrategy,
)


# ============================================================
# Context Factory
# ============================================================


def make_context(
    *,
    timestamp=1,
    symbol="ESU6",

    mid_price=100.0,
    micro_price=100.0,

    best_bid=99.75,
    best_ask=100.25,

    bid_size=100,
    ask_size=100,

    spread=0.50,

    queue_imbalance=0.0,
    ofi=0.0,

    trade_volume=100,

    aggressive_buy_volume=50,
    aggressive_sell_volume=50,

    trade_imbalance=0.0,
    volatility=0.25,

    allowed=True,
    kill_switch=False,
):
    """
    创建标准 StrategyContext。

    此处人为构造 Feature / OrderBook 状态，
    用于测试 StrategyManager 上层集成。

    不依赖真实 OrderBook。
    """

    return StrategyContext(
        timestamp=timestamp,
        symbol=symbol,

        orderbook=OrderBookContext(
            best_bid=best_bid,
            best_ask=best_ask,
            bid_size=bid_size,
            ask_size=ask_size,
            spread=spread,
            depth={},
            active_orders=1000,
        ),

        features=FeatureContext(
            mid_price=mid_price,
            micro_price=micro_price,
            obi=0.0,
            queue_imbalance=queue_imbalance,
            ofi=ofi,
            trade_volume=trade_volume,
            aggressive_buy_volume=(
                aggressive_buy_volume
            ),
            aggressive_sell_volume=(
                aggressive_sell_volume
            ),
            trade_imbalance=trade_imbalance,
            volatility=volatility,
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


# ============================================================
# Composite Contract
# ============================================================


def assert_composite_contract(
    result
):
    """
    验证 StrategyManager 输出符合
    CompositeSignal 契约。
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
# Manager Factory
# ============================================================


def make_manager(
    *strategies,
    composite_engine=None,
):
    """
    创建 StrategyManager，
    并注册指定真实策略。

    composite_engine:
        测试需要时允许显式注入，
        不修改生产代码默认参数。
    """

    manager = StrategyManager(
        composite_engine=composite_engine
    )

    for strategy in strategies:
        manager.register(
            strategy
        )

    return manager


# ============================================================
# Registration
# ============================================================


def test_real_strategies_can_register():
    """
    四个真实策略必须可以同时注册。
    """

    strategies = [
        MeanReversionStrategy(
            window=5
        ),

        MomentumBreakoutStrategy(
            lookback=5
        ),

        LiquidityVacuumStrategy(
            lookback=5
        ),

        AbsorptionRefillStrategy(
            lookback=5
        ),
    ]

    manager = make_manager(
        *strategies
    )

    assert len(
        manager.strategies
    ) == 4

    assert manager.strategies[
        0
    ] is strategies[0]

    assert manager.strategies[
        1
    ] is strategies[1]

    assert manager.strategies[
        2
    ] is strategies[2]

    assert manager.strategies[
        3
    ] is strategies[3]


# ============================================================
# Warmup
# ============================================================


def test_real_strategies_warmup_through_manager():
    """
    四个真实策略同时处于warmup阶段。

    Manager必须能够正常驱动，
    不允许出现运行时接口错误。
    """

    manager = make_manager(
        MeanReversionStrategy(
            window=10
        ),

        MomentumBreakoutStrategy(
            lookback=10
        ),

        LiquidityVacuumStrategy(
            lookback=10
        ),

        AbsorptionRefillStrategy(
            lookback=10
        ),
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


# ============================================================
# Mean Reversion Integration
# ============================================================


def test_mean_reversion_through_manager():
    """
    人工制造明显价格下偏：

        100
        100
        100
        100
         95

    真实链路：

        StrategyContext
              ↓
        MeanReversionStrategy
              ↓
        StrategyManager
              ↓
        CompositeSignalEngine
              ↓
        CompositeSignal

    最后应该产生交易。
    """

    strategy = MeanReversionStrategy(
        window=5,
        deviation_threshold=1.0,
        min_confidence=0.0,
    )

    manager = make_manager(
        strategy,
        composite_engine=CompositeSignalEngine(
            min_confidence=0.50,
            min_score=1.0,
        ),
    )

    prices = [
        100.0,
        100.0,
        100.0,
        100.0,
        95.0,
    ]

    result = None

    for index, price in enumerate(
        prices,
        start=1
    ):
        context = make_context(
            timestamp=index,
            mid_price=price,
            queue_imbalance=1.0,
            ofi=20.0,
            trade_imbalance=1.0,
        )

        result = manager.on_context(
            context
        )

    assert result is not None

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert result.confidence > 0.0
    assert result.score > 0.0

    assert manager.total_events == 5
    assert manager.signal_count >= 1


# ============================================================
# Momentum Integration
# ============================================================


def test_momentum_breakout_through_manager():
    """
    人工制造向上突破：

        100.00
        100.10
        100.20
        100.30
        101.00

    预期：

        Momentum策略产生信号
            ↓
        Manager融合
            ↓
        Trade
    """

    strategy = MomentumBreakoutStrategy(
        lookback=5,
        breakout_threshold=0.5,
        min_confidence=0.0,
    )

    manager = make_manager(
        strategy
    )

    prices = [
        100.00,
        100.10,
        100.20,
        100.30,
        101.00,
    ]

    result = None

    for index, price in enumerate(
        prices,
        start=1
    ):
        context = make_context(
            timestamp=index,
            mid_price=price,
            queue_imbalance=1.0,
            ofi=20.0,
            trade_imbalance=1.0,
        )

        result = manager.on_context(
            context
        )

    assert result is not None

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert result.confidence > 0.0
    assert result.score > 0.0

    assert manager.total_events == 5
    assert manager.signal_count >= 1


# ============================================================
# Liquidity Vacuum Integration
# ============================================================


def test_liquidity_vacuum_through_manager():
    """
    人工制造Bid流动性骤降：

        100
        100
        100
         20

    预期：

        LiquidityVacuum
              ↓
        SELL Signal
              ↓
        StrategyManager
              ↓
        CompositeSignal
    """

    strategy = LiquidityVacuumStrategy(
        lookback=4,
        depth_drop_threshold=0.30,
        min_confidence=0.0,
    )

    manager = make_manager(
        strategy
    )

    bid_sizes = [
        100,
        100,
        100,
        20,
    ]

    result = None

    for index, bid_size in enumerate(
        bid_sizes,
        start=1
    ):
        context = make_context(
            timestamp=index,
            bid_size=bid_size,
            ask_size=100,
            queue_imbalance=-1.0,
            ofi=-20.0,
            trade_imbalance=-1.0,
        )

        result = manager.on_context(
            context
        )

    assert result is not None

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert result.confidence > 0.0
    assert result.score > 0.0

    assert manager.total_events == 4
    assert manager.signal_count >= 1


# ============================================================
# Absorption / Refill Integration
# ============================================================


def test_absorption_refill_through_manager():
    """
    人工制造：

        成交量快速增加
        +
        价格变化小
        +
        Bid流动性明显增加

    预期：

        AbsorptionRefill
              ↓
        SELL Signal
              ↓
        StrategyManager
              ↓
        CompositeSignal
    """

    strategy = AbsorptionRefillStrategy(
        lookback=4,
        trade_threshold=1.5,
        refill_threshold=0.5,
        min_confidence=0.0,
    )

    manager = make_manager(
        strategy
    )

    data = [
        # price, trade_volume, bid_size, ask_size
        (100.00, 100, 100, 100),
        (100.10, 100, 100, 100),
        (100.20, 100, 100, 100),
        (100.30, 400, 300, 100),
    ]

    result = None

    for index, (
        price,
        trade_volume,
        bid_size,
        ask_size,
    ) in enumerate(
        data,
        start=1
    ):
        context = make_context(
            timestamp=index,

            mid_price=price,

            trade_volume=(
                trade_volume
            ),

            bid_size=bid_size,
            ask_size=ask_size,

            queue_imbalance=1.0,
            ofi=20.0,
            trade_imbalance=1.0,
        )

        result = manager.on_context(
            context
        )

    assert result is not None

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert result.confidence > 0.0
    assert result.score > 0.0

    assert manager.total_events == 4
    assert manager.signal_count >= 1


# ============================================================
# All Real Strategies
# ============================================================


def test_all_real_strategies_run_together():
    """
    四个真实策略同时注册。

    给出普通稳定数据，
    连续运行多个Context。

    本测试重点：

        不是要求一定产生交易，

    而是确认：

        四个Strategy
            +
        StrategyManager
            +
        CompositeSignalEngine

    能长期共同运行而没有接口冲突。
    """

    manager = make_manager(
        MeanReversionStrategy(
            window=5,
            deviation_threshold=1.5,
            min_confidence=0.0,
        ),

        MomentumBreakoutStrategy(
            lookback=5,
            breakout_threshold=1.0,
            min_confidence=0.0,
        ),

        LiquidityVacuumStrategy(
            lookback=5,
            depth_drop_threshold=0.50,
            min_confidence=0.0,
        ),

        AbsorptionRefillStrategy(
            lookback=5,
            trade_threshold=1.5,
            refill_threshold=0.5,
            min_confidence=0.0,
        ),
    )

    prices = [
        100.00,
        100.05,
        100.10,
        100.05,
        100.00,
        100.10,
        100.15,
        100.10,
        100.05,
        100.00,
    ]

    result = None

    for index, price in enumerate(
        prices,
        start=1
    ):
        context = make_context(
            timestamp=index,
            mid_price=price,

            bid_size=100,
            ask_size=100,

            trade_volume=100,

            queue_imbalance=0.0,
            ofi=0.0,
            trade_imbalance=0.0,
        )

        result = manager.on_context(
            context
        )

        assert result is not None

        assert_composite_contract(
            result
        )

    assert manager.total_events == len(
        prices
    )


# ============================================================
# All Strategies - Longer Sequence
# ============================================================


def test_all_real_strategies_long_runtime():
    """
    使用100个StrategyContext连续运行。

    目的：

        检查：

        - deque更新
        - warmup
        - Strategy内部状态
        - Manager统计
        - Composite调用

    在连续运行情况下是否稳定。
    """

    manager = make_manager(
        MeanReversionStrategy(
            window=20,
            deviation_threshold=2.0,
            min_confidence=0.50,
        ),

        MomentumBreakoutStrategy(
            lookback=20,
            breakout_threshold=1.5,
            min_confidence=0.50,
        ),

        LiquidityVacuumStrategy(
            lookback=20,
            depth_drop_threshold=0.50,
            min_confidence=0.50,
        ),

        AbsorptionRefillStrategy(
            lookback=20,
            trade_threshold=1.5,
            refill_threshold=0.5,
            min_confidence=0.50,
        ),
    )

    result = None

    for index in range(
        1,
        101
    ):

        # ----------------------------------------------------
        # 构造小幅变化的市场状态
        # ----------------------------------------------------

        price = (
            100.0
            +
            ((index % 10) - 5)
            *
            0.05
        )

        bid_size = (
            100
            +
            index % 20
        )

        ask_size = (
            100
            +
            (20 - index % 20)
        )

        trade_volume = (
            100
            +
            index % 50
        )

        context = make_context(
            timestamp=index,

            mid_price=price,

            bid_size=bid_size,
            ask_size=ask_size,

            trade_volume=trade_volume,

            queue_imbalance=0.10,
            ofi=0.50,
            trade_imbalance=0.10,
        )

        result = manager.on_context(
            context
        )

        assert result is not None

        assert_composite_contract(
            result
        )

    assert manager.total_events == 100


# ============================================================
# Lifecycle
# ============================================================


def test_real_strategy_manager_lifecycle():
    """
    验证Manager生命周期可以作用于
    四个真实Strategy。
    """

    strategies = [
        MeanReversionStrategy(
            window=5
        ),

        MomentumBreakoutStrategy(
            lookback=5
        ),

        LiquidityVacuumStrategy(
            lookback=5
        ),

        AbsorptionRefillStrategy(
            lookback=5
        ),
    ]

    manager = make_manager(
        *strategies
    )

    manager.on_start()

    for strategy in strategies:

        assert strategy.running is True

    manager.on_stop()

    for strategy in strategies:

        assert strategy.running is False


# ============================================================
# Statistics
# ============================================================


def test_real_strategy_manager_stats():
    """
    验证真实策略运行后的Manager统计。
    """

    manager = make_manager(
        MeanReversionStrategy(
            window=10
        ),

        MomentumBreakoutStrategy(
            lookback=10
        ),

        LiquidityVacuumStrategy(
            lookback=10
        ),

        AbsorptionRefillStrategy(
            lookback=10
        ),
    )

    for index in range(
        1,
        6
    ):
        context = make_context(
            timestamp=index
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
    ] == 5

    assert stats[
        "strategies"
    ] == 4

    assert stats[
        "exit_strategies"
    ] == 0

    assert stats[
        "signals"
    ] >= 0


# ============================================================
# Manager Result Always Composite
# ============================================================


def test_manager_always_returns_composite_signal():
    """
    固定Manager输出契约：

        StrategyManager.on_context()
            ↓
        CompositeSignal

    即使没有交易，也必须返回：

        CompositeSignal(is_trade=False)

    而不是None。
    """

    manager = make_manager(
        MeanReversionStrategy(
            window=100
        )
    )

    context = make_context()

    result = manager.on_context(
        context
    )

    assert isinstance(
        result,
        CompositeSignal
    )

    assert result.is_trade() is False