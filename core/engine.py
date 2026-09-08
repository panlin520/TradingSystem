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

所有 MBO raw record 必须更新 OrderBook。


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

是可选接口。


Risk 的核心职责仍然是：

    Signal
      ↓
    check_signal()


Execution 的核心职责仍然是：

    Order
      ↓
    submit()


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





# ============================================================
# Databento Flag
# ============================================================


F_LAST = 128





# ============================================================
# Engine Mode
# ============================================================


class EngineMode(Enum):


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


    Runtime 数据流：


        Feed
          ↓
        MarketEvent
          ↓
        Clock
          ↓
        State
          ↓
        OrderBook


    每一条 raw MBO：

        都必须经过以上流程。


    ========================================================


    F_LAST：

        MarketEvent
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


        当前方法保留作为通用静态接口。
        """


        flags = getattr(

            event,

            "flags",

            0

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


        只有 F_LAST 才允许向上层读取稳定状态。


        OrderBook：

            所有 raw event 都处理。
        """


        try:

            flags = event.flags


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

                "on_start"

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

                "on_stop"

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

            "generate_signal"

        ):


            return self.strategy.generate_signal(

                event,

                self.state

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

                self.portfolio

            )


            if not decision.approved:


                self.risk_reject_count += 1


                return None





        # ==================================================
        # Create Order
        # ==================================================

        from order.order import Order



        order = Order(

            symbol=signal.symbol,

            side=signal.side,

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

                self.state

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
        # RiskManagerV2 当前真实接口：
        #
        #     on_fill(
        #         fill,
        #         portfolio
        #     )
        #
        # Position 实际变化仍然由 Portfolio 负责。
        #
        # Risk 这里只刷新 Exposure 状态。
        #
        # ==================================================

        if self.risk:


            if hasattr(

                self.risk,

                "on_fill"

            ):


                self.risk.on_fill(

                    fill,

                    self.portfolio

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

        self.stable_events += 1





        # ==================================================
        # 6.
        # Strategy Market Event
        # ==================================================

        if self.strategy:


            if hasattr(

                self.strategy,

                "on_market_event"

            ):


                self.strategy.on_market_event(

                    event,

                    self.state

                )





        # ==================================================
        # 7.
        # Optional Risk Market Event Hook
        # ==================================================
        #
        # RiskManagerV2 当前不要求 on_event()。
        #
        # 这里保留 Optional Hook，
        # 方便未来：
        #
        #     real-time exposure monitoring
        #     market halt
        #     volatility kill switch
        #     stale market detection
        #
        # ==================================================

        if self.risk:


            if hasattr(

                self.risk,

                "on_event"

            ):


                self.risk.on_event(

                    event,

                    self.state

                )





        # ==================================================
        # 8.
        # Optional Execution Market Event Hook
        # ==================================================
        #
        # ExecutionEngine 当前核心入口：
        #
        #     submit(order, state)
        #
        # 不强制要求：
        #
        #     on_event()
        #
        # 未来 L3 Matching / Queue Position
        # 可以实现该 Hook。
        #
        # ==================================================

        if self.execution:


            if hasattr(

                self.execution,

                "on_event"

            ):


                self.execution.on_event(

                    event,

                    self.state

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
        外部 Execution 回调。


        用于：

            Live Broker

            Async Execution


        ====================================================

        注意：

        当前同步 BACKTEST 流程：

            _process_signal()

        会直接收到 Execution.submit() 返回的 Fill。


        本接口主要保留给：

            LIVE
            async execution

        ====================================================
        """


        if fill is None:

            return





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

                "on_fill"

            ):


                self.risk.on_fill(

                    fill,

                    self.portfolio

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


        feed 必须是 iterable：


            for event in feed:

                self.on_event(event)
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
        返回 Engine Runtime 统计。
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


        提供：

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

            }

        }





        # ==================================================
        # Portfolio Snapshot
        # ==================================================

        if self.portfolio:


            if hasattr(

                self.portfolio,

                "snapshot"

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

                "snapshot"

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
        输出 Engine Runtime 状态。
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