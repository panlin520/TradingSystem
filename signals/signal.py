"""
signal/signal.py


============================================================

Trading Signal Definition


============================================================


职责：

    Strategy
        ↓
    Signal
        ↓
    RiskManager
        ↓
    Order


负责：

    - 定义交易意图
    - 保存策略产生的交易信号
    - Signal数据校验
    - Signal状态描述
    - Signal快照


不负责：

    - 风控
    - 下单
    - 撮合
    - 成交
    - 仓位管理


============================================================


设计目标：

    同时支持：

        BACKTEST
        PAPER
        LIVE


============================================================

"""


from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from typing import Any, Dict, Optional




# ============================================================
# Signal Side
# ============================================================


class SignalSide(Enum):
    """
    信号方向。


    BUY:
        开多 / 买入


    SELL:
        开空 / 卖出


    FLAT:
        平仓
    """

    BUY = "BUY"

    SELL = "SELL"

    FLAT = "FLAT"




# ============================================================
# Signal Type
# ============================================================


class SignalType(Enum):
    """
    信号类型。


    ENTRY:
        开仓信号


    EXIT:
        平仓信号


    REVERSAL:
        反转信号


    """

    ENTRY = "ENTRY"

    EXIT = "EXIT"

    REVERSAL = "REVERSAL"




# ============================================================
# Signal Status
# ============================================================


class SignalStatus(Enum):
    """
    Signal生命周期。


    CREATED:
        Strategy刚生成


    APPROVED:
        Risk通过


    REJECTED:
        Risk拒绝


    EXECUTED:
        已执行


    """

    CREATED = "CREATED"

    APPROVED = "APPROVED"

    REJECTED = "REJECTED"

    EXECUTED = "EXECUTED"




# ============================================================
# Signal
# ============================================================


@dataclass
class Signal:
    """
    Strategy交易信号。


    示例：

        signal = Signal(
            symbol="ESU6",
            side=SignalSide.BUY,
            quantity=1,
            strategy="mean_reversion"
        )


    """



    # ========================================================
    # 基础交易信息
    # ========================================================


    symbol: str


    side: SignalSide


    quantity: int



    # ========================================================
    # Signal类型
    # ========================================================


    signal_type: SignalType = SignalType.ENTRY




    # ========================================================
    # 策略来源
    # ========================================================


    strategy: str = "UNKNOWN"




    # ========================================================
    # 价格信息
    # ========================================================


    price: Optional[float] = None




    # ========================================================
    # 信号质量
    # ========================================================


    confidence: float = 0.0




    # ========================================================
    # 时间
    # ========================================================


    timestamp: datetime = field(
        default_factory=lambda:
        datetime.now(timezone.utc)
    )




    # ========================================================
    # 状态
    # ========================================================


    status: SignalStatus = SignalStatus.CREATED




    # ========================================================
    # 扩展数据
    # ========================================================


    metadata: Dict[str, Any] = field(
        default_factory=dict
    )




    # ========================================================
    # Validation
    # ========================================================


    def validate(self) -> bool:
        """
        Signal合法性检查。


        检查：

            symbol
            side
            quantity
            confidence


        """



        if not self.symbol:

            return False



        if not isinstance(
            self.side,
            SignalSide
        ):

            return False



        if self.quantity <= 0:

            return False



        if not (
            0.0
            <=
            self.confidence
            <=
            1.0
        ):

            return False



        return True





    # ========================================================
    # Approve
    # ========================================================


    def approve(self):
        """
        Risk通过。
        """

        self.status = SignalStatus.APPROVED




    # ========================================================
    # Reject
    # ========================================================


    def reject(
        self,
        reason: str
    ):
        """
        Risk拒绝。
        """

        self.status = SignalStatus.REJECTED

        self.metadata["reject_reason"] = reason





    # ========================================================
    # Execute
    # ========================================================


    def executed(self):
        """
        成交执行完成。
        """

        self.status = SignalStatus.EXECUTED





    # ========================================================
    # Snapshot
    # ========================================================


    def snapshot(self) -> dict:
        """
        Signal状态快照。

        用于：

            logging
            debug
            replay
            UI


        """

        return {

            "symbol":
                self.symbol,


            "side":
                self.side.value,


            "quantity":
                self.quantity,


            "signal_type":
                self.signal_type.value,


            "strategy":
                self.strategy,


            "price":
                self.price,


            "confidence":
                self.confidence,


            "timestamp":
                self.timestamp.isoformat(),


            "status":
                self.status.value,


            "metadata":
                self.metadata.copy(),

        }





    # ========================================================
    # String
    # ========================================================


    def __repr__(self):

        return (
            "Signal("
            f"{self.symbol}, "
            f"{self.side.value}, "
            f"qty={self.quantity}, "
            f"strategy={self.strategy}, "
            f"status={self.status.value}"
            ")"
        )