"""
strategy/base.py

============================================================
Strategy Base Interface
============================================================

职责：

    所有交易策略的基础接口。


所有策略必须继承：

    Strategy


例如：

    L3ScalperStrategy

    MeanReversionStrategy

    ImbalanceStrategy

    MarketMakerStrategy



============================================================


生命周期：


启动：

    on_start()


运行：

    on_market_event()


订单更新：

    on_order_update()


成交：

    on_trade()


停止：

    on_stop()



============================================================


设计原则：


Strategy:

    产生交易意图。



不负责：

    - 风控

    - 下单

    - 撮合

    - Portfolio更新



============================================================


"""



from abc import ABC, abstractmethod
from typing import Any, Optional



# ============================================================
# Strategy Base
# ============================================================

class Strategy(ABC):
    """
    所有策略基类。


    """


    def __init__(
        self,
        name: str = "BaseStrategy"
    ):

        """
        初始化策略。


        """

        self.name = name



        # ====================================================
        # 策略运行状态
        # ====================================================

        self.active = False



        # ====================================================
        # 策略内部状态
        #
        # 例如：
        #
        # window
        # position model
        # parameters
        #
        # ====================================================

        self.state = {}



    # ========================================================
    # 启动
    # ========================================================

    def on_start(
        self,
        context: Any = None
    ):
        """
        策略启动。


        Engine启动时调用。


        """

        self.active = True



    # ========================================================
    # 市场事件
    # ========================================================

    @abstractmethod
    def on_market_event(
        self,
        event: Any,
        state: Any
    ):
        """
        接收市场事件。


        高频策略主要入口。


        参数：


        event:

            MarketEvent



        state:

            SystemState



        策略通过：

            OrderBook

            Feature

        获取市场状态。


        """


        pass



    # ========================================================
    # 订单更新
    # ========================================================

    def on_order_update(
        self,
        order_update: Any,
        state: Any
    ):
        """
        订单状态变化。


        例如：

        Submitted

        Accepted

        Cancelled

        Rejected



        """

        pass



    # ========================================================
    # 成交通知
    # ========================================================

    def on_trade(
        self,
        trade: Any,
        state: Any
    ):
        """
        成交通知。


        """

        pass



    # ========================================================
    # 停止
    # ========================================================

    def on_stop(
        self,
        context: Any = None
    ):
        """
        策略停止。


        """

        self.active = False



    # ========================================================
    # 状态
    # ========================================================

    def get_state(
        self
    ) -> dict:
        """
        返回策略内部状态。


        """

        return {

            "name":
                self.name,


            "active":
                self.active,


            "state":
                self.state,

        }



    # ========================================================
    # 参数更新
    # ========================================================

    def update_parameters(
        self,
        params: dict
    ):
        """
        动态更新策略参数。


        用于：

        Web Dashboard

        参数调整。



        """

        for key, value in params.items():

            setattr(
                self,
                key,
                value
            )