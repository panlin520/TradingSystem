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

    FeatureSnapshot



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


from typing import Optional


from orderbook.book import OrderBook


from features.snapshot import FeatureSnapshot





# ============================================================
# Feature Engine
# ============================================================


class FeatureEngine:
    """
    L3 Feature计算引擎。



    负责：

        OrderBook

            ↓

        FeatureSnapshot



    不负责：

        Strategy

        Risk

        Execution



    """



    def __init__(
        self,
        orderbook: OrderBook
    ):

        self.orderbook = orderbook



        # 最近一次Feature Snapshot

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



        参数：

            timestamp:

                当前事件时间



        返回：

            FeatureSnapshot



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



            obi=
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



        return self.last_snapshot.to_dict()