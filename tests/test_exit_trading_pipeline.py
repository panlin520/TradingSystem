"""
tests/test_exit_trading_pipeline.py

============================================================
EXIT Trading Pipeline Integration Contract
============================================================

验证当前真实接口的完整退出链：

Strategy Signal (HOLD + EXIT)
    ↓
CompositeSignalEngine
    ↓
CompositeSignal (resolved BUY / SELL EXIT)
    ↓
StrategySignalAdapter
    ↓
signals.signal.Signal
    ↓
RiskManagerV2
    ↓
order.order.Order
    ↓
ExecutionEngine
    ↓
execution.fill.Fill
    ↓
Portfolio
    ↓
Position -> FLAT

覆盖：

1. LONG 3 -> HOLD EXIT -> SELL 3 -> FLAT
2. SHORT 2 -> HOLD EXIT -> BUY 2 -> FLAT
3. FLAT -> HOLD EXIT -> no trade

============================================================
"""

from execution.execution_engine import (
    ExecutionEngine,
    ExecutionMode,
)
from execution.fill import Fill
from order.order import (
    Order,
    OrderSide,
    OrderType,
)
from portfolio.portfolio import Portfolio
from risk.risk_manager_v2 import RiskManagerV2
from runtime.strategy_signal_adapter import StrategySignalAdapter
from signals.signal import (
    SignalSide as RuntimeSignalSide,
    SignalType as RuntimeSignalType,
)
from strategy.composite_signal import CompositeSignalEngine
from strategy.context import (
    PositionContext,
    StrategyContext,
)
from strategy.signal import (
    Signal as StrategySignal,
    SignalSide as StrategySignalSide,
    SignalType as StrategySignalType,
    StrategyCategory,
)


# ============================================================
# Shared Market State
# ============================================================


class FakeOrderBook:
    """
    满足 RiskMarketValuation / ExecutionEngine 当前接口。

    Databento-style raw nano prices:

        bid = 5999.75
        ask = 6000.00
    """

    def best_bid(self):
        return 5_999_750_000_000

    def best_ask(self):
        return 6_000_000_000_000


class FakeState:
    def __init__(self, last_price: float):
        self.last_price = last_price
        self.orderbook = FakeOrderBook()


# ============================================================
# Helpers
# ============================================================


def make_hold_exit() -> StrategySignal:
    return StrategySignal(
        side=StrategySignalSide.HOLD,
        signal_type=StrategySignalType.EXIT,
        category=StrategyCategory.EXIT,
        size=1,
        confidence=0.8,
        score=1.5,
        reason="exit current position",
        strategy="exit_strategy",
    )


def make_context_from_portfolio(
    portfolio: Portfolio,
    symbol: str = "ESU6",
) -> StrategyContext:
    position = portfolio.get_position(symbol)

    return StrategyContext(
        symbol=symbol,
        position=PositionContext(
            symbol=symbol,
            quantity=int(position.quantity),
            side=position.side.value,
            entry_price=float(position.avg_price),
        ),
    )


def build_runtime_exit_signal(
    portfolio: Portfolio,
    adapter_quantity: int = 1,
):
    context = make_context_from_portfolio(
        portfolio
    )

    composite_engine = CompositeSignalEngine()

    composite = composite_engine.combine(
        [make_hold_exit()],
        context=context,
    )

    adapter = StrategySignalAdapter(
        quantity=adapter_quantity
    )

    runtime_signal = adapter.adapt(
        composite,
        context,
    )

    return context, composite, runtime_signal


def execute_runtime_signal(
    runtime_signal,
    portfolio: Portfolio,
    execution: ExecutionEngine,
    risk_manager: RiskManagerV2,
    state: FakeState,
):
    decision = risk_manager.check_signals(
        runtime_signal,
        portfolio,
        state=state,
    )

    assert decision.approved is True

    order_side = OrderSide(
        runtime_signal.side.value
    )

    order = Order(
        symbol=runtime_signal.symbol,
        side=order_side,
        quantity=runtime_signal.quantity,
        order_type=OrderType.MARKET,
    )

    fill = execution.submit(
        order,
        state,
    )

    assert fill is not None

    return decision, order, fill


# ============================================================
# LONG Exit
# ============================================================


