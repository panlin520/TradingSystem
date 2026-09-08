"""
features/engine.py

============================================================
Feature Engine
============================================================

职责：

    L3市场微观结构特征计算。


输入：

    OrderBook


输出：

    Feature Snapshot



============================================================


计算：

    Best Bid

    Best Ask

    Spread

    Mid Price

    Micro Price

    Bid Volume

    Ask Volume

    Order Imbalance



============================================================


原则：

Feature Engine:

    读取 OrderBook


不负责：

    - 修改Book

    - 策略判断

    - 下单


============================================================

"""


from dataclasses import dataclass
from typing import Optional



from orderbook.book import OrderBook




# ============================================================
# Feature Snapshot
# ============================================================

@dataclass(slots=True)
class FeatureSnapshot:
    """
    市场特征快照。


    一个snapshot代表：

    当前一个时间点的市场状态。



    """



    # ========================================================
    # 盘口价格
    # ========================================================

    best_bid: Optional[int]

    best_ask: Optional[int]



    # ========================================================
    # Spread
    # ========================================================

    spread: Optional[int]



    # ========================================================
    # Mid Price
    # ========================================================

    mid_price: Optional[float]



    # ========================================================
    # Micro Price
    # ========================================================

    micro_price: Optional[float]



    # ========================================================
    # Volume
    # ========================================================

    bid_volume: int


    ask_volume: int



    # ========================================================
    # Order Imbalance
    # ========================================================

    imbalance: Optional[float]



    # ========================================================
    # Event Timestamp
    # ========================================================

    timestamp: Optional[int] = None





# ============================================================
# Feature Engine
# ============================================================

class FeatureEngine:
    """
    L3 Feature计算引擎。



    """



    def __init__(
        self,
        orderbook: OrderBook
    ):

        self.orderbook = orderbook



        self.last_snapshot: Optional[
            FeatureSnapshot
        ] = None




    # ========================================================
    # 更新Feature
    # ========================================================

    def update(
        self,
        timestamp: Optional[int] = None
    ) -> FeatureSnapshot:
        """
        从当前OrderBook计算特征。


        """



        book = self.orderbook



        snapshot = FeatureSnapshot(


            best_bid=
                book.best_bid(),



            best_ask=
                book.best_ask(),



            spread=
                book.spread(),



            mid_price=
                book.mid_price(),



            micro_price=
                book.micro_price(),



            bid_volume=
                book.bid_volume(),



            ask_volume=
                book.ask_volume(),



            imbalance=
                book.imbalance(),



            timestamp=
                timestamp,

        )



        self.last_snapshot = snapshot



        return snapshot




    # ========================================================
    # 获取最新状态
    # ========================================================

    def get_latest(
        self
    ) -> Optional[FeatureSnapshot]:
        """
        返回最近一次计算结果。

        """

        return self.last_snapshot




    # ========================================================
    # 字典输出
    # ========================================================

    def to_dict(
        self
    ) -> dict:
        """
        转换为Web/API格式。


        """

        if self.last_snapshot is None:

            return {}



        return {


            "best_bid":
                self.last_snapshot.best_bid,


            "best_ask":
                self.last_snapshot.best_ask,


            "spread":
                self.last_snapshot.spread,


            "mid_price":
                self.last_snapshot.mid_price,


            "micro_price":
                self.last_snapshot.micro_price,


            "bid_volume":
                self.last_snapshot.bid_volume,


            "ask_volume":
                self.last_snapshot.ask_volume,


            "imbalance":
                self.last_snapshot.imbalance,


            "timestamp":
                self.last_snapshot.timestamp,

        }