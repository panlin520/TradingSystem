"""
orderbook/builder.py


============================================================
L3 OrderBook Builder
============================================================


职责：

    将 MarketEvent 应用到 OrderBook。


数据来源：

    Databento MBO


流程：

    MarketEvent
          |
          v
    OrderBookBuilder
          |
          v
    OrderBook


============================================================


Databento Action 规则：


A:
    Add Order
    修改 Book


M:
    Modify Order
    修改 Book


C:
    Cancel Order
    修改 Book


R:
    Reset
    清空 Book


T:
    Trade

    表示主动成交。

    更新：
        trade_count
        trade_volume

    不直接修改 Book。


F:
    Fill

    表示被动挂单成交明细。

    不增加 trade_count。
    不增加 trade_volume。
    不直接修改 Book。

    原因：

    Databento / CME MBO 中，
    同一次真实成交可能同时产生：

        T = Trade
        F = Fill

    如果同时统计 T 和 F：

        trade_count
        trade_volume

    会产生重复统计。


N:
    None / Ignore

    不修改 Book。


============================================================


核心原则：


1.
不重新排序事件。


2.
严格按照 Databento Feed 输入顺序处理。


3.
sequence 只用于诊断，
不作为全局排序依据。


4.
Trade / Fill 不直接修改 OrderBook。


5.
OrderBook 的真实数量变化由：

    Add
    Modify
    Cancel
    Reset

等盘口事件完成。


============================================================
"""


from typing import Optional

from core.event import (
    MarketEvent,
    OrderAction,
)

from orderbook.order import Order
from orderbook.book import OrderBook


# ============================================================
# OrderBook Builder
# ============================================================


class OrderBookBuilder:
    """
    L3 OrderBook 构建器。
    """

    def __init__(
        self,
        book: Optional[OrderBook] = None,
    ):

        self.book = (
            book
            if book is not None
            else OrderBook()
        )

        # ====================================================
        # 事件统计
        # ====================================================

        self.event_count = 0

        self.action_count = {
            "A": 0,
            "M": 0,
            "C": 0,
            "R": 0,
            "T": 0,
            "F": 0,
            "N": 0,
        }

        # ====================================================
        # Sequence 检查
        #
        # 注意：
        #
        # 不排序
        #
        # 不阻断 Replay
        #
        # 只统计异常
        #
        # ====================================================

        self.last_sequence = None

        self.out_of_order_count = 0

    # ========================================================
    # 接收事件
    # ========================================================

    def on_event(
        self,
        event: MarketEvent,
    ):
        """
        接收并处理单个 MarketEvent。
        """

        # ====================================================
        # 总事件统计
        # ====================================================

        self.event_count += 1

        action = event.action.value

        if action in self.action_count:
            self.action_count[action] += 1

        # ====================================================
        # Sequence 诊断
        # ====================================================

        self._check_sequence(
            event.sequence
        )

        # ====================================================
        # Action 分发
        # ====================================================

        if event.action == OrderAction.ADD:

            self._add(
                event
            )

        elif event.action == OrderAction.MODIFY:

            self._modify(
                event
            )

        elif event.action == OrderAction.CANCEL:

            self._cancel(
                event
            )

        elif event.action == OrderAction.RESET:

            self._reset()

        elif event.action == OrderAction.TRADE:

            self._trade(
                event
            )

        elif event.action == OrderAction.FILL:

            self._fill(
                event
            )

        elif event.action == OrderAction.NONE:

            pass

    # ========================================================
    # Add
    # ========================================================

    def _add(
        self,
        event: MarketEvent,
    ):
        """
        A:

        新增挂单。

        修改 OrderBook。
        """

        if event.order_id is None:
            return

        if event.side is None:
            return

        if event.price is None:
            return

        if event.size is None:
            return

        order = Order(
            order_id=event.order_id,
            side=event.side,
            price=event.price,
            size=event.size,
            sequence=event.sequence,
            ts_event=event.ts_event,
        )

        self.book.add_order(
            order
        )

    # ========================================================
    # Modify
    # ========================================================

    def _modify(
        self,
        event: MarketEvent,
    ):
        """
        M:

        修改订单。


        Databento MBO Modify 可能改变：

            price
            size
            side


        具体修改逻辑交给 OrderBook。
        """

        if event.order_id is None:
            return

        self.book.modify_order(
            order_id=event.order_id,
            price=event.price,
            size=event.size,
            side=event.side,
        )

    # ========================================================
    # Cancel
    # ========================================================

    def _cancel(
        self,
        event: MarketEvent,
    ):
        """
        C:

        删除或减少订单。

        具体处理交给 OrderBook。
        """

        if event.order_id is None:
            return

        self.book.cancel_order(
            event.order_id
        )

    # ========================================================
    # Reset
    # ========================================================

    def _reset(
        self,
    ):
        """
        R:

        清空订单簿。
        """

        self.book.clear()

    # ========================================================
    # Trade
    # ========================================================

    def _trade(
        self,
        event: MarketEvent,
    ):
        """
        T:

        Trade 成交事件。


        Databento 定义：

        Trade 表示主动成交。


        注意：

        Trade 本身不直接修改 OrderBook。


        这里只维护成交统计：

            trade_count

            trade_volume
        """

        self.book.trade_count += 1

        if event.size is not None:
            self.book.trade_volume += event.size

    # ========================================================
    # Fill
    # ========================================================

    def _fill(
        self,
        event: MarketEvent,
    ):
        """
        F:

        Fill 成交明细。


        Databento 定义：

        Fill 表示 resting order
        被成交的被动方明细。


        ====================================================

        重要：

        Fill 不直接修改 OrderBook。

        Fill 也不能再次增加：

            trade_count
            trade_volume


        原因：

        对 CME MBO：

        一次真实成交可能被 Databento 规范化为：

            Trade (T)
                +
            Fill (F)


        Trade 已经用于成交统计。

        如果 Fill 再统计一次，
        将导致成交次数和成交量重复计算。


        Book 的实际变化由后续对应的：

            Cancel
            Modify

        等事件完成。

        ====================================================
        """

        return

    # ========================================================
    # Sequence 检查
    # ========================================================

    def _check_sequence(
        self,
        sequence: int,
    ):
        """
        检查 Databento sequence。


        注意：

        Databento MBO 的 sequence：

            不是整个 DBN 文件的全局递增编号。


        因此：

            不能重新排序
            不能因为 sequence 回退而中断 Replay


        Builder 只做：

            保持 Feed 输入顺序

            统计 sequence 回退次数

            不修改原始事件顺序
        """

        if self.last_sequence is None:

            self.last_sequence = sequence

            return

        if sequence < self.last_sequence:

            self.out_of_order_count += 1

        self.last_sequence = sequence

    # ========================================================
    # 获取 Book
    # ========================================================

    def get_book(
        self,
    ) -> OrderBook:
        """
        返回当前 OrderBook。
        """

        return self.book

    # ========================================================
    # 状态
    # ========================================================

    def status(
        self,
    ) -> dict:
        """
        返回 Builder 当前状态。
        """

        return {
            "events": self.event_count,
            "sequence": self.last_sequence,
            "out_of_order": self.out_of_order_count,
            "actions": self.action_count,
            "book": self.book.snapshot(),
        }