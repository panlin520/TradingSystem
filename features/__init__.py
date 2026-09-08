"""
features/__init__.py

============================================================
Market Feature Package
============================================================

职责：

    管理高频交易系统市场特征计算模块。



输入：

    L3 OrderBook


输出：

    Strategy 可使用的特征数据。



============================================================


核心特征：

Market Microstructure


包括：


1.
Mid Price


    (Bid + Ask) / 2



2.
Spread


    Ask - Bid



3.
Micro Price


    (Ask*BidSize + Bid*AskSize)

    /

    (BidSize + AskSize)



4.
Order Imbalance


    (BidVolume - AskVolume)

    /

    (BidVolume + AskVolume)



5.
Order Flow


    主动买卖压力



6.
Queue Information


    队列位置


============================================================


设计原则：


Feature Layer:

        OrderBook

             |

             v

        Features



Strategy:

        只读取Features


不要：

        Strategy直接修改Book



============================================================

"""


# ============================================================
# Version
# ============================================================

__version__ = "0.1.0"



# ============================================================
# Public API
#
# Feature模块完成后在此导出
#
# ============================================================


__all__ = [

]