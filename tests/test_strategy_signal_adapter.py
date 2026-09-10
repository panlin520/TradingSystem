"""
tests/test_strategy_signal_adapter.py

============================================================
Strategy Signal Adapter Contract Test
============================================================

验证：

    CompositeSignal
        ↓
    StrategySignalAdapter
        ↓
    signals.signal.Signal

覆盖：

    BUY ENTRY
    SELL ENTRY
    BUY EXIT
    SELL EXIT
    HOLD / NONE
    symbol mapping
    quantity policy
    confidence mapping
    metadata mapping

============================================================
"""


import pytest


from runtime.strategy_signal_adapter import (
    StrategySignalAdapter,
)

from strategy.composite_signal import CompositeSignal

from strategy.signal import (
    SignalSide as StrategySignalSide,
    SignalType as StrategySignalType,
    StrategyCategory,
)

from signals.signal import (
    Signal as RuntimeSignal,
    SignalSide as RuntimeSignalSide,
    SignalType as RuntimeSignalType,
)





class FakeContext:

    def __init__(
        self,
        symbol="ESU6",
        timestamp=123456789,
    ):

        self.symbol = symbol

        self.timestamp = timestamp





def create_composite(
    side=StrategySignalSide.BUY,
    signal_type=StrategySignalType.ENTRY,
):

    return CompositeSignal(

        side=side,

        signal_type=signal_type,

        category=StrategyCategory.MEAN_REVERSION,

        confidence=0.85,

        score=1.75,

        reasons=[
            "reason-1",
            "reason-2",
        ],

        strategies=[
            "mean_reversion",
            "absorption_refill",
        ],

        metadata={
            "source": "test",
        },

    )





def test_adapter_can_initialize():

    adapter = StrategySignalAdapter(
        quantity=2
    )

    assert adapter.quantity == 2





def test_adapter_rejects_invalid_quantity():

    with pytest.raises(
        ValueError
    ):

        StrategySignalAdapter(
            quantity=0
        )





def test_buy_entry_mapping():

    adapter = StrategySignalAdapter(
        quantity=2
    )


    result = adapter.adapt(

        create_composite(
            side=StrategySignalSide.BUY,
            signal_type=StrategySignalType.ENTRY,
        ),

        FakeContext(),

    )


    assert isinstance(
        result,
        RuntimeSignal,
    )


    assert result.symbol == "ESU6"

    assert result.side == RuntimeSignalSide.BUY

    assert result.quantity == 2

    assert result.signal_type == RuntimeSignalType.ENTRY

    assert result.confidence == 0.85

    assert result.strategy == "COMPOSITE"





def test_sell_entry_mapping():

    adapter = StrategySignalAdapter(
        quantity=3
    )


    result = adapter.adapt(

        create_composite(
            side=StrategySignalSide.SELL,
            signal_type=StrategySignalType.ENTRY,
        ),

        FakeContext(),

    )


    assert result.side == RuntimeSignalSide.SELL

    assert result.quantity == 3

    assert result.signal_type == RuntimeSignalType.ENTRY





def test_buy_exit_mapping():

    adapter = StrategySignalAdapter(
        quantity=1
    )


    result = adapter.adapt(

        create_composite(
            side=StrategySignalSide.BUY,
            signal_type=StrategySignalType.EXIT,
        ),

        FakeContext(),

    )


    assert result.side == RuntimeSignalSide.BUY

    assert result.signal_type == RuntimeSignalType.EXIT





def test_sell_exit_mapping():

    adapter = StrategySignalAdapter(
        quantity=1
    )


    result = adapter.adapt(

        create_composite(
            side=StrategySignalSide.SELL,
            signal_type=StrategySignalType.EXIT,
        ),

        FakeContext(),

    )


    assert result.side == RuntimeSignalSide.SELL

    assert result.signal_type == RuntimeSignalType.EXIT





def test_hold_signal_returns_none():

    adapter = StrategySignalAdapter(
        quantity=1
    )


    result = adapter.adapt(

        CompositeSignal(),

        FakeContext(),

    )


    assert result is None





def test_missing_symbol_returns_none():

    adapter = StrategySignalAdapter(
        quantity=1
    )


    result = adapter.adapt(

        create_composite(),

        FakeContext(
            symbol=""
        ),

    )


    assert result is None





def test_metadata_mapping():

    adapter = StrategySignalAdapter(
        quantity=1
    )


    result = adapter.adapt(

        create_composite(),

        FakeContext(
            timestamp=987654321
        ),

    )


    assert result.metadata["source"] == "test"

    assert result.metadata["composite_score"] == 1.75

    assert result.metadata["composite_reasons"] == [
        "reason-1",
        "reason-2",
    ]

    assert result.metadata["composite_strategies"] == [
        "mean_reversion",
        "absorption_refill",
    ]

    assert (
        result.metadata["strategy_timestamp"]
        ==
        987654321
    )

    assert (
        result.metadata["strategy_category"]
        ==
        "MEAN_REVERSION"
    )





def test_runtime_signal_validate_after_mapping():

    adapter = StrategySignalAdapter(
        quantity=1
    )


    result = adapter.adapt(

        create_composite(),

        FakeContext(),

    )


    assert result.validate() is True
