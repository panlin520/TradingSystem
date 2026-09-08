"""
features/trade_features.py


============================================================
Trade Features
============================================================


职责：

    从市场成交事件中提取成交行为特征。



数据流：

    MBO Trade Event

            |
            ↓

    TradeFeatures

            |
            ↓

    FeatureSnapshot



============================================================

负责：

    - 成交数量统计
    - 成交方向统计
    - 主动买卖统计
    - Trade Imbalance
    - 成交强度


============================================================

不负责：

    - OrderBook维护
    - 订单流计算
    - 策略判断
    - 风控


============================================================

"""


from typing import Optional


from features.snapshot import FeatureSnapshot




class TradeFeatures:
    """
    成交特征计算器。


    注意：

        当前版本处理单个 MarketEvent。


        历史累计统计由 FeatureEngine 管理。


    """



    def __init__(self):
        pass




    # ======================================================
    # 主入口
    # ======================================================


    def update(
        self,
        event,
        snapshot: Optional[FeatureSnapshot] = None
    ):
        """
        使用一个成交事件更新 FeatureSnapshot。


        参数：

            event:

                MarketEvent


            snapshot:

                当前特征快照


        返回：

            FeatureSnapshot


        """



        if snapshot is None:

            snapshot = FeatureSnapshot()



        # ==================================================
        # 只处理成交事件
        # ==================================================

        if not self._is_trade(event):

            return snapshot




        # ==================================================
        # 基础成交信息
        # ==================================================

        snapshot.last_trade_price = (
            event.price
        )


        snapshot.last_trade_size = (
            event.size
            or 0
        )



        snapshot.trade_count += 1



        snapshot.trade_volume += (
            event.size
            or 0
        )





        # ==================================================
        # 主动方向判断
        # ==================================================

        aggressor = (
            self._detect_aggressor(
                event
            )
        )



        if aggressor == "BUY":

            snapshot.aggressive_buy_volume += (
                event.size
                or 0
            )



        elif aggressor == "SELL":

            snapshot.aggressive_sell_volume += (
                event.size
                or 0
            )




        # ==================================================
        # Trade Imbalance
        # ==================================================

        snapshot.trade_imbalance = (
            self._trade_imbalance(
                snapshot.aggressive_buy_volume,
                snapshot.aggressive_sell_volume
            )
        )



        return snapshot





    # ======================================================
    # 判断成交事件
    # ======================================================


    def _is_trade(
        self,
        event
    ):
        """
        判断是否成交。


        Databento MBO:

            Action = T


        """



        try:

            return (
                event.action.value
                ==
                "T"
            )


        except Exception:

            return False





    # ======================================================
    # 主动方向判断
    # ======================================================


    def _detect_aggressor(
        self,
        event
    ):
        """
        判断主动买卖。


        CME MBO:

        T事件本身通常不直接提供 aggressor。


        需要结合：

            trade price
            best bid
            best ask


        当前保留接口。


        后续 FeatureEngine
        会传入盘口状态。


        """


        side = getattr(
            event,
            "side",
            None
        )



        if side is None:

            return None



        value = getattr(
            side,
            "value",
            side
        )



        if value in (
            "B",
            "BUY"
        ):

            return "BUY"



        if value in (
            "A",
            "ASK",
            "SELL"
        ):

            return "SELL"



        return None





    # ======================================================
    # Trade Imbalance
    # ======================================================


    def _trade_imbalance(
        self,
        buy_volume,
        sell_volume
    ):
        """
        Trade Imbalance:


            (Buy - Sell)
            /
            (Buy + Sell)



        范围:

            -1 ~ +1


        """



        total = (
            buy_volume
            +
            sell_volume
        )



        if total == 0:

            return 0.0



        return (
            buy_volume
            -
            sell_volume
        ) / total





    # ======================================================
    # Average Trade Size
    # ======================================================


    def average_trade_size(
        self,
        snapshot: FeatureSnapshot
    ):
        """
        平均成交大小。



        """

        if snapshot.trade_count == 0:

            return 0



        return (
            snapshot.trade_volume
            /
            snapshot.trade_count
        )





    # ======================================================
    # Buy Sell Ratio
    # ======================================================


    def buy_sell_ratio(
        self,
        snapshot: FeatureSnapshot
    ):
        """
        主动买卖比例。


        """



        sell = (
            snapshot.aggressive_sell_volume
        )



        if sell == 0:

            return 0



        return (
            snapshot.aggressive_buy_volume
            /
            sell
        )