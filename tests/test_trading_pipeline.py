"""
tests/test_trading_pipeline.py


============================================================
Trading Pipeline Integration Test
============================================================


验证完整交易链：

Signal

    ↓

RiskManagerV2

    ↓

RiskMarketValuation

    ↓

ExposureEngine

    ↓

Order

    ↓

ExecutionEngine

    ↓

Fill

    ↓

Portfolio

    ↓

Position


============================================================

当前 Risk 契约：

- RiskManagerV2 支持 state context
- Dollar Exposure 必须使用有效 market valuation
- 非零 projected position 缺少 valuation / point_value 时 fail closed

因此本测试必须显式提供：

- Portfolio point_values
- state.orderbook
- Best Bid / Best Ask

============================================================
"""


from signals.signal import (
    Signal,
    SignalSide,
)


from risk.risk_manager_v2 import (
    RiskManagerV2,
)


from order.order import (
    Order,
    OrderSide,
)


from execution.execution_engine import (
    ExecutionEngine,
    ExecutionMode,
)


from portfolio.portfolio import (
    Portfolio,
)




# ============================================================
# Fake OrderBook
# ============================================================


class FakeOrderBook:
    """
    满足 RiskMarketValuation 当前真实接口：

        best_bid()
        best_ask()

    返回 Databento 风格 raw nano-price，
    用于验证 Risk 层价格归一化。
    """


    def best_bid(self):

        return 5_999_750_000_000


    def best_ask(self):

        return 6_000_000_000_000




# ============================================================
# Fake State
# ============================================================


class FakeState:
    """
    同一个 state 同时满足：

    RiskManagerV2:
        state.orderbook

    ExecutionEngine.submit():
        state.last_price
    """


    def __init__(self):

        self.last_price = 6000.00

        self.orderbook = FakeOrderBook()




# ============================================================
# Fake Signal
# ============================================================


def create_signal():

    return Signal(

        symbol="ESU6",

        side=SignalSide.BUY,

        quantity=1,

    )




# ============================================================
# Pipeline Test
# ============================================================


def test_complete_trading_pipeline():


    # ==================================================
    # Portfolio
    # ==================================================
    #
    # 当前 ExposureEngine 不在 Risk 层猜合约乘数。
    # 测试显式提供 ESU6 point_value。
    # ==================================================

    portfolio = Portfolio(

        initial_capital=100000,

        point_values={
            "ESU6": 50.0,
        },

    )



    # ==================================================
    # Execution
    # ==================================================

    execution = ExecutionEngine(

        mode=ExecutionMode.BACKTEST,

        on_fill=portfolio.on_fill,

    )



    # ==================================================
    # Risk
    # ==================================================

    risk_manager = RiskManagerV2()



    # ==================================================
    # State
    # ==================================================

    state = FakeState()



    # ==================================================
    # Strategy Signal
    # ==================================================

    signal = create_signal()



    # ==================================================
    # Risk Check
    # ==================================================
    #
    # BUY valuation：Best Ask
    #
    # raw:
    #     6_000_000_000_000
    #
    # normalized:
    #     6000.0
    #
    # projected gross notional:
    #     1 × 6000 × 50
    #     = 300000 USD
    # ==================================================

    decision = risk_manager.check_signals(

        signal,

        portfolio,

        state=state,

    )


    assert decision.approved is True


    assert (
        risk_manager.last_valuation_price
        ==
        6000.00
    )


    assert (
        risk_manager
        .last_projected_exposure
        .gross_notional
        ==
        300000.00
    )



    # ==================================================
    # Create Order
    # ==================================================

    order = Order(

        symbol=signal.symbol,

        side=OrderSide.BUY,

        quantity=signal.quantity,

    )


    assert order.validate() is True



    # ==================================================
    # Execute
    # ==================================================
    #
    # ExecutionEngine.submit() 当前真实兼容规则：
    #
    #     1. state.last_price
    #     2. state.orderbook
    #
    # 因此这里 Fill price = 6000.00。
    # ==================================================

    fill = execution.submit(

        order,

        state,

    )


    assert fill is not None

    assert fill.symbol == "ESU6"

    assert fill.quantity == 1

    assert fill.price == 6000.00



    # ==================================================
    # Portfolio Check
    # ==================================================

    position = portfolio.get_position(
        "ESU6"
    )


    assert position.quantity == 1

    assert position.avg_price == 6000.00


    assert portfolio.trade_count == 1

    assert portfolio.volume == 1

    assert portfolio.market_prices[
        "ESU6"
    ] == 6000.00


    assert execution.total_fills == 1
