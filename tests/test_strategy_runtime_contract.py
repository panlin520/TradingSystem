"""
tests/test_strategy_runtime_contract.py

============================================================
Strategy Runtime Contract Tests
============================================================

目标：

    验证：

        StrategyContext
                ↓
        Concrete Strategy
                ↓
        Signal / None

    运行时接口是否真正闭合。

============================================================

本测试不负责：

    - OrderBook重建正确性
    - Databento MBO解析
    - Engine F_LAST
    - Execution
    - Portfolio
    - Risk
    - 策略盈利能力

============================================================

测试对象：

    MeanReversionStrategy
    MomentumBreakoutStrategy
    LiquidityVacuumStrategy
    AbsorptionRefillStrategy

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
# Helpers
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
):
    """
    创建标准 StrategyContext。

    注意：

        这里完全按照 strategy/context.py
        当前标准接口构造。

    不创建：

        context.snapshot
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
            aggressive_buy_volume=aggressive_buy_volume,
            aggressive_sell_volume=aggressive_sell_volume,
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
            allowed=True,
            kill_switch=False,
            current_exposure=0.0,
            max_exposure=10.0,
        ),
    )


def assert_signal_contract(
    signal,
    expected_side=None,
    expected_category=None,
):
    """
    验证 Strategy 返回的 Signal
    是否符合当前 signal.py 标准契约。
    """

    assert isinstance(
        signal,
        Signal
    )

    assert isinstance(
        signal.side,
        SignalSide
    )

    assert isinstance(
        signal.signal_type,
        SignalType
    )

    assert isinstance(
        signal.category,
        StrategyCategory
    )

    assert isinstance(
        signal.confidence,
        float
    )

    assert 0.0 <= signal.confidence <= 1.0

    assert isinstance(
        signal.metadata,
        dict
    )

    # --------------------------------------------------------
    # 当前真实 Signal 包含 score 字段
    # --------------------------------------------------------

    assert hasattr(
        signal,
        "score"
    )

    assert isinstance(
        signal.score,
        float
    )

    if expected_side is not None:

        assert signal.side == expected_side

    if expected_category is not None:

        assert signal.category == expected_category


# ============================================================
# Context Contract
# ============================================================


def test_strategy_context_runtime_contract():
    """
    验证 StrategyContext 当前标准结构。

    最重要：

        不应该依赖旧版 context.snapshot。
    """

    context = make_context()

    assert not hasattr(
        context,
        "snapshot"
    )

    assert context.orderbook.best_bid == 99.75
    assert context.orderbook.best_ask == 100.25

    assert context.orderbook.bid_size == 100
    assert context.orderbook.ask_size == 100

    assert context.features.mid_price == 100.0
    assert context.features.trade_volume == 100

    assert context.features.ofi == 0.0
    assert context.features.queue_imbalance == 0.0

    assert context.position.side == "FLAT"

    assert context.risk.allowed is True
    assert context.risk.kill_switch is False


# ============================================================
# Empty / Warmup Runtime
# ============================================================


