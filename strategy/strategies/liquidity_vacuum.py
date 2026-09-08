"""
strategy/strategies/liquidity_vacuum.py

============================================================
Liquidity Vacuum Strategy
============================================================

职责：

    检测盘口流动性突然消失后的价格移动机会。

============================================================
"""

from collections import deque

from strategy.base_strategy import BaseStrategy
from strategy.signal import (
    Signal,
    SignalSide,
    SignalType,
    StrategyCategory,
)


class LiquidityVacuumStrategy(BaseStrategy):

    def __init__(
        self,
        name="liquidity_vacuum",
        lookback=50,
        depth_drop_threshold=0.5,
        min_confidence=0.65,
    ):
        super().__init__(name=name)

        self.lookback = lookback
        self.depth_drop_threshold = depth_drop_threshold
        self.min_confidence = min_confidence

        self.bid_depth_history = deque(
            maxlen=lookback
        )

        self.ask_depth_history = deque(
            maxlen=lookback
        )

        self.spread_history = deque(
            maxlen=lookback
        )

    # ======================================================
    # Strategy Context
    # ======================================================

    def on_context(
        self,
        context
    ) -> Signal | None:

        orderbook = context.orderbook

        bid_depth = orderbook.bid_size
        ask_depth = orderbook.ask_size
        spread = orderbook.spread

        self.bid_depth_history.append(
            bid_depth
        )

        self.ask_depth_history.append(
            ask_depth
        )

        self.spread_history.append(
            spread
        )

        if len(self.bid_depth_history) < self.lookback:
            return None

        bid_drop = self._drop_ratio(
            self.bid_depth_history
        )

        ask_drop = self._drop_ratio(
            self.ask_depth_history
        )

        flow = self._flow_confirmation(
            context
        )

        # ==================================================
        # Bid Vacuum -> SELL
        # ==================================================

        if bid_drop > self.depth_drop_threshold:

            confidence = self._confidence(
                bid_drop,
                flow
            )

            if confidence >= self.min_confidence:

                score = (
                    bid_drop
                    *
                    2.0
                )

                return Signal(
                    side=SignalSide.SELL,
                    signal_type=SignalType.ENTRY,
                    category=StrategyCategory.LIQUIDITY,
                    confidence=confidence,
                    score=float(score),
                    timestamp=context.timestamp,
                    strategy=self.name,
                    reason="Bid liquidity vacuum",
                    metadata={
                        "score": score,
                        "bid_drop": bid_drop,
                        "ask_drop": ask_drop,
                        "bid_size": bid_depth,
                        "ask_size": ask_depth,
                        "spread": spread,
                        "flow": flow,
                    }
                )

        # ==================================================
        # Ask Vacuum -> BUY
        # ==================================================

        if ask_drop > self.depth_drop_threshold:

            confidence = self._confidence(
                ask_drop,
                flow
            )

            if confidence >= self.min_confidence:

                score = (
                    ask_drop
                    *
                    2.0
                )

                return Signal(
                    side=SignalSide.BUY,
                    signal_type=SignalType.ENTRY,
                    category=StrategyCategory.LIQUIDITY,
                    confidence=confidence,
                    score=float(score),
                    timestamp=context.timestamp,
                    strategy=self.name,
                    reason="Ask liquidity vacuum",
                    metadata={
                        "score": score,
                        "bid_drop": bid_drop,
                        "ask_drop": ask_drop,
                        "bid_size": bid_depth,
                        "ask_size": ask_depth,
                        "spread": spread,
                        "flow": flow,
                    }
                )

        return None

    # ======================================================
    # Position / Exit
    # ======================================================

    def on_position(
        self,
        context
    ) -> Signal | None:

        bid_depth = context.orderbook.bid_size
        ask_depth = context.orderbook.ask_size

        if (
            bid_depth > 0
            and
            ask_depth > 0
        ):

            score = 1.0

            return Signal(
                side=SignalSide.HOLD,
                signal_type=SignalType.EXIT,
                category=StrategyCategory.LIQUIDITY,
                confidence=0.75,
                score=score,
                timestamp=context.timestamp,
                strategy=self.name,
                reason="Liquidity restored",
                metadata={
                    "score": score,
                    "bid_size": bid_depth,
                    "ask_size": ask_depth,
                }
            )

        return None

    # ======================================================
    # Helpers
    # ======================================================

    def _drop_ratio(
        self,
        values
    ) -> float:

        data = list(
            values
        )

        if len(data) < 2:
            return 0.0

        previous = (
            sum(data[:-1])
            /
            (len(data) - 1)
        )

        current = data[-1]

        if previous <= 0:
            return 0.0

        return max(
            0.0,
            (
                previous
                -
                current
            )
            /
            previous
        )

    def _flow_confirmation(
        self,
        context
    ) -> float:

        features = context.features

        queue_strength = min(
            1.0,
            abs(features.queue_imbalance)
        )

        trade_strength = min(
            1.0,
            abs(features.trade_imbalance)
        )

        ofi_abs = abs(
            features.ofi
        )

        ofi_strength = (
            ofi_abs
            /
            (1.0 + ofi_abs)
        )

        return (
            queue_strength
            +
            trade_strength
            +
            ofi_strength
        ) / 3.0

    def _confidence(
        self,
        vacuum_strength,
        flow
    ) -> float:

        return min(
            1.0,
            vacuum_strength * 0.7
            +
            flow * 0.3
        )