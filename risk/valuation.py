"""
risk/valuation.py

============================================================
Risk Market Valuation
============================================================

职责：

    从当前稳定 OrderBook 状态中提取 Risk 可使用的
    normalized market price。

============================================================

Databento Price Boundary：

    OrderBook Layer
        ↓
    Databento raw nano-price

例如：

    7_571_250_000_000
        ↓ / 1_000_000_000
    7571.25

Risk / Portfolio / Execution Layer：

    使用正常交易价格：

        7571.25

============================================================

原则：

1. 不修改 OrderBook
2. 不修改 Portfolio
3. 不负责 Exposure 计算
4. 不负责 RiskDecision
5. 不负责 Strategy
6. 缺少有效盘口时返回 None
7. 不把缺失价格当成 0
8. 支持 OrderBookBuilder.book 和直接 OrderBook
9. 支持 best_bid / best_ask 方法或属性

============================================================
"""


from dataclasses import dataclass
from typing import Optional, Any






# ============================================================
# Risk Valuation Snapshot
# ============================================================


@dataclass(frozen=True)
class RiskValuationSnapshot:
    """
    Risk 使用的稳定市场估值快照。

    所有价格均为 normalized price。
    """

    best_bid: Optional[float] = None

    best_ask: Optional[float] = None

    mid_price: Optional[float] = None


    def is_valid(self) -> bool:
        """
        至少存在一个有效可交易价格。
        """

        return (
            self.best_bid is not None
            or
            self.best_ask is not None
        )






# ============================================================
# Risk Market Valuation
# ============================================================


class RiskMarketValuation:
    """
    从 OrderBook 获取 Risk 使用的 normalized price。

    注意：

        这里不直接读取 MarketEvent.price。

    原因：

        F_LAST event 可能是 Add / Modify / Cancel / None，
        event.price 不等于当前可成交价格。

    Risk 应读取稳定盘口：
        BUY  -> Best Ask
        SELL -> Best Bid
    """


    DATABENTO_PRICE_SCALE = 1_000_000_000

    DATABENTO_RAW_THRESHOLD = 1_000_000_000



    # ========================================================
    # Normalize Price
    # ========================================================


    @classmethod
    def normalize_price(
        cls,
        price: Any,
    ) -> Optional[float]:
        """
        将 Databento raw nano-price 转为 normal price。

        同时兼容已经 normalized 的普通价格。
        """

        if price is None:

            return None


        try:

            value = float(price)

        except (
            TypeError,
            ValueError,
        ):

            return None


        if abs(value) >= cls.DATABENTO_RAW_THRESHOLD:

            value = (
                value
                /
                cls.DATABENTO_PRICE_SCALE
            )


        return value



    # ========================================================
    # Build Snapshot
    # ========================================================


    def snapshot(
        self,
        orderbook,
    ) -> RiskValuationSnapshot:
        """
        从 OrderBook / OrderBookBuilder 构建 normalized snapshot。
        """


        book = self._unwrap_book(
            orderbook
        )


        if book is None:

            return RiskValuationSnapshot()


        raw_bid = self._read_price(
            book,
            "best_bid",
        )

        raw_ask = self._read_price(
            book,
            "best_ask",
        )


        best_bid = self.normalize_price(
            raw_bid
        )

        best_ask = self.normalize_price(
            raw_ask
        )


        mid_price = None


        if (
            best_bid is not None
            and
            best_ask is not None
        ):

            mid_price = (
                best_bid
                +
                best_ask
            ) / 2.0


        return RiskValuationSnapshot(

            best_bid=best_bid,

            best_ask=best_ask,

            mid_price=mid_price,

        )



    # ========================================================
    # Resolve Signal Price
    # ========================================================


    def price_for_side(
        self,
        orderbook,
        side,
    ) -> Optional[float]:
        """
        获取新订单的保守估值价格。

        BUY:
            Best Ask

        SELL:
            Best Bid

        不支持的 side：
            None
        """


        snapshot = self.snapshot(
            orderbook
        )


        side_value = getattr(
            side,
            "value",
            side,
        )


        if side_value is None:

            return None


        side_value = str(
            side_value
        ).upper()


        if side_value == "BUY":

            return snapshot.best_ask


        if side_value == "SELL":

            return snapshot.best_bid


        return None



    # ========================================================
    # Helpers
    # ========================================================


    @staticmethod
    def _unwrap_book(
        orderbook,
    ):
        """
        支持：

            state.orderbook -> OrderBookBuilder -> .book
            state.orderbook -> OrderBook
        """


        if orderbook is None:

            return None


        return getattr(
            orderbook,
            "book",
            orderbook,
        )



    @staticmethod
    def _read_price(
        book,
        attribute_name,
    ):
        """
        支持：

            best_bid()
            best_bid property

            best_ask()
            best_ask property

        返回值兼容：

            int
            float
            tuple/list -> 第一项
            object.price
        """


        if not hasattr(
            book,
            attribute_name,
        ):

            return None


        value = getattr(
            book,
            attribute_name,
        )


        if callable(value):

            value = value()


        if value is None:

            return None


        if isinstance(
            value,
            (int, float),
        ):

            return value


        if isinstance(
            value,
            (tuple, list),
        ):

            if not value:

                return None


            first = value[0]


            if isinstance(
                first,
                (int, float),
            ):

                return first


        price = getattr(
            value,
            "price",
            None,
        )


        if isinstance(
            price,
            (int, float),
        ):

            return price


        return None
