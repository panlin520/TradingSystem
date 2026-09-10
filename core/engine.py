"""
core/engine.py


============================================================

Trading Engine V2.1

============================================================


职责：

    整个交易系统事件驱动核心。


核心流程：

    Market Data Feed

            |

            v

    MarketEvent

            |

            v

    Trading Engine

            |

            +----------------+

            |                |

            v                v

        Raw Update       F_LAST Boundary

            |                |

            v                v

        Clock            Strategy

            |

            v

        State

            |

            v

        OrderBook

                             |

                             v

                         Signal

                             |

                             v

                          Risk

                             |

                             v

                          Order

                             |

                             v

                       Execution

                             |

                             v

                          Fill

                             |

                             v

                       Portfolio


============================================================


支持模式：

    BACKTEST

    PAPER

    LIVE


============================================================


核心原则：


1.

所有 MBO raw record 必须更新：

    Clock

    State

    OrderBook


2.

只有 F_LAST：

    Strategy

    Signal

    Risk

    Execution

    Portfolio

允许读取稳定市场状态。


3.

Risk / Execution 的 MarketEvent Hook：

    on_event()

属于可选接口。


4.

Signal 和 Order 属于不同领域模型：

    SignalSide
        ↓
    OrderSide

必须在 Engine 边界显式转换。


============================================================

"""


from enum import Enum

from typing import Any


from core.clock import (
    Clock,
    ClockMode,
)


from core.state import (
    SystemState,
)


from runtime.feature_runtime import FeatureRuntime


from runtime.strategy_context_runtime import (
    StrategyContextRuntime,
)




# ============================================================
# Databento Flag
# ============================================================


F_LAST = 128




# ============================================================
# Engine Mode
# ============================================================


class EngineMode(Enum):
    """
    Trading Engine运行模式。
    """

    BACKTEST = "BACKTEST"

    PAPER = "PAPER"

    LIVE = "LIVE"




# ============================================================
# Trading Engine
# ============================================================


