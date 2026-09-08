"""
strategy/regime_classifier.py


============================================================
Market Regime Classifier
============================================================


职责：

    根据 FeatureSnapshot 判断当前市场环境。


============================================================


输入：

    FeatureSnapshot

    RegimeFeatures


输出：

    MarketRegime


============================================================


负责：

    - 市场状态分类
    - 策略环境选择


不负责：

    - Entry
    - Exit
    - Order
    - Execution


============================================================


Strategy Architecture:


                 FeatureEngine

                       |

                       v


             RegimeFeatures


                       |

                       v


             RegimeClassifier


                       |

                       v


 ------------------------------------------------

 |              |              |               |

Mean        Momentum       Liquidity       Absorption

Reversion   Breakout       Vacuum          Refill


 ------------------------------------------------


============================================================

"""


from enum import Enum





# ==========================================================
# 市场状态
# ==========================================================


class MarketRegime(Enum):

    """
    当前市场主要状态。
    """

    UNKNOWN = "UNKNOWN"


    RANGE = "RANGE"


    TREND = "TREND"


    HIGH_VOLATILITY = "HIGH_VOLATILITY"


    LOW_LIQUIDITY = "LOW_LIQUIDITY"


    ABSORPTION = "ABSORPTION"







class RegimeClassifier:
    """
    市场状态分类器。



    根据：

        Trend

        Volatility

        Liquidity

        OrderFlow


    判断当前交易环境。



    """



    def __init__(

        self

    ):


        # 当前状态

        self.current_regime = (

            MarketRegime.UNKNOWN

        )





        # 统计

        self.classifications = 0






    # ======================================================
    # 主入口
    # ======================================================


    def classify(

        self,

        regime_features,

        snapshot=None

    ):

        """
        分类当前市场。


        参数：


        regime_features:

            features.regime_features.RegimeFeatures



        snapshot:

            FeatureSnapshot



        返回：

            MarketRegime



        """



        self.classifications += 1





        # ==================================================
        # 获取状态
        # ==================================================

        trend = (

            regime_features.trend

        )


        volatility = (

            regime_features.volatility

        )


        liquidity = (

            regime_features.liquidity

        )






        # ==================================================
        # 1.
        # 流动性真空
        # ==================================================

        if liquidity.value == "VACUUM":


            self.current_regime = (

                MarketRegime.LOW_LIQUIDITY

            )


            return self.current_regime






        # ==================================================
        # 2.
        # 高波动趋势
        # ==================================================

        if (

            volatility.value == "HIGH"

            and

            trend.value in (

                "TREND_UP",

                "TREND_DOWN"

            )

        ):


            self.current_regime = (

                MarketRegime.TREND

            )


            return self.current_regime






        # ==================================================
        # 3.
        # 高波动无方向
        # ==================================================

        if volatility.value == "HIGH":


            self.current_regime = (

                MarketRegime.HIGH_VOLATILITY

            )


            return self.current_regime






        # ==================================================
        # 4.
        # 横盘
        # ==================================================

        if trend.value == "RANGE":


            self.current_regime = (

                MarketRegime.RANGE

            )


            return self.current_regime






        # ==================================================
        # 默认
        # ==================================================

        self.current_regime = (

            MarketRegime.UNKNOWN

        )


        return self.current_regime







    # ======================================================
    # 快捷判断
    # ======================================================


    def is_mean_reversion(

        self

    ):

        """
        是否适合均值回归。


        条件：

        RANGE


        """

        return (

            self.current_regime

            ==

            MarketRegime.RANGE

        )







    def is_breakout(

        self

    ):

        """
        是否适合突破策略。


        """

        return (

            self.current_regime

            ==

            MarketRegime.TREND

        )







    def is_liquidity_vacuum(

        self

    ):

        return (

            self.current_regime

            ==

            MarketRegime.LOW_LIQUIDITY

        )







    # ======================================================
    # 状态输出
    # ======================================================


    def state(

        self

    ):

        return {


            "regime":

                self.current_regime.value,


            "classifications":

                self.classifications,


        }