"""
tests/test_orderbook_reference.py


============================================================
OrderBook Reference Test
============================================================


目的：

使用一个独立的简单 OrderBook 实现

作为参考模型。


验证：

Databento MBO
        |
        v

OrderBookBuilder
        |
        v

正式 OrderBook


是否和参考结果一致。


============================================================


注意：

这里不是测试代码运行。

而是测试：

结果一致性。


============================================================

"""


from pathlib import Path

import pytest


from data.databento_feed import DatabentoFeed

from orderbook.builder import OrderBookBuilder



# ============================================================
# 测试数据
# ============================================================


TEST_DATA = (
    Path("data")
    /
    "ESU6_2026-06-15_MBO.dbn.zst"
)



# ============================================================
# Side 判断
#
# Databento MBO:
#
# B / A
# BUY / SELL
#
# ============================================================


def is_bid(side):

    return (
        getattr(
            side,
            "value",
            None
        )
        ==
        "B"

        or

        getattr(
            side,
            "name",
            ""
        )
        in (
            "BUY",
            "BID"
        )
    )



def is_ask(side):

    return (
        getattr(
            side,
            "value",
            None
        )
        ==
        "A"

        or

        getattr(
            side,
            "name",
            ""
        )
        in (
            "SELL",
            "ASK"
        )
    )



# ============================================================
# 简化参考订单簿
#
# 注意：
#
# 不复用正式 OrderBook
#
# ============================================================


class ReferenceOrderBook:


    def __init__(self):

        # order_id -> order

        self.orders = {}


        # trade统计

        self.trade_count = 0



    # ========================================================
    # Apply Event
    # ========================================================


    def apply(
        self,
        event
    ):


        action = event.action.value



        # ----------------------------------------------------
        # Add
        # ----------------------------------------------------

        if action == "A":


            if event.order_id is None:

                return



            self.orders[
                event.order_id
            ] = {

                "side":
                    event.side,

                "price":
                    event.price,

                "size":
                    event.size
            }



        # ----------------------------------------------------
        # Modify
        # ----------------------------------------------------

        elif action == "M":


            if event.order_id not in self.orders:

                return



            order = self.orders[
                event.order_id
            ]



            if event.price is not None:

                order["price"] = event.price



            if event.size is not None:

                order["size"] = event.size



            if event.side is not None:

                order["side"] = event.side



        # ----------------------------------------------------
        # Cancel
        # ----------------------------------------------------

        elif action == "C":


            if event.order_id in self.orders:

                del self.orders[
                    event.order_id
                ]



        # ----------------------------------------------------
        # Reset
        # ----------------------------------------------------

        elif action == "R":


            self.orders.clear()



        # ----------------------------------------------------
        # Trade
        # ----------------------------------------------------

        elif action == "T":


            self.trade_count += 1




    # ========================================================
    # Best Bid
    # ========================================================


    def best_bid(self):


        prices = [

            order["price"]

            for order
            in self.orders.values()

            if is_bid(
                order["side"]
            )

        ]


        if not prices:

            return None


        return max(
            prices
        )



    # ========================================================
    # Best Ask
    # ========================================================


    def best_ask(self):


        prices = [

            order["price"]

            for order
            in self.orders.values()

            if is_ask(
                order["side"]
            )

        ]


        if not prices:

            return None


        return min(
            prices
        )



    # ========================================================
    # Bid Volume
    # ========================================================


    def bid_volume(self):


        return sum(

            order["size"]

            for order
            in self.orders.values()

            if is_bid(
                order["side"]
            )

        )



    # ========================================================
    # Ask Volume
    # ========================================================


    def ask_volume(self):


        return sum(

            order["size"]

            for order
            in self.orders.values()

            if is_ask(
                order["side"]
            )

        )



# ============================================================
# 数据检查
# ============================================================


def check_data():


    if not TEST_DATA.exists():

        pytest.skip(
            f"Databento file not found:{TEST_DATA}"
        )



# ============================================================
# 核心测试
# ============================================================


def test_reference_orderbook_match():


    check_data()



    feed = DatabentoFeed(
        str(TEST_DATA)
    )



    builder = OrderBookBuilder()



    reference = ReferenceOrderBook()



    count = 0



    LIMIT = 50000



    for event in feed:



        # ====================================================
        # 正式系统
        # ====================================================


        builder.on_event(
            event
        )



        # ====================================================
        # 独立参考系统
        # ====================================================


        reference.apply(
            event
        )



        count += 1



        book = builder.get_book()



        # ====================================================
        #
        # 每个事件比较
        #
        # OrderBook
        #
        #       VS
        #
        # ReferenceOrderBook
        #
        # ====================================================


        assert (

            book.best_bid()

            ==

            reference.best_bid()

        )



        assert (

            book.best_ask()

            ==

            reference.best_ask()

        )



        assert (

            book.bid_volume()

            ==

            reference.bid_volume()

        )



        assert (

            book.ask_volume()

            ==

            reference.ask_volume()

        )



        assert (

            len(
                book.orders
            )

            ==

            len(
                reference.orders
            )

        )



        if count >= LIMIT:

            break




    print()

    print("=" * 60)

    print(
        "REFERENCE TEST PASSED"
    )

    print("=" * 60)


    print(
        "events:",
        count
    )


    print(
        "orders:",
        len(
            builder.book.orders
        )
    )


    print(
        "trades:",
        builder.book.trade_count
    )


    print("=" * 60)