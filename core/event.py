"""
core/event.py

============================================================
Market Event Definition
============================================================

职责：

    定义整个交易系统内部统一事件结构。


数据流：

    Databento MBO
          |
          v
    MarketEvent
          |
          v
    OrderBook
          |
          v
    Strategy
          |
          v
    Execution


本文件只负责：

    - 事件数据结构
    - Action定义
    - Side定义


不负责：

    - 数据读取
    - MBO解析
    - OrderBook更新
    - 撮合
    - 策略逻辑


核心原则：

    所有行情来源必须转换成 MarketEvent。

    Backtest:
        Historical Data
              |
              v
        MarketEvent


    Paper:
        Live Feed
              |
              v
        MarketEvent


    Live:
        Exchange Feed
              |
              v
        MarketEvent


三种模式共用同一个事件模型。


============================================================
"""


from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ============================================================
# MBO Action 定义
# ============================================================

class OrderAction(Enum):
    """
    Databento MBO Action

    A:
        Add Order
        新订单进入盘口


    M:
        Modify Order
        修改订单


    C:
        Cancel Order
        撤销订单


    R:
        Reset / Clear Book
        清空订单簿


    T:
        Trade
        成交事件

        注意：
        不直接修改OrderBook


    F:
        Fill
        成交回报

        注意：
        不直接修改OrderBook


    N:
        None
        无状态变化
    """

    ADD = "A"

    MODIFY = "M"

    CANCEL = "C"

    RESET = "R"

    TRADE = "T"

    FILL = "F"

    NONE = "N"



# ============================================================
# 买卖方向
# ============================================================

class OrderSide(Enum):
    """
    MBO Side

    B:
        Bid
        买方订单


    A:
        Ask
        卖方订单
    """


    BID = "B"

    ASK = "A"



# ============================================================
# Market Event
# ============================================================

@dataclass(slots=True)
class MarketEvent:
    """
    系统统一市场事件。


    对应：

        Databento MBO Record


    一个事件代表：

        一个订单状态变化
        或
        一个成交事件


    ========================================================


    时间字段：

        ts_event

            交易所事件时间


        ts_recv

            数据接收时间


    ========================================================


    顺序字段：

        sequence

            Databento 原始消息序号


            重要：

            OrderBook 重建必须保持
            sequence顺序。


    ========================================================


    订单字段：

        order_id

            L3核心字段。


            用于：

            - 查找订单
            - 修改订单
            - 删除订单
            - Queue Position


    ========================================================


    价格字段：

        price

            原始价格。


        size

            数量。


    ========================================================


    其他：

        symbol

        channel_id

        publisher_id

        instrument_id

        flags


    ========================================================

    """


    # ========================================================
    # 时间
    # ========================================================

    ts_event: int

    ts_recv: int



    # ========================================================
    # Databento 原始顺序
    # ========================================================

    sequence: int



    # ========================================================
    # MBO Action
    # ========================================================

    action: OrderAction



    # ========================================================
    # 买卖方向
    # ========================================================

    side: Optional[OrderSide]



    # ========================================================
    # Order信息
    # ========================================================

    order_id: Optional[int]



    price: Optional[int]

    size: Optional[int]



    # ========================================================
    # 合约信息
    # ========================================================

    symbol: str


    channel_id: Optional[int]


    publisher_id: Optional[int]


    instrument_id: Optional[int]


    flags: Optional[int]



    # ========================================================
    # 辅助方法
    # ========================================================

    def is_book_update(self) -> bool:
        """
        判断该事件是否修改订单簿。


        根据 Databento MBO规则：


        修改Book:

            A
            M
            C
            R


        不修改:

            T
            F
            N

        """

        return self.action in (
            OrderAction.ADD,
            OrderAction.MODIFY,
            OrderAction.CANCEL,
            OrderAction.RESET,
        )



    def is_trade(self) -> bool:
        """
        判断是否成交事件。
        """

        return self.action in (
            OrderAction.TRADE,
            OrderAction.FILL,
        )