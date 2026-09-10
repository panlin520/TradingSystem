"""
execution/fill.py

============================================================
Canonical Execution Fill
============================================================

职责：

    ExecutionEngine
        ↓
      Fill
        ↓
    Portfolio.on_fill()

本文件是 execution 层唯一 Fill 数据模型。

负责：

- 成交 ID
- Order ID
- Symbol
- Side
- 成交数量
- normalized 成交价格
- 时间戳
- metadata
- snapshot

不负责：

- Order 生命周期
- Risk
- Position
- PnL

============================================================

价格契约：

    Fill.price 必须是 normalized trading price。

    Databento raw nano-price 不允许直接进入 Portfolio。

============================================================
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict
import uuid


@dataclass
class Fill:
    """
    系统统一成交对象。

    fill_id 放在带默认值字段区域，保证旧调用：

        Fill(
            order_id=...,
            symbol=...,
            side=...,
            quantity=...,
            price=...,
        )

    继续兼容；ExecutionEngine 也可以显式传入 fill_id。
    """

    order_id: str
    symbol: str
    side: object
    quantity: int
    price: float

    fill_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self):
        if not self.order_id:
            raise ValueError(
                "Fill requires order_id"
            )

        if not self.symbol:
            raise ValueError(
                "Fill requires symbol"
            )

        if self.quantity <= 0:
            raise ValueError(
                "Fill quantity must be positive"
            )

        if self.price is None:
            raise ValueError(
                "Fill requires price"
            )

        self.price = float(
            self.price
        )

        if self.price <= 0.0:
            raise ValueError(
                "Fill price must be positive"
            )

        self.symbol = str(
            self.symbol
        ).upper()

        if self.timestamp is None:
            self.timestamp = datetime.now(
                timezone.utc
            )

    def snapshot(self) -> dict:
        """
        Fill 状态快照。
        """

        side = getattr(
            self.side,
            "value",
            self.side,
        )

        timestamp = (
            self.timestamp.isoformat()
            if hasattr(
                self.timestamp,
                "isoformat",
            )
            else self.timestamp
        )

        return {
            "fill_id": self.fill_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": side,
            "quantity": self.quantity,
            "price": self.price,
            "timestamp": timestamp,
            "metadata": self.metadata.copy(),
        }
