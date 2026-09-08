"""
tests/test_feature_strategy_integration.py

============================================================
Feature -> Strategy Integration Tests
============================================================

目标：

    验证：

        MarketEvent
            ↓
        FeatureEngine
            ↓
        FeatureSnapshot
            ↓
        StrategyContext
            ↓
        Real Strategy
            ↓
        StrategyManager
            ↓
        CompositeSignalEngine
            ↓
        CompositeSignal

    整条 Feature / Strategy 跨层链路可以运行。

============================================================

当前边界：

    本测试不使用 Databento DBN。

    使用最小 FakeOrderBook / FakeEvent，
    但接口严格模拟已经冻结的 OrderBook 公开接口：

        best_bid()
        best_ask()
        bid_volume()
        ask_volume()

============================================================

重要字段映射：

    FeatureSnapshot.queue_pressure
                ↓
    FeatureContext.queue_imbalance


    FeatureSnapshot.extra["volatility_score"]
                ↓
    FeatureContext.volatility

============================================================

本测试不负责：

    - 验证 Frozen OrderBook 重建正确性
    - Databento Feed
    - Risk
    - Execution
    - Portfolio
    - 策略盈利能力

============================================================
"""

from enum import Enum

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
# Fake Event Enums
# ============================================================


class FakeAction(Enum):

    ADD = "A"

    MODIFY = "M"

    CANCEL = "C"

    RESET = "R"

    TRADE = "T"

    FILL = "F"

    NONE = "N"


class FakeSide(Enum):

    BID = "B"

    ASK = "A"


# ============================================================
# Fake Event
# ============================================================


class FakeEvent:
    """
    最小 MarketEvent。

    保留当前 Feature 层会读取的字段。
    """

    def __init__(
        self,
        *,
        action,
        side=FakeSide.BID,
        price=100,
        size=1,
        timestamp=1,
        sequence=1,
        symbol="ESU6",
    ):

        self.action = action

        self.side = side

        self.price = price

        self.size = size

        self.timestamp = timestamp

        self.sequence = sequence

        self.symbol = symbol


# ============================================================
# Fake Price Level
# ============================================================


class FakeLevel:
    """
    模拟冻结 OrderBook 中 PriceLevel.volume。
    """

    def __init__(
        self,
        volume
    ):

        self.volume = volume


# ============================================================
# Fake OrderBook
# ============================================================


