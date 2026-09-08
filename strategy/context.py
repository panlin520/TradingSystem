"""
strategy/context.py


============================================================
Strategy Context
============================================================


职责：

    为所有策略提供统一市场上下文。


数据流：

    MarketEvent
          |
          v
    OrderBook
          |
          v
    FeatureEngine
          |
          v
    StrategyContext
          |
          v
    Strategy


============================================================

原则：

策略禁止直接访问：

    OrderBook
    FeatureEngine
    Portfolio
    Risk


只能读取：

    StrategyContext


============================================================
"""


from dataclasses import dataclass, field
from typing import Optional, Dict



# ============================================================
# OrderBook Context
# ============================================================


@dataclass
class OrderBookContext:


    best_bid: Optional[int] = None

    best_ask: Optional[int] = None


    bid_size: int = 0

    ask_size: int = 0


    spread: int = 0


    depth: Dict = field(
        default_factory=dict
    )


    active_orders: int = 0





# ============================================================
# Feature Context
# ============================================================


@dataclass
class FeatureContext:


    # -------------------------
    # Price
    # -------------------------

    mid_price: Optional[float] = None

    micro_price: Optional[float] = None



    # -------------------------
    # OrderBook
    # -------------------------

    obi: float = 0.0

    queue_imbalance: float = 0.0


    ofi: float = 0.0




    # -------------------------
    # Trade Flow
    # -------------------------

    trade_volume: int = 0


    aggressive_buy_volume: int = 0


    aggressive_sell_volume: int = 0


    trade_imbalance: float = 0.0




    # -------------------------
    # Absorption
    # -------------------------

    absorption_ratio: float = 0.0


    passive_refill: float = 0.0





    # -------------------------
    # Volatility
    # -------------------------

    volatility: float = 0.0



    extra: Dict = field(
        default_factory=dict
    )





# ============================================================
# Regime Context
# ============================================================


@dataclass
class RegimeContext:


    UNKNOWN = "UNKNOWN"

    RANGE = "RANGE"

    TREND = "TREND"

    VOLATILE = "VOLATILE"

    LIQUIDITY = "LIQUIDITY"



    name: str = UNKNOWN



    trending: bool = False


    ranging: bool = False


    high_volatility: bool = False


    liquidity_event: bool = False



    extra: Dict = field(
        default_factory=dict
    )





# ============================================================
# Position Context
# ============================================================


@dataclass
class PositionContext:


    symbol: Optional[str] = None


    quantity: int = 0


    side: str = "FLAT"



    entry_price: float = 0.0


    holding_time: int = 0



    unrealized_pnl: float = 0.0


    realized_pnl: float = 0.0






# ============================================================
# Risk Context
# ============================================================


@dataclass
class RiskContext:


    allowed: bool = True


    kill_switch: bool = False


    current_exposure: float = 0.0


    max_exposure: float = 0.0






# ============================================================
# Strategy Context
# ============================================================


@dataclass
class StrategyContext:


    timestamp: int = 0


    symbol: Optional[str] = None



    orderbook: OrderBookContext = field(
        default_factory=OrderBookContext
    )


    features: FeatureContext = field(
        default_factory=FeatureContext
    )


    regime: RegimeContext = field(
        default_factory=RegimeContext
    )



    position: PositionContext = field(
        default_factory=PositionContext
    )


    risk: RiskContext = field(
        default_factory=RiskContext
    )



    metadata: Dict = field(
        default_factory=dict
    )




    def can_trade(self):

        return (
            self.risk.allowed
            and
            not self.risk.kill_switch
        )



    def is_long(self):

        return self.position.side == "LONG"



    def is_short(self):

        return self.position.side == "SHORT"



    def is_flat(self):

        return self.position.side == "FLAT"




    def reset(self):


        self.orderbook = OrderBookContext()

        self.features = FeatureContext()

        self.regime = RegimeContext()

        self.position = PositionContext()

        self.risk = RiskContext()

        self.metadata.clear()