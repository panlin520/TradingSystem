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


    Exchange/Broker API

          |

          v

    Real Execution



============================================================


核心模块：


order.py


    定义订单对象



order_manager.py


    管理订单生命周期



simulator.py


    模拟成交



broker.py


    实盘交易接口



============================================================


执行流程：


Signal


   |

   v


Order


   |

   v


Order Manager


   |

   v


Execution Engine


   |

   v


Fill


   |

   v


Portfolio



============================================================


原则：


Backtest / Paper / Live


共享：

    Order结构

    Execution接口

    Risk接口



避免：

    三套交易代码。



============================================================

"""


# ============================================================
# Version
# ============================================================

__version__ = "0.1.0"



# ============================================================
# Public API
#
# 后续模块完成后导出
#
# ============================================================


from .execution_engine import (
    ExecutionEngine,
    ExecutionMode,
    Fill,
)


__all__ = [
    "ExecutionEngine",
    "ExecutionMode",
    "Fill",
]