class FakeOrderBook:
    """
    模拟当前冻结 OrderBook 的公开读取接口。

    Feature 层允许读取：

        best_bid()
        best_ask()

        bid_volume()
        ask_volume()

        bids
        asks

    不模拟订单匹配。
    """

    def __init__(
        self,
        *,
        best_bid=100,
        best_ask=102,
        bid_levels=None,
        ask_levels=None,
    ):

        self._best_bid = best_bid

        self._best_ask = best_ask

        if bid_levels is None:

            bid_levels = {
                100: 100,
            }

        if ask_levels is None:

            ask_levels = {
                102: 100,
            }

        self.bids = {
            price:
                FakeLevel(volume)

            for price, volume
            in bid_levels.items()
        }

        self.asks = {
            price:
                FakeLevel(volume)

            for price, volume
            in ask_levels.items()
        }

    # ======================================================
    # Price
    # ======================================================

    def best_bid(
        self
    ):

        return self._best_bid

    def best_ask(
        self
    ):

        return self._best_ask

    def set_prices(
        self,
        bid,
        ask
    ):

        self._best_bid = bid

        self._best_ask = ask

    # ======================================================
    # Volume
    # ======================================================

    def bid_volume(
        self
    ):

        return sum(
            level.volume

            for level
            in self.bids.values()
        )

    def ask_volume(
        self
    ):

        return sum(
            level.volume

            for level
            in self.asks.values()
        )

    # ======================================================
    # Depth Update
    # ======================================================

    def set_bid_depth(
        self,
        volume
    ):

        if self._best_bid is None:

            self.bids = {}

            return

        self.bids = {
            self._best_bid:
                FakeLevel(
                    volume
                )
        }

    def set_ask_depth(
        self,
        volume
    ):

        if self._best_ask is None:

            self.asks = {}

            return

        self.asks = {
            self._best_ask:
                FakeLevel(
                    volume
                )
        }


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
    将 FeatureEngine 输出转换为策略唯一输入。

    当前真实字段映射：

        snapshot.queue_pressure
            ->
        context.features.queue_imbalance

    当前 RegimeFeatures 数值波动：

        snapshot.extra["volatility_score"]
            ->
        context.features.volatility
    """

    volatility = snapshot.extra.get(
        "volatility_score",
        0.0
    )

    trend_regime = snapshot.extra.get(
        "trend_regime",
        "UNKNOWN"
    )

    liquidity_regime = snapshot.extra.get(
        "liquidity_regime",
        "UNKNOWN"
    )

    return StrategyContext(

        timestamp=(
            snapshot.timestamp
        ),

        symbol=(
            snapshot.symbol
        ),

        # ==================================================
        # OrderBook Context
        # ==================================================

        orderbook=OrderBookContext(

            best_bid=(
                snapshot.best_bid
            ),

            best_ask=(
                snapshot.best_ask
            ),

            bid_size=(
                snapshot.bid_volume
            ),

            ask_size=(
                snapshot.ask_volume
            ),

            spread=(
                snapshot.spread
                or 0
            ),

            depth={
                "bid_5":
                    snapshot.bid_depth_5,

                "ask_5":
                    snapshot.ask_depth_5,

                "bid_10":
                    snapshot.bid_depth_10,

                "ask_10":
                    snapshot.ask_depth_10,
            },

            active_orders=0,
        ),

        # ==================================================
        # Feature Context
        # ==================================================

        features=FeatureContext(

            mid_price=(
                snapshot.mid_price
            ),

            micro_price=(
                snapshot.micro_price
            ),

            obi=(
                snapshot.obi
            ),

            queue_imbalance=(
                snapshot.queue_pressure
            ),

            ofi=(
                snapshot.ofi
            ),

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

        # ==================================================
        # Regime Context
        # ==================================================

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

        # ==================================================
        # Position
        # ==================================================

        position=PositionContext(

            symbol=(
                snapshot.symbol
            ),

            quantity=0,

            side="FLAT",

            unrealized_pnl=0.0,

            realized_pnl=0.0,
        ),

        # ==================================================
        # Risk
        # ==================================================

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
# Helpers
# ============================================================


def make_feature_engine(
    *,
    bid=100,
    ask=102,
    bid_depth=100,
    ask_depth=100,
):
    """
    创建 FeatureEngine + FakeOrderBook。
    """

    book = FakeOrderBook(

        best_bid=bid,

        best_ask=ask,

        bid_levels={
            bid:
                bid_depth
        },

        ask_levels={
            ask:
                ask_depth
        },
    )

    engine = FeatureEngine(
        orderbook=book,
        regime_window_size=20,
    )

    return (
        engine,
        book
    )


def make_manager(
    *strategies,
    min_confidence=0.0,
    min_score=0.0,
):
    """
    创建真实 StrategyManager。

    集成测试重点是链路，
    因此允许降低 Composite 过滤阈值。

    不修改生产默认值。
    """

    composite_engine = (
        CompositeSignalEngine(
            min_confidence=(
                min_confidence
            ),
            min_score=(
                min_score
            ),
        )
    )

    manager = StrategyManager(
        composite_engine=(
            composite_engine
        )
    )

    for strategy in strategies:

        manager.register(
            strategy
        )

    return manager


def assert_composite_contract(
    result
):
    """
    验证 Manager 最终输出契约。
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
# Snapshot -> Context Contract
# ============================================================


def test_feature_snapshot_to_strategy_context():
    """
    验证 FeatureSnapshot 能完整转换为 StrategyContext。
    """

    engine, book = make_feature_engine(
        bid=100,
        ask=102,
        bid_depth=150,
        ask_depth=50,
    )

    event = FakeEvent(
        action=FakeAction.ADD,
        side=FakeSide.BID,
        price=100,
        size=10,
        timestamp=123,
        sequence=456,
        symbol="ESU6",
    )

    snapshot = engine.on_event(
        event
    )

    context = snapshot_to_context(
        snapshot
    )

    assert isinstance(
        context,
        StrategyContext
    )

    assert context.timestamp == 123

    assert context.symbol == "ESU6"

    assert context.orderbook.best_bid == 100

    assert context.orderbook.best_ask == 102

    assert context.orderbook.bid_size == 150

    assert context.orderbook.ask_size == 50

    assert context.features.mid_price == 101.0

    assert context.features.obi == snapshot.obi

    assert (
        context.features.queue_imbalance
        ==
        snapshot.queue_pressure
    )

    assert (
        context.features.ofi
        ==
        snapshot.ofi
    )


