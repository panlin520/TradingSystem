"""
features/snapshot.py

============================================================
Feature Snapshot
============================================================

职责：

    保存市场微观结构特征状态。

数据流：

    MarketEvent
        ↓
    FeatureEngine
        ↓
    FeatureSnapshot
        ↓
    Strategy / Risk / Exit

============================================================

负责：

    - 盘口特征
    - 成交特征
    - Order Flow特征
    - Liquidity特征
    - Directional OFI
    - Market Regime状态
    - 额外诊断信息

不负责：

    - 修改OrderBook
    - 计算策略信号
    - Risk
    - Execution

============================================================

重要：

    ofi

        现在定义为：

            Directional Order Flow Imbalance

        Positive Flow：

            Bid Add
            Ask Remove

        Negative Flow：

            Ask Add
            Bid Remove


    liquidity_balance

        单独表示：

            Liquidity Added / Removed Balance

        与directional OFI不是同一个指标。

============================================================
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FeatureSnapshot:
    """
    市场微观结构特征快照。

    当前对象会由FeatureEngine持续更新。

    Strategy如果需要保存历史状态，
    应调用：

        snapshot.copy()
    """

    # ======================================================
    # 基础市场信息
    # ======================================================

    timestamp: int = 0

    sequence: int = 0

    symbol: str = ""

    # ======================================================
    # Top Of Book
    # ======================================================

    best_bid: Optional[int] = None

    best_ask: Optional[int] = None

    spread: Optional[int] = None

    # ======================================================
    # Price Metrics
    # ======================================================

    mid_price: Optional[float] = None

    micro_price: Optional[float] = None

    micro_price_delta: Optional[float] = None

    # ======================================================
    # OrderBook Depth
    # ======================================================

    bid_volume: int = 0

    ask_volume: int = 0

    bid_depth_5: int = 0

    ask_depth_5: int = 0

    bid_depth_10: int = 0

    ask_depth_10: int = 0

    # ======================================================
    # OrderBook Imbalance
    # ======================================================

    obi: float = 0.0

    # ======================================================
    # Trade Information
    # ======================================================

    last_trade_price: Optional[int] = None

    last_trade_size: int = 0

    trade_count: int = 0

    trade_volume: int = 0

    # ======================================================
    # Aggressor Flow
    # ======================================================

    aggressive_buy_volume: int = 0

    aggressive_sell_volume: int = 0

    trade_imbalance: float = 0.0

    # ======================================================
    # Raw Order Flow
    #
    # 保留原接口。
    # ======================================================

    add_volume: int = 0

    cancel_volume: int = 0

    # 注意：
    #
    # modify_volume继续表示：
    #
    #     所有M事件中的event.size累计
    #
    # 它不是Modify真实delta。
    #
    # 真正delta使用：
    #
    #     modify_added_volume
    #     modify_removed_volume
    #
    modify_volume: int = 0

    # ======================================================
    # Directional Order Flow
    # ======================================================

    # Bid新增挂单
    bid_added_volume: int = 0

    # Bid撤掉/减少
    bid_removed_volume: int = 0

    # Ask新增挂单
    ask_added_volume: int = 0

    # Ask撤掉/减少
    ask_removed_volume: int = 0

    # ======================================================
    # Modify Delta
    # ======================================================

    # M导致订单数量增加的真实delta
    modify_added_volume: int = 0

    # M导致订单数量减少的真实delta
    modify_removed_volume: int = 0

    # ======================================================
    # Modify Price Migration
    # ======================================================

    # M改变价格的次数
    price_move_count: int = 0

    # Price Move在新价格层加入的数量
    price_move_added_volume: int = 0

    # Price Move从旧价格层移除的数量
    price_move_removed_volume: int = 0

    # ======================================================
    # Signed Order Flow
    #
    # Positive:
    #
    #     Bid Add
    #     Ask Remove
    #
    # Negative:
    #
    #     Ask Add
    #     Bid Remove
    #
    # ======================================================

    signed_order_flow: int = 0

    # ======================================================
    # Directional OFI
    #
    # signed_order_flow
    # ------------------------------
    # total directional activity
    #
    # 范围：
    #
    #     -1.0 ~ +1.0
    #
    # ======================================================

    ofi: float = 0.0

    # ======================================================
    # Liquidity
    # ======================================================

    liquidity_added: int = 0

    liquidity_removed: int = 0

    # ======================================================
    # Liquidity Balance
    #
    # (Added - Removed)
    # -----------------
    # (Added + Removed)
    #
    # 注意：
    #
    #     这不是directional OFI。
    #
    # ======================================================

    liquidity_balance: float = 0.0

    # ======================================================
    # Queue / Replenishment
    # ======================================================

    queue_pressure: float = 0.0

    replenishment: int = 0

    # ======================================================
    # Market Regime
    # ======================================================

    spread_regime: str = "UNKNOWN"

    volatility_regime: str = "UNKNOWN"

    # ======================================================
    # Metadata
    # ======================================================

    extra: dict = field(
        default_factory=dict
    )

    # ======================================================
    # Copy
    # ======================================================

    def copy(self):
        """
        创建独立快照副本。

        extra同时复制，
        防止历史Snapshot共享同一个extra字典。
        """

        data = self.__dict__.copy()

        data["extra"] = self.extra.copy()

        return FeatureSnapshot(
            **data
        )

    # ======================================================
    # Dict
    # ======================================================

    def to_dict(self):
        """
        转换为dict。

        用于：

            CSV
            Excel
            Backtest
            Web
            Debug
        """

        data = self.__dict__.copy()

        data["extra"] = self.extra.copy()

        return data

    # ======================================================
    # Repr
    # ======================================================

    def __repr__(self):
        """
        简洁显示。
        """

        return (
            f"FeatureSnapshot("
            f"{self.symbol} "
            f"seq={self.sequence} "
            f"bid={self.best_bid} "
            f"ask={self.best_ask} "
            f"mid={self.mid_price}"
            f")"
        )