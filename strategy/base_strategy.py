"""
strategy/base_strategy.py

============================================================
Base Strategy Interface
============================================================

所有交易策略的基类。

策略：

    MeanReversion
    MomentumBreakout
    LiquidityVacuum
    AbsorptionRefill

必须继承此类。

============================================================

Strategy Pipeline:

Market Data
        |
        v
OrderBook
        |
        v
FeatureEngine
        |
        v
StrategyContext
        |
        v
Strategy
        |
        v
Signal

============================================================

Strategy 不负责：

    - Order
    - Execution
    - Risk
    - Portfolio

============================================================
"""

from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    """
    所有策略抽象基类。

    每一个策略实例代表一个独立交易逻辑。
    """

    def __init__(
        self,
        name="BaseStrategy"
    ):
        # ==================================================
        # 策略名称
        # ==================================================

        self.name = name

        # ==================================================
        # 运行状态
        # ==================================================

        self.running = False

        # ==================================================
        # 统计
        # ==================================================

        self.events_processed = 0
        self.signals_generated = 0

    # ======================================================
    # 生命周期
    # ======================================================

    def on_start(self):
        """
        策略启动。

        StrategyManager启动时调用。
        """

        self.running = True

    def on_stop(self):
        """
        策略停止。

        StrategyManager关闭时调用。
        """

        self.running = False

    # ======================================================
    # Strategy Context入口
    # ======================================================

    @abstractmethod
    def on_context(
        self,
        context
    ):
        """
        接收稳定市场状态。

        参数：

            context:
                StrategyContext

        StrategyContext包含：

            - OrderBook Context
            - Feature Context
            - Regime Context
            - Position Context
            - Risk Context

        返回：

            Signal 或 None

        每个策略必须实现。
        """

        raise NotImplementedError

    # ======================================================
    # 外部统一调用入口
    # ======================================================

    def update(
        self,
        context
    ):
        """
        外部统一调用入口。

        等价于：

            strategy.on_context(context)

        保留此接口，方便未来：
            - 单独测试策略
            - 回测工具调用
            - StrategyManager之外的统一调度
        """

        if not self.running:
            return None

        self.events_processed += 1

        signal = self.on_context(
            context
        )

        if signal is not None:
            self.record_signal()

        return signal

    # ======================================================
    # 状态查询
    # ======================================================

    def status(self):
        """
        返回策略运行状态。
        """

        return {
            "name": self.name,
            "running": self.running,
            "events_processed": self.events_processed,
            "signals_generated": self.signals_generated,
        }

    # ======================================================
    # Signal统计
    # ======================================================

    def record_signal(self):
        """
        记录产生一次信号。
        """

        self.signals_generated += 1