# ============================================================
# FeatureEngine -> StrategyManager Warmup
# ============================================================


def test_feature_to_strategy_manager_warmup():
    """
    FeatureEngine输出直接送入真实StrategyManager。

    warmup阶段不要求交易，
    但不能发生跨层接口错误。
    """

    feature_engine, book = (
        make_feature_engine()
    )

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

    event = FakeEvent(
        action=FakeAction.ADD,
        size=10,
        timestamp=1,
        sequence=1,
    )

    snapshot = feature_engine.on_event(
        event
    )

    context = snapshot_to_context(
        snapshot
    )

    result = manager.on_context(
        context
    )

    assert_composite_contract(
        result
    )

    assert manager.total_events == 1


# ============================================================
# Mean Reversion
# ============================================================


def test_feature_to_mean_reversion_strategy():
    """
    使用真实FeatureEngine生成mid_price，
    再驱动真实MeanReversionStrategy。

    人工构造：

        100
        100
        100
        100
         95

    注意：

        这里不是直接给Strategy填mid_price。

        mid_price来自：

            FakeOrderBook
                ↓
            FeatureEngine
                ↓
            FeatureSnapshot
    """

    feature_engine, book = (
        make_feature_engine(
            bid=99,
            ask=101,
            bid_depth=200,
            ask_depth=50,
        )
    )

    strategy = MeanReversionStrategy(
        window=5,
        deviation_threshold=1.0,
        min_confidence=0.0,
    )

    manager = make_manager(
        strategy,
        min_confidence=0.0,
        min_score=0.0,
    )

    mids = [
        100.0,
        100.0,
        100.0,
        100.0,
        95.0,
    ]

    result = None

    for index, mid in enumerate(
        mids,
        start=1
    ):

        bid = mid - 1.0

        ask = mid + 1.0

        book.set_prices(
            bid,
            ask
        )

        book.set_bid_depth(
            200
        )

        book.set_ask_depth(
            50
        )

        event = FakeEvent(
            action=FakeAction.ADD,
            side=FakeSide.BID,
            price=bid,
            size=10,
            timestamp=index,
            sequence=index,
        )

        snapshot = (
            feature_engine.on_event(
                event
            )
        )

        context = (
            snapshot_to_context(
                snapshot
            )
        )

        result = manager.on_context(
            context
        )

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert result.score > 0.0


# ============================================================
# Momentum
# ============================================================


def test_feature_to_momentum_breakout_strategy():
    """
    使用FeatureEngine生成真实mid序列，
    驱动MomentumBreakoutStrategy。
    """

    feature_engine, book = (
        make_feature_engine()
    )

    strategy = MomentumBreakoutStrategy(
        lookback=5,
        breakout_threshold=0.5,
        min_confidence=0.0,
    )

    manager = make_manager(
        strategy,
        min_confidence=0.0,
        min_score=0.0,
    )

    mids = [
        100.00,
        100.10,
        100.20,
        100.30,
        101.00,
    ]

    result = None

    for index, mid in enumerate(
        mids,
        start=1
    ):

        book.set_prices(
            mid - 0.25,
            mid + 0.25
        )

        event = FakeEvent(
            action=FakeAction.ADD,
            side=FakeSide.BID,
            price=mid,
            size=10,
            timestamp=index,
            sequence=index,
        )

        snapshot = (
            feature_engine.on_event(
                event
            )
        )

        context = (
            snapshot_to_context(
                snapshot
            )
        )

        result = manager.on_context(
            context
        )

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert result.score > 0.0


# ============================================================
# Liquidity Vacuum
# ============================================================


def test_feature_to_liquidity_vacuum_strategy():
    """
    Bid深度骤降：

        100
        100
        100
         20

    深度来自FeatureEngine产生的Snapshot，
    再转换给StrategyContext。
    """

    feature_engine, book = (
        make_feature_engine(
            bid_depth=100,
            ask_depth=100,
        )
    )

    strategy = LiquidityVacuumStrategy(
        lookback=4,
        depth_drop_threshold=0.30,
        min_confidence=0.0,
    )

    manager = make_manager(
        strategy,
        min_confidence=0.0,
        min_score=0.0,
    )

    bid_depths = [
        100,
        100,
        100,
        20,
    ]

    result = None

    for index, depth in enumerate(
        bid_depths,
        start=1
    ):

        book.set_bid_depth(
            depth
        )

        book.set_ask_depth(
            100
        )

        event = FakeEvent(
            action=FakeAction.ADD,
            side=FakeSide.BID,
            price=100,
            size=1,
            timestamp=index,
            sequence=index,
        )

        snapshot = (
            feature_engine.on_event(
                event
            )
        )

        context = (
            snapshot_to_context(
                snapshot
            )
        )

        result = manager.on_context(
            context
        )

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert result.score > 0.0