@pytest.mark.parametrize(
    "strategy",
    [
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
)
def test_strategy_warmup_does_not_crash(
    strategy
):
    """
    在历史数据不足时：

        Strategy允许返回None。

    重点：

        不能出现：

            AttributeError:
                StrategyContext has no attribute snapshot

            AttributeError:
                FeatureContext has no attribute get

            AttributeError:
                StrategyCategory.xxx
    """

    context = make_context()

    result = strategy.on_context(
        context
    )

    assert (
        result is None
        or
        isinstance(
            result,
            Signal
        )
    )


# ============================================================
# BaseStrategy.update()
# ============================================================


@pytest.mark.parametrize(
    "strategy",
    [
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
)
def test_base_strategy_update_dispatches_on_context(
    strategy
):
    """
    验证：

        BaseStrategy.update(context)

    能正确调用：

        strategy.on_context(context)
    """

    context = make_context()

    # 未启动时不处理
    result = strategy.update(
        context
    )

    assert result is None
    assert strategy.events_processed == 0

    # 启动
    strategy.on_start()

    strategy.update(
        context
    )

    assert strategy.events_processed == 1

    # 停止
    strategy.on_stop()

    assert strategy.running is False


# ============================================================
# Mean Reversion
# ============================================================


def test_mean_reversion_runtime_signal():
    """
    人工制造明显下偏：

        100
        100
        100
        100
         95

    预期：

        BUY
        MEAN_REVERSION
    """

    strategy = MeanReversionStrategy(
        window=5,
        deviation_threshold=1.0,
        min_confidence=0.0,
    )

    prices = [
        100.0,
        100.0,
        100.0,
        100.0,
        95.0,
    ]

    signal = None

    for index, price in enumerate(
        prices,
        start=1
    ):
        context = make_context(
            timestamp=index,
            mid_price=price,
            queue_imbalance=0.5,
            ofi=2.0,
            trade_imbalance=0.5,
        )

        signal = strategy.on_context(
            context
        )

    assert signal is not None

    assert_signal_contract(
        signal,
        expected_side=SignalSide.BUY,
        expected_category=(
            StrategyCategory.MEAN_REVERSION
        ),
    )

    assert signal.signal_type == SignalType.ENTRY

    assert "score" in signal.metadata
    assert "zscore" in signal.metadata
    assert "mean_price" in signal.metadata
    assert "mid_price" in signal.metadata


# ============================================================
# Momentum Breakout
# ============================================================


def test_momentum_breakout_runtime_signal():
    """
    人工制造向上突破。

    预期：

        BUY
        MOMENTUM
    """

    strategy = MomentumBreakoutStrategy(
        lookback=5,
        breakout_threshold=0.5,
        min_confidence=0.0,
    )

    prices = [
        100.00,
        100.10,
        100.20,
        100.30,
        101.00,
    ]

    signal = None

    for index, price in enumerate(
        prices,
        start=1
    ):
        context = make_context(
            timestamp=index,
            mid_price=price,
            queue_imbalance=0.7,
            ofi=5.0,
            trade_imbalance=0.7,
        )

        signal = strategy.on_context(
            context
        )

    assert signal is not None

    assert_signal_contract(
        signal,
        expected_side=SignalSide.BUY,
        expected_category=(
            StrategyCategory.MOMENTUM
        ),
    )

    assert signal.signal_type == SignalType.ENTRY

    assert "score" in signal.metadata
    assert "breakout_level" in signal.metadata
    assert "volatility" in signal.metadata


# ============================================================
# Liquidity Vacuum
# ============================================================


def test_liquidity_vacuum_runtime_signal():
    """
    人工制造 Bid 流动性快速消失：

        100
        100
        100
         20

    预期：

        SELL
        LIQUIDITY
    """

    strategy = LiquidityVacuumStrategy(
        lookback=4,
        depth_drop_threshold=0.30,
        min_confidence=0.0,
    )

    bid_sizes = [
        100,
        100,
        100,
        20,
    ]

    signal = None

    for index, bid_size in enumerate(
        bid_sizes,
        start=1
    ):
        context = make_context(
            timestamp=index,
            bid_size=bid_size,
            ask_size=100,
            queue_imbalance=-0.7,
            ofi=-5.0,
            trade_imbalance=-0.7,
        )

        signal = strategy.on_context(
            context
        )

    assert signal is not None

    assert_signal_contract(
        signal,
        expected_side=SignalSide.SELL,
        expected_category=(
            StrategyCategory.LIQUIDITY
        ),
    )

    assert signal.signal_type == SignalType.ENTRY

    assert "score" in signal.metadata
    assert "bid_drop" in signal.metadata
    assert "ask_drop" in signal.metadata


# ============================================================
# Absorption / Refill
# ============================================================


def test_absorption_refill_runtime_signal():
    """
    人工制造：

        成交量快速增加
        +
        价格变化很小
        +
        顶层流动性明显回补

    用于触发：

        Buy Pressure Absorption

    预期：

        SELL
        ABSORPTION
    """

    strategy = AbsorptionRefillStrategy(
        lookback=4,
        trade_threshold=1.5,
        refill_threshold=0.5,
        min_confidence=0.0,
    )

    data = [
        # price, trade_volume, bid_size, ask_size
        (100.00, 100, 100, 100),
        (100.10, 100, 100, 100),
        (100.20, 100, 100, 100),
        (100.30, 400, 300, 100),
    ]

    signal = None

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
            trade_volume=trade_volume,
            bid_size=bid_size,
            ask_size=ask_size,
            queue_imbalance=0.8,
            ofi=5.0,
            trade_imbalance=0.8,
        )

        signal = strategy.on_context(
            context
        )

    assert signal is not None

    assert_signal_contract(
        signal,
        expected_side=SignalSide.SELL,
        expected_category=(
            StrategyCategory.ABSORPTION
        ),
    )

    assert signal.signal_type == SignalType.ENTRY

    assert "score" in signal.metadata
    assert "trade_pressure" in signal.metadata
    assert "price_move" in signal.metadata
    assert "refill" in signal.metadata


# ============================================================
# Signal Category Contract
# ============================================================


def test_strategy_category_contract():
    """
    防止未来再次误用不存在的：

        MOMENTUM_BREAKOUT
        LIQUIDITY_VACUUM
        ABSORPTION_REFILL
    """

    assert hasattr(
        StrategyCategory,
        "MEAN_REVERSION"
    )

    assert hasattr(
        StrategyCategory,
        "MOMENTUM"
    )

    assert hasattr(
        StrategyCategory,
        "LIQUIDITY"
    )

    assert hasattr(
        StrategyCategory,
        "ABSORPTION"
    )

    assert not hasattr(
        StrategyCategory,
        "MOMENTUM_BREAKOUT"
    )

    assert not hasattr(
        StrategyCategory,
        "LIQUIDITY_VACUUM"
    )

    assert not hasattr(
        StrategyCategory,
        "ABSORPTION_REFILL"
    )


# ============================================================
# Signal Field Contract
# ============================================================


def test_signal_has_score_field():
    """
    当前真实 Signal 包含 score 顶层字段。

    score 用途：

        - Composite Signal评分
        - 策略排序
        - 权重计算
        - 回测分析

    metadata["score"]：

        用于保留策略内部计算结果和诊断信息。
    """

    signal = Signal(
        side=SignalSide.BUY,
        signal_type=SignalType.ENTRY,
        category=StrategyCategory.MEAN_REVERSION,
        confidence=0.80,
        score=1.5,
        strategy="test",
        metadata={
            "score": 1.5,
        },
    )

    assert hasattr(
        signal,
        "score"
    )

    assert isinstance(
        signal.score,
        float
    )

    assert signal.score == 1.5

    assert signal.metadata[
        "score"
    ] == 1.5