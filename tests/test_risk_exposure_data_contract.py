"""
tests/test_risk_exposure_data_contract.py

============================================================
Risk Exposure Data Contract
============================================================

目的：

在把 ExposureEngine 升级成 dollar / notional exposure 之前，
先验证 Risk 可以依赖的价格与 point value 数据契约。

验证：

1. ExecutionEngine 会把 Databento nano-dollar 价格
   转成正常交易价格。

2. Portfolio.on_fill() 会把正常 Fill price 保存到：

       portfolio.market_prices[symbol]

3. Portfolio 会按 symbol 保存 point value：

       ES  = 50
       MES = 5
       NQ  = 20
       MNQ = 2

4. 可以安全计算：

       notional =
           abs(quantity)
           *
           market_price
           *
           point_value

============================================================
"""


import pytest


from core.mode import TradingMode

from execution.execution_engine import (
    ExecutionEngine,
    ExecutionMode,
)

from execution.fill import Fill

from portfolio.portfolio import Portfolio





# ============================================================
# Execution Price Contract
# ============================================================


def test_execution_normalizes_databento_nano_price():

    raw_price = 7_571_250_000_000


    normalized = (
        ExecutionEngine
        ._normalize_market_price(
            raw_price
        )
    )


    assert normalized == pytest.approx(
        7571.25
    )





def test_execution_keeps_normal_price_unchanged():

    normalized = (
        ExecutionEngine
        ._normalize_market_price(
            7571.25
        )
    )


    assert normalized == pytest.approx(
        7571.25
    )





# ============================================================
# Portfolio Market Price Contract
# ============================================================


def test_portfolio_fill_price_is_stored_as_market_price():

    portfolio = Portfolio(

        initial_capital=100_000.0,

        mode=TradingMode.BACKTEST,

        point_values={
            "ESU6": 50.0,
        },

    )


    fill = Fill(

        fill_id="F1",

        order_id="O1",

        symbol="ESU6",

        side="BUY",

        quantity=2,

        price=7571.25,

    )


    portfolio.on_fill(
        fill
    )


    assert (
        portfolio.market_prices["ESU6"]
        ==
        pytest.approx(
            7571.25
        )
    )





# ============================================================
# Point Value Contract
# ============================================================


@pytest.mark.parametrize(
    (
        "symbol",
        "point_value",
    ),
    [
        ("ESU6", 50.0),
        ("MESU6", 5.0),
        ("NQU6", 20.0),
        ("MNQU6", 2.0),
    ],
)
def test_portfolio_position_uses_symbol_point_value(
    symbol,
    point_value,
):

    portfolio = Portfolio(

        point_values={
            symbol: point_value,
        }

    )


    position = portfolio.get_position(
        symbol
    )


    assert position.point_value == pytest.approx(
        point_value
    )





# ============================================================
# Dollar / Notional Exposure Contract
# ============================================================


@pytest.mark.parametrize(
    (
        "symbol",
        "quantity",
        "price",
        "point_value",
        "expected_notional",
    ),
    [
        (
            "ESU6",
            2,
            7571.25,
            50.0,
            757125.0,
        ),
        (
            "MESU6",
            2,
            7571.25,
            5.0,
            75712.5,
        ),
        (
            "NQU6",
            1,
            25000.0,
            20.0,
            500000.0,
        ),
        (
            "MNQU6",
            1,
            25000.0,
            2.0,
            50000.0,
        ),
    ],
)
def test_notional_formula_uses_normalized_price_and_point_value(
    symbol,
    quantity,
    price,
    point_value,
    expected_notional,
):

    portfolio = Portfolio(

        point_values={
            symbol: point_value,
        }

    )


    portfolio.update_market_price(
        symbol,
        price,
    )


    position = portfolio.get_position(
        symbol
    )


    notional = (

        abs(quantity)

        *

        portfolio.market_prices[symbol]

        *

        position.point_value

    )


    assert notional == pytest.approx(
        expected_notional
    )
