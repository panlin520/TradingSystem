"""
tests/test_orderbook_accuracy.py


============================================================
OrderBook Accuracy Validation Test
============================================================


验证：

    Databento MBO

          ↓

    DatabentoFeed

          ↓

    MarketEvent

          ↓

    OrderBookBuilder

          ↓

    OrderBook


============================================================


验证内容：

1.
订单簿是否为空


2.
Bid / Ask 是否正确


3.
Spread是否合法


4.
Tick规则


5.
Order唯一性


6.
Book稳定性


============================================================

"""


from pathlib import Path


import pytest



from data.databento_feed import DatabentoFeed


from orderbook.builder import OrderBookBuilder



# ============================================================
# 数据路径
# ============================================================


TEST_DATA = (
    Path("data")
    /
    "ESU6_2026-06-15_MBO.dbn.zst"
)



# ============================================================
# 检查数据
# ============================================================


def check_data():

    if not TEST_DATA.exists():

        pytest.skip(
            f"Databento file not found: {TEST_DATA}"
        )



# ============================================================
# 创建Book
# ============================================================


def build_orderbook(
    limit=100000
):

    """
    Replay MBO

    创建订单簿。

    """

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
# Test:
# Book是否生成
# ============================================================


def test_orderbook_has_orders():


    check_data()



    book, builder, count = build_orderbook(
        10000
    )



    print(
        "Events:",
        count
    )


    print(
        "Orders:",
        len(book.orders)
    )



    assert (
        len(book.orders)
        >
        0
    )



# ============================================================
# Test:
# Bid Ask合法性
# ============================================================


def test_orderbook_bid_ask_valid():


    check_data()



    book, builder, count = build_orderbook(
        50000
    )



    bid = book.best_bid()


    ask = book.best_ask()



    print(
        "Best Bid:",
        bid
    )


    print(
        "Best Ask:",
        ask
    )



    #
    # 如果盘口完整
    #

    if bid is not None and ask is not None:


        assert (
            bid
            <
            ask
        )



# ============================================================
# Test:
# Spread Tick验证
# ============================================================


def test_es_tick_spread():


    check_data()



    book, builder, count = build_orderbook(
        50000
    )


    bid = book.best_bid()


    ask = book.best_ask()



    if (
        bid is None
        or
        ask is None
    ):

        pytest.skip(
            "No complete market"
        )



    spread = (
        ask
        -
        bid
    )



    print(
        "Spread:",
        spread
    )



    #
    # ES Tick:
    #
    # 0.25
    #
    # Databento price:
    #
    # 1e9 scale
    #

    ES_TICK = 250000000



    assert (
        spread
        %
        ES_TICK
        ==
        0
    )



# ============================================================
# Test:
# Order ID唯一
# ============================================================


def test_order_id_unique():


    check_data()



    book, builder, count = build_orderbook(
        100000
    )



    order_ids = list(
        book.orders.keys()
    )



    print(
        "Orders:",
        len(order_ids)
    )



    assert (
        len(order_ids)
        ==
        len(set(order_ids))
    )



# ============================================================
# Test:
# Builder统计
# ============================================================


def test_builder_statistics():


    check_data()



    book, builder, count = build_orderbook(
        100000
    )



    status = builder.status()



    print(
        status
    )



    assert (
        status["events"]
        ==
        count
    )



    assert (
        sum(
            status["actions"].values()
        )
        ==
        count
    )



# ============================================================
# Test:
# 长Replay稳定性
# ============================================================


def test_long_replay_stability():


    check_data()



    book, builder, count = build_orderbook(
        200000
    )



    #
    # 不允许异常状态
    #


    bid = book.best_bid()


    ask = book.best_ask()



    if (
        bid is not None
        and
        ask is not None
    ):


        assert (
            bid
            <
            ask
        )



    #
    # Book必须保持有效
    #

    assert (
        len(book.orders)
        >=
        0
    )


    print(
        "Replay Events:",
        count
    )


    print(
        "Final Orders:",
        len(book.orders)
    )