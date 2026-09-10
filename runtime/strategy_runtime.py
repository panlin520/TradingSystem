"""
runtime/strategy_runtime.py

============================================================
Strategy Runtime
============================================================

职责：

    SystemState.strategy_context
            ↓
    StrategyManager.on_context(context)
            ↓
    CompositeSignal
            ↓
    StrategySignalAdapter.adapt(...)
            ↓
    signals.signal.Signal

============================================================

负责：

    - StrategyManager 生命周期调度
    - 从 SystemState 读取 StrategyContext
    - 调用 StrategyManager
    - 将 CompositeSignal 转换为 Runtime Signal
    - 保存最近一次 CompositeSignal / Runtime Signal
    - 基础运行统计

不负责：

    - OrderBook
    - FeatureEngine
    - Risk
    - Order
    - Execution
    - Portfolio

============================================================

核心原则：

    Engine 不需要知道 Alpha Strategy、
    CompositeSignal 的内部结构。

    Engine 只需要：

        strategy_runtime.update(state)

    并接收：

        signals.signal.Signal | None

============================================================
"""


class StrategyRuntime:
    """
    Strategy 层运行时适配器。

    Parameters
    ----------
    strategy_manager:
        strategy.strategy_manager.StrategyManager

    signal_adapter:
        runtime.strategy_signal_adapter.StrategySignalAdapter
    """

    def __init__(
        self,
        strategy_manager,
        signal_adapter,
    ):

        if strategy_manager is None:

            raise ValueError(
                "strategy_manager is required"
            )


        if signal_adapter is None:

            raise ValueError(
                "signal_adapter is required"
            )


        self.strategy_manager = (
            strategy_manager
        )

        self.signal_adapter = (
            signal_adapter
        )


        # ==================================================
        # Runtime State
        # ==================================================

        self.running = False


        # ==================================================
        # Statistics
        # ==================================================

        self.context_count = 0

        self.composite_signal_count = 0

        self.runtime_signal_count = 0


        # ==================================================
        # Last State
        # ==================================================

        self.last_context = None

        self.last_composite_signal = None

        self.last_signal = None





    # ========================================================
    # Lifecycle
    # ========================================================


    def start(self):
        """
        启动 StrategyRuntime 和 StrategyManager。
        """

        if self.running:

            return


        self.running = True


        if hasattr(
            self.strategy_manager,
            "on_start",
        ):

            self.strategy_manager.on_start()





    def stop(self):
        """
        停止 StrategyRuntime 和 StrategyManager。
        """

        if not self.running:

            return


        if hasattr(
            self.strategy_manager,
            "on_stop",
        ):

            self.strategy_manager.on_stop()


        self.running = False





    # ========================================================
    # Update
    # ========================================================


    def update(
        self,
        state,
    ):
        """
        使用 SystemState 中已经构建完成的 StrategyContext。

        流程：

            state.strategy_context
                    ↓
            StrategyManager.on_context(context)
                    ↓
            CompositeSignal
                    ↓
            StrategySignalAdapter.adapt(...)
                    ↓
            Runtime Signal

        返回：

            signals.signal.Signal | None
        """

        if not self.running:

            return None


        if state is None:

            return None


        context = getattr(
            state,
            "strategy_context",
            None,
        )


        if context is None:

            return None


        self.context_count += 1

        self.last_context = context


        composite_signal = (
            self.strategy_manager.on_context(
                context
            )
        )


        self.last_composite_signal = (
            composite_signal
        )


        if composite_signal is None:

            self.last_signal = None

            return None


        if composite_signal.is_trade():

            self.composite_signal_count += 1


        signal = self.signal_adapter.adapt(
            composite_signal,
            context,
        )


        self.last_signal = signal


        if signal is not None:

            self.runtime_signal_count += 1


        return signal





    # ========================================================
    # Reset
    # ========================================================


    def reset(self):
        """
        重置 StrategyRuntime 自身统计。

        不主动重置 StrategyManager 内部策略状态，
        避免越过其正式接口边界。
        """

        self.context_count = 0

        self.composite_signal_count = 0

        self.runtime_signal_count = 0

        self.last_context = None

        self.last_composite_signal = None

        self.last_signal = None





    # ========================================================
    # Status
    # ========================================================


    def status(self):
        """
        返回 StrategyRuntime 运行状态。
        """

        return {

            "running":
                self.running,

            "contexts":
                self.context_count,

            "composite_signals":
                self.composite_signal_count,

            "runtime_signals":
                self.runtime_signal_count,

        }
