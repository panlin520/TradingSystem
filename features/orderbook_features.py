"""
features/orderbook_features.py


============================================================
OrderBook Features
============================================================


职责：

    从 L3 OrderBook 中提取盘口微观结构特征。



数据流：

    OrderBook
        |
        ↓
    OrderBookFeatures
        |
        ↓
    FeatureSnapshot



============================================================

负责：

    - 最优买卖价
    - Spread
    - Mid Price
    - Micro Price
    - Depth
    - OBI
    - Queue Pressure


============================================================

不负责：

    - 成交分析
    - 订单流分析
    - 策略信号
    - 风控


============================================================

"""


from typing import Optional



from features.snapshot import FeatureSnapshot




class OrderBookFeatures:
    """
    OrderBook 特征计算器。



    注意：

        不保存 OrderBook 状态。


        每次调用：

            calculate(book)

        都基于当前盘口重新计算。


    """



    def __init__(
        self,
        depth_levels: int = 10
    ):


        # ==================================================
        # 计算深度档位
        # ==================================================

        self.depth_levels = depth_levels





    # ======================================================
    # 主入口
    # ======================================================


    def calculate(
        self,
        book,
        snapshot: Optional[FeatureSnapshot] = None
    ):
        """
        根据当前 OrderBook 生成盘口特征。


        参数：

            book:
                orderbook.book.OrderBook


            snapshot:
                已存在 FeatureSnapshot


        返回：

            FeatureSnapshot


        """



        if snapshot is None:

            snapshot = FeatureSnapshot()



        # ==================================================
        # Top Of Book
        # ==================================================

        bid = self._best_bid(book)

        ask = self._best_ask(book)



        snapshot.best_bid = bid

        snapshot.best_ask = ask




        # ==================================================
        # Spread
        # ==================================================

        if (
            bid is not None
            and ask is not None
        ):

            snapshot.spread = ask - bid



        # ==================================================
        # Mid Price
        # ==================================================

        snapshot.mid_price = (
            self._mid_price(
                bid,
                ask
            )
        )



        # ==================================================
        # Volume
        # ==================================================

        snapshot.bid_volume = (
            self._side_volume(
                book,
                "bid"
            )
        )


        snapshot.ask_volume = (
            self._side_volume(
                book,
                "ask"
            )
        )



        # ==================================================
        # Depth
        # ==================================================

        snapshot.bid_depth_5 = (
            self._depth(
                book,
                "bid",
                5
            )
        )


        snapshot.ask_depth_5 = (
            self._depth(
                book,
                "ask",
                5
            )
        )



        snapshot.bid_depth_10 = (
            self._depth(
                book,
                "bid",
                10
            )
        )


        snapshot.ask_depth_10 = (
            self._depth(
                book,
                "ask",
                10
            )
        )



        # ==================================================
        # Micro Price
        # ==================================================

        snapshot.micro_price = (
            self._micro_price(
                bid,
                ask,
                snapshot.bid_volume,
                snapshot.ask_volume
            )
        )



        if (
            snapshot.mid_price is not None
            and snapshot.micro_price is not None
        ):

            snapshot.micro_price_delta = (
                snapshot.micro_price
                -
                snapshot.mid_price
            )



        # ==================================================
        # Order Book Imbalance
        # ==================================================

        snapshot.obi = (
            self._obi(
                snapshot.bid_volume,
                snapshot.ask_volume
            )
        )



        # ==================================================
        # Queue Pressure
        # ==================================================

        snapshot.queue_pressure = (
            snapshot.obi
        )



        return snapshot





    # ======================================================
    # Best Bid / Ask
    # ======================================================


    def _best_bid(
        self,
        book
    ):

        """
        获取最高买价。


        """

        try:

            return book.best_bid()


        except AttributeError:

            return None





    def _best_ask(
        self,
        book
    ):

        """
        获取最低卖价。


        """

        try:

            return book.best_ask()


        except AttributeError:

            return None





    # ======================================================
    # Mid Price
    # ======================================================


    def _mid_price(
        self,
        bid,
        ask
    ):

        if (
            bid is None
            or ask is None
        ):

            return None



        return (
            bid
            +
            ask
        ) / 2





    # ======================================================
    # Micro Price
    # ======================================================


    def _micro_price(
        self,
        bid,
        ask,
        bid_volume,
        ask_volume
    ):

        """
        Micro Price:

        MP =
        (Ask * BidVolume +
         Bid * AskVolume)
        /
        (BidVolume + AskVolume)



        反映盘口压力后的公平价格。



        """



        if (
            bid is None
            or ask is None
        ):

            return None



        total = (
            bid_volume
            +
            ask_volume
        )


        if total == 0:

            return (
                bid
                +
                ask
            ) / 2



        return (
            ask * bid_volume
            +
            bid * ask_volume
        ) / total





    # ======================================================
    # Volume
    # ======================================================


    def _side_volume(
        self,
        book,
        side
    ):


        try:


            if side == "bid":

                return book.bid_volume()



            else:

                return book.ask_volume()



        except AttributeError:


            return 0





    # ======================================================
    # Depth
    # ======================================================


    def _depth(
        self,
        book,
        side,
        levels
    ):

        """
        计算前 N 档深度。



        """

        total = 0



        try:


            if side == "bid":

                prices = sorted(
                    book.bids.keys(),
                    reverse=True
                )


            else:

                prices = sorted(
                    book.asks.keys()
                )



            for price in prices[:levels]:

                level = (
                    book.bids[price]
                    if side == "bid"
                    else book.asks[price]
                )


                total += level.volume



        except Exception:


            return 0



        return total





    # ======================================================
    # OBI
    # ======================================================


    def _obi(
        self,
        bid_volume,
        ask_volume
    ):

        """
        Order Book Imbalance


        OBI:

            (Bid - Ask)
            /
            (Bid + Ask)



        范围:

            -1 ~ +1



        """



        total = (
            bid_volume
            +
            ask_volume
        )



        if total == 0:

            return 0.0



        return (
            bid_volume
            -
            ask_volume
        ) / total