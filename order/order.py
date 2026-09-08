"""
order/order.py


============================================================

Order Management


============================================================


职责：

    Signal
        ↓
    Order
        ↓
    Execution Engine
        ↓
    Fill


负责：

    - Order数据结构
    - Order生命周期管理
    - Order状态转换
    - Order类型定义
    - 下单参数校验


不负责：

    - Strategy
    - Risk
    - Execution撮合
    - Portfolio
    - Position


============================================================


支持：

    BACKTEST

    PAPER

    LIVE


============================================================

"""


from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import uuid




# ============================================================
# Order Side
# ============================================================


class OrderSide(Enum):
    """
    Order方向。


    BUY:

        买入 / 开多


    SELL:

        卖出 / 开空


    """

    BUY = "BUY"

    SELL = "SELL"




# ============================================================
# Order Type
# ============================================================


class OrderType(Enum):
    """
    订单类型。


    MARKET:

        市价单


    LIMIT:

        限价单


    STOP:

        Stop订单


    """

    MARKET = "MARKET"

    LIMIT = "LIMIT"

    STOP = "STOP"




# ============================================================
# Order Status
# ============================================================


class OrderStatus(Enum):
    """
    Order生命周期。


    CREATED:

        创建


    SUBMITTED:

        已提交


    ACCEPTED:

        交易系统接受


    PARTIAL_FILLED:

        部分成交


    FILLED:

        完全成交


    CANCELLED:

        已取消


    REJECTED:

        拒绝


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


@dataclass
class Order:
    """
    交易订单。


    Signal转换后生成。


    示例：


        order = Order(

            symbol="ESU6",

            side=OrderSide.BUY,

            quantity=1,

            order_type=OrderType.MARKET

        )


    """



    # ========================================================
    # Identity
    # ========================================================


    order_id: str = field(
        default_factory=lambda:
        str(uuid.uuid4())
    )



    # ========================================================
    # Trading Information
    # ========================================================


    symbol: str = ""


    side: OrderSide = OrderSide.BUY


    quantity: int = 0



    order_type: OrderType = OrderType.MARKET




    # ========================================================
    # Price
    # ========================================================


    price: Optional[float] = None


    stop_price: Optional[float] = None





    # ========================================================
    # Execution State
    # ========================================================


    filled_quantity: int = 0


    average_fill_price: float = 0.0




    status: OrderStatus = (
        OrderStatus.CREATED
    )




    # ========================================================
    # Metadata
    # ========================================================


    strategy: str = "UNKNOWN"


    signal_id: Optional[str] = None



    timestamp: datetime = field(
        default_factory=lambda:
        datetime.now(timezone.utc)
    )



    metadata: Dict[str, Any] = field(
        default_factory=dict
    )





    # ========================================================
    # Validation
    # ========================================================


    def validate(self) -> bool:
        """
        Order合法性检查。



        """

        if not self.symbol:

            return False



        if not isinstance(
            self.side,
            OrderSide
        ):

            return False



        if self.quantity <= 0:

            return False



        if (
            self.order_type
            ==
            OrderType.LIMIT
            and
            self.price is None
        ):

            return False



        return True





    # ========================================================
    # Remaining Quantity
    # ========================================================


    @property
    def remaining_quantity(self) -> int:
        """
        剩余未成交数量。
        """

        return (
            self.quantity
            -
            self.filled_quantity
        )





    # ========================================================
    # Submit
    # ========================================================


    def submit(self):
        """
        Order提交。
        """

        self.status = (
            OrderStatus.SUBMITTED
        )





    # ========================================================
    # Accept
    # ========================================================


    def accept(self):
        """
        Execution Engine接受订单。
        """

        self.status = (
            OrderStatus.ACCEPTED
        )





    # ========================================================
    # Fill
    # ========================================================

    def fill(
            self,
            quantity: int
    ):
        """
        更新订单成交数量。

        注意：

        Order 不保存成交价格。

        成交价格属于 Fill。

        Order 只维护：

            - filled_quantity
            - status

        """

        if quantity <= 0:
            raise ValueError(
                "fill quantity must > 0"
            )

        if quantity > self.remaining_quantity:
            raise ValueError(
                "fill exceeds order quantity"
            )

        # ==========================================
        # 更新成交数量
        # ==========================================

        self.filled_quantity += quantity

        # ==========================================
        # 更新订单状态
        # ==========================================

        if self.filled_quantity >= self.quantity:

            self.filled_quantity = self.quantity

            self.status = OrderStatus.FILLED


        else:

            self.status = OrderStatus.PARTIALLY_FILLED




    # ========================================================
    # Cancel
    # ========================================================


    def cancel(self):
        """
        取消订单。
        """

        self.status = (
            OrderStatus.CANCELLED
        )





    # ========================================================
    # Reject
    # ========================================================


    def reject(
        self,
        reason: str
    ):
        """
        拒绝订单。
        """

        self.status = (
            OrderStatus.REJECTED
        )


        self.metadata[
            "reject_reason"
        ] = reason





    # ========================================================
    # Snapshot
    # ========================================================


    def snapshot(self) -> dict:
        """
        Order状态快照。


        用于：

            logging

            replay

            UI


        """

        return {

            "order_id":
                self.order_id,


            "symbol":
                self.symbol,


            "side":
                self.side.value,


            "quantity":
                self.quantity,


            "filled_quantity":
                self.filled_quantity,


            "remaining_quantity":
                self.remaining_quantity,


            "order_type":
                self.order_type.value,


            "price":
                self.price,


            "average_fill_price":
                self.average_fill_price,


            "status":
                self.status.value,


            "strategy":
                self.strategy,


            "timestamp":
                self.timestamp.isoformat(),


            "metadata":
                self.metadata.copy(),

        }





    # ========================================================
    # Representation
    # ========================================================


    def __repr__(self):

        return (

            "Order("

            f"{self.symbol}, "

            f"{self.side.value}, "

            f"qty={self.quantity}, "

            f"status={self.status.value}"

            ")"

        )