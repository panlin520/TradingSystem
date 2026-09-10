"""
execution/fill.py

============================================================
Fill Event
============================================================

职责：

    Execution
        |
        v
      Fill
        |
        v
    Portfolio.on_fill()

负责：

- 成交事件定义
- 成交价格
- 成交数量
- 成交方向

不负责：

- Order管理
- 风控
- Position
- PnL

价格契约：

Fill.price 必须使用 normalized price。

禁止：

Databento nano price 直接进入 Portfolio。

============================================================
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Fill:
    """
    成交对象。
    """

    order_id: str

    symbol: str

    side: object

    quantity: int

    price: float

    timestamp: Optional[datetime] = None


    def __post_init__(self):

        if not self.symbol:

            raise ValueError(
                "Fill requires symbol"
            )


        if self.quantity <= 0:

            raise ValueError(
                "Fill quantity must be positive"
            )


        if self.price <= 0:

            raise ValueError(
                "Fill price must be positive"
            )


        self.symbol = str(
            self.symbol
        ).upper()
