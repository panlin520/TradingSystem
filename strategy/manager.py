"""
strategy/manager.py

============================================================
Strategy Manager
============================================================

职责：

    管理多个策略实例。


============================================================


功能：

    - 注册策略

    - 启动策略

    - 停止策略

    - 分发MarketEvent

    - 分发Order Update

    - 分发Trade

    - 收集Signal



============================================================


设计：

支持：

    多策略同时运行



例如：


StrategyManager


    |

    +----------------+

    |                |


L3Scalper      MeanReversion


    |                |


 Signal          Signal



============================================================


原则：

新增策略：

只需要：

    创建strategy文件

    继承Strategy

    注册即可



无需修改：

    Engine

    Data

    OrderBook

    Risk

    Execution



============================================================

"""


from typing import Dict, List, Any


from strategy.base import Strategy

from strategy.signal import Signal




class StrategyManager:
    """
    策略管理器。


    """



    def __init__(self):

        # ====================================================
        # 策略列表
        #
        # name -> Strategy
        #
        # ====================================================

        self.strategies: Dict[
            str,
            Strategy
        ] = {}



        # ====================================================
        # 最新Signal
        # ====================================================

        self.signals: List[
            Signal
        ] = []



        # ====================================================
        # 状态
        # ====================================================

        self.running = False





    # ========================================================
    # 添加策略
    # ========================================================

    def add_strategy(
        self,
        strategy: Strategy
    ):
        """
        注册策略。


        """

        if strategy.name in self.strategies:

            raise ValueError(
                f"Strategy exists: {strategy.name}"
            )


        self.strategies[
            strategy.name
        ] = strategy




    # ========================================================
    # 删除策略
    # ========================================================

    def remove_strategy(
        self,
        name: str
    ):
        """
        删除策略。


        """

        strategy = self.strategies.pop(
            name,
            None
        )


        if strategy:

            strategy.on_stop()




    # ========================================================
    # 启动全部策略
    # ========================================================

    def start(
        self,
        state: Any = None
    ):
        """
        启动策略。


        """

        self.running = True


        for strategy in self.strategies.values():

            strategy.on_start(
                state
            )




    # ========================================================
    # 停止全部策略
    # ========================================================

    def stop(
        self,
        state: Any = None
    ):
        """
        停止策略。


        """

        self.running = False


        for strategy in self.strategies.values():

            strategy.on_stop(
                state
            )




    # ========================================================
    # 市场事件
    # ========================================================

    def on_market_event(
        self,
        event: Any,
        state: Any
    ):
        """
        分发市场事件。


        """

        if not self.running:

            return



        self.signals.clear()



        for strategy in self.strategies.values():


            if not strategy.active:

                continue



            result = strategy.on_market_event(

                event,

                state

            )



            if isinstance(
                result,
                Signal
            ):

                result.strategy = strategy.name


                self.signals.append(
                    result
                )




    # ========================================================
    # 订单更新
    # ========================================================

    def on_order_update(
        self,
        order_update: Any,
        state: Any
    ):
        """
        分发订单更新。


        """

        for strategy in self.strategies.values():

            strategy.on_order_update(

                order_update,

                state

            )




    # ========================================================
    # 成交
    # ========================================================

    def on_trade(
        self,
        trade: Any,
        state: Any
    ):
        """
        分发成交。


        """

        for strategy in self.strategies.values():

            strategy.on_trade(

                trade,

                state

            )




    # ========================================================
    # 获取Signal
    # ========================================================

    def get_signals(
        self
    ) -> List[Signal]:
        """
        返回当前信号。


        """

        return self.signals




    # ========================================================
    # 状态
    # ========================================================

    def status(
        self
    ) -> dict:
        """
        返回策略状态。


        """

        return {


            "running":
                self.running,


            "strategies":
            [

                strategy.get_state()

                for strategy
                in self.strategies.values()

            ],


            "signals":

            [

                signal.to_dict()

                for signal
                in self.signals

            ]

        }