# ============================================================
# Absorption / Refill
# ============================================================


def test_feature_to_absorption_refill_strategy():
    """
    使用FeatureEngine生成：

        trade_volume
        bid / ask depth
        trade_imbalance
        mid_price

    再驱动真实AbsorptionRefillStrategy。
    """

    feature_engine, book = (
        make_feature_engine(
            bid=99.75,
            ask=100.25,
            bid_depth=100,
            ask_depth=100,
        )
    )

    strategy = AbsorptionRefillStrategy(
        lookback=4,
        trade_threshold=1.5,
        refill_threshold=0.5,
        min_confidence=0.0,
    )

    manager = make_manager(
        strategy,
        min_confidence=0.0,
        min_score=0.0,
    )

    # --------------------------------------------------------
    # TradeFeatures当前为累计trade_volume。
    #
    # 所以这里通过：
    #
    #     +10
    #     +10
    #     +10
    #     +100
    #
    # 形成累计：
    #
    #     10
    #     20
    #     30
    #     130
    #
    # 最后一项相对于前序平均具有明显压力。
    # --------------------------------------------------------

    trade_sizes = [
        10,
        10,
        10,
        100,
    ]

    bid_depths = [
        100,
        100,
        100,
        400,
    ]

    result = None

    for index, (
        trade_size,
        bid_depth,
    ) in enumerate(
        zip(
            trade_sizes,
            bid_depths
        ),
        start=1
    ):

        book.set_bid_depth(
            bid_depth
        )

        book.set_ask_depth(
            100
        )

        event = FakeEvent(
            action=FakeAction.TRADE,
            side=FakeSide.BID,
            price=100,
            size=trade_size,
            timestamp=index,
            sequence=index,
        )

        snapshot = (
            feature_engine.on_event(
                event
            )
        )

        context = (
            snapshot_to_context(
                snapshot
            )
        )

        result = manager.on_context(
            context
        )

    assert_composite_contract(
        result
    )

    assert result.is_trade() is True

    assert result.score > 0.0


# ============================================================
# All Strategies
# ============================================================


def test_feature_to_all_real_strategies_runtime():
    """
    四个真实策略同时运行。

    重点：

        FeatureEngine
            ↓
        StrategyContext
            ↓
        四个Strategy
            ↓
        StrategyManager
            ↓
        Composite

    连续运行不能发生接口错误。
    """

    feature_engine, book = (
        make_feature_engine()
    )

    manager = make_manager(

        MeanReversionStrategy(
            window=10,
            deviation_threshold=2.0,
            min_confidence=0.50,
        ),

        MomentumBreakoutStrategy(
            lookback=10,
            breakout_threshold=1.5,
            min_confidence=0.50,
        ),

        LiquidityVacuumStrategy(
            lookback=10,
            depth_drop_threshold=0.50,
            min_confidence=0.50,
        ),

        AbsorptionRefillStrategy(
            lookback=10,
            trade_threshold=1.5,
            refill_threshold=0.50,
            min_confidence=0.50,
        ),

        min_confidence=0.60,
        min_score=1.0,
    )

    result = None

    for index in range(
        1,
        51
    ):

        mid = (
            100.0
            +
            (
                (
                    index % 10
                )
                -
                5
            )
            *
            0.05
        )

        book.set_prices(
            mid - 0.25,
            mid + 0.25
        )

        book.set_bid_depth(
            100
            +
            index % 20
        )

        book.set_ask_depth(
            100
            +
            (
                20
                -
                index % 20
            )
        )

        action = (
            FakeAction.TRADE

            if index % 5 == 0

            else FakeAction.ADD
        )

        event = FakeEvent(
            action=action,
            side=(
                FakeSide.BID

                if index % 2 == 0

                else FakeSide.ASK
            ),
            price=mid,
            size=(
                5
                +
                index % 10
            ),
            timestamp=index,
            sequence=index,
        )

        snapshot = (
            feature_engine.on_event(
                event
            )
        )

        context = (
            snapshot_to_context(
                snapshot
            )
        )

        result = manager.on_context(
            context
        )

        assert_composite_contract(
            result
        )

    assert feature_engine.events_processed == 50

    assert manager.total_events == 50


