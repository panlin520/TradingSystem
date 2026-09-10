"""
tests/test_state_strategy_context.py


============================================================
SystemState StrategyContext Contract Test
============================================================


验证：

    SystemState

        ↓

    StrategyContext

        ↓

    snapshot()


============================================================


测试范围：

    - State 可以保存 StrategyContext
    - StrategyContext 可以读取
    - snapshot 可以导出


不测试：

    - Engine

    - Strategy

    - Signal

    - Risk

    - Execution


============================================================

"""


from core.state import SystemState

from strategy.context import StrategyContext





class FakeContext:

    """
    简单 StrategyContext Mock
    """

    def __init__(self):

        self.name = "ESU6_CONTEXT"



    def to_dict(self):

        return {

            "name": self.name

        }





def test_state_can_initialize_strategy_context():

    state = SystemState()


    assert state.strategy_context is None





def test_state_can_set_strategy_context():


    state = SystemState()


    context = FakeContext()


    state.set_strategy_context(

        context

    )


    assert state.strategy_context is context





def test_state_strategy_context_mapping():


    state = SystemState()


    context = FakeContext()


    state.set_strategy_context(

        context

    )


    assert (

        state.strategy_context.name

        ==

        "ESU6_CONTEXT"

    )





def test_state_snapshot_contains_strategy_context():


    state = SystemState()


    context = FakeContext()


    state.set_strategy_context(

        context

    )


    snapshot = state.snapshot()



    assert (

        snapshot["strategy_context"]["name"]

        ==

        "ESU6_CONTEXT"

    )





def test_state_without_strategy_context():


    state = SystemState()


    snapshot = state.snapshot()



    assert (

        snapshot["strategy_context"]

        is None

    )