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
        state
    ):
        """
        根据 SystemState 创建 StrategyContext。


        Parameters
        ----------

        state:

            SystemState



        Returns
        -------

        StrategyContext



        """


        context = self.context_builder.build(

            snapshot=state.feature_snapshot,

            orderbook=state.orderbook,

            portfolio=state.portfolio,

            risk_manager=getattr(

                state,

                "risk_manager",

                None

            ),

        )


        return context





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