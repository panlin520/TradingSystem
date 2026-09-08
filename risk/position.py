"""
risk/position.py

============================================================
Position Management
============================================================

职责：

    管理账户当前持仓。


============================================================


仓位生命周期：


      Entry

        |

        v


    FLAT


        |

        v


     LONG / SHORT


        |

        v


      Exit


        |

        v


     FLAT



============================================================


用于：


Risk Manager


Portfolio


PnL Engine



============================================================


不负责：

    - 下单

    - 撮合

    - 策略判断



============================================================

"""


from dataclasses import dataclass
from enum import Enum
from typing import Optional




# ============================================================
# Position Side
# ============================================================

class PositionSide(Enum):
    """
    持仓方向。


    """

    FLAT = "FLAT"


    LONG = "LONG"


    SHORT = "SHORT"





# ============================================================
# Position
# ============================================================

@dataclass(slots=True)
class Position:
    """
    单品种持仓。


    ========================================================


    示例：


        ES


        LONG 2


        avg_price = 6959.75



    ========================================================


    """



    # ========================================================
    # 合约
    # ========================================================

    symbol: str



    # ========================================================
    # 方向
    # ========================================================

    side: PositionSide = PositionSide.FLAT



    # ========================================================
    # 数量
    # ========================================================

    quantity: int = 0



    # ========================================================
    # 平均成本
    # ========================================================

    average_price: float = 0.0



    # ========================================================
    # 已实现盈亏
    # ========================================================

    realized_pnl: float = 0.0



    # ========================================================
    # 最新价格
    # ========================================================

    market_price: Optional[float] = None




    # ========================================================
    # 开仓
    # ========================================================

    def open(
        self,
        side: PositionSide,
        quantity: int,
        price: float
    ):
        """
        建立仓位。


        """

        self.side = side


        self.quantity = quantity


        self.average_price = price




    # ========================================================
    # 增加仓位
    # ========================================================

    def add(
        self,
        quantity: int,
        price: float
    ):
        """
        增加同方向仓位。


        """

        total_cost = (

            self.average_price
            *
            self.quantity

            +

            price
            *
            quantity

        )


        self.quantity += quantity



        self.average_price = (

            total_cost
            /
            self.quantity

        )




    # ========================================================
    # 减少仓位
    # ========================================================

    def reduce(
        self,
        quantity: int,
        price: float
    ):
        """
        减仓。


        """

        if quantity > self.quantity:

            quantity = self.quantity



        pnl = 0.0



        if self.side == PositionSide.LONG:


            pnl = (

                price
                -
                self.average_price

            ) * quantity



        elif self.side == PositionSide.SHORT:


            pnl = (

                self.average_price
                -
                price

            ) * quantity



        self.realized_pnl += pnl



        self.quantity -= quantity



        if self.quantity == 0:

            self.side = PositionSide.FLAT

            self.average_price = 0.0




    # ========================================================
    # 更新市场价格
    # ========================================================

    def update_market_price(
        self,
        price: float
    ):
        """
        更新最新价格。


        """

        self.market_price = price




    # ========================================================
    # 未实现盈亏
    # ========================================================

    def unrealized_pnl(
        self
    ) -> float:
        """
        未实现盈亏。


        """

        if self.market_price is None:

            return 0.0



        if self.side == PositionSide.LONG:


            return (

                self.market_price
                -
                self.average_price

            ) * self.quantity




        elif self.side == PositionSide.SHORT:


            return (

                self.average_price
                -
                self.market_price

            ) * self.quantity




        return 0.0




    # ========================================================
    # 名义价值
    # ========================================================

    def exposure(
        self
    ) -> float:
        """
        当前风险敞口。


        """

        if self.market_price is None:

            return 0.0



        return (

            abs(self.quantity)

            *

            self.market_price

        )




    # ========================================================
    # 清仓
    # ========================================================

    def clear(self):
        """
        清空仓位。


        """

        self.side = PositionSide.FLAT


        self.quantity = 0


        self.average_price = 0.0




    # ========================================================
    # 状态
    # ========================================================

    def is_flat(
        self
    ) -> bool:
        """
        是否空仓。


        """

        return (

            self.side == PositionSide.FLAT

            or

            self.quantity == 0

        )




    # ========================================================
    # 输出
    # ========================================================

    def snapshot(
        self
    ) -> dict:
        """
        状态输出。


        """

        return {


            "symbol":
                self.symbol,


            "side":
                self.side.value,


            "quantity":
                self.quantity,


            "average_price":
                self.average_price,


            "market_price":
                self.market_price,


            "realized_pnl":
                self.realized_pnl,


            "unrealized_pnl":
                self.unrealized_pnl(),

        }