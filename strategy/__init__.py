"""
strategy/__init__.py

============================================================
Strategy Package
============================================================

职责：

    管理交易策略模块。


============================================================


策略设计：

所有策略必须继承：

    Strategy Base



统一接口：


    on_start()

        策略启动



    on_market_event()

        接收市场事件



    on_order_update()

        订单状态更新



    on_trade()

        成交通知



    on_stop()

        停止策略



============================================================


支持策略：


未来：


1.

L3 Scalping Strategy


利用：

    Queue Position

    Order Flow

    Micro Price

    Imbalance



2.

Mean Reversion


利用：

    Price Deviation

    Volatility

    Order Flow Reversal



3.

Order Imbalance


利用：

    Bid/Ask Pressure



4.

Market Making


利用：

    Spread

    Inventory

    Queue


============================================================


原则：

Strategy:

    产生 Signal


不负责：

    - 下单

    - 风控

    - 撮合


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

Execution Engine


============================================================

"""


# ============================================================
# Version
# ============================================================

__version__ = "0.1.0"



# ============================================================
# Public API
#
# 后续添加：
#
# Strategy
# Signal
# StrategyManager
#
# ============================================================


__all__ = [

]