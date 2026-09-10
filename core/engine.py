"""
core/engine.py


============================================================

Trading Engine V2.2

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
        Clock         Strategy Context
            |                |
            v                v
        State         Strategy Runtime
            |                |
            v                v
        OrderBook          Signal
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
    FeatureRuntime


2.
只有 F_LAST：

    StrategyContext
    StrategyRuntime / Legacy Strategy
    Signal
    Risk
    Execution
    Portfolio

允许读取稳定市场状态。


3.
正式 Strategy Runtime：

    StrategyContext
        ↓
    StrategyRuntime
        ↓
    Runtime Signal


4.
旧 Strategy 接口继续兼容：

    strategy.on_market_event(event, state)

    strategy.generate_signal(event, state)


5.
当 strategy_runtime 存在时：

    优先使用 strategy_runtime.update(state)

    不再同时调用 legacy generate_signal()，
    避免同一稳定事件产生两套交易信号。


6.
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


    Raw Market Path：

        MarketEvent
            ↓
        Clock
            ↓
        State
            ↓
        OrderBook
            ↓
        FeatureRuntime


    Stable Trading Path：

        F_LAST
            ↓
        StrategyContextRuntime
            ↓
        StrategyRuntime
            ↓
        Runtime Signal
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


    Legacy Strategy Path：

        F_LAST
            ↓
        strategy.on_market_event(event, state)
            ↓
        strategy.generate_signal(event, state)


    StrategyRuntime 存在时优先使用正式 Runtime Path。
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
        strategy_runtime=None,
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

        # Legacy Strategy
        self.strategy = strategy

        self.risk = risk

        self.execution = execution

        self.portfolio = portfolio

        self.feature_runtime = feature_runtime

        self.strategy_context_runtime = (
            strategy_context_runtime
        )

        # Formal Strategy Runtime
        self.strategy_runtime = (
            strategy_runtime
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
        判断当前 MBO event 是否为稳定事件边界。

        所有 raw MBO 必须先更新 OrderBook。
        只有 F_LAST 才允许进入 Strategy/Risk/Execution。
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


        # ==================================================
        # Formal Strategy Runtime
        # ==================================================

        if self.strategy_runtime:

            if hasattr(
                self.strategy_runtime,
                "start",
            ):

                self.strategy_runtime.start()


        # ==================================================
        # Legacy Strategy
        # ==================================================

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


        # ==================================================
        # Formal Strategy Runtime
        # ==================================================

        if self.strategy_runtime:

            if hasattr(
                self.strategy_runtime,
                "stop",
            ):

                self.strategy_runtime.stop()


        # ==================================================
        # Legacy Strategy
        # ==================================================

        if self.strategy:

            if hasattr(
                self.strategy,
                "on_stop",
            ):

                self.strategy.on_stop(
                    self.state
                )




    # ========================================================
    # Legacy Strategy Adapter
    # ========================================================


    def _generate_signal(
        self,
        event,
    ):
        """
        Legacy Strategy Signal Adapter。

        旧接口：

            strategy.generate_signal(
                event,
                state
            )

        正式 StrategyRuntime 存在时，
        on_event() 不调用本接口。
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

        Runtime Signal
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

            # ==================================================
            # Risk Context Compatibility
            # ==================================================
            #
            # RiskManagerV2 supports:
            #
            #     check_signal(
            #         signal,
            #         portfolio,
            #         state=state,
            #     )
            #
            # 旧 Risk 实现仍然只接受：
            #
            #     check_signal(
            #         signal,
            #         portfolio,
            #     )
            #
            # 不能无条件传 state，
            # 否则会破坏旧接口。
            # ==================================================

            if getattr(
                self.risk,
                "supports_state_context",
                False,
            ):

                decision = self.risk.check_signal(
                    signal,
                    self.portfolio,
                    state=self.state,
                )

            else:

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
        # Signal:
        #
        #     signals.signal.SignalSide
        #
        # Order:
        #
        #     order.order.OrderSide
        #
        # 必须显式转换。
        # ==================================================

        from order.order import (
            Order,
            OrderSide,
        )


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


        所有 MBO raw record：

            Clock
            State
            OrderBook
            FeatureRuntime
            processed_events


        只有 F_LAST：

            StrategyContextRuntime
            Legacy Strategy Market Hook
            Optional Risk Market Hook
            Optional Execution Market Hook

            然后：

                strategy_runtime.update(state)

            或旧接口：

                strategy.generate_signal(event, state)

            最后：

                Risk
                Order
                Execution
                Portfolio
        """

        if not self.running:

            return


        self.last_event = event


        # ==================================================
        # 1. Clock Update
        # ==================================================

        self.clock.update(
            event.ts_event
        )


        # ==================================================
        # 2. State Update
        # ==================================================

        self.state.update_event(
            event
        )


        # ==================================================
        # 3. OrderBook Update
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
        # 4. Raw Counter
        # ==================================================

        self.processed_events += 1


        # ==================================================
        # 5. Wait F_LAST
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
        # 5.5 Strategy Context Runtime
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
        # 6. Legacy Strategy Market Event Hook
        # ==================================================
        #
        # 保留已有接口兼容。
        #
        # 正式 Alpha Strategy 不通过该接口执行，
        # 而是由 StrategyRuntime 调度。
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
        # 7. Optional Risk Market Event Hook
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
        # 8. Optional Execution Market Event Hook
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
        # 9. Strategy Signal
        # ==================================================
        #
        # 正式 Runtime 优先。
        #
        # 如果 strategy_runtime 存在：
        #
        #     state.strategy_context
        #           ↓
        #     strategy_runtime.update(state)
        #           ↓
        #     Runtime Signal
        #
        # 否则：
        #
        #     legacy strategy.generate_signal(event, state)
        #
        # 不允许两个路径同时产生交易信号。
        # ==================================================

        if self.strategy_runtime:

            signal = self.strategy_runtime.update(
                self.state
            )

        else:

            signal = self._generate_signal(
                event
            )


        # ==================================================
        # 10. Trading Pipeline
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
            "TRADING ENGINE V2.2 DIAGNOSTIC"
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