def test_long_three_hold_exit_closes_position():
    portfolio = Portfolio(
        initial_capital=100000,
        point_values={
            "ESU6": 50.0,
        },
    )

    # 建立真实 LONG 3 portfolio state。
    portfolio.on_fill(
        Fill(
            order_id="OPEN_LONG",
            symbol="ESU6",
            side=OrderSide.BUY,
            quantity=3,
            price=6000.00,
        )
    )

    position = portfolio.get_position(
        "ESU6"
    )

    assert position.quantity == 3
    assert position.side.value == "LONG"

    context, composite, runtime_signal = (
        build_runtime_exit_signal(
            portfolio
        )
    )

    assert context.position.side == "LONG"
    assert context.position.quantity == 3

    assert composite.is_exit() is True
    assert composite.side == StrategySignalSide.SELL

    assert runtime_signal is not None
    assert runtime_signal.side == RuntimeSignalSide.SELL
    assert runtime_signal.signal_type == RuntimeSignalType.EXIT
    assert runtime_signal.quantity == 3

    execution = ExecutionEngine(
        mode=ExecutionMode.BACKTEST,
        on_fill=portfolio.on_fill,
    )

    risk_manager = RiskManagerV2()
    state = FakeState(
        last_price=5999.75
    )

    decision, order, fill = execute_runtime_signal(
        runtime_signal=runtime_signal,
        portfolio=portfolio,
        execution=execution,
        risk_manager=risk_manager,
        state=state,
    )

    assert decision.approved is True
    assert order.side == OrderSide.SELL
    assert order.quantity == 3
    assert fill.side == OrderSide.SELL
    assert fill.quantity == 3
    assert fill.price == 5999.75

    position = portfolio.get_position(
        "ESU6"
    )

    assert position.quantity == 0
    assert position.side.value == "FLAT"


# ============================================================
# SHORT Exit
# ============================================================


def test_short_two_hold_exit_closes_position():
    portfolio = Portfolio(
        initial_capital=100000,
        point_values={
            "ESU6": 50.0,
        },
    )

    # 建立真实 SHORT 2 portfolio state。
    portfolio.on_fill(
        Fill(
            order_id="OPEN_SHORT",
            symbol="ESU6",
            side=OrderSide.SELL,
            quantity=2,
            price=6000.00,
        )
    )

    position = portfolio.get_position(
        "ESU6"
    )

    assert position.quantity == -2
    assert position.side.value == "SHORT"

    context, composite, runtime_signal = (
        build_runtime_exit_signal(
            portfolio
        )
    )

    assert context.position.side == "SHORT"
    assert context.position.quantity == -2

    assert composite.is_exit() is True
    assert composite.side == StrategySignalSide.BUY

    assert runtime_signal is not None
    assert runtime_signal.side == RuntimeSignalSide.BUY
    assert runtime_signal.signal_type == RuntimeSignalType.EXIT
    assert runtime_signal.quantity == 2

    execution = ExecutionEngine(
        mode=ExecutionMode.BACKTEST,
        on_fill=portfolio.on_fill,
    )

    risk_manager = RiskManagerV2()
    state = FakeState(
        last_price=6000.00
    )

    decision, order, fill = execute_runtime_signal(
        runtime_signal=runtime_signal,
        portfolio=portfolio,
        execution=execution,
        risk_manager=risk_manager,
        state=state,
    )

    assert decision.approved is True
    assert order.side == OrderSide.BUY
    assert order.quantity == 2
    assert fill.side == OrderSide.BUY
    assert fill.quantity == 2
    assert fill.price == 6000.00

    position = portfolio.get_position(
        "ESU6"
    )

    assert position.quantity == 0
    assert position.side.value == "FLAT"


# ============================================================
# FLAT Exit
# ============================================================


def test_flat_hold_exit_produces_no_runtime_signal():
    portfolio = Portfolio(
        initial_capital=100000,
        point_values={
            "ESU6": 50.0,
        },
    )

    context = make_context_from_portfolio(
        portfolio
    )

    assert context.position.side == "FLAT"
    assert context.position.quantity == 0

    composite_engine = CompositeSignalEngine()

    composite = composite_engine.combine(
        [make_hold_exit()],
        context=context,
    )

    assert composite.is_trade() is False

    adapter = StrategySignalAdapter(
        quantity=1
    )

    runtime_signal = adapter.adapt(
        composite,
        context,
    )

    assert runtime_signal is None
