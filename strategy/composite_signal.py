"""
strategy/composite_signal.py


============================================================

Composite Signal Engine


============================================================


职责：

    接收多个策略 Signal

            |
            v

    过滤

            |
            v

    加权融合

            |
            v

    输出最终交易信号



============================================================


策略体系：

Market Regime

        |

Strategy Signals


    Mean Reversion

    Momentum Breakout

    Liquidity Vacuum

    Absorption / Refill


        |

Queue / OFI / Trade Flow Confirmation


        |

Composite Signal


============================================================

"""


from dataclasses import dataclass, field

from typing import List, Dict, Any



from strategy.signal import (

    Signal,

    SignalSide,

    SignalType,

    StrategyCategory,

)







# ============================================================
# Composite Result
# ============================================================


@dataclass(slots=True)
class CompositeSignal:


    """
    多策略融合后的最终信号。
    """


    side: SignalSide = SignalSide.HOLD


    signal_type: SignalType = SignalType.NONE


    category: StrategyCategory = (
        StrategyCategory.UNKNOWN
    )


    confidence: float = 0.0


    score: float = 0.0


    reasons: List[str] = field(
        default_factory=list
    )


    strategies: List[str] = field(
        default_factory=list
    )


    metadata: Dict[str, Any] = field(
        default_factory=dict
    )





    def is_trade(self):

        return (

            self.side

            !=

            SignalSide.HOLD

            and

            self.signal_type

            !=

            SignalType.NONE

        )





    def is_entry(self):

        return (

            self.signal_type

            ==

            SignalType.ENTRY

        )





    def is_exit(self):

        return (

            self.signal_type

            ==

            SignalType.EXIT

        )









# ============================================================
# Composite Engine
# ============================================================


class CompositeSignalEngine:



    def __init__(

        self,

        min_confidence=0.6,

        min_score=1.0

    ):


        self.min_confidence = (
            min_confidence
        )


        self.min_score = (
            min_score
        )









    # ========================================================
    # Combine
    # ========================================================


    def combine(

        self,

        signals: List[Signal],

        context=None

    ) -> CompositeSignal:



        if not signals:

            return CompositeSignal()






        # ----------------------------------------------------
        # Filter invalid
        # ----------------------------------------------------


        valid = [

            s

            for s in signals

            if s.is_valid()

        ]



        if not valid:

            return CompositeSignal()






        # ----------------------------------------------------
        # Exit priority
        # ----------------------------------------------------


        exits = [

            s

            for s in valid

            if s.signal_type
            ==
            SignalType.EXIT

        ]



        if exits:


            return self._merge(

                exits

            )







        # ----------------------------------------------------
        # Regime permission
        # ----------------------------------------------------


        if context is not None:


            if not context.can_trade():

                return CompositeSignal()







        # ----------------------------------------------------
        # Entry
        # ----------------------------------------------------


        entries = [

            s

            for s in valid

            if s.signal_type
            ==
            SignalType.ENTRY

        ]



        if not entries:

            return CompositeSignal()





        return self._merge(

            entries

        )









    # ========================================================
    # Merge
    # ========================================================


    def _merge(

        self,

        signals: List[Signal]

    ) -> CompositeSignal:




        score = sum(

            s.score

            for s in signals

        )




        confidence = (

            sum(

                s.confidence

                for s in signals

            )

            /

            len(signals)

        )






        if confidence < self.min_confidence:

            return CompositeSignal()





        if score < self.min_score:

            return CompositeSignal()








        # ----------------------------------------------------
        # Direction vote
        # ----------------------------------------------------


        buy_score = sum(

            s.confidence

            for s in signals

            if s.side
            ==
            SignalSide.BUY

        )



        sell_score = sum(

            s.confidence

            for s in signals

            if s.side
            ==
            SignalSide.SELL

        )







        if buy_score > sell_score:


            side = SignalSide.BUY



        elif sell_score > buy_score:


            side = SignalSide.SELL



        else:


            return CompositeSignal()








        # ----------------------------------------------------
        # Category
        # ----------------------------------------------------


        categories = [

            s.category

            for s in signals

        ]



        category = categories[0]









        return CompositeSignal(


            side=side,


            signal_type=SignalType.ENTRY,


            category=category,


            confidence=confidence,


            score=score,



            reasons=[

                s.reason

                for s in signals

                if s.reason

            ],



            strategies=[

                s.strategy

                for s in signals

                if s.strategy

            ],



            metadata={

                "signals":

                    [

                        s.to_dict()

                        for s in signals

                    ]

            }

        )