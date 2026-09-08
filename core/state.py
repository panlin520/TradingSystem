"""
core/state.py

============================================================
Trading System State
============================================================

职责：

    保存整个交易系统运行状态。


设计目标：

    所有模块共享统一状态。


包括：

    - 当前运行模式
    - 当前系统时间
    - 当前事件信息
    - OrderBook状态
    - Portfolio状态
    - Strategy状态
    - Risk状态
    - Execution状态


============================================================


核心原则：

State 是数据容器。

不包含业务逻辑。


不要在这里：

    - 撮合订单
    - 更新盘口
    - 计算指标
    - 产生信号


============================================================


系统结构：

                Trading Engine

                      |

                      v

                 SystemState


        +-------------+-------------+

        |             |             |

     OrderBook   Portfolio     Risk


        |

     Strategy


============================================================

"""


from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from core.clock import ClockMode



# ============================================================
# System State
# ============================================================

@dataclass
class SystemState:
    """
    整个交易系统状态。


    一个实例代表：

        当前系统快照。



    用于：

        Backtest

        Paper Trading

        Live Trading



    """



    # ========================================================
    # 系统运行模式
    # ========================================================

    mode: ClockMode = ClockMode.BACKTEST



    # ========================================================
    # 当前系统时间
    # ========================================================

    timestamp: Optional[int] = None



    # ========================================================
    # 已处理事件数量
    # ========================================================

    event_count: int = 0



    # ========================================================
    # 当前事件
    # ========================================================

    last_event: Optional[Any] = None



    # ========================================================
    # OrderBook状态
    #
    # 实际对象由OrderBook模块注入
    #
    # ========================================================

    orderbook: Optional[Any] = None



    # ========================================================
    # Portfolio状态
    #
    # 实际对象由Portfolio模块注入
    #
    # ========================================================

    portfolio: Optional[Any] = None



    # ========================================================
    # Strategy状态
    # ========================================================

    strategy_state: Dict[str, Any] = field(
        default_factory=dict
    )



    # ========================================================
    # Risk状态
    # ========================================================

    risk_state: Dict[str, Any] = field(
        default_factory=dict
    )



    # ========================================================
    # Execution状态
    # ========================================================

    execution_state: Dict[str, Any] = field(
        default_factory=dict
    )



    # ========================================================
    # 系统统计
    # ========================================================

    metrics: Dict[str, Any] = field(
        default_factory=dict
    )



    # ========================================================
    # 更新事件
    # ========================================================

    def update_event(
        self,
        event: Any
    ):
        """
        更新最新市场事件。


        Engine每处理一个MarketEvent调用。


        """

        self.last_event = event


        self.timestamp = event.ts_event


        self.event_count += 1



    # ========================================================
    # 更新OrderBook
    # ========================================================

    def set_orderbook(
        self,
        orderbook: Any
    ):
        """
        注入OrderBook对象。
        """

        self.orderbook = orderbook



    # ========================================================
    # 更新Portfolio
    # ========================================================

    def set_portfolio(
        self,
        portfolio: Any
    ):
        """
        注入Portfolio对象。
        """

        self.portfolio = portfolio



    # ========================================================
    # 设置策略状态
    # ========================================================

    def update_strategy_state(
        self,
        key: str,
        value: Any
    ):
        """
        更新策略状态。

        例如：

            signals
            confidence
            position


        """

        self.strategy_state[key] = value



    # ========================================================
    # 更新风险状态
    # ========================================================

    def update_risk_state(
        self,
        key: str,
        value: Any
    ):
        """
        更新风险状态。
        """

        self.risk_state[key] = value



    # ========================================================
    # 更新执行状态
    # ========================================================

    def update_execution_state(
        self,
        key: str,
        value: Any
    ):
        """
        更新执行状态。
        """

        self.execution_state[key] = value



    # ========================================================
    # 添加统计
    # ========================================================

    def update_metric(
        self,
        key: str,
        value: Any
    ):
        """
        更新系统指标。

        例如：

            latency

            throughput

            pnl

            drawdown

        """

        self.metrics[key] = value



    # ========================================================
    # 快照
    # ========================================================

    def snapshot(self) -> dict:
        """
        返回当前系统状态摘要。


        用于：

        - Web Dashboard
        - 日志
        - 回测报告


        """

        return {

            "mode":
                self.mode.value,


            "timestamp":
                self.timestamp,


            "event_count":
                self.event_count,


            "strategy":
                self.strategy_state,


            "risk":
                self.risk_state,


            "execution":
                self.execution_state,


            "metrics":
                self.metrics,

        }