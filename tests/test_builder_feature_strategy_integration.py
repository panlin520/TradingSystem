"""
tests/test_builder_feature_strategy_integration.py

============================================================
Builder -> Feature -> Strategy Full Integration Tests
============================================================

目标：

    验证当前真实系统链路：

        MarketEvent
            ↓
        OrderBookBuilder
            ↓
        OrderBook
            ↓
        FeatureEngine
            ↓
        FeatureSnapshot
            ↓
        StrategyContext
            ↓
        Real Strategies
            ↓
        StrategyManager
            ↓
        CompositeSignalEngine
            ↓
        CompositeSignal

============================================================

本测试使用真实：

    core.event.MarketEvent

    orderbook.builder.OrderBookBuilder
    orderbook.book.OrderBook

    features.feature_engine.FeatureEngine
    features.snapshot.FeatureSnapshot

    strategy.context.StrategyContext

    MeanReversionStrategy
    MomentumBreakoutStrategy
    LiquidityVacuumStrategy
    AbsorptionRefillStrategy

    StrategyManager
    CompositeSignalEngine
    CompositeSignal

============================================================

冻结层原则：

    以下模块：

        core/event.py
        orderbook/order.py
        orderbook/level.py
        orderbook/book.py
        orderbook/builder.py

    只调用。

    不修改。

============================================================

IMPORTANT:

    已经确认：

        Builder 对乱序 sequence：

            10 -> 11 -> 9

        当前会接受并应用。

    该问题保留为独立：

        CRITICAL / CONFIRMED

    本文件不是 sequence 防御测试。

    所有事件使用严格递增 sequence。

============================================================
"""

import pytest

from core.event import (
    MarketEvent,
    OrderAction,
    OrderSide,
)

from orderbook.book import OrderBook
from orderbook.builder import OrderBookBuilder

from features.feature_engine import FeatureEngine
from features.snapshot import FeatureSnapshot

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

from strategy.strategy_manager import StrategyManager

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
# MarketEvent Factory
# ============================================================


def make_event(
    *,
    sequence,
    action,
    side=None,
    order_id=None,
    price=None,
    size=None,
    ts_event=None,
    ts_recv=None,
    symbol="ESU6",
    channel_id=0,
    publisher_id=1,
    instrument_id=1,
    flags=0,
):
    """
    创建真实 MarketEvent。
    """

    if ts_event is None:
        ts_event = sequence

    if ts_recv is None:
        ts_recv = ts_event

    return MarketEvent(
        ts_event=ts_event,
        ts_recv=ts_recv,
        sequence=sequence,
        action=action,
        side=side,
        order_id=order_id,
        price=price,
        size=size,
        symbol=symbol,
        channel_id=channel_id,
        publisher_id=publisher_id,
        instrument_id=instrument_id,
        flags=flags,
    )


# ============================================================
# FeatureSnapshot -> StrategyContext
# ============================================================