# ============================================================
# Longer Runtime
# ============================================================


def test_feature_strategy_long_runtime():
    """
    200个事件连续经过：

        FeatureEngine
            ↓
        StrategyContext
            ↓
        StrategyManager

    检查：

        - Snapshot累计
        - Regime历史
        - Strategy deque
        - Manager统计
        - Composite返回契约
    """

    feature_engine, book = (
        make_feature_engine()
    )

    manager = make_manager(

        MeanReversionStrategy(
            window=20
        ),

        MomentumBreakoutStrategy(
            lookback=20
        ),

        LiquidityVacuumStrategy(
            lookback=20
        ),

        AbsorptionRefillStrategy(
            lookback=20
        ),

        min_confidence=0.60,
        min_score=1.0,
    )

    for index in range(
        1,
        201
    ):

        mid = (
            100.0
            +
            (
                (
                    index % 20
                )
                -
                10
            )
            *
            0.025
        )

        book.set_prices(
            mid - 0.125,
            mid + 0.125
        )

        book.set_bid_depth(
            200
            +
            index % 50
        )

        book.set_ask_depth(
            200
            +
            (
                50
                -
                index % 50
            )
        )

        if index % 10 == 0:

            action = (
                FakeAction.TRADE
            )

        elif index % 7 == 0:

            action = (
                FakeAction.CANCEL
            )

        else:

            action = (
                FakeAction.ADD
            )

        event = FakeEvent(
            action=action,
            side=(
                FakeSide.BID

                if index % 2 == 0

                else FakeSide.ASK
            ),
            price=mid,
            size=(
                1
                +
                index % 10
            ),
            timestamp=index,
            sequence=index,
        )

        snapshot = (
            feature_engine.on_event(
                event
            )
        )

        context = (
            snapshot_to_context(
                snapshot
            )
        )

        result = manager.on_context(
            context
        )

        assert_composite_contract(
            result
        )

    assert (
        feature_engine.events_processed
        ==
        200
    )

    assert (
        manager.total_events
        ==
        200
    )

    assert (
        len(
            feature_engine
            .regime_features
            .mid_prices
        )
        <= 20
    )


# ============================================================
# RESET Across Layers
# ============================================================


def test_reset_event_survives_feature_strategy_pipeline():
    """
    R = RESET。

    验证RESET经过完整跨层链路时：

        - FeatureEngine不崩
        - 不虚构cancel volume
        - StrategyContext可以构建
        - Manager可以处理
    """

    feature_engine, book = (
        make_feature_engine()
    )

    manager = make_manager(

        MeanReversionStrategy(
            window=10
        )
    )

    event = FakeEvent(
        action=FakeAction.RESET,
        size=999,
        timestamp=1,
        sequence=1,
    )

    snapshot = (
        feature_engine.on_event(
            event
        )
    )

    assert snapshot.cancel_volume == 0

    assert snapshot.liquidity_removed == 0

    context = (
        snapshot_to_context(
            snapshot
        )
    )

    result = manager.on_context(
        context
    )

    assert_composite_contract(
        result
    )


# ============================================================
# Risk Gate Context
# ============================================================


def test_feature_strategy_context_can_disable_trading():
    """
    FeatureSnapshot转换为StrategyContext时，
    RiskContext必须仍能控制can_trade()。
    """

    feature_engine, book = (
        make_feature_engine()
    )

    snapshot = feature_engine.on_event(

        FakeEvent(
            action=FakeAction.ADD,
            size=10,
        )
    )

    context = snapshot_to_context(
        snapshot,
        allowed=False,
    )

    assert (
        context.can_trade()
        is False
    )


def test_feature_strategy_context_kill_switch():
    """
    Kill Switch状态必须通过Context保留。
    """

    feature_engine, book = (
        make_feature_engine()
    )

    snapshot = feature_engine.on_event(

        FakeEvent(
            action=FakeAction.ADD,
            size=10,
        )
    )

    context = snapshot_to_context(
        snapshot,
        kill_switch=True,
    )

    assert (
        context.can_trade()
        is False
    )