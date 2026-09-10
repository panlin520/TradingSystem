"""
execution/order.py

============================================================
Execution Order Compatibility Module
============================================================

正式订单模型统一定义于：

    order/order.py

本模块仅保留旧 import 路径兼容：

    from execution.order import Order

等价于：

    from order.order import Order

这样可以避免项目中出现两套不同的：

    Order
    OrderSide
    OrderType
    OrderStatus

尤其避免两个独立 Enum 类型导致：

    execution.order.OrderSide.BUY
        !=
    order.order.OrderSide.BUY

============================================================

注意：

- 不在本文件重新定义订单模型。
- 新代码应优先从 order 或 order.order 导入。
- 旧测试和旧调用方仍可继续使用 execution.order 导入路径。

============================================================
"""

from order.order import (
    Order,
    OrderSide,
    OrderType,
    OrderStatus,
)


__all__ = [
    "Order",
    "OrderSide",
    "OrderType",
    "OrderStatus",
]
