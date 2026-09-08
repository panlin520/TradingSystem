"""
features/feature_engine.py

============================================================
Feature Engine
============================================================

职责：

    统一管理所有市场微观结构特征。

输入：

    MarketEvent
    OrderBook

输出：

    FeatureSnapshot

============================================================

Feature Pipeline:

    MarketEvent
          |
          v
    FlowFeatures
          |
          v
    OrderBookFeatures
          |
          v
    TradeFeatures
          |
          v
    RegimeFeatures
          |
          v
    FeatureSnapshot

============================================================

负责：

    - Feature生命周期管理
    - Feature更新顺序
    - Snapshot维护
    - Regime状态维护

不负责：

    - OrderBook维护
    - Strategy
    - Risk
    - Execution

============================================================

冻结边界：

    本模块只读取 OrderBook。

    不允许修改：

        orderbook/*
        data/*
        core/engine.py

============================================================
"""

from features.snapshot import FeatureSnapshot
from features.orderbook_features import OrderBookFeatures
from features.trade_features import TradeFeatures
from features.flow_features import FlowFeatures
from features.regime_features import RegimeFeatures


class FeatureEngine:
    """
    市场特征统一计算引擎。

    一个 FeatureEngine
    对应一个交易标的。
    """

    def __init__(
        self,
        orderbook=None,
        regime_window_size=100
    ):

        # ==================================================
        # OrderBook
        # ==================================================

        self.orderbook = (
            orderbook
        )

        # ==================================================
        # Feature Modules
        # ==================================================

        self.orderbook_features = (
            OrderBookFeatures()
        )

        self.trade_features = (
            TradeFeatures()
        )

        self.flow_features = (
            FlowFeatures()
        )

        self.regime_features = (
            RegimeFeatures(
                window_size=(
                    regime_window_size
                )
            )
        )

        # ==================================================
        # Current Snapshot
        # ==================================================

        self.snapshot = (
            FeatureSnapshot()
        )

        # ==================================================
        # Statistics
        # ==================================================

        self.events_processed = 0

    # ======================================================
    # Event
    # ======================================================

    def on_event(
        self,
        event,
        orderbook=None
    ) -> FeatureSnapshot:
        """
        接收一个 MarketEvent。

        调用顺序：

            1. FlowFeatures
            2. OrderBookFeatures
            3. TradeFeatures
            4. RegimeFeatures

        注意：

            OrderBook 必须已经由上游
            OrderBookBuilder 处理完当前事件。

            FeatureEngine 只读取当前状态。
        """

        # ==================================================
        # Statistics
        # ==================================================

        self.events_processed += 1

        # ==================================================
        # Update Book Reference
        # ==================================================

        if orderbook is not None:

            self.orderbook = (
                orderbook
            )

        # ==================================================
        # Basic Event Metadata
        # ==================================================

        self._update_event_metadata(
            event
        )

        # ==================================================
        # 1. Flow
        # ==================================================

        self.snapshot = (
            self.flow_features.update(
                event,
                self.snapshot
            )
        )

        # ==================================================
        # 2. OrderBook
        # ==================================================

        if self.orderbook is not None:

            self.snapshot = (
                self.orderbook_features.calculate(
                    self.orderbook,
                    self.snapshot
                )
            )

        # ==================================================
        # 3. Trade
        # ==================================================
        #
        # TradeFeatures 当前正式接口：
        #
        #     update(event, snapshot)
        #
        # 不传 OrderBook。
        # ==================================================

        self.snapshot = (
            self.trade_features.update(
                event,
                self.snapshot
            )
        )

        # ==================================================
        # 4. Regime
        # ==================================================

        if self.orderbook is not None:

            self.regime_features.update(
                self.orderbook,
                self.snapshot
            )

        return self.snapshot

    # ======================================================
    # Event Metadata
    # ======================================================

    def _update_event_metadata(
        self,
        event
    ):
        """
        将 MarketEvent 中可用的基础信息
        写入当前 FeatureSnapshot。

        缺失字段不会报错。
        """

        timestamp = self._first_value(
            event,
            "timestamp",
            "ts_event",
            default=None
        )

        if timestamp is not None:

            self.snapshot.timestamp = (
                timestamp
            )

        sequence = self._first_value(
            event,
            "sequence",
            default=None
        )

        if sequence is not None:

            self.snapshot.sequence = (
                sequence
            )

        symbol = self._first_value(
            event,
            "symbol",
            default=None
        )

        if symbol is not None:

            self.snapshot.symbol = (
                str(
                    symbol
                )
            )

    def _first_value(
        self,
        obj,
        *names,
        default=None
    ):
        """
        获取第一个存在且非None的属性。
        """

        for name in names:

            try:

                value = getattr(
                    obj,
                    name
                )

            except Exception:

                continue

            if value is not None:

                return value

        return default

    # ======================================================
    # Current Snapshot
    # ======================================================

    def get_snapshot(
        self
    ) -> FeatureSnapshot:
        """
        返回当前 FeatureSnapshot。

        注意：

            返回的是当前实时对象。

        如果调用方需要保存历史状态：

            snapshot.copy()
        """

        return self.snapshot

    # ======================================================
    # Snapshot Copy
    # ======================================================

    def snapshot_copy(
        self
    ) -> FeatureSnapshot:
        """
        返回当前 FeatureSnapshot 独立副本。
        """

        return self.snapshot.copy()

    # ======================================================
    # Regime State
    # ======================================================

    def get_regime_state(
        self
    ) -> dict:
        """
        返回当前 RegimeFeatures 状态。
        """

        return (
            self.regime_features.state()
        )

    # ======================================================
    # Reset
    # ======================================================

    def reset(
        self
    ):
        """
        新交易日 / 新回测周期时清空所有 Feature 状态。

        清空：

            - FlowFeatures Shadow Orders
            - RegimeFeatures历史状态
            - TradeFeatures内部状态（如果存在reset）
            - FeatureSnapshot
            - events_processed

        注意：

            不修改 OrderBook。
            不清空 OrderBook。
            不替换 OrderBook 引用。

        OrderBook 生命周期由上游负责。
        """

        # ==================================================
        # 1. FlowFeatures
        # ==================================================
        #
        # 必须清空：
        #
        #     Shadow Orders
        #
        # 否则上一交易日 / 上一回测周期的order_id
        # 会泄漏到新的Feature Session。
        # ==================================================

        self.flow_features.reset()

        # ==================================================
        # 2. RegimeFeatures
        # ==================================================
        #
        # 清空：
        #
        #     mid_prices
        #     returns
        #     trend state
        #     volatility state
        #     liquidity state
        #     scores
        # ==================================================

        self.regime_features.reset()

        # ==================================================
        # 3. TradeFeatures
        # ==================================================
        #
        # 当前TradeFeatures的成交累计状态主要存放在
        # FeatureSnapshot中。
        #
        # 如果TradeFeatures现在或未来提供reset()，
        # FeatureEngine统一负责调用。
        # ==================================================

        trade_reset = getattr(
            self.trade_features,
            "reset",
            None
        )

        if callable(
            trade_reset
        ):

            trade_reset()

        # ==================================================
        # 4. Snapshot
        # ==================================================
        #
        # 创建全新的Snapshot对象，
        # 防止上一周期状态泄漏。
        # ==================================================

        self.snapshot = (
            FeatureSnapshot()
        )

        # ==================================================
        # 5. Statistics
        # ==================================================

        self.events_processed = 0