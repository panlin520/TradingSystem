"""
execution/__init__.py

============================================================
Execution Package
============================================================

职责：

    管理交易执行系统。

============================================================

正式 Runtime 链：

Signal
   |
   v
Order
   |
   v
ExecutionEngine
   |
   v
Fill
   |
   v
Portfolio

============================================================

Canonical API：

    ExecutionEngine
    ExecutionMode
    Fill

说明：

    - Order 的 canonical 定义位于 order/order.py
    - Fill 的 canonical 定义位于 execution/fill.py
    - ExecutionEngine 是当前正式执行入口

不再从 package 根目录导出：

    OrderExecutor
    ExecutionSimulator

这样避免与 ExecutionEngine 形成多套并行执行入口。

============================================================
"""


__version__ = "0.2.0"


from .execution_engine import (
    ExecutionEngine,
    ExecutionMode,
)

from .fill import Fill


__all__ = [
    "ExecutionEngine",
    "ExecutionMode",
    "Fill",
]
