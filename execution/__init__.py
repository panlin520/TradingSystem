"""
execution/__init__.py

============================================================
Execution Package
============================================================

职责：

    管理交易执行系统。

============================================================

支持模式：

BACKTEST
    Historical Data
        |
        v
    Execution Simulator

PAPER
    Real Market Data
        |
        v
    Simulated Execution

LIVE
    Exchange / Broker API
        |
        v
    Real Execution

============================================================

执行流程：

Signal
   |
   v
Order
   |
   v
Execution
   |
   v
Fill
   |
   v
Portfolio

============================================================

原则：

Backtest / Paper / Live 共享：

    Order 结构
    Execution 接口
    Risk 接口

避免三套交易代码。

============================================================
"""


__version__ = "0.2.0"


# ============================================================
# Canonical Runtime API
# ============================================================

from .execution_engine import (
    ExecutionEngine,
    ExecutionMode,
)


# ============================================================
# Canonical Fill
# ============================================================
#
# 当前项目中的独立 Fill 定义位于 execution/fill.py。
# 包级导出统一从这里获取，避免 __init__.py 与
# execution_engine.py 内部 Fill 定义产生歧义。
# ============================================================

from .fill import Fill


# ============================================================
# Execution Abstractions
# ============================================================

from .order_executor import OrderExecutor
from .simulator import ExecutionSimulator


__all__ = [
    "ExecutionEngine",
    "ExecutionMode",
    "Fill",
    "OrderExecutor",
    "ExecutionSimulator",
]
