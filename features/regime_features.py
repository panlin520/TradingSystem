"""
features/regime_features.py

============================================================
Market Regime Features
============================================================

职责：

    计算市场环境状态。

用于：

    Market Regime Classifier

============================================================

输出：

    Trend State
    Volatility State
    Liquidity State
    Regime Score

============================================================

输入：

    OrderBook
    FeatureSnapshot

============================================================

OrderBook Contract：

    当前冻结 OrderBook 使用：

        orderbook.best_bid()
        orderbook.best_ask()

        orderbook.bid_volume()
        orderbook.ask_volume()

    best_bid() / best_ask()
    返回价格值。

    不使用：

        orderbook.best_bid.price
        orderbook.best_ask.price

============================================================

不负责：

    Strategy
    Signal
    Entry
    Exit

============================================================
"""

from enum import Enum


# ============================================================
# Trend Regime
# ============================================================


class TrendRegime(Enum):
    """
    市场趋势状态。
    """

    UNKNOWN = "UNKNOWN"

    RANGE = "RANGE"

    TREND_UP = "TREND_UP"

    TREND_DOWN = "TREND_DOWN"


# ============================================================
# Volatility Regime
# ============================================================


class VolatilityRegime(Enum):
    """
    波动环境。
    """

    UNKNOWN = "UNKNOWN"

    LOW = "LOW"

    NORMAL = "NORMAL"

    HIGH = "HIGH"


# ============================================================
# Liquidity Regime
# ============================================================


class LiquidityRegime(Enum):
    """
    盘口流动性环境。
    """

    UNKNOWN = "UNKNOWN"

    NORMAL = "NORMAL"

    THIN = "THIN"

    VACUUM = "VACUUM"

    DEEP = "DEEP"


# ============================================================
# Regime Features
# ============================================================


