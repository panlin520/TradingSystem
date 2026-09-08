"""
tests/test_orderbook_long_replay.py


============================================================
OrderBook Long Replay Stability Test
============================================================


目的：

验证长时间 MBO Replay 后：

OrderBook 是否保持稳定。


测试：

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


============================================================


验证内容：

1.
Replay 是否可以持续运行


2.
盘口是否有效


3.
订单数量是否合理


4.
Bid / Ask 是否正常


5.
Spread 是否异常


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
# Replay参数
# ============================================================


# 长Replay数量

# 根据机器性能调整

LIMIT = 1_000_000



# 每多少事件打印一次状态

CHECK_INTERVAL = 100_000



# ============================================================
# 数据检查
# ============================================================


def check_data():


    if not TEST_DATA.exists():

        pytest.skip(
            f"Databento file not found: {TEST_DATA}"
        )



# ============================================================
# 长Replay测试
# ============================================================


def test_orderbook_long_replay():


    check_data()



    feed = DatabentoFeed(
        str(TEST_DATA)
    )



    builder = OrderBookBuilder()



    count = 0



    checkpoints = []



    for event in feed:



        # ====================================================
        # Feed -> Builder -> OrderBook
        # ====================================================


        builder.on_event(
            event
        )


        count += 1



        # ====================================================
        # 定期检查
        # ====================================================


        if count % CHECK_INTERVAL == 0:


            book = builder.get_book()



            best_bid = (
                book.best_bid()
            )


            best_ask = (
                book.best_ask()
            )



            order_count = len(
                book.orders
            )



            trade_count = (
                book.trade_count
            )



            print()

            print("=" * 60)

            print(
                "LONG REPLAY CHECK"
            )

            print("=" * 60)


            print(
                "events:",
                count
            )


            print(
                "best_bid:",
                best_bid
            )


            print(
                "best_ask:",
                best_ask
            )


            print(
                "orders:",
                order_count
            )


            print(
                "trades:",
                trade_count
            )


            print("=" * 60)



            checkpoints.append(
                {
                    "events": count,

                    "best_bid": best_bid,

                    "best_ask": best_ask,

                    "orders": order_count,

                    "trades": trade_count,
                }
            )



            # =================================================
            # 基础盘口有效性检查
            # =================================================


            if best_bid is not None and best_ask is not None:


                assert (
                    best_bid
                    <=
                    best_ask
                )



            assert (
                order_count
                >=
                0
            )



            assert (
                trade_count
                >=
                0
            )



        if count >= LIMIT:

            break



    # ========================================================
    # 最终检查
    # ========================================================


    assert (
        count
        ==
        LIMIT
    )



    assert (
        len(checkpoints)
        >
        0
    )



    print()

    print("=" * 60)

    print(
        "LONG REPLAY PASSED"
    )

    print("=" * 60)


    print(
        "total events:",
        count
    )


    print(
        "checkpoints:",
        len(checkpoints)
    )


    print("=" * 60)