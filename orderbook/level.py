"""
orderbook/level.py

============================================================
Price Level Management
============================================================

职责：

    管理订单簿中的一个价格层。


例如：

    ES


    Bid

    6959.75

        Order A

        Order B

        Order C



一个 PriceLevel 对应：

    一个价格

    一个FIFO订单队列



============================================================


核心规则：

    同一个价格：

        sequence越小

        越靠前



即：

    FIFO


============================================================


不负责：

    - 价格排序

    - 买卖方向判断

    - 撮合

    - 策略


这些由：

    OrderBook

负责。


============================================================

"""


from collections import OrderedDict
from typing import Optional, Iterator


from orderbook.order import Order



# ============================================================
# Price Level
# ============================================================

class PriceLevel:
    """
    单个价格层。


    例如：


        Bid 6959.75


        Queue:


        order1
        order2
        order3



    """



    def __init__(
        self,
        price: int
    ):

        """
        创建价格层。


        """

        self.price = price



        # ====================================================
        # FIFO订单队列
        #
        # key:
        #       order_id
        #
        # value:
        #       Order
        #
        #
        # Python 3.7+
        # dict保持插入顺序
        #
        # ====================================================

        self.orders = OrderedDict()



        # ====================================================
        # 总数量
        # ====================================================

        self.volume = 0



    # ========================================================
    # 添加订单
    # ========================================================

    def add_order(
        self,
        order: Order
    ):
        """
        添加订单到FIFO尾部。


        对应：

            Databento A


        """

        if order.order_id in self.orders:

            raise ValueError(
                f"Order already exists {order.order_id}"
            )


        self.orders[
            order.order_id
        ] = order



        self.volume += order.size



    # ========================================================
    # 删除订单
    # ========================================================

    def remove_order(
        self,
        order_id: int
    ) -> Optional[Order]:
        """
        删除订单。


        对应：

            Databento C


        """

        order = self.orders.pop(
            order_id,
            None
        )


        if order:

            self.volume -= order.size



        return order



    # ========================================================
    # 修改订单
    # ========================================================

    def modify_order(
        self,
        order_id: int,
        new_size: int
    ):
        """
        修改订单数量。


        对应：

            Databento M



        """

        order = self.orders.get(
            order_id
        )


        if order is None:

            return



        old_size = order.size



        order.modify(
            new_size
        )


        self.volume += (
            order.size
            -
            old_size
        )



    # ========================================================
    # 获取第一个订单
    # ========================================================

    def first_order(
        self
    ) -> Optional[Order]:
        """
        获取FIFO队首订单。


        用于：

        成交模拟

        Queue Position



        """

        if not self.orders:

            return None



        return next(
            iter(
                self.orders.values()
            )
        )



    # ========================================================
    # 获取最后订单
    # ========================================================

    def last_order(
        self
    ) -> Optional[Order]:
        """
        获取队尾订单。


        """

        if not self.orders:

            return None


        return next(
            reversed(
                self.orders.values()
            )
        )



    # ========================================================
    # 查询订单
    # ========================================================

    def get_order(
        self,
        order_id: int
    ) -> Optional[Order]:
        """
        根据order_id查询订单。


        """

        return self.orders.get(
            order_id
        )



    # ========================================================
    # 队列长度
    # ========================================================

    def order_count(
        self
    ) -> int:
        """
        当前价格订单数量。

        """

        return len(
            self.orders
        )



    # ========================================================
    # Queue Position
    # ========================================================

    def queue_position(
        self,
        order_id: int
    ) -> Optional[int]:
        """
        查询订单排队位置。


        返回：

        0:

            当前最前


        1:

            第二个



        """

        for index, oid in enumerate(
            self.orders.keys()
        ):

            if oid == order_id:

                return index



        return None



    # ========================================================
    # 迭代
    # ========================================================

    def __iter__(
        self
    ) -> Iterator[Order]:
        """
        FIFO遍历订单。

        """

        return iter(
            self.orders.values()
        )



    # ========================================================
    # 是否为空
    # ========================================================

    def empty(
        self
    ) -> bool:
        """
        是否没有订单。

        """

        return len(
            self.orders
        ) == 0



    # ========================================================
    # 清空
    # ========================================================

    def clear(
        self
    ):
        """
        清空价格层。

        """

        self.orders.clear()


        self.volume = 0



    # ========================================================
    # Debug
    # ========================================================

    def snapshot(
        self
    ) -> dict:
        """
        返回价格层状态。

        """

        return {

            "price":
                self.price,


            "volume":
                self.volume,


            "orders":
                len(self.orders),

        }