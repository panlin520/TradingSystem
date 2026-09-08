"""
strategy/strategies/momentum_breakout.py

============================================================
Momentum Breakout Strategy
============================================================

职责：

    捕捉价格突破后的趋势延续。

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


class MomentumBreakoutStrategy(BaseStrategy):

    def __init__(
        self,
        name="momentum_breakout",
        lookback=50,
        breakout_threshold=1.5,
        min_confidence=0.65,
    ):
        super().__init__(name=name)

        self.lookback = lookback
        self.breakout_threshold = breakout_threshold
        self.min_confidence = min_confidence

        self.prices = deque(
            maxlen=lookback
        )

        self.high_history = deque(
            maxlen=lookback
        )

        self.low_history = deque(
            maxlen=lookback
        )

    # ======================================================
    # Strategy Context
    # ======================================================

    def on_context(
        self,
        context
    ) -> Signal | None:

        price = context.features.mid_price

        if price is None:
            return None

        self.prices.append(
            price
        )

        self.high_history.append(
            price
        )

        self.low_history.append(
            price
        )

        if len(self.prices) < self.lookback:
            return None

        previous_high = max(
            list(self.high_history)[:-1]
        )

        previous_low = min(
            list(self.low_history)[:-1]
        )

        volatility = self._volatility()

        if volatility <= 0:
            return None

        # ==================================================
        # Upward Breakout
        # ==================================================

        if (
            price
            >
            previous_high
            +
            volatility
            *
            self.breakout_threshold
        ):

            flow = self._flow_confirmation(
                context
            )

            distance = (
                price
                -
                previous_high
            )

            confidence = self._confidence(
                distance,
                volatility,
                flow
            )

            if confidence >= self.min_confidence:

                score = (
                    confidence
                    *
                    2.0
                )

                return Signal(
                    side=SignalSide.BUY,
                    signal_type=SignalType.ENTRY,
                    category=StrategyCategory.MOMENTUM,
                    confidence=confidence,
                    score=float(score),
                    timestamp=context.timestamp,
                    strategy=self.name,
                    reason="Upside momentum breakout",
                    metadata={
                        "score": score,
                        "price": price,
                        "breakout_level": previous_high,
                        "distance": distance,
                        "volatility": volatility,
                        "flow": flow,
                    }
                )

        # ==================================================
        # Downward Breakout
        # ==================================================

        if (
            price
            <
            previous_low
            -
            volatility
            *
            self.breakout_threshold
        ):

            flow = self._flow_confirmation(
                context
            )

            distance = (
                previous_low
                -
                price
            )

            confidence = self._confidence(
                distance,
                volatility,
                flow
            )

            if confidence >= self.min_confidence:

                score = (
                    confidence
                    *
                    2.0
                )

                return Signal(
                    side=SignalSide.SELL,
                    signal_type=SignalType.ENTRY,
                    category=StrategyCategory.MOMENTUM,
                    confidence=confidence,
                    score=float(score),
                    timestamp=context.timestamp,
                    strategy=self.name,
                    reason="Downside momentum breakout",
                    metadata={
                        "score": score,
                        "price": price,
                        "breakout_level": previous_low,
                        "distance": distance,
                        "volatility": volatility,
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

        if context.features.mid_price is None:
            return None

        if len(self.prices) < self.lookback:
            return None

        volatility = self._volatility()

        if volatility <= 0:

            score = 1.0

            return Signal(
                side=SignalSide.HOLD,
                signal_type=SignalType.EXIT,
                category=StrategyCategory.MOMENTUM,
                confidence=0.75,
                score=score,
                timestamp=context.timestamp,
                strategy=self.name,
                reason="Momentum disappeared",
                metadata={
                    "score": score,
                    "volatility": volatility,
                }
            )

        return None

    # ======================================================
    # Helpers
    # ======================================================

    def _volatility(self) -> float:

        if len(self.prices) < 2:
            return 0.0

        data = list(
            self.prices
        )

        total_move = 0.0

        for index in range(
            1,
            len(data)
        ):
            total_move += abs(
                data[index]
                -
                data[index - 1]
            )

        return (
            total_move
            /
            (len(data) - 1)
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
        distance,
        volatility,
        flow
    ) -> float:

        if volatility <= 0:
            return 0.0

        breakout_strength = (
            distance
            /
            volatility
        )

        breakout_score = min(
            breakout_strength / 5.0,
            1.0
        )

        return min(
            1.0,
            breakout_score * 0.7
            +
            flow * 0.3
        )