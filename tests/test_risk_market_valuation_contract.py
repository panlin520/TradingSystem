"""
tests/test_risk_market_valuation_contract.py

============================================================
Risk Market Valuation Contract
============================================================

验证：

1. Databento nano-price -> normalized price
2. 已 normalized price 不重复除 1e9
3. OrderBookBuilder.book 兼容
4. 直接 OrderBook 兼容
5. BUY 风控估值使用 Best Ask
6. SELL 风控估值使用 Best Bid
7. Runtime Enum side 兼容
8. 缺失盘口返回 None
9. 缺失价格不会被转换为 0
10. Mid Price 使用 normalized bid/ask 计算

============================================================
"""


import pytest


from risk.valuation import (
    RiskMarketValuation,
)

from signals.signal import (
    SignalSide,
)





class FakeBook:

    def __init__(
        self,
        bid=None,
        ask=None,
    ):

        self._bid = bid

        self._ask = ask


    def best_bid(self):

        return self._bid


    def best_ask(self):

        return self._ask





class FakeBuilder:

    def __init__(
        self,
        book,
    ):

        self.book = book





def test_normalize_databento_nano_price():

    result = (
        RiskMarketValuation
        .normalize_price(
            7_571_250_000_000
        )
    )


    assert result == pytest.approx(
        7571.25
    )





def test_normalized_price_is_not_scaled_again():

    result = (
        RiskMarketValuation
        .normalize_price(
            7571.25
        )
    )


    assert result == pytest.approx(
        7571.25
    )





def test_snapshot_from_direct_orderbook():

    valuation = RiskMarketValuation()


    snapshot = valuation.snapshot(

        FakeBook(

            bid=7_571_000_000_000,

            ask=7_571_250_000_000,

        )

    )


    assert snapshot.best_bid == pytest.approx(
        7571.00
    )

    assert snapshot.best_ask == pytest.approx(
        7571.25
    )

    assert snapshot.mid_price == pytest.approx(
        7571.125
    )





def test_snapshot_from_orderbook_builder():

    valuation = RiskMarketValuation()


    builder = FakeBuilder(

        FakeBook(

            bid=7_571_000_000_000,

            ask=7_571_250_000_000,

        )

    )


    snapshot = valuation.snapshot(
        builder
    )


    assert snapshot.best_bid == pytest.approx(
        7571.00
    )

    assert snapshot.best_ask == pytest.approx(
        7571.25
    )





def test_buy_uses_best_ask():

    valuation = RiskMarketValuation()


    book = FakeBook(

        bid=7_571_000_000_000,

        ask=7_571_250_000_000,

    )


    result = valuation.price_for_side(

        book,

        SignalSide.BUY,

    )


    assert result == pytest.approx(
        7571.25
    )





def test_sell_uses_best_bid():

    valuation = RiskMarketValuation()


    book = FakeBook(

        bid=7_571_000_000_000,

        ask=7_571_250_000_000,

    )


    result = valuation.price_for_side(

        book,

        SignalSide.SELL,

    )


    assert result == pytest.approx(
        7571.00
    )





def test_string_side_is_supported():

    valuation = RiskMarketValuation()


    book = FakeBook(

        bid=100.0,

        ask=101.0,

    )


    assert valuation.price_for_side(
        book,
        "BUY",
    ) == pytest.approx(
        101.0
    )


    assert valuation.price_for_side(
        book,
        "SELL",
    ) == pytest.approx(
        100.0
    )





def test_missing_book_returns_empty_snapshot():

    valuation = RiskMarketValuation()


    snapshot = valuation.snapshot(
        None
    )


    assert snapshot.best_bid is None

    assert snapshot.best_ask is None

    assert snapshot.mid_price is None

    assert snapshot.is_valid() is False





def test_missing_ask_causes_buy_price_to_be_none():

    valuation = RiskMarketValuation()


    book = FakeBook(

        bid=7571.0,

        ask=None,

    )


    assert valuation.price_for_side(
        book,
        SignalSide.BUY,
    ) is None





def test_missing_bid_causes_sell_price_to_be_none():

    valuation = RiskMarketValuation()


    book = FakeBook(

        bid=None,

        ask=7571.25,

    )


    assert valuation.price_for_side(
        book,
        SignalSide.SELL,
    ) is None





def test_missing_price_is_never_converted_to_zero():

    assert (
        RiskMarketValuation
        .normalize_price(
            None
        )
        is None
    )