class TradingEngine:
    """
    交易系统核心驱动。


    不负责：

        行情解析

        策略逻辑

        风控逻辑

        撮合逻辑


    负责：

        模块调度

        生命周期

        事件分发

        状态管理


    ========================================================


    Raw Market Path：

        MarketEvent
            ↓
        Clock
            ↓
        State
            ↓
        OrderBook


    每一条 raw MBO 都必须经过。


    ========================================================


    Stable Trading Path：

        F_LAST
            ↓
        Strategy
            ↓
        Signal
            ↓
        Risk
            ↓
        Order
            ↓
        Execution
            ↓
        Fill
            ↓
        Portfolio


    ========================================================
    """



    def __init__(
        self,
        mode: EngineMode = EngineMode.BACKTEST,
        feed=None,
        orderbook=None,
        strategy=None,
        risk=None,
        execution=None,
        portfolio=None,
        feature_runtime=None,
        strategy_context_runtime=None,
    ):


        # ==================================================
        # Mode
        # ==================================================

        self.mode = mode



        # ==================================================
        # Components
        # ==================================================

        self.feed = feed

        self.orderbook = orderbook

        self.strategy = strategy

        self.risk = risk

        self.execution = execution

        self.portfolio = portfolio

        self.feature_runtime = feature_runtime

        self.strategy_context_runtime = (
            strategy_context_runtime
        )



        # ==================================================
        # Clock
        # ==================================================

        self.clock = Clock(
            ClockMode(
                mode.value
            )
        )



        # ==================================================
        # State
        # ==================================================

        self.state = SystemState(
            mode=self.clock.mode
        )



        # ==================================================
        # Shared State Injection
        # ==================================================

        self.state.set_orderbook(
            self.orderbook
        )


        self.state.set_portfolio(
            self.portfolio
        )



        # ==================================================
        # Runtime
        # ==================================================

        self.running = False



        # ==================================================
        # Market Statistics
        # ==================================================

        self.processed_events = 0

        self.stable_events = 0



        # ==================================================
        # Trading Statistics
        # ==================================================

        self.signals = []

        self.orders = []

        self.fills = []


        self.signal_count = 0

        self.order_count = 0

        self.fill_count = 0


        self.risk_reject_count = 0

        self.execution_fail_count = 0



        # ==================================================
        # Lifecycle State
        # ==================================================

        self.last_event = None

        self.last_signal = None

        self.last_order = None

        self.last_fill = None




    # ========================================================
    # F_LAST Check
    # ========================================================


    @staticmethod
    def _is_last_event(
        event: Any
    ) -> bool:
        """
        判断 MarketEvent 是否包含 F_LAST。


        Databento：

            F_LAST = 0x80
        """


        flags = getattr(
            event,
            "flags",
            0,
        )


        try:

            flags = int(flags)

        except Exception:

            return False


        return bool(
            flags
            &
            F_LAST
        )




    def _is_last(
        self,
        event,
    ) -> bool:
        """
        判断当前 MBO event 是否为交易周期最后事件。


        Databento MBO：

            flags 包含 F_LAST

        表示：

            当前事件组结束。


        只有 F_LAST 才允许向上层读取稳定市场状态。


        OrderBook：

            所有 raw event 都必须处理。
        """


        try:

            flags = int(
                event.flags
                or
                0
            )


            return bool(
                flags
                &
                F_LAST
            )


        except Exception:

            return False




    # ========================================================
    # Start
    # ========================================================


    def start(self):
        """
        启动 TradingEngine。
        """


        self.running = True


        if self.strategy:


            if hasattr(
                self.strategy,
                "on_start",
            ):


                self.strategy.on_start(
                    self.state
                )




    # ========================================================
    # Stop
    # ========================================================


    def stop(self):
        """
        停止 TradingEngine。
        """


        self.running = False


        if self.strategy:


            if hasattr(
                self.strategy,
                "on_stop",
            ):


                self.strategy.on_stop(
                    self.state
                )




    # ========================================================
    # Strategy Adapter
    # ========================================================


    def _generate_signal(
        self,
        event,
    ):
        """
        Strategy Signal Adapter。


        当前 Engine 使用：

            strategy.generate_signal(
                event,
                state
            )


        如果 Strategy 不提供该接口：

            返回 None。
        """


        if self.strategy is None:

            return None


        if hasattr(
            self.strategy,
            "generate_signal",
        ):


            return self.strategy.generate_signal(
                event,
                self.state,
            )


        return None




    # ========================================================
    # Signal Pipeline
    # ========================================================


    def _process_signal(
        self,
        signal,
    ):
        """
        Signal 完整交易处理链。


        Signal

            ↓

        Risk

            ↓

        Order

            ↓

        Execution

            ↓

        Fill

            ↓

        Portfolio

            ↓

        Risk Exposure Update
        """


        if signal is None:

            return None



        # ==================================================
        # Save Signal
        # ==================================================

        self.signals.append(
            signal
        )


        self.last_signal = signal


        self.signal_count += 1



        # ==================================================
        # Risk Check
        # ==================================================

        if self.risk:


            decision = self.risk.check_signal(
                signal,
                self.portfolio,
            )


            if not decision.approved:


                self.risk_reject_count += 1


                return None



        # ==================================================
        # Create Order
        # ==================================================
        #
        # Signal 和 Order 是两个不同领域模型。
        #
        # Signal:
        #
        #     signals.signal.SignalSide
        #
        # Order:
        #
        #     order.order.OrderSide
        #
        #
        # 不能直接：
        #
        #     side=signal.side
        #
        #
        # 必须显式执行：
        #
        #     SignalSide
        #         ↓
        #     OrderSide
        #
        # ==================================================

        from order.order import (
            Order,
            OrderSide,
        )



        # ==================================================
        # SignalSide → OrderSide
        # ==================================================

        signal_side_value = getattr(
            signal.side,
            "value",
            signal.side,
        )


        try:

            order_side = OrderSide(
                signal_side_value
            )


        except Exception as exc:


            raise ValueError(
                "Unsupported Signal side for Order: "
                f"{signal.side}"
            ) from exc



        # ==================================================
        # Order
        # ==================================================

        order = Order(
            symbol=signal.symbol,
            side=order_side,
            quantity=signal.quantity,
        )



        self.orders.append(
            order
        )


        self.last_order = order


        self.order_count += 1



        # ==================================================
        # Execution
        # ==================================================

        if self.execution is None:

            return None



        try:


            fill = self.execution.submit(
                order,
                self.state,
            )


        except Exception:


            self.execution_fail_count += 1


            return None



        if fill is None:

            return None



        # ==================================================
        # Fill Received
        # ==================================================

        self.fills.append(
            fill
        )


        self.last_fill = fill


        self.fill_count += 1



        # ==================================================
        # Portfolio Update
        # ==================================================

        if self.portfolio:


            self.portfolio.on_fill(
                fill
            )



        # ==================================================
        # Risk Exposure Update
        # ==================================================
        #
        # RiskManagerV2 当前正式接口：
        #
        #     on_fill(
        #         fill,
        #         portfolio
        #     )
        #
        #
        # Portfolio 负责实际 Position 变化。
        #
        # Risk 这里只重新计算 Exposure。
        #
        # ==================================================

        if self.risk:


            if hasattr(
                self.risk,
                "on_fill",
            ):


                self.risk.on_fill(
                    fill,
                    self.portfolio,
                )



        return fill




    # ========================================================
    # Market Event
    # ========================================================


    def on_event(
        self,
        event: Any,
    ):
        """
        单个 MarketEvent 处理。


        ====================================================

        所有 MBO raw record：

            Clock

            State

            OrderBook

            processed_events


        ====================================================

        只有 F_LAST：

            Strategy Market Hook

            Optional Risk Market Hook

            Optional Execution Market Hook

            Strategy.generate_signal()

            Risk

            Execution

            Portfolio


        ====================================================
        """


        if not self.running:

            return



        self.last_event = event



        # ==================================================
        # 1.
        # Clock Update
        # ==================================================

        self.clock.update(
            event.ts_event
        )



        # ==================================================
        # 2.
        # State Update
        # ==================================================

        self.state.update_event(
            event
        )



        # ==================================================
        # 3.
        # OrderBook Update
        # ==================================================

        if self.orderbook:


            self.orderbook.on_event(
                event
            )


        # ==================================================
        # 3.5 Feature Runtime Update
        # ==================================================

        if self.feature_runtime:

            snapshot = self.feature_runtime.update(
                timestamp=event.ts_event
            )

            self.state.set_feature_snapshot(
                snapshot
            )



        # ==================================================
        # 4.
        # Raw Counter
        # ==================================================

        self.processed_events += 1



        # ==================================================
        # 5.
        # Wait F_LAST
        # ==================================================

        if not self._is_last(
            event
        ):

            return



        # ==================================================
        # Stable Event Counter
        # ==================================================
        #
        # stable_events：
        #
        #     只统计 F_LAST。
        #
        #
        # processed_events：
        #
        #     统计所有 raw MBO。
        #
        # ==================================================

        self.stable_events += 1



        # ==================================================
        # 5.5
        # Strategy Context Runtime
        # ==================================================

        if self.strategy_context_runtime:

            context = self.strategy_context_runtime.build(
                state=self.state,
                risk_manager=self.risk,
            )

            self.state.set_strategy_context(
                context
            )



        # ==================================================
        # 6.
        # Strategy Market Event
        # ==================================================

        if self.strategy:


            if hasattr(
                self.strategy,
                "on_market_event",
            ):


                self.strategy.on_market_event(
                    event,
                    self.state,
                )



        # ==================================================
        # 7.
        # Optional Risk Market Event Hook
        # ==================================================
        #
        # RiskManagerV2 当前核心入口是：
        #
        #     check_signal()
        #
        #
        # 当前并不强制实现：
        #
        #     on_event()
        #
        #
        # 未来可以用于：
        #
        #     volatility monitoring
        #     stale market detection
        #     market halt
        #     kill switch
        #
        # ==================================================

        if self.risk:


            if hasattr(
                self.risk,
                "on_event",
            ):


                self.risk.on_event(
                    event,
                    self.state,
                )



        # ==================================================
        # 8.
        # Optional Execution Market Event Hook
        # ==================================================
        #
        # 当前 ExecutionEngine 核心入口：
        #
        #     submit(order, state)
        #
        #
        # 当前不强制：
        #
        #     on_event()
        #
        #
        # 后续 L3 Matching：
        #
        #     Queue Position
        #     Passive Fill
        #     Market Simulation
        #
        # 可以通过该 Hook 扩展。
        #
        # ==================================================

        if self.execution:


            if hasattr(
                self.execution,
                "on_event",
            ):


                self.execution.on_event(
                    event,
                    self.state,
                )



        # ==================================================
        # 9.
        # Strategy Signal
        # ==================================================

        signal = self._generate_signal(
            event
        )



        # ==================================================
        # 10.
        # Trading Pipeline
        # ==================================================

        self._process_signal(
            signal
        )




    # ========================================================
    # Fill Callback
    # ========================================================


    def on_fill(
        self,
        fill,
    ):
        """
        外部 Execution Fill Callback。


        用于：

            LIVE Broker

            Async Execution


        当前 BACKTEST 同步流程：

            Execution.submit()

        直接返回 Fill。


        本接口主要保留：

            LIVE
            PAPER async execution
        """


        if fill is None:

            return



        # ==================================================
        # Save Fill
        # ==================================================

        self.fills.append(
            fill
        )


        self.last_fill = fill


        self.fill_count += 1



        # ==================================================
        # Portfolio
        # ==================================================

        if self.portfolio:


            self.portfolio.on_fill(
                fill
            )



        # ==================================================
        # Risk
        # ==================================================

        if self.risk:


            if hasattr(
                self.risk,
                "on_fill",
            ):


                self.risk.on_fill(
                    fill,
                    self.portfolio,
                )




    # ========================================================
    # Run Loop
    # ========================================================


    def run(
        self,
        feed=None,
    ):
        """
        Engine 主事件循环。


        Feed 必须支持：

            for event in feed
        """


        if feed is not None:

            self.feed = feed



        if self.feed is None:


            raise ValueError(
                "Feed is required"
            )



        self.start()



        try:


            for event in self.feed:


                if not self.running:

                    break


                self.on_event(
                    event
                )



        except KeyboardInterrupt:


            print(
                "Engine interrupted"
            )



        finally:


            self.stop()




    # ========================================================
    # Progress
    # ========================================================


    def progress(
        self,
    ):
        """
        返回 TradingEngine Runtime Statistics。
        """


        return {


            "mode":

                self.mode.value,


            "running":

                self.running,


            "processed_events":

                self.processed_events,


            "stable_events":

                self.stable_events,


            "signals":

                self.signal_count,


            "orders":

                self.order_count,


            "fills":

                self.fill_count,


            "risk_rejects":

                self.risk_reject_count,


            "execution_failures":

                self.execution_fail_count,

        }




    # ========================================================
    # Snapshot
    # ========================================================


    def snapshot(
        self,
    ):
        """
        系统状态快照。


        用于：

            Web UI

            Dashboard

            Monitoring

            Backtest Diagnostics
        """


        data = {


            "engine": {


                "mode":

                    self.mode.value,


                "running":

                    self.running,


                "processed_events":

                    self.processed_events,


                "stable_events":

                    self.stable_events,

            },


            "trading": {


                "signals":

                    self.signal_count,


                "orders":

                    self.order_count,


                "fills":

                    self.fill_count,


                "risk_rejects":

                    self.risk_reject_count,


                "execution_failures":

                    self.execution_fail_count,

            },


            "last": {


                "event":

                    self.last_event,


                "signals":

                    self.last_signal,


                "order":

                    self.last_order,


                "fill":

                    self.last_fill,

            },

        }



        # ==================================================
        # Portfolio Snapshot
        # ==================================================

        if self.portfolio:


            if hasattr(
                self.portfolio,
                "snapshot",
            ):


                data["portfolio"] = (
                    self.portfolio.snapshot()
                )



        # ==================================================
        # Risk Snapshot
        # ==================================================

        if self.risk:


            if hasattr(
                self.risk,
                "snapshot",
            ):


                data["risk"] = (
                    self.risk.snapshot()
                )



        return data




    # ========================================================
    # Diagnostic
    # ========================================================


    def diagnostic(
        self,
    ):
        """
        输出 TradingEngine Runtime Diagnostic。
        """


        print(
            "=" * 60
        )


        print(
            "TRADING ENGINE V2.1 DIAGNOSTIC"
        )


        print(
            "=" * 60
        )



        for key, value in self.progress().items():


            print(
                f"{key}: {value}"
            )



        print(
            "=" * 60
        )




    # ========================================================
    # Representation
    # ========================================================


    def __repr__(self):


        return (
            "<TradingEngine "
            f"mode={self.mode.value} "
            f"running={self.running} "
            f"events={self.processed_events}>"
        )