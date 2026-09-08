"""
execution/order.py


============================================================
Execution Order Definition
============================================================


职责：

    定义交易系统统一订单对象。


============================================================


流程：


Strategy

    |

    v


Signal


    |

    v


Risk Manager


    |

    v


Order


    |

    v


Execution Engine



============================================================


支持：

    Limit Order

    Market Order

    Stop Order (future)



============================================================


订单生命周期：


CREATED

    |

SUBMITTED

    |

ACCEPTED

    |

PARTIAL_FILLED

    |

FILLED


异常：

CANCELLED

REJECTED



============================================================


注意：

OrderBook中的Order：

    代表市场挂单



Execution中的Order：

    代表自己的交易订单



两者不同。


============================================================

"""


from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
import uuid



# ============================================================
# Order Side
# ============================================================


class OrderSide(Enum):

    """
    交易方向。
    """


    BUY = "BUY"


    SELL = "SELL"




# ============================================================
# Order Type
# ============================================================


class OrderType(Enum):

    """
    订单类型。
    """


    LIMIT = "LIMIT"


    MARKET = "MARKET"


    STOP = "STOP"




# ============================================================
# Order Status
# ============================================================


class OrderStatus(Enum):

    """
    订单状态。
    """


    CREATED = "CREATED"


    SUBMITTED = "SUBMITTED"


    ACCEPTED = "ACCEPTED"


    PARTIAL_FILLED = "PARTIAL_FILLED"


    FILLED = "FILLED"


    CANCELLED = "CANCELLED"


    REJECTED = "REJECTED"






# ============================================================
# Order
# ============================================================


@dataclass(slots=True)
class Order:

    """
    系统交易订单。


    不是 OrderBook 中的市场订单。



    ========================================================

    """



    # ========================================================
    # 系统订单ID
    # ========================================================

    order_id: str = field(
        default_factory=lambda:
            str(uuid.uuid4())
    )



    # ========================================================
    # 交易品种
    # ========================================================

    symbol: str = ""



    # ========================================================
    # 买卖方向
    # ========================================================

    side: OrderSide = OrderSide.BUY




    # ========================================================
    # 类型
    # ========================================================

    order_type: OrderType = OrderType.LIMIT




    # ========================================================
    # 价格
    #
    # Limit订单使用
    #
    # ========================================================

    price: Optional[int] = None




    # ========================================================
    # 数量
    # ========================================================

    quantity: int = 0




    # ========================================================
    # 已成交数量
    # ========================================================

    filled_quantity: int = 0




    # ========================================================
    # 状态
    # ========================================================

    status: OrderStatus = OrderStatus.CREATED




    # ========================================================
    # 创建时间
    # ========================================================

    timestamp: Optional[int] = None




    # ========================================================
    # 策略来源
    # ========================================================

    strategy: Optional[str] = None




    # ========================================================
    # 附加信息
    # ========================================================

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )





    # ========================================================
    # Validate
    # ========================================================

    def validate(self) -> bool:

        """
        订单合法性检查。


        ExecutionEngine提交订单前调用。


        检查：

            symbol

            quantity

            side

            order_type

            LIMIT price


        """



        # -----------------------------
        # Symbol
        # -----------------------------

        if not self.symbol:

            return False



        # -----------------------------
        # Quantity
        # -----------------------------

        if self.quantity <= 0:

            return False




        # -----------------------------
        # Side
        # -----------------------------

        if not isinstance(
            self.side,
            OrderSide
        ):

            return False




        # -----------------------------
        # Type
        # -----------------------------

        if not isinstance(
            self.order_type,
            OrderType
        ):

            return False




        # -----------------------------
        # Limit Price
        # -----------------------------

        if (
            self.order_type == OrderType.LIMIT
            and self.price is None
        ):

            return False




        return True






    # ========================================================
    # 剩余数量
    # ========================================================


    def remaining(self) -> int:

        """
        剩余未成交数量。
        """


        return (
            self.quantity
            -
            self.filled_quantity
        )






    # ========================================================
    # 成交更新
    # ========================================================


    def fill(
        self,
        quantity: int
    ):

        """
        更新成交数量。


        注意：

        成交价格属于 Fill。

        Order 不保存成交价格。


        """



        self.filled_quantity += quantity



        if self.remaining() <= 0:


            self.status = OrderStatus.FILLED


        else:


            self.status = (
                OrderStatus.PARTIAL_FILLED
            )






    # ========================================================
    # 提交
    # ========================================================


    def submit(self):

        """
        提交订单。
        """


        self.status = (
            OrderStatus.SUBMITTED
        )






    # ========================================================
    # 接受
    # ========================================================


    def accept(self):

        """
        市场接受订单。
        """


        self.status = (
            OrderStatus.ACCEPTED
        )






    # ========================================================
    # 取消
    # ========================================================


    def cancel(self):

        """
        取消订单。
        """


        self.status = (
            OrderStatus.CANCELLED
        )






    # ========================================================
    # 拒绝
    # ========================================================


    def reject(
        self
    ):

        """
        拒绝订单。
        """


        self.status = (
            OrderStatus.REJECTED
        )






    # ========================================================
    # 是否完成
    # ========================================================


    def is_done(
        self
    ) -> bool:

        """
        判断订单是否结束。
        """


        return self.status in (

            OrderStatus.FILLED,

            OrderStatus.CANCELLED,

            OrderStatus.REJECTED,

        )






    # ========================================================
    # Snapshot
    # ========================================================


    def snapshot(
        self
    ) -> dict:

        """
        状态快照。
        """


        return self.to_dict()






    # ========================================================
    # 输出
    # ========================================================


    def to_dict(
        self
    ) -> dict:

        """
        Web/API格式。
        """



        return {


            "order_id":
                self.order_id,



            "symbol":
                self.symbol,



            "side":
                self.side.value,



            "type":
                self.order_type.value,



            "price":
                self.price,



            "quantity":
                self.quantity,



            "filled":
                self.filled_quantity,



            "remaining":
                self.remaining(),



            "status":
                self.status.value,



            "strategy":
                self.strategy,

        }