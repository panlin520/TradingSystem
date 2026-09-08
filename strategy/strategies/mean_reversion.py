"""
strategy/strategies/mean_reversion.py

============================================================
Mean Reversion Strategy
============================================================

职责：

    利用短周期价格偏离均值后的回归机会。

核心逻辑：

    Price Deviation
            ↓
    Mean Distance
            ↓
    Reversion Probability
            ↓
    Queue / OFI / Trade Flow Confirmation
            ↓
    Signal

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


class MeanReversionStrategy(BaseStrategy):

    def __init__(
        self,
        name="mean_reversion",
        window=50,
        deviation_threshold=2.0,
        min_confidence=0.65,
    ):
        super().__init__(name=name)

        self.window = window
        self.deviation_threshold = deviation_threshold
        self.min_confidence = min_confidence

        self.prices = deque(
            maxlen=window
        )

        self.last_signal = None

    # ======================================================
    # Strategy Context
    # ======================================================

    def on_context(
        self,
        context
    ) -> Signal | None:

        mid_price = context.features.mid_price

        if mid_price is None:
            return None

        self.prices.append(
            mid_price
        )

        if len(self.prices) < self.window:
            return None

        # ==================================================
        # Mean
        # ==================================================

        mean_price = (
            sum(self.prices)
            /
            len(self.prices)
        )

        deviation = (
            mid_price
            -
            mean_price
        )

        std = self._std()

        if std <= 0:
            return None

        zscore = (
            deviation
            /
            std
        )

        # ==================================================
        # Flow Confirmation
        # ==================================================

        flow_score = self._flow_confirmation(
            context
        )

        # ==================================================
        # Oversold
        # ==================================================

        if zscore <= -self.deviation_threshold:

            confidence = self._confidence(
                abs(zscore),
                flow_score
            )

            if confidence >= self.min_confidence:

                score = (
                    abs(zscore)
                    *
                    flow_score
                )

                signal = Signal(
                    side=SignalSide.BUY,
                    signal_type=SignalType.ENTRY,
                    category=StrategyCategory.MEAN_REVERSION,
                    confidence=confidence,
                    score=float(score),
                    timestamp=context.timestamp,
                    strategy=self.name,
                    reason="Price below mean equilibrium",
                    metadata={
                        "score": score,
                        "zscore": zscore,
                        "mean_price": mean_price,
                        "mid_price": mid_price,
                        "flow_score": flow_score,
                    }
                )

                self.last_signal = signal

                return signal

        # ==================================================
        # Overbought
        # ==================================================

        if zscore >= self.deviation_threshold:

            confidence = self._confidence(
                abs(zscore),
                flow_score
            )

            if confidence >= self.min_confidence:

                score = (
                    abs(zscore)
                    *
                    flow_score
                )

                signal = Signal(
                    side=SignalSide.SELL,
                    signal_type=SignalType.ENTRY,
                    category=StrategyCategory.MEAN_REVERSION,
                    confidence=confidence,
                    score=float(score),
                    timestamp=context.timestamp,
                    strategy=self.name,
                    reason="Price above mean equilibrium",
                    metadata={
                        "score": score,
                        "zscore": zscore,
                        "mean_price": mean_price,
                        "mid_price": mid_price,
                        "flow_score": flow_score,
                    }
                )

                self.last_signal = signal

                return signal

        return None

    # ======================================================
    # Position / Exit
    # ======================================================

    def on_position(
        self,
        context
    ) -> Signal | None:

        mid_price = context.features.mid_price

        if mid_price is None:
            return None

        if len(self.prices) < self.window:
            return None

        mean_price = (
            sum(self.prices)
            /
            len(self.prices)
        )

        distance = abs(
            mid_price
            -
            mean_price
        )

        if distance < 0.25:

            score = 1.0

            return Signal(
                side=SignalSide.HOLD,
                signal_type=SignalType.EXIT,
                category=StrategyCategory.MEAN_REVERSION,
                confidence=0.80,
                score=score,
                timestamp=context.timestamp,
                strategy=self.name,
                reason="Price reverted to mean",
                metadata={
                    "score": score,
                    "mean_price": mean_price,
                    "mid_price": mid_price,
                    "distance": distance,
                }
            )

        return None

    # ======================================================
    # Helpers
    # ======================================================

    def _std(self) -> float:

        if not self.prices:
            return 0.0

        mean = (
            sum(self.prices)
            /
            len(self.prices)
        )

        variance = (
            sum(
                (price - mean) ** 2
                for price in self.prices
            )
            /
            len(self.prices)
        )

        return variance ** 0.5

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
        deviation_strength,
        flow_score
    ) -> float:

        deviation_score = min(
            deviation_strength / 5.0,
            1.0
        )

        return min(
            1.0,
            deviation_score * 0.7
            +
            flow_score * 0.3
        )