class RegimeFeatures:
    """
    市场状态特征计算器。

    当前实现：

        每次 update() 读取一次稳定 OrderBook 状态。

    后续正式接 Engine 时，
    可以选择只在 F_LAST 稳定边界更新。
    """

    def __init__(
        self,
        window_size=100
    ):

        # ==================================================
        # Parameters
        # ==================================================

        self.window_size = window_size

        # ==================================================
        # Mid Price History
        # ==================================================

        self.mid_prices = []

        # ==================================================
        # Return / Movement History
        # ==================================================

        self.returns = []

        # ==================================================
        # Current Regime
        # ==================================================

        self.trend = (
            TrendRegime.UNKNOWN
        )

        self.volatility = (
            VolatilityRegime.UNKNOWN
        )

        self.liquidity = (
            LiquidityRegime.UNKNOWN
        )

        # ==================================================
        # Scores
        # ==================================================

        self.trend_score = 0.0

        self.volatility_score = 0.0

        self.liquidity_score = 0.0

    # ======================================================
    # Update
    # ======================================================

    def update(
        self,
        orderbook,
        snapshot
    ):
        """
        更新市场状态。

        参数：

            orderbook:
                当前冻结 OrderBook

            snapshot:
                当前 FeatureSnapshot

        返回：

            self
        """

        # ==================================================
        # 1. Mid Price
        # ==================================================

        mid = self._get_mid_price(
            orderbook
        )

        if mid is not None:

            self._update_price_history(
                mid
            )

        # ==================================================
        # 2. Trend
        # ==================================================

        self._calculate_trend()

        # ==================================================
        # 3. Volatility
        # ==================================================

        self._calculate_volatility()

        # ==================================================
        # 4. Liquidity
        # ==================================================

        self._calculate_liquidity(
            orderbook
        )

        # ==================================================
        # 5. Snapshot
        # ==================================================
        #
        # FeatureSnapshot 当前已经有：
        #
        #     spread_regime
        #     volatility_regime
        #
        # Liquidity / Trend完整结构暂时保留在
        # RegimeFeatures.state() 中。
        # ==================================================

        if snapshot is not None:

            snapshot.volatility_regime = (
                self.volatility.value
            )

            snapshot.extra[
                "trend_regime"
            ] = self.trend.value

            snapshot.extra[
                "liquidity_regime"
            ] = self.liquidity.value

            snapshot.extra[
                "trend_score"
            ] = self.trend_score

            snapshot.extra[
                "volatility_score"
            ] = self.volatility_score

            snapshot.extra[
                "liquidity_score"
            ] = self.liquidity_score

        return self

    # ======================================================
    # Mid Price
    # ======================================================

    def _get_mid_price(
        self,
        orderbook
    ):
        """
        从当前冻结 OrderBook 获取 Mid Price。

        正式接口：

            best_bid()
            best_ask()
        """

        if orderbook is None:

            return None

        try:

            bid = orderbook.best_bid()

            ask = orderbook.best_ask()

        except (AttributeError, TypeError):

            return None

        if (
            bid is None
            or
            ask is None
        ):

            return None

        return (
            bid
            +
            ask
        ) / 2

    # ======================================================
    # Price History
    # ======================================================

    def _update_price_history(
        self,
        price
    ):

        # --------------------------------------------------
        # Return / Movement
        # --------------------------------------------------

        if self.mid_prices:

            previous = (
                self.mid_prices[-1]
            )

            self.returns.append(
                price
                -
                previous
            )

            if len(
                self.returns
            ) > self.window_size:

                self.returns.pop(
                    0
                )

        # --------------------------------------------------
        # Mid
        # --------------------------------------------------

        self.mid_prices.append(
            price
        )

        if len(
            self.mid_prices
        ) > self.window_size:

            self.mid_prices.pop(
                0
            )

    # ======================================================
    # Trend
    # ======================================================

    def _calculate_trend(
        self
    ):

        if len(
            self.mid_prices
        ) < 20:

            return

        start = (
            self.mid_prices[0]
        )

        end = (
            self.mid_prices[-1]
        )

        change = (
            end
            -
            start
        )

        if change > 0:

            self.trend_score = 1.0

        elif change < 0:

            self.trend_score = -1.0

        else:

            self.trend_score = 0.0

        # --------------------------------------------------
        # Regime
        # --------------------------------------------------

        if self.trend_score > 0.5:

            self.trend = (
                TrendRegime.TREND_UP
            )

        elif self.trend_score < -0.5:

            self.trend = (
                TrendRegime.TREND_DOWN
            )

        else:

            self.trend = (
                TrendRegime.RANGE
            )

    # ======================================================
    # Volatility
    # ======================================================

    def _calculate_volatility(
        self
    ):

        if len(
            self.mid_prices
        ) < 20:

            return

        moves = []

        for index in range(
            1,
            len(
                self.mid_prices
            )
        ):

            moves.append(
                abs(
                    self.mid_prices[index]
                    -
                    self.mid_prices[index - 1]
                )
            )

        if not moves:

            return

        avg_move = (
            sum(
                moves
            )
            /
            len(
                moves
            )
        )

        self.volatility_score = (
            avg_move
        )

        # --------------------------------------------------
        # 当前阈值保持原代码不变
        # --------------------------------------------------

        if avg_move < 0.25:

            self.volatility = (
                VolatilityRegime.LOW
            )

        elif avg_move < 1.0:

            self.volatility = (
                VolatilityRegime.NORMAL
            )

        else:

            self.volatility = (
                VolatilityRegime.HIGH
            )

    # ======================================================
    # Liquidity
    # ======================================================

    def _calculate_liquidity(
        self,
        orderbook
    ):

        if orderbook is None:

            return

        try:

            bid_volume = (
                orderbook.bid_volume()
            )

            ask_volume = (
                orderbook.ask_volume()
            )

        except (AttributeError, TypeError):

            return

        depth = (
            bid_volume
            +
            ask_volume
        )

        self.liquidity_score = (
            depth
        )

        # --------------------------------------------------
        # 当前阈值保持原代码不变
        # --------------------------------------------------

        if depth < 50:

            self.liquidity = (
                LiquidityRegime.VACUUM
            )

        elif depth < 500:

            self.liquidity = (
                LiquidityRegime.THIN
            )

        elif depth > 5000:

            self.liquidity = (
                LiquidityRegime.DEEP
            )

        else:

            self.liquidity = (
                LiquidityRegime.NORMAL
            )

    # ======================================================
    # State
    # ======================================================

    def state(
        self
    ) -> dict:
        """
        输出当前 Regime 状态。
        """

        return {
            "trend":
                self.trend,

            "volatility":
                self.volatility,

            "liquidity":
                self.liquidity,

            "trend_score":
                self.trend_score,

            "volatility_score":
                self.volatility_score,

            "liquidity_score":
                self.liquidity_score,
        }

    # ======================================================
    # Reset
    # ======================================================

    def reset(
        self
    ):
        """
        清空 Regime 历史状态。
        """

        self.mid_prices.clear()

        self.returns.clear()

        self.trend = (
            TrendRegime.UNKNOWN
        )

        self.volatility = (
            VolatilityRegime.UNKNOWN
        )

        self.liquidity = (
            LiquidityRegime.UNKNOWN
        )

        self.trend_score = 0.0

        self.volatility_score = 0.0

        self.liquidity_score = 0.0