def snapshot_to_context(
    snapshot: FeatureSnapshot,
    *,
    allowed=True,
    kill_switch=False,
):
    """
    FeatureSnapshot转换为策略统一输入。

    当前确认字段映射：

        FeatureSnapshot.queue_pressure
            ->
        FeatureContext.queue_imbalance

    RegimeFeatures数值波动：

        snapshot.extra["volatility_score"]
            ->
        context.features.volatility
    """

    volatility = snapshot.extra.get(
        "volatility_score",
        0.0,
    )

    trend_regime = snapshot.extra.get(
        "trend_regime",
        "UNKNOWN",
    )

    liquidity_regime = snapshot.extra.get(
        "liquidity_regime",
        "UNKNOWN",
    )

    return StrategyContext(
        timestamp=snapshot.timestamp,
        symbol=snapshot.symbol,

        orderbook=OrderBookContext(
            best_bid=snapshot.best_bid,
            best_ask=snapshot.best_ask,
            bid_size=snapshot.bid_volume,
            ask_size=snapshot.ask_volume,
            spread=snapshot.spread or 0,

            depth={
                "bid_5": snapshot.bid_depth_5,
                "ask_5": snapshot.ask_depth_5,
                "bid_10": snapshot.bid_depth_10,
                "ask_10": snapshot.ask_depth_10,
            },

            active_orders=0,
        ),

        features=FeatureContext(
            mid_price=snapshot.mid_price,
            micro_price=snapshot.micro_price,
            obi=snapshot.obi,

            queue_imbalance=(
                snapshot.queue_pressure
            ),

            ofi=snapshot.ofi,

            trade_volume=(
                snapshot.trade_volume
            ),

            aggressive_buy_volume=(
                snapshot.aggressive_buy_volume
            ),

            aggressive_sell_volume=(
                snapshot.aggressive_sell_volume
            ),

            trade_imbalance=(
                snapshot.trade_imbalance
            ),

            volatility=float(
                volatility
            ),

            extra={
                "micro_price_delta":
                    snapshot.micro_price_delta,

                "add_volume":
                    snapshot.add_volume,

                "cancel_volume":
                    snapshot.cancel_volume,

                "modify_volume":
                    snapshot.modify_volume,

                "liquidity_added":
                    snapshot.liquidity_added,

                "liquidity_removed":
                    snapshot.liquidity_removed,

                "replenishment":
                    snapshot.replenishment,

                "feature_snapshot":
                    snapshot,
            },
        ),

        regime=RegimeContext(
            name=trend_regime,

            trending=(
                trend_regime
                in (
                    "TREND_UP",
                    "TREND_DOWN",
                )
            ),

            ranging=(
                trend_regime
                ==
                "RANGE"
            ),

            high_volatility=(
                snapshot.volatility_regime
                ==
                "HIGH"
            ),

            liquidity_event=(
                liquidity_regime
                in (
                    "THIN",
                    "VACUUM",
                )
            ),

            extra={
                "trend":
                    trend_regime,

                "liquidity":
                    liquidity_regime,

                "spread_regime":
                    snapshot.spread_regime,

                "volatility_regime":
                    snapshot.volatility_regime,
            },
        ),

        position=PositionContext(
            symbol=snapshot.symbol,
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

        metadata={
            "sequence":
                snapshot.sequence,
        },
    )


# ============================================================
# Pipeline Factory
# ============================================================


def make_pipeline(
    *,
    min_confidence=0.0,
    min_score=0.0,
):
    """
    创建完整真实Pipeline。
    """

    book = OrderBook()

    builder = OrderBookBuilder(
        book=book
    )

    feature_engine = FeatureEngine(
        orderbook=book,
        regime_window_size=20,
    )

    composite_engine = CompositeSignalEngine(
        min_confidence=min_confidence,
        min_score=min_score,
    )

    manager = StrategyManager(
        composite_engine=composite_engine
    )

    return (
        book,
        builder,
        feature_engine,
        manager,
    )


# ============================================================
# Register Strategies
# ============================================================


def register_all_strategies(
    manager,
    *,
    window=10,
):
    """
    注册当前四个真实策略族。
    """

    manager.register(
        MeanReversionStrategy(
            window=window,
        )
    )

    manager.register(
        MomentumBreakoutStrategy(
            lookback=window,
        )
    )

    manager.register(
        LiquidityVacuumStrategy(
            lookback=window,
        )
    )

    manager.register(
        AbsorptionRefillStrategy(
            lookback=window,
        )
    )


# ============================================================
# Apply Full Pipeline
# ============================================================


def apply_full_pipeline(
    *,
    builder,
    feature_engine,
    manager,
    event,
    allowed=True,
    kill_switch=False,
):
    """
    完整事件处理顺序：

        MarketEvent

            ↓

        OrderBookBuilder

            ↓

        OrderBook

            ↓

        FeatureEngine

            ↓

        FeatureSnapshot

            ↓

        StrategyContext

            ↓

        StrategyManager

            ↓

        CompositeSignal
    """

    # ======================================================
    # 1. Builder更新真实盘口
    # ======================================================

    builder.on_event(
        event
    )

    # ======================================================
    # 2. Feature读取更新后的真实盘口
    # ======================================================

    snapshot = feature_engine.on_event(
        event
    )

    # ======================================================
    # 3. FeatureSnapshot -> StrategyContext
    # ======================================================

    context = snapshot_to_context(
        snapshot,
        allowed=allowed,
        kill_switch=kill_switch,
    )

    # ======================================================
    # 4. StrategyManager
    # ======================================================

    result = manager.on_context(
        context
    )

    return (
        snapshot,
        context,
        result,
    )


# ============================================================
# Composite Contract
# ============================================================


def assert_composite_contract(
    result
):
    """
    检查最终CompositeSignal契约。
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
# Initialization
# ============================================================


def test_full_pipeline_can_initialize():
    """
    完整系统链可以初始化。
    """

    (
        book,
        builder,
        feature_engine,
        manager,
    ) = make_pipeline()

    register_all_strategies(
        manager
    )

    assert builder.get_book() is book

    assert feature_engine.orderbook is book

    assert book.best_bid() is None

    assert book.best_ask() is None


# ============================================================
# ADD Through Full Pipeline
# ============================================================


def test_add_event_full_pipeline():
    """
    单个真实ADD事件穿过完整链路。
    """

    (
        book,
        builder,
        feature_engine,
        manager,
    ) = make_pipeline()

    register_all_strategies(
        manager
    )

    event = make_event(
        sequence=1,
        action=OrderAction.ADD,
        side=OrderSide.BID,
        order_id=1,
        price=100,
        size=10,
    )

    snapshot, context, result = (
        apply_full_pipeline(
            builder=builder,
            feature_engine=feature_engine,
            manager=manager,
            event=event,
        )
    )

    assert book.best_bid() == 100

    assert snapshot.best_bid == 100

    assert context.orderbook.best_bid == 100

    assert context.features.mid_price is None

    assert_composite_contract(
        result
    )

    assert builder.event_count == 1

    assert feature_engine.events_processed == 1

    assert manager.total_events == 1


# ============================================================
# Full Top Of Book
# ============================================================


def test_bid_ask_full_pipeline():
    """
    建立Bid + Ask后验证三个层次状态：

        Real Book
        FeatureSnapshot
        StrategyContext
    """

    (
        book,
        builder,
        feature_engine,
        manager,
    ) = make_pipeline()

    register_all_strategies(
        manager
    )

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=100,
        ),
    )

    snapshot, context, result = (
        apply_full_pipeline(
            builder=builder,
            feature_engine=feature_engine,
            manager=manager,
            event=make_event(
                sequence=2,
                action=OrderAction.ADD,
                side=OrderSide.ASK,
                order_id=2,
                price=102,
                size=50,
            ),
        )
    )

    assert book.best_bid() == 100

    assert book.best_ask() == 102

    assert snapshot.best_bid == 100

    assert snapshot.best_ask == 102

    assert snapshot.mid_price == pytest.approx(
        101.0
    )

    assert context.orderbook.best_bid == 100

    assert context.orderbook.best_ask == 102

    assert context.features.mid_price == pytest.approx(
        101.0
    )

    assert context.features.obi == pytest.approx(
        snapshot.obi
    )

    assert (
        context.features.queue_imbalance
        ==
        snapshot.queue_pressure
    )

    assert_composite_contract(
        result
    )


# ============================================================
# MODIFY Through Full Pipeline
# ============================================================


def test_modify_event_full_pipeline():
    """
    ADD：

        Bid 100 @ 10

    MODIFY：

        Bid 100 @ 25

    验证：

        Builder
        Book
        Feature
        Context
        Strategy

    全部同步。
    """

    (
        book,
        builder,
        feature_engine,
        manager,
    ) = make_pipeline()

    register_all_strategies(
        manager
    )

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    snapshot, context, result = (
        apply_full_pipeline(
            builder=builder,
            feature_engine=feature_engine,
            manager=manager,
            event=make_event(
                sequence=2,
                action=OrderAction.MODIFY,
                side=OrderSide.BID,
                order_id=1,
                price=100,
                size=25,
            ),
        )
    )

    assert book.bid_volume() == 25

    assert snapshot.bid_volume == 25

    assert context.orderbook.bid_size == 25

    assert snapshot.modify_volume == 25

    assert_composite_contract(
        result
    )


# ============================================================
# CANCEL Through Full Pipeline
# ============================================================


def test_cancel_event_full_pipeline():
    """
    Cancel后所有上层状态必须同步。
    """

    (
        book,
        builder,
        feature_engine,
        manager,
    ) = make_pipeline()

    register_all_strategies(
        manager
    )

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=2,
            price=99,
            size=20,
        ),
    )

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=3,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=3,
            price=102,
            size=30,
        ),
    )

    snapshot, context, result = (
        apply_full_pipeline(
            builder=builder,
            feature_engine=feature_engine,
            manager=manager,
            event=make_event(
                sequence=4,
                action=OrderAction.CANCEL,
                side=OrderSide.BID,
                order_id=1,
                price=100,
                size=10,
            ),
        )
    )

    assert book.best_bid() == 99

    assert snapshot.best_bid == 99

    assert context.orderbook.best_bid == 99

    assert snapshot.cancel_volume == 10

    assert snapshot.liquidity_removed == 10

    assert_composite_contract(
        result
    )


# ============================================================
# TRADE Through Full Pipeline
# ============================================================


def test_trade_event_full_pipeline():
    """
    T事件完整穿过：

        Builder
        Book Trade Stats
        Feature Trade Stats
        StrategyContext
        StrategyManager
    """

    (
        book,
        builder,
        feature_engine,
        manager,
    ) = make_pipeline()

    register_all_strategies(
        manager
    )

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=100,
        ),
    )

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=2,
            price=102,
            size=100,
        ),
    )

    snapshot, context, result = (
        apply_full_pipeline(
            builder=builder,
            feature_engine=feature_engine,
            manager=manager,
            event=make_event(
                sequence=3,
                action=OrderAction.TRADE,
                side=OrderSide.BID,
                order_id=None,
                price=102,
                size=5,
            ),
        )
    )

    # Builder book stats
    assert book.trade_count == 1
    assert book.trade_volume == 5

    # Feature
    assert snapshot.trade_count == 1
    assert snapshot.trade_volume == 5

    assert snapshot.last_trade_price == 102

    assert snapshot.last_trade_size == 5

    # Context
    assert context.features.trade_volume == 5

    assert (
        context.features.aggressive_buy_volume
        ==
        5
    )

    assert (
        context.features.aggressive_sell_volume
        ==
        0
    )

    assert context.features.trade_imbalance == pytest.approx(
        1.0
    )

    assert_composite_contract(
        result
    )


# ============================================================
# RESET Through Full Pipeline
# ============================================================


def test_reset_event_full_pipeline():
    """
    R：

        Builder清空Book
            ↓
        Feature看到空Book
            ↓
        StrategyContext看到空盘口
            ↓
        StrategyManager仍然安全
    """

    (
        book,
        builder,
        feature_engine,
        manager,
    ) = make_pipeline()

    register_all_strategies(
        manager
    )

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=2,
            price=102,
            size=20,
        ),
    )

    snapshot, context, result = (
        apply_full_pipeline(
            builder=builder,
            feature_engine=feature_engine,
            manager=manager,
            event=make_event(
                sequence=3,
                action=OrderAction.RESET,
                side=None,
                order_id=None,
                price=None,
                size=999,
            ),
        )
    )

    assert len(
        book.orders
    ) == 0

    assert book.best_bid() is None

    assert book.best_ask() is None

    assert snapshot.best_bid is None

    assert snapshot.best_ask is None

    assert snapshot.mid_price is None

    assert context.orderbook.best_bid is None

    assert context.orderbook.best_ask is None

    assert context.features.mid_price is None

    # RESET不是Cancel
    assert snapshot.cancel_volume == 0

    assert snapshot.liquidity_removed == 0

    assert_composite_contract(
        result
    )


# ============================================================
# Risk Gate
# ============================================================


def test_risk_gate_survives_full_pipeline():
    """
    Feature产生正常Context，
    但RiskContext禁止交易。
    """

    (
        book,
        builder,
        feature_engine,
        manager,
    ) = make_pipeline()

    register_all_strategies(
        manager
    )

    snapshot, context, result = (
        apply_full_pipeline(
            builder=builder,
            feature_engine=feature_engine,
            manager=manager,
            event=make_event(
                sequence=1,
                action=OrderAction.ADD,
                side=OrderSide.BID,
                order_id=1,
                price=100,
                size=10,
            ),
            allowed=False,
        )
    )

    assert context.can_trade() is False

    assert context.risk.allowed is False

    assert_composite_contract(
        result
    )


# ============================================================
# Kill Switch
# ============================================================


def test_kill_switch_survives_full_pipeline():
    """
    Kill Switch状态必须传递到StrategyContext。
    """

    (
        book,
        builder,
        feature_engine,
        manager,
    ) = make_pipeline()

    register_all_strategies(
        manager
    )

    snapshot, context, result = (
        apply_full_pipeline(
            builder=builder,
            feature_engine=feature_engine,
            manager=manager,
            event=make_event(
                sequence=1,
                action=OrderAction.ADD,
                side=OrderSide.BID,
                order_id=1,
                price=100,
                size=10,
            ),
            kill_switch=True,
        )
    )

    assert context.risk.kill_switch is True

    assert context.can_trade() is False

    assert_composite_contract(
        result
    )


# ============================================================
# Raw ES Price Units
# ============================================================


def test_raw_es_price_full_pipeline():
    """
    使用真实ES整数价格单位。

        7571.00
        7571.25

    经过所有层以后不能被偷偷改变单位。
    """

    (
        book,
        builder,
        feature_engine,
        manager,
    ) = make_pipeline()

    register_all_strategies(
        manager
    )

    bid = 7_571_000_000_000

    ask = 7_571_250_000_000

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=bid,
            size=100,
        ),
    )

    snapshot, context, result = (
        apply_full_pipeline(
            builder=builder,
            feature_engine=feature_engine,
            manager=manager,
            event=make_event(
                sequence=2,
                action=OrderAction.ADD,
                side=OrderSide.ASK,
                order_id=2,
                price=ask,
                size=100,
            ),
        )
    )

    assert book.best_bid() == bid

    assert book.best_ask() == ask

    assert snapshot.best_bid == bid

    assert snapshot.best_ask == ask

    assert context.orderbook.best_bid == bid

    assert context.orderbook.best_ask == ask

    assert snapshot.spread == 250_000_000

    assert context.orderbook.spread == 250_000_000

    assert context.features.mid_price == pytest.approx(
        (
            bid + ask
        ) / 2
    )

    assert_composite_contract(
        result
    )


# ============================================================
# Mean Reversion Full Chain
# ============================================================


def test_mean_reversion_real_builder_full_chain():
    """
    重点测试：

        不是直接给Strategy mid_price。

    而是通过真实：

        MarketEvent
            ↓
        Builder
            ↓
        Real Book
            ↓
        FeatureEngine
            ↓
        mid_price
            ↓
        MeanReversionStrategy

    构造Mid：

        100
        100
        100
        100
         95
    """

    (
        book,
        builder,
        feature_engine,
        manager,
    ) = make_pipeline(
        min_confidence=0.0,
        min_score=0.0,
    )

    manager.register(
        MeanReversionStrategy(
            window=5,
            deviation_threshold=1.0,
            min_confidence=0.0,
        )
    )

    sequence = 0
    previous_bid_id = None
    previous_ask_id = None

    mids = [
        100,
        100,
        100,
        100,
        95,
    ]

    result = None

    for index, mid in enumerate(
        mids,
        start=1,
    ):

        # ==================================================
        # 删除上一组盘口
        # ==================================================

        if previous_bid_id is not None:

            sequence += 1

            apply_full_pipeline(
                builder=builder,
                feature_engine=feature_engine,
                manager=manager,
                event=make_event(
                    sequence=sequence,
                    action=OrderAction.CANCEL,
                    side=OrderSide.BID,
                    order_id=previous_bid_id,
                    price=mid,
                    size=200,
                ),
            )

        if previous_ask_id is not None:

            sequence += 1

            apply_full_pipeline(
                builder=builder,
                feature_engine=feature_engine,
                manager=manager,
                event=make_event(
                    sequence=sequence,
                    action=OrderAction.CANCEL,
                    side=OrderSide.ASK,
                    order_id=previous_ask_id,
                    price=mid,
                    size=50,
                ),
            )

        # ==================================================
        # 新Bid
        # ==================================================

        sequence += 1

        bid_id = (
            index * 10
            +
            1
        )

        apply_full_pipeline(
            builder=builder,
            feature_engine=feature_engine,
            manager=manager,
            event=make_event(
                sequence=sequence,
                action=OrderAction.ADD,
                side=OrderSide.BID,
                order_id=bid_id,
                price=mid - 1,
                size=200,
            ),
        )

        # ==================================================
        # 新Ask
        # ==================================================

        sequence += 1

        ask_id = (
            index * 10
            +
            2
        )

        snapshot, context, result = (
            apply_full_pipeline(
                builder=builder,
                feature_engine=feature_engine,
                manager=manager,
                event=make_event(
                    sequence=sequence,
                    action=OrderAction.ADD,
                    side=OrderSide.ASK,
                    order_id=ask_id,
                    price=mid + 1,
                    size=50,
                ),
            )
        )

        assert context.features.mid_price == pytest.approx(
            mid
        )

        previous_bid_id = bid_id

        previous_ask_id = ask_id

    assert result is not None

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert result.score > 0.0


# ============================================================
# Momentum Full Chain
# ============================================================


def test_momentum_real_builder_full_chain():
    """
    真实Builder产生连续上涨mid，
    再驱动MomentumBreakoutStrategy。
    """

    (
        book,
        builder,
        feature_engine,
        manager,
    ) = make_pipeline(
        min_confidence=0.0,
        min_score=0.0,
    )

    manager.register(
        MomentumBreakoutStrategy(
            lookback=5,
            breakout_threshold=0.5,
            min_confidence=0.0,
        )
    )

    mids = [
        100.0,
        100.1,
        100.2,
        100.3,
        101.0,
    ]

    sequence = 0

    previous_bid_id = None
    previous_ask_id = None

    result = None

    for index, mid in enumerate(
        mids,
        start=1,
    ):

        if previous_bid_id is not None:

            sequence += 1

            apply_full_pipeline(
                builder=builder,
                feature_engine=feature_engine,
                manager=manager,
                event=make_event(
                    sequence=sequence,
                    action=OrderAction.CANCEL,
                    side=OrderSide.BID,
                    order_id=previous_bid_id,
                    price=mid,
                    size=100,
                ),
            )

        if previous_ask_id is not None:

            sequence += 1

            apply_full_pipeline(
                builder=builder,
                feature_engine=feature_engine,
                manager=manager,
                event=make_event(
                    sequence=sequence,
                    action=OrderAction.CANCEL,
                    side=OrderSide.ASK,
                    order_id=previous_ask_id,
                    price=mid,
                    size=100,
                ),
            )

        sequence += 1

        bid_id = (
            1000
            +
            index * 2
        )

        apply_full_pipeline(
            builder=builder,
            feature_engine=feature_engine,
            manager=manager,
            event=make_event(
                sequence=sequence,
                action=OrderAction.ADD,
                side=OrderSide.BID,
                order_id=bid_id,
                price=mid - 0.25,
                size=100,
            ),
        )

        sequence += 1

        ask_id = (
            1001
            +
            index * 2
        )

        snapshot, context, result = (
            apply_full_pipeline(
                builder=builder,
                feature_engine=feature_engine,
                manager=manager,
                event=make_event(
                    sequence=sequence,
                    action=OrderAction.ADD,
                    side=OrderSide.ASK,
                    order_id=ask_id,
                    price=mid + 0.25,
                    size=100,
                ),
            )
        )

        assert context.features.mid_price == pytest.approx(
            mid
        )

        previous_bid_id = bid_id
        previous_ask_id = ask_id

    assert result is not None

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert result.score > 0.0


# ============================================================
# Four Strategies Runtime
# ============================================================


def test_all_strategies_real_builder_runtime():
    """
    四个真实策略同时连接真实Builder。

    连续100个真实MarketEvent运行。
    """

    (
        book,
        builder,
        feature_engine,
        manager,
    ) = make_pipeline(
        min_confidence=0.60,
        min_score=1.0,
    )

    register_all_strategies(
        manager,
        window=10,
    )

    sequence = 0

    active_bid_ids = []

    # ======================================================
    # 固定Ask
    # ======================================================

    sequence += 1

    snapshot, context, result = (
        apply_full_pipeline(
            builder=builder,
            feature_engine=feature_engine,
            manager=manager,
            event=make_event(
                sequence=sequence,
                action=OrderAction.ADD,
                side=OrderSide.ASK,
                order_id=100_000,
                price=200,
                size=500,
            ),
        )
    )

    # ======================================================
    # 100个事件
    # ======================================================

    for index in range(
        1,
        101,
    ):

        sequence += 1

        if index % 10 == 0:

            event = make_event(
                sequence=sequence,
                action=OrderAction.TRADE,
                side=(
                    OrderSide.BID
                    if index % 20 == 0
                    else OrderSide.ASK
                ),
                order_id=None,
                price=150,
                size=5,
            )

        elif (
            index % 7 == 0
            and active_bid_ids
        ):

            order_id = active_bid_ids.pop(
                0
            )

            order = book.orders.get(
                order_id
            )

            event = make_event(
                sequence=sequence,
                action=OrderAction.CANCEL,
                side=OrderSide.BID,
                order_id=order_id,
                price=(
                    order.price
                    if order is not None
                    else 0
                ),
                size=(
                    order.size
                    if order is not None
                    else 0
                ),
            )

        else:

            order_id = (
                1000
                +
                index
            )

            active_bid_ids.append(
                order_id
            )

            event = make_event(
                sequence=sequence,
                action=OrderAction.ADD,
                side=OrderSide.BID,
                order_id=order_id,
                price=(
                    100
                    +
                    index % 50
                ),
                size=(
                    1
                    +
                    index % 10
                ),
            )

        snapshot, context, result = (
            apply_full_pipeline(
                builder=builder,
                feature_engine=feature_engine,
                manager=manager,
                event=event,
            )
        )

        assert_composite_contract(
            result
        )

        # ==================================================
        # Book -> Feature exact
        # ==================================================

        assert snapshot.best_bid == (
            book.best_bid()
        )

        assert snapshot.best_ask == (
            book.best_ask()
        )

        assert snapshot.bid_volume == (
            book.bid_volume()
        )

        assert snapshot.ask_volume == (
            book.ask_volume()
        )

        # ==================================================
        # Feature -> Context exact
        # ==================================================

        assert context.orderbook.best_bid == (
            snapshot.best_bid
        )

        assert context.orderbook.best_ask == (
            snapshot.best_ask
        )

        assert context.features.mid_price == (
            snapshot.mid_price
        )

        assert context.features.ofi == (
            snapshot.ofi
        )

        assert (
            context.features.trade_imbalance
            ==
            snapshot.trade_imbalance
        )

    expected_events = (
        101
    )

    assert builder.event_count == (
        expected_events
    )

    assert feature_engine.events_processed == (
        expected_events
    )

    assert manager.total_events == (
        expected_events
    )


# ============================================================
# RESET + Rebuild + Strategy
# ============================================================


def test_reset_rebuild_strategy_full_pipeline():
    """
    完整系统RESET以后重新建立盘口，
    策略层必须继续工作。
    """

    (
        book,
        builder,
        feature_engine,
        manager,
    ) = make_pipeline()

    register_all_strategies(
        manager
    )

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=1,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=1,
            price=100,
            size=10,
        ),
    )

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=2,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=2,
            price=102,
            size=10,
        ),
    )

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=3,
            action=OrderAction.RESET,
            side=None,
            order_id=None,
            price=None,
            size=0,
        ),
    )

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=4,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=10,
            price=200,
            size=50,
        ),
    )

    snapshot, context, result = (
        apply_full_pipeline(
            builder=builder,
            feature_engine=feature_engine,
            manager=manager,
            event=make_event(
                sequence=5,
                action=OrderAction.ADD,
                side=OrderSide.ASK,
                order_id=11,
                price=204,
                size=70,
            ),
        )
    )

    assert book.best_bid() == 200

    assert book.best_ask() == 204

    assert snapshot.best_bid == 200

    assert snapshot.best_ask == 204

    assert context.orderbook.best_bid == 200

    assert context.orderbook.best_ask == 204

    assert context.features.mid_price == pytest.approx(
        202.0
    )

    assert_composite_contract(
        result
    )


# ============================================================
# Long Full Pipeline
# ============================================================


def test_full_pipeline_long_runtime():
    """
    500个真实MarketEvent连续通过整个系统：

        MarketEvent
            ↓
        Builder
            ↓
        Book
            ↓
        Feature
            ↓
        Context
            ↓
        Strategies
            ↓
        Manager
            ↓
        Composite

    重点验证：

        - 无接口异常
        - sequence严格递增
        - 三层状态持续同步
        - 统计数量完全一致
    """

    (
        book,
        builder,
        feature_engine,
        manager,
    ) = make_pipeline(
        min_confidence=0.60,
        min_score=1.0,
    )

    register_all_strategies(
        manager,
        window=20,
    )

    sequence = 0

    active_bid_ids = []

    active_ask_ids = []

    # ======================================================
    # Initial Bid
    # ======================================================

    sequence += 1

    initial_bid_id = 1

    active_bid_ids.append(
        initial_bid_id
    )

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=sequence,
            action=OrderAction.ADD,
            side=OrderSide.BID,
            order_id=initial_bid_id,
            price=100,
            size=100,
        ),
    )

    # ======================================================
    # Initial Ask
    # ======================================================

    sequence += 1

    initial_ask_id = 2

    active_ask_ids.append(
        initial_ask_id
    )

    apply_full_pipeline(
        builder=builder,
        feature_engine=feature_engine,
        manager=manager,
        event=make_event(
            sequence=sequence,
            action=OrderAction.ADD,
            side=OrderSide.ASK,
            order_id=initial_ask_id,
            price=200,
            size=100,
        ),
    )

    next_order_id = 10_000

    # ======================================================
    # 500 Events
    # ======================================================

    for index in range(
        1,
        501,
    ):

        sequence += 1

        # --------------------------------------------------
        # Trade
        # --------------------------------------------------

        if index % 20 == 0:

            event = make_event(
                sequence=sequence,
                action=OrderAction.TRADE,
                side=(
                    OrderSide.BID
                    if index % 40 == 0
                    else OrderSide.ASK
                ),
                order_id=None,
                price=150,
                size=(
                    1
                    +
                    index % 10
                ),
            )

        # --------------------------------------------------
        # Cancel Bid
        # --------------------------------------------------

        elif (
            index % 13 == 0
            and
            len(
                active_bid_ids
            ) > 1
        ):

            order_id = (
                active_bid_ids.pop(
                    0
                )
            )

            order = book.orders.get(
                order_id
            )

            event = make_event(
                sequence=sequence,
                action=OrderAction.CANCEL,
                side=OrderSide.BID,
                order_id=order_id,
                price=(
                    order.price
                    if order is not None
                    else 0
                ),
                size=(
                    order.size
                    if order is not None
                    else 0
                ),
            )

        # --------------------------------------------------
        # Cancel Ask
        # --------------------------------------------------

        elif (
            index % 17 == 0
            and
            len(
                active_ask_ids
            ) > 1
        ):

            order_id = (
                active_ask_ids.pop(
                    0
                )
            )

            order = book.orders.get(
                order_id
            )

            event = make_event(
                sequence=sequence,
                action=OrderAction.CANCEL,
                side=OrderSide.ASK,
                order_id=order_id,
                price=(
                    order.price
                    if order is not None
                    else 0
                ),
                size=(
                    order.size
                    if order is not None
                    else 0
                ),
            )

        # --------------------------------------------------
        # Add Ask
        # --------------------------------------------------

        elif index % 5 == 0:

            next_order_id += 1

            order_id = next_order_id

            active_ask_ids.append(
                order_id
            )

            event = make_event(
                sequence=sequence,
                action=OrderAction.ADD,
                side=OrderSide.ASK,
                order_id=order_id,
                price=(
                    151
                    +
                    index % 20
                ),
                size=(
                    1
                    +
                    index % 15
                ),
            )

        # --------------------------------------------------
        # Add Bid
        # --------------------------------------------------

        else:

            next_order_id += 1

            order_id = next_order_id

            active_bid_ids.append(
                order_id
            )

            event = make_event(
                sequence=sequence,
                action=OrderAction.ADD,
                side=OrderSide.BID,
                order_id=order_id,
                price=(
                    100
                    +
                    index % 40
                ),
                size=(
                    1
                    +
                    index % 15
                ),
            )

        snapshot, context, result = (
            apply_full_pipeline(
                builder=builder,
                feature_engine=feature_engine,
                manager=manager,
                event=event,
            )
        )

        assert_composite_contract(
            result
        )

        # ==================================================
        # RealBook -> Feature
        # ==================================================

        assert snapshot.best_bid == (
            book.best_bid()
        )

        assert snapshot.best_ask == (
            book.best_ask()
        )

        assert snapshot.bid_volume == (
            book.bid_volume()
        )

        assert snapshot.ask_volume == (
            book.ask_volume()
        )

        # ==================================================
        # Feature -> Context
        # ==================================================

        assert context.orderbook.best_bid == (
            snapshot.best_bid
        )

        assert context.orderbook.best_ask == (
            snapshot.best_ask
        )

        assert context.features.mid_price == (
            snapshot.mid_price
        )

        assert context.features.micro_price == (
            snapshot.micro_price
        )

        assert context.features.obi == (
            snapshot.obi
        )

        assert context.features.ofi == (
            snapshot.ofi
        )

    expected = (
        502
    )

    assert builder.event_count == expected

    assert feature_engine.events_processed == expected

    assert manager.total_events == expected

    # sequence在本测试中严格递增
    assert builder.last_sequence == (
        sequence
    )