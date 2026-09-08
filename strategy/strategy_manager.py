"""
strategy/strategy_manager.py

============================================================
Strategy Manager
============================================================

职责：

    管理所有策略生命周期。

负责：

    - Strategy 注册
    - Strategy 调用
    - Regime 分类
    - Signal 收集
    - Composite Signal

不负责：

    - 下单
    - 风控执行
    - OrderBook
    - Portfolio

============================================================

Pipeline:

Market Data
      |
      v
Feature Engine
      |
      v
Strategy Context
      |
      v
Strategy Manager
      |
      v
Strategy Signals
      |
      v
Composite Signal
      |
      v
Execution

============================================================
"""

from typing import List

from strategy.signal import Signal

from strategy.composite_signal import (
    CompositeSignalEngine,
    CompositeSignal,
)


class StrategyManager:

    def __init__(
        self,
        strategies=None,
        regime_classifier=None,
        composite_engine=None,
        exit_strategies=None
    ):
        # ====================================================
        # Entry Strategies
        # ====================================================

        self.strategies = (
            strategies
            if strategies
            else []
        )

        # ====================================================
        # Exit Strategies
        # ====================================================

        self.exit_strategies = (
            exit_strategies
            if exit_strategies
            else []
        )

        # ====================================================
        # Regime Classifier
        # ====================================================

        self.regime_classifier = regime_classifier

        # ====================================================
        # Composite Signal Engine
        # ====================================================

        self.composite_engine = (
            composite_engine
            if composite_engine
            else CompositeSignalEngine()
        )

        # ====================================================
        # Statistics
        # ====================================================

        self.total_events = 0
        self.signal_count = 0

    # ========================================================
    # Add Strategy
    # ========================================================

    def add_strategy(
        self,
        strategy
    ):
        """
        添加 Entry Strategy。

        返回：

            已注册的 strategy 对象。
        """

        self.strategies.append(
            strategy
        )

        return strategy

    # ========================================================
    # Register Strategy
    # ========================================================

    def register(
        self,
        strategy
    ):
        """
        Strategy 注册兼容接口。

        等价于：

            add_strategy(strategy)

        用于：

            - 外部策略注册
            - 测试
            - 旧接口兼容
        """

        return self.add_strategy(
            strategy
        )

    # ========================================================
    # Add Exit Strategy
    # ========================================================

    def add_exit_strategy(
        self,
        strategy
    ):
        """
        添加 Exit Strategy。
        """

        self.exit_strategies.append(
            strategy
        )

        return strategy

    # ========================================================
    # Event Handler
    # ========================================================

    def on_context(
        self,
        context
    ) -> CompositeSignal:
        """
        接收 StrategyContext。

        执行流程：

            1. Regime Classification
            2. Exit Strategies
            3. Entry Strategies
            4. Composite Signal

        Exit Strategy 永远优先于 Entry Strategy。
        """

        self.total_events += 1

        # ====================================================
        # 1. Regime Classification
        # ====================================================

        if self.regime_classifier:

            regime = self.regime_classifier.classify(
                context
            )

            if regime:
                context.regime = regime

        signals: List[Signal] = []

        # ====================================================
        # 2. Exit Strategy First
        #
        # 退出永远优先
        # ====================================================

        for strategy in self.exit_strategies:

            signal = strategy.on_context(
                context
            )

            if signal:

                signals.append(
                    signal
                )

        # ====================================================
        # 3. Entry Strategies
        # ====================================================

        for strategy in self.strategies:

            signal = strategy.on_context(
                context
            )

            if signal:

                signals.append(
                    signal
                )

        # ====================================================
        # 4. Composite
        # ====================================================

        final_signal = self.composite_engine.combine(
            signals,
            context
        )

        if final_signal.is_trade():

            self.signal_count += 1

        return final_signal

    # ========================================================
    # Lifecycle
    # ========================================================

    def on_start(self):
        """
        启动所有 Entry / Exit Strategy。
        """

        for strategy in (
            self.strategies
            +
            self.exit_strategies
        ):

            if hasattr(
                strategy,
                "on_start"
            ):

                strategy.on_start()

    def on_stop(self):
        """
        停止所有 Entry / Exit Strategy。
        """

        for strategy in (
            self.strategies
            +
            self.exit_strategies
        ):

            if hasattr(
                strategy,
                "on_stop"
            ):

                strategy.on_stop()

    # ========================================================
    # Status
    # ========================================================

    def stats(self):
        """
        返回 StrategyManager 运行统计。
        """

        return {
            "events": self.total_events,
            "signals": self.signal_count,
            "strategies": len(self.strategies),
            "exit_strategies": len(
                self.exit_strategies
            ),
        }