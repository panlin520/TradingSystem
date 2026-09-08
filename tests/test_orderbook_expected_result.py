"""
tests/test_orderbook_expected_result.py


============================================================
OrderBook Expected Result Test
============================================================


目的：

验证：

Databento MBO
        |
        v
DatabentoFeed
        |
        v
OrderBookBuilder
        |
        v
OrderBook


最终输出结果是否等于预期黄金结果。


注意：

这里测试真实数值。

不是测试程序是否运行。


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
# 黄金结果
#
# 来源：
#
# ESU6 MBO replay
# 前10000 events
#
# 生成日期：
# 当前OrderBook版本
#
# ============================================================


EXPECTED = {


    # replay事件数量

    "events": 10000,


    # 最优买价

    "best_bid": 7558750000000,


    # 最优卖价

    "best_ask": 7559000000000,


    # Bid总挂单量

    "bid_volume": 6538,


    # Ask总挂单量

    "ask_volume": 4539,


    # 当前订单数量

    "order_count": 5130,


    # 成交次数

    "trade_count": 192,


}



# ============================================================
# 检查数据
# ============================================================


def check_data():


    if not TEST_DATA.exists():

        pytest.skip(
            f"Databento file not found: {TEST_DATA}"
        )



# ============================================================
# 构建OrderBook
# ============================================================


def build_book(limit):


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



        if count >= limit:

            break



    return (
        builder.get_book(),
        builder,
        count
    )



# ============================================================
# 打印当前快照
#
# 用于人工检查
#
# ============================================================


def print_snapshot(book, count):


    print()

    print("=" * 60)

    print(
        "CURRENT SNAPSHOT"
    )

    print("=" * 60)


    print(
        "events:",
        count
    )


    print(
        "best_bid:",
        book.best_bid()
    )


    print(
        "best_ask:",
        book.best_ask()
    )


    print(
        "bid_volume:",
        book.bid_volume()
    )


    print(
        "ask_volume:",
        book.ask_volume()
    )


    print(
        "order_count:",
        len(book.orders)
    )


    print(
        "trade_count:",
        book.trade_count
    )


    print("=" * 60)



# ============================================================
# 黄金快照显示
#
# 不参与判断
#
# ============================================================


def test_generate_expected_snapshot():


    check_data()



    book, builder, count = build_book(
        EXPECTED["events"]
    )


    print_snapshot(
        book,
        count
    )



    assert count == EXPECTED["events"]



# ============================================================
# 核心测试
#
# 当前结果 == 黄金结果
#
# ============================================================


def test_orderbook_expected_result():


    check_data()



    book, builder, count = build_book(
        EXPECTED["events"]
    )



    # --------------------------------------------------------
    # 事件数量
    # --------------------------------------------------------

    assert (
        count
        ==
        EXPECTED["events"]
    )



    # --------------------------------------------------------
    # Best Bid
    # --------------------------------------------------------

    assert (
        book.best_bid()
        ==
        EXPECTED["best_bid"]
    )



    # --------------------------------------------------------
    # Best Ask
    # --------------------------------------------------------

    assert (
        book.best_ask()
        ==
        EXPECTED["best_ask"]
    )



    # --------------------------------------------------------
    # Bid Volume
    # --------------------------------------------------------

    assert (
        book.bid_volume()
        ==
        EXPECTED["bid_volume"]
    )



    # --------------------------------------------------------
    # Ask Volume
    # --------------------------------------------------------

    assert (
        book.ask_volume()
        ==
        EXPECTED["ask_volume"]
    )



    # --------------------------------------------------------
    # Order数量
    # --------------------------------------------------------

    assert (
        len(book.orders)
        ==
        EXPECTED["order_count"]
    )



    # --------------------------------------------------------
    # Trade数量
    # --------------------------------------------------------

    assert (
        book.trade_count
        ==
        EXPECTED["trade_count"]
    )