"""
strategy/signal.py


============================================================

Strategy Signal Definition


============================================================


职责：

    定义策略标准输出信号。



流程：

    Strategy

        ↓

    Signal

        ↓

    Composite Signal

        ↓

    Risk Manager

        ↓

    Execution



============================================================

注意：

    Signal != Order


    Signal:

        策略交易意图


    Order:

        实际交易指令


============================================================

"""


from dataclasses import dataclass, field

from enum import Enum

from typing import Optional, Dict, Any





# ============================================================
# Signal Direction
# ============================================================


class SignalSide(Enum):


    BUY = "BUY"


    SELL = "SELL"


    HOLD = "HOLD"







# ============================================================
# Signal Type
# ============================================================


class SignalType(Enum):


    ENTRY = "ENTRY"


    EXIT = "EXIT"


    CANCEL = "CANCEL"


    NONE = "NONE"







# ============================================================
# Strategy Category
# ============================================================


class StrategyCategory(Enum):


    MEAN_REVERSION = "MEAN_REVERSION"


    MOMENTUM = "MOMENTUM"


    LIQUIDITY = "LIQUIDITY"


    ABSORPTION = "ABSORPTION"


    EXIT = "EXIT"


    UNKNOWN = "UNKNOWN"








# ============================================================
# Trading Signal
# ============================================================


@dataclass(slots=True)
class Signal:



    # ========================================================
    # Direction
    # ========================================================


    side: SignalSide





    # ========================================================
    # Type
    # ========================================================


    signal_type: SignalType = SignalType.ENTRY





    # ========================================================
    # Strategy Category
    # ========================================================


    category: StrategyCategory = (
        StrategyCategory.UNKNOWN
    )





    # ========================================================
    # Price
    # ========================================================


    price: Optional[int] = None





    # ========================================================
    # Size
    # ========================================================


    size: int = 1





    # ========================================================
    # Confidence
    # ========================================================


    confidence: float = 0.0





    # ========================================================
    # Score
    # ========================================================

    score: float = 0.0





    # ========================================================
    # Reason
    # ========================================================


    reason: str = ""





    # ========================================================
    # Timestamp
    # ========================================================


    timestamp: Optional[int] = None





    # ========================================================
    # Strategy Name
    # ========================================================


    strategy: Optional[str] = None





    # ========================================================
    # Metadata
    # ========================================================


    metadata: Dict[str, Any] = field(

        default_factory=dict

    )







    # ========================================================
    # Validation
    # ========================================================


    def is_valid(self) -> bool:


        return (

            self.side != SignalSide.HOLD

            and

            self.signal_type != SignalType.NONE

            and

            self.size > 0

        )







    # ========================================================
    # Entry
    # ========================================================


    def is_entry(self):


        return (

            self.signal_type

            ==

            SignalType.ENTRY

        )






    # ========================================================
    # Exit
    # ========================================================


    def is_exit(self):


        return (

            self.signal_type

            ==

            SignalType.EXIT

        )







    # ========================================================
    # Trade Direction
    # ========================================================


    def is_buy(self):


        return (

            self.side

            ==

            SignalSide.BUY

        )






    def is_sell(self):


        return (

            self.side

            ==

            SignalSide.SELL

        )







    # ========================================================
    # Dict Output
    # ========================================================


    def to_dict(self):


        return {


            "side":

                self.side.value,


            "type":

                self.signal_type.value,


            "category":

                self.category.value,


            "price":

                self.price,


            "size":

                self.size,


            "confidence":

                self.confidence,


            "score":

                self.score,


            "reason":

                self.reason,


            "timestamp":

                self.timestamp,


            "strategy":

                self.strategy,


            "metadata":

                self.metadata

        }