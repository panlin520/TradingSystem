"""
runtime/strategy_signal_adapter.py

============================================================
Strategy Signal Adapter
============================================================

职责：

    StrategyManager
        ↓
    CompositeSignal
        ↓
    StrategySignalAdapter
        ↓
    signals.signal.Signal
        ↓
    RiskManagerV2

============================================================

核心原则：

1. strategy.composite_signal.CompositeSignal
   属于 Alpha / Strategy 领域。

2. signals.signal.Signal
   属于 Runtime / Trading 领域。

3. 两者不能直接混用，必须在 Adapter 边界显式转换。

4. CompositeSignal 当前没有 symbol / quantity。
   symbol 从 StrategyContext 获取。
   quantity 必须由 Adapter 配置明确提供，不能猜测。

5. CompositeSignal 当前没有可直接映射到 Runtime datetime 的时间字段。
   Runtime Signal 保留自己的 datetime timestamp；
   StrategyContext.timestamp 保存到 metadata。

============================================================
"""


from typing import Optional


from strategy.composite_signal import CompositeSignal

from strategy.signal import (
    SignalSide as StrategySignalSide,
    SignalType as StrategySignalType,
)

from signals.signal import (
    Signal as RuntimeSignal,
    SignalSide as RuntimeSignalSide,
    SignalType as RuntimeSignalType,
)





class StrategySignalAdapter:
    """
    Alpha CompositeSignal → Runtime Signal 转换器。
    """


    def __init__(
        self,
        quantity: int,
    ):

        if quantity <= 0:

            raise ValueError(
                "quantity must > 0"
            )


        self.quantity = quantity





    # ========================================================
    # Public API
    # ========================================================


    def adapt(
        self,
        composite_signal: CompositeSignal,
        context,
    ) -> Optional[RuntimeSignal]:
        """
        将 CompositeSignal 转换为 Runtime Signal。

        返回 None：

            - composite_signal 为 None
            - 非交易信号
            - HOLD
            - NONE
            - CANCEL
            - 缺少 symbol
        """


        if composite_signal is None:

            return None


        if not composite_signal.is_trade():

            return None


        symbol = getattr(
            context,
            "symbol",
            None,
        )


        if not symbol:

            return None


        runtime_side = self._map_side(
            composite_signal.side
        )


        if runtime_side is None:

            return None


        runtime_type = self._map_signal_type(
            composite_signal.signal_type
        )


        if runtime_type is None:

            return None


        metadata = dict(
            composite_signal.metadata
            if composite_signal.metadata
            else {}
        )


        metadata.update(
            {
                "composite_score":
                    composite_signal.score,

                "composite_reasons":
                    list(
                        composite_signal.reasons
                    ),

                "composite_strategies":
                    list(
                        composite_signal.strategies
                    ),

                "strategy_timestamp":
                    getattr(
                        context,
                        "timestamp",
                        None,
                    ),

                "strategy_category":
                    getattr(
                        composite_signal.category,
                        "value",
                        composite_signal.category,
                    ),
            }
        )


        return RuntimeSignal(

            symbol=symbol,

            side=runtime_side,

            quantity=self.quantity,

            signal_type=runtime_type,

            strategy="COMPOSITE",

            price=None,

            confidence=composite_signal.confidence,

            metadata=metadata,

        )





    # ========================================================
    # Side Mapping
    # ========================================================


    @staticmethod
    def _map_side(
        side,
    ) -> Optional[RuntimeSignalSide]:


        if side == StrategySignalSide.BUY:

            return RuntimeSignalSide.BUY


        if side == StrategySignalSide.SELL:

            return RuntimeSignalSide.SELL


        return None





    # ========================================================
    # Signal Type Mapping
    # ========================================================


    @staticmethod
    def _map_signal_type(
        signal_type,
    ) -> Optional[RuntimeSignalType]:


        if signal_type == StrategySignalType.ENTRY:

            return RuntimeSignalType.ENTRY


        if signal_type == StrategySignalType.EXIT:

            return RuntimeSignalType.EXIT


        return None
