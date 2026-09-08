"""
orderbook/book.py


============================================================
L3 OrderBook
============================================================


职责：

    维护完整 L3 订单簿状态。


数据来源：

    Databento MBO


支持：

    A:
        Add Order

    M:
        Modify Order

    C:
        Cancel Order

    R:
        Reset


============================================================


核心结构：


Bid
 |
 |-- PriceLevel
       |
       |-- Order
       |-- Order
       |-- Order


Ask
 |
 |-- PriceLevel
       |
       |-- Order
       |-- Order
       |-- Order


============================================================


核心原则：


1.

所有订单通过 order_id 管理。


2.

PriceLevel 负责 FIFO。


3.

OrderBook 负责：

    - 价格层管理
    - 买卖方向
    - order索引
    - best bid/ask


4.

order_id 在整个活动 OrderBook 中必须唯一。


5.

任何会破坏：

    book.orders

与：

    bids / asks -> PriceLevel.orders

一致性的操作必须被拒绝。


============================================================
"""


from typing import Dict, Optional


from orderbook.order import (
    Order,
    OrderSide,
)


from orderbook.level import (
    PriceLevel,
)



# ============================================================
# OrderBook
# ============================================================


class OrderBook:
    """
    L3 OrderBook。


    保存：

        所有活动订单。


    核心索引：

        self.orders

            order_id -> Order


    价格结构：

        self.bids

            price -> PriceLevel


        self.asks

            price -> PriceLevel
    """


    def __init__(
        self
    ):


        # ====================================================
        # Bid价格层
        #
        # price -> PriceLevel
        #
        # ====================================================

        self.bids: Dict[int, PriceLevel] = {}


        # ====================================================
        # Ask价格层
        #
        # price -> PriceLevel
        #
        # ====================================================

        self.asks: Dict[int, PriceLevel] = {}


        # ====================================================
        # 全局订单索引
        #
        # order_id -> Order
        #
        # L3核心
        #
        # ====================================================

        self.orders: Dict[int, Order] = {}


        # ====================================================
        # 成交统计
        #
        # Trade事件使用
        #
        # Fill不重复统计
        #
        # ====================================================

        self.trade_count = 0

        self.trade_volume = 0



    # ========================================================
    # 获取价格层集合
    # ========================================================


    def _get_levels(
        self,
        side: OrderSide
    ):
        """
        根据 Side 返回：

            Bid levels

        或：

            Ask levels
        """


        if side == OrderSide.BID:

            return self.bids


        return self.asks



    # ========================================================
    # 添加订单
    # ========================================================


    def add_order(
        self,
        order: Order
    ):
        """
        Add Order


        Databento:

            A


        ====================================================

        重要规则：

        order_id 在活动 OrderBook 中必须唯一。


        如果收到重复：

            order_id

        直接拒绝。


        不允许：

            覆盖 self.orders

        同时让旧订单残留在：

            PriceLevel


        否则会导致：

            book.orders

        和：

            bids / asks

        内部状态不一致。


        ====================================================

        原子性原则：

        重复 order_id 的检查必须发生在：

            PriceLevel 创建

            PriceLevel.add_order()

        之前。


        这样发生异常时：

            OrderBook 完全不发生变化。

        ====================================================
        """


        # ====================================================
        # Duplicate Order ID Guard
        #
        # 必须在任何盘口修改之前执行
        # ====================================================

        if order.order_id in self.orders:

            raise ValueError(
                f"Order already exists: {order.order_id}"
            )


        # ====================================================
        # 获取 Bid / Ask 价格层
        # ====================================================

        levels = self._get_levels(
            order.side
        )


        # ====================================================
        # PriceLevel不存在则创建
        # ====================================================

        if order.price not in levels:


            levels[
                order.price
            ] = PriceLevel(
                order.price
            )


        # ====================================================
        # 加入FIFO价格层
        # ====================================================

        levels[
            order.price
        ].add_order(
            order
        )


        # ====================================================
        # 加入全局Order索引
        # ====================================================

        self.orders[
            order.order_id
        ] = order



    # ========================================================
    # 修改订单
    # ========================================================


    def modify_order(
        self,
        order_id: int,
        price: int,
        size: int,
        side: OrderSide
    ):
        """
        Modify Order


        Databento:

            M


        注意：

        M事件可能改变：

            1.
            size


            2.
            price


            3.
            side


        因此不能只修改：

            order.size


        如果：

            price

        或：

            side

        发生变化：

            必须从旧PriceLevel移除

            然后加入新的PriceLevel。


        ====================================================

        情况1：

            price未变化
            side未变化

        只修改size。


        ====================================================

        情况2：

            price变化

        或：

            side变化

        执行完整迁移。


        ====================================================
        """


        # ----------------------------------------------------
        # 查找订单
        # ----------------------------------------------------

        order = self.orders.get(
            order_id
        )


        if order is None:

            return


        old_price = order.price

        old_side = order.side


        # ----------------------------------------------------
        # 判断是否移动价格层
        # ----------------------------------------------------

        price_changed = (
            old_price != price
        )


        side_changed = (
            old_side != side
        )


        # ====================================================
        # 情况1：
        #
        # price / side 未变化
        #
        # 只修改数量
        #
        # ====================================================

        if not price_changed and not side_changed:


            level = self._get_levels(
                old_side
            ).get(
                old_price
            )


            if level:


                level.modify_order(
                    order_id,
                    size
                )


            return


        # ====================================================
        # 情况2：
        #
        # price 或 side变化
        #
        # 删除旧订单位置
        #
        # 创建新位置
        #
        # ====================================================


        old_levels = self._get_levels(
            old_side
        )


        old_level = old_levels.get(
            old_price
        )


        if old_level:


            old_level.remove_order(
                order_id
            )


            # =================================================
            # 如果旧PriceLevel已经为空
            # 删除整个Level
            # =================================================

            if old_level.empty():


                del old_levels[
                    old_price
                ]


        # ----------------------------------------------------
        # 更新Order对象
        # ----------------------------------------------------

        order.price = price

        order.side = side

        order.size = size


        # ----------------------------------------------------
        # 获取新的Side价格层
        # ----------------------------------------------------

        new_levels = self._get_levels(
            side
        )


        # ----------------------------------------------------
        # 新价格层不存在则创建
        # ----------------------------------------------------

        if price not in new_levels:


            new_levels[
                price
            ] = PriceLevel(
                price
            )


        # ----------------------------------------------------
        # 插入新的价格层
        # ----------------------------------------------------

        new_levels[
            price
        ].add_order(
            order
        )



    # ========================================================
    # 删除订单
    # ========================================================


    def cancel_order(
        self,
        order_id: int
    ):
        """
        Cancel Order


        Databento:

            C


        流程：

            1.
            从全局order索引删除

            2.
            找到对应PriceLevel

            3.
            从PriceLevel删除

            4.
            如果PriceLevel为空

                删除PriceLevel
        """


        order = self.orders.pop(
            order_id,
            None
        )


        if order is None:

            return


        levels = self._get_levels(
            order.side
        )


        level = levels.get(
            order.price
        )


        if level:


            level.remove_order(
                order_id
            )


            if level.empty():


                del levels[
                    order.price
                ]



    # ========================================================
    # Reset
    # ========================================================


    def clear(
        self
    ):
        """
        Reset Book。


        Databento:

            R


        清空：

            bids

            asks

            orders


        同时重置当前Book级成交统计：

            trade_count

            trade_volume
        """


        self.bids.clear()

        self.asks.clear()

        self.orders.clear()


        self.trade_count = 0

        self.trade_volume = 0



    # ========================================================
    # 查询 Best Bid
    # ========================================================


    def best_bid(
        self
    ) -> Optional[int]:
        """
        返回最高 Bid价格。
        """


        if not self.bids:

            return None


        return max(
            self.bids.keys()
        )



    # ========================================================
    # 查询 Best Ask
    # ========================================================


    def best_ask(
        self
    ) -> Optional[int]:
        """
        返回最低 Ask价格。
        """


        if not self.asks:

            return None


        return min(
            self.asks.keys()
        )



    # ========================================================
    # Mid Price
    # ========================================================


    def mid_price(
        self
    ) -> Optional[float]:
        """
        Mid Price:


            (Bid + Ask) / 2
        """


        bid = self.best_bid()

        ask = self.best_ask()


        if bid is None or ask is None:

            return None


        return (
            bid + ask
        ) / 2



    # ========================================================
    # Spread
    # ========================================================


    def spread(
        self
    ) -> Optional[int]:
        """
        Spread:


            Ask - Bid
        """


        bid = self.best_bid()

        ask = self.best_ask()


        if bid is None or ask is None:

            return None


        return ask - bid



    # ========================================================
    # Bid Volume
    # ========================================================


    def bid_volume(
        self
    ) -> int:
        """
        所有Bid挂单数量。
        """


        return sum(
            level.volume
            for level in self.bids.values()
        )



    # ========================================================
    # Ask Volume
    # ========================================================


    def ask_volume(
        self
    ) -> int:
        """
        所有Ask挂单数量。
        """


        return sum(
            level.volume
            for level in self.asks.values()
        )



    # ========================================================
    # Micro Price
    # ========================================================


    def micro_price(
        self
    ) -> Optional[float]:
        """
        Micro Price:


              Ask * BidSize
            +
              Bid * AskSize

        ---------------------

              BidSize + AskSize


        注意：

        这里只使用：

            Best Bid Level

            Best Ask Level

        的挂单数量。
        """


        bid = self.best_bid()

        ask = self.best_ask()


        if bid is None or ask is None:

            return None


        bid_level = self.bids.get(
            bid
        )


        ask_level = self.asks.get(
            ask
        )


        if bid_level is None or ask_level is None:

            return None


        bid_size = bid_level.volume

        ask_size = ask_level.volume


        if bid_size + ask_size == 0:

            return None


        return (

            ask * bid_size

            +

            bid * ask_size

        ) / (

            bid_size + ask_size

        )



    # ========================================================
    # Order Imbalance
    # ========================================================


    def imbalance(
        self
    ) -> Optional[float]:
        """
        Order Imbalance:


             BidVolume - AskVolume

        ---------------------------

             BidVolume + AskVolume
        """


        bid = self.bid_volume()

        ask = self.ask_volume()


        if bid + ask == 0:

            return None


        return (

            bid - ask

        ) / (

            bid + ask

        )



    # ========================================================
    # Snapshot
    # ========================================================


    def snapshot(
        self
    ) -> dict:
        """
        返回盘口状态。
        """


        return {


            "best_bid":

                self.best_bid(),


            "best_ask":

                self.best_ask(),


            "mid":

                self.mid_price(),


            "spread":

                self.spread(),


            "bid_volume":

                self.bid_volume(),


            "ask_volume":

                self.ask_volume(),


            "orders":

                len(self.orders),


            "trade_count":

                self.trade_count,


            "trade_volume":

                self.trade_volume,

        }