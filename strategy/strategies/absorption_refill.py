"""
strategy/strategies/absorption_refill.py

============================================================
Absorption / Refill Strategy
============================================================

职责：

    检测被动流动性吸收主动成交后的反转机会。

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


class AbsorptionRefillStrategy(BaseStrategy):

    def __init__(
        self,
        name="absorption_refill",
        lookback=30,
        trade_threshold=1.5,
        refill_threshold=0.5,
        min_confidence=0.65,
    ):
        super().__init__(name=name)

        self.lookback = lookback
        self.trade_threshold = trade_threshold
        self.refill_threshold = refill_threshold
        self.min_confidence = min_confidence

        self.trade_history = deque(
            maxlen=lookback
        )

        self.price_history = deque(
            maxlen=lookback
        )

        self.bid_depth_history = deque(
            maxlen=lookback
        )

        self.ask_depth_history = deque(
            maxlen=lookback
        )

    # ======================================================
    # Strategy Context
    # ======================================================

    def on_context(
        self,
        context
    ) -> Signal | None:

        features = context.features
        orderbook = context.orderbook

        price = features.mid_price

        if price is None:
            return None

        trade_volume = features.trade_volume

        bid_depth = orderbook.bid_size
        ask_depth = orderbook.ask_size

        self.trade_history.append(
            trade_volume
        )

        self.price_history.append(
            price
        )

        self.bid_depth_history.append(
            bid_depth
        )

        self.ask_depth_history.append(
            ask_depth
        )

        if len(self.trade_history) < self.lookback:
            return None

        trade_pressure = self._trade_pressure()
        price_move = self._price_move()
        refill = self._refill_score()

        flow = self._flow_confirmation(
            context
        )

        # ==================================================
        # Sell Pressure Absorption -> BUY
        # ==================================================

        if (
            trade_pressure
            <
            -self.trade_threshold
            and
            abs(price_move)
            <
            1.0
            and
            refill
            >
            self.refill_threshold
        ):

            confidence = self._confidence(
                refill,
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
                    category=StrategyCategory.ABSORPTION,
                    confidence=confidence,
                    score=float(score),
                    timestamp=context.timestamp,
                    strategy=self.name,
                    reason="Buy absorption detected",
                    metadata={
                        "score": score,
                        "trade_pressure": trade_pressure,
                        "price_move": price_move,
                        "refill": refill,
                        "flow": flow,
                        "trade_volume": trade_volume,
                        "bid_size": bid_depth,
                        "ask_size": ask_depth,
                    }
                )

        # ==================================================
        # Buy Pressure Absorption -> SELL
        # ==================================================

        if (
            trade_pressure
            >
            self.trade_threshold
            and
            abs(price_move)
            <
            1.0
            and
            refill
            >
            self.refill_threshold
        ):

            confidence = self._confidence(
                refill,
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
                    category=StrategyCategory.ABSORPTION,
                    confidence=confidence,
                    score=float(score),
                    timestamp=context.timestamp,
                    strategy=self.name,
                    reason="Sell absorption detected",
                    metadata={
                        "score": score,
                        "trade_pressure": trade_pressure,
                        "price_move": price_move,
                        "refill": refill,
                        "flow": flow,
                        "trade_volume": trade_volume,
                        "bid_size": bid_depth,
                        "ask_size": ask_depth,
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

        refill = self._refill_score()

        if refill < 0.2:

            score = 1.0

            return Signal(
                side=SignalSide.HOLD,
                signal_type=SignalType.EXIT,
                category=StrategyCategory.ABSORPTION,
                confidence=0.75,
                score=score,
                timestamp=context.timestamp,
                strategy=self.name,
                reason="Absorption disappeared",
                metadata={
                    "score": score,
                    "refill": refill,
                }
            )

        return None

    # ======================================================
    # Helpers
    # ======================================================

    def _trade_pressure(self) -> float:

        data = list(
            self.trade_history
        )

        if len(data) < 2:
            return 0.0

        previous_average = (
            sum(data[:-1])
            /
            (len(data) - 1)
        )

        current = data[-1]

        if previous_average <= 0:
            return 0.0

        return (
            current
            -
            previous_average
        ) / previous_average

    def _price_move(self) -> float:

        data = list(
            self.price_history
        )

        if len(data) < 2:
            return 0.0

        return (
            data[-1]
            -
            data[0]
        )

    def _refill_score(self) -> float:

        bid = list(
            self.bid_depth_history
        )

        ask = list(
            self.ask_depth_history
        )

        if (
            len(bid) < 2
            or
            len(ask) < 2
        ):
            return 0.0

        bid_change = (
            bid[-1]
            -
            bid[0]
        )

        ask_change = (
            ask[-1]
            -
            ask[0]
        )

        total_change = (
            abs(bid_change)
            +
            abs(ask_change)
        )

        if total_change <= 0:
            return 0.0

        return min(
            1.0,
            total_change
            /
            (
                total_change
                +
                100.0
            )
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
        refill,
        flow
    ) -> float:

        return min(
            1.0,
            refill * 0.7
            +
            flow * 0.3
        )