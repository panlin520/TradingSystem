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

只有 F_LAST:

    Strategy

    Risk

    Execution

    Portfolio

允许读取稳定市场状态。



============================================================

"""


from enum import Enum

from typing import Any, Optional



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

    """



    def __init__(

        self,

        mode: EngineMode = EngineMode.BACKTEST,

        feed=None,

        orderbook=None,

        strategy=None,

        risk=None,

        execution=None,

        portfolio=None

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




        # 注入共享状态

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
        # Lifecycle
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

            flags & F_LAST

        )

    def _is_last(self, event):
        """
        判断当前 MBO event 是否为交易周期最后事件。

        Databento MBO:
            flags 包含 F_LAST 表示
            当前事件组结束。

        只有 F_LAST 才向上层发送:
            Strategy
            Risk
            Execution
            Portfolio

        OrderBook:
            所有事件都处理。
        """

        try:

            flags = event.flags


            # Databento flag:
            # F_LAST = 0x80

            return bool(
                flags & 0x80
            )


        except Exception:

            return False



    # ========================================================
    # Start
    # ========================================================


    def start(self):


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
            event
    ):

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

        signal

    ):


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

            quantity=signal.quantity

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

        if self.risk:


            if hasattr(

                self.risk,

                "on_fill"

            ):

                self.risk.on_fill(

                    fill

                )



        return fill






    # ========================================================
    # Market Event
    # ========================================================


    def on_event(

        self,

        event: Any

    ):


        """
        单个 MarketEvent 处理。


        所有 MBO:

            Clock

            State

            OrderBook


        只有 F_LAST:

            Strategy

            Risk

            Execution

            Portfolio


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

        if self._is_last(event):

            if self.strategy:
                self.strategy.on_market_event(
                    event,
                    self.state
                )

            if self.risk:
                self.risk.on_event(
                    event,
                    self.state
                )

            if self.execution:
                self.execution.on_event(
                    event,
                    self.state
                )




        self.stable_events += 1

        # ==================================================
        # 6.
        # Strategy + Trading Pipeline
        #
        # ONLY F_LAST
        # ==================================================

        if self._is_last(event):
            signal = self._generate_signal(

                event

            )

            self._process_signal(

                signal

            )





    # ========================================================
    # Fill Callback
    # ========================================================


    def on_fill(

        self,

        fill

    ):


        """
        外部 Execution 回调。


        用于：

            Live Broker

            Async Execution


        """



        if fill is None:

            return



        self.fills.append(

            fill

        )


        self.last_fill = fill


        self.fill_count += 1




        if self.portfolio:


            self.portfolio.on_fill(

                fill

            )



        if self.risk:


            if hasattr(

                self.risk,

                "on_fill"

            ):

                self.risk.on_fill(

                    fill

                )






    # ========================================================
    # Run Loop
    # ========================================================


    def run(

        self,

        feed=None

    ):


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

        self

    ):


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

        self

    ):


        """
        系统状态快照。


        提供：

            Web UI

            Dashboard

            Monitoring

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



        if self.portfolio:


            if hasattr(

                self.portfolio,

                "snapshot"

            ):


                data["portfolio"] = (

                    self.portfolio.snapshot()

                )



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

        self

    ):


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

                f"{key:<25}: {value}"

            )



        print(

            "=" * 60

        )






    # ========================================================
    # Reset
    # ========================================================


    def reset(

        self

    ):


        """
        重置交易引擎。


        用于：

            Backtest 参数优化

            Strategy Replay

        """



        self.running = False



        self.processed_events = 0

        self.stable_events = 0



        self.signal_count = 0

        self.order_count = 0

        self.fill_count = 0



        self.risk_reject_count = 0

        self.execution_fail_count = 0




        self.signals.clear()

        self.orders.clear()

        self.fills.clear()




        self.last_event = None

        self.last_signal = None

        self.last_order = None

        self.last_fill = None





        if self.clock:


            self.clock.reset()




        if self.state:


            self.state.reset()




        if self.orderbook:


            if hasattr(

                self.orderbook,

                "clear"

            ):


                self.orderbook.clear()




        if self.portfolio:


            if hasattr(

                self.portfolio,

                "reset"

            ):


                self.portfolio.reset()




        if self.risk:


            if hasattr(

                self.risk,

                "reset"

            ):


                self.risk.reset()




    # ========================================================
    # Representation
    # ========================================================


    def __repr__(

        self

    ):


        return (

            f"<TradingEngine "

            f"mode={self.mode.value} "

            f"running={self.running} "

            f"events={self.processed_events}>"

        )