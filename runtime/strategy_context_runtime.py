"""
runtime/strategy_context_runtime.py


============================================================
Strategy Context Runtime
============================================================


职责：

    将 SystemState 转换为 StrategyContext。


数据流：

    SystemState

        ↓

    ContextBuilder

        ↓

    StrategyContext


============================================================


负责：

    - 管理 ContextBuilder
    - 从 Runtime State 创建 StrategyContext
    - 显式接收 RiskManager


============================================================


不负责：

    - Strategy调用

    - Signal生成

    - Order创建

    - Risk判断

    - Execution

    - Portfolio更新


============================================================

"""


from runtime.context_builder import ContextBuilder


class StrategyContextRuntime:
    """
    Strategy Context Runtime。


    将：

        SystemState


    转换为：


        StrategyContext


    """

    def __init__(
        self,
        context_builder=None
    ):
        """
        初始化。


        参数：

            context_builder:

                ContextBuilder实例
        """

        if context_builder is None:

            context_builder = ContextBuilder()

        self.context_builder = context_builder


    # ========================================================
    # Build Context
    # ========================================================

    def build(
        self,
        state,
        risk_manager=None,
    ):
        """
        根据 SystemState 创建 StrategyContext。


        Parameters
        ----------

        state:

            SystemState


        risk_manager:

            RiskManagerV2

            由 TradingEngine 显式传入。

            不从 SystemState 猜测或读取不存在的
            state.risk_manager。


        Returns
        -------

        StrategyContext
        """

        return self.context_builder.build(

            snapshot=state.feature_snapshot,

            orderbook=state.orderbook,

            portfolio=state.portfolio,

            risk_manager=risk_manager,

        )


    # ========================================================
    # Validation
    # ========================================================

    def has_feature(
        self,
        state
    ):
        """
        判断是否已经存在 FeatureSnapshot。
        """

        return (

            getattr(

                state,

                "feature_snapshot",

                None

            )

            is not None

        )
