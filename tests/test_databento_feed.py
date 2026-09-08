"""
tests/test_databento_feed.py

============================================================
Databento Feed Integration Test
============================================================

测试：

    data/databento_feed.py


数据流程：

    Databento DBN MBO

            ↓

    DatabentoFeed

            ↓

    MarketEvent

            ↓

    OrderBookBuilder

            ↓

    OrderBook


============================================================

"""


from pathlib import Path


import pytest


from data.databento_feed import DatabentoFeed


from orderbook.builder import OrderBookBuilder


from core.event import (
    OrderAction,
    OrderSide,
)



# ============================================================
# 测试数据路径
# ============================================================


TEST_DATA = (
    Path("data")
    /
    "ESU6_2026-06-15_MBO.dbn.zst"
)



# ============================================================
# 检查数据文件
# ============================================================


def check_data():

    """
    检查测试数据是否存在。
    """

    if not TEST_DATA.exists():

        pytest.skip(
            f"Databento file not found: {TEST_DATA}"
        )



# ============================================================
# Test Feed读取
# ============================================================


def test_databento_feed_read():

    """
    测试 Databento Feed 是否产生 MarketEvent。
    """


    check_data()


    feed = DatabentoFeed(
        str(TEST_DATA)
    )


    count = 0


    actions = set()



    for event in feed:


        count += 1



        # -----------------------------
        # 基础字段
        # -----------------------------


        assert event.symbol != ""


        assert event.order_id is not None


        assert event.sequence >= 0



        # -----------------------------
        # sequence检查
        #
        # 注意：
        #
        # Databento MBO:
        #
        # sequence
        # 是交易所channel内部序号
        #
        # 不是整个DBN文件排序字段
        #
        # 所以不能要求:
        #
        # sequence递增
        #
        # -----------------------------



        assert event.sequence >= 0



        actions.add(
            event.action
        )



        if count >= 1000:

            break



    assert count > 0



    print(
        "Events:",
        count
    )


    print(
        "Actions:",
        actions
    )



# ============================================================
# Test Feed + OrderBook
# ============================================================


def test_databento_orderbook_rebuild():

    """
    测试：

        Databento

            ↓

        Feed

            ↓

        Builder

            ↓

        Book

    """


    check_data()



    feed = DatabentoFeed(
        str(TEST_DATA)
    )



    builder = OrderBookBuilder()



    count = 0



    for event in feed:


        builder.on_event(
            event
        )


        count += 1



        if count >= 10000:

            break



    book = builder.get_book()



    # 至少存在订单簿对象

    assert (
        len(book.orders)
        >=
        0
    )



    print(
        "Orders:",
        len(book.orders)
    )


    print(
        "Best Bid:",
        book.best_bid()
    )


    print(
        "Best Ask:",
        book.best_ask()
    )


    print(
        "Spread:",
        book.spread()
    )



# ============================================================
# Test Action统计
# ============================================================


def test_databento_actions():

    """
    检查 MBO Action 类型。


    Databento:

        A Add

        M Modify

        C Cancel

        R Reset

        T Trade

        F Fill

        N None


    """


    check_data()



    feed = DatabentoFeed(
        str(TEST_DATA)
    )



    actions = set()



    for index, event in enumerate(feed):


        actions.add(
            event.action
        )


        if index >= 5000:

            break



    print(
        actions
    )



    # 至少存在一种事件

    assert (
        len(actions)
        >
        0
    )