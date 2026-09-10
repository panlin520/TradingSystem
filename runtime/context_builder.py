"""
runtime/context_builder.py


============================================================
Strategy Context Builder
============================================================

职责：

    将 Runtime 当前状态转换为 StrategyContext。


数据流：

    FeatureSnapshot
            |
            |
    OrderBook
            |
            |
    Portfolio
            |
            |
    RiskManager
            |
            v

    StrategyContext


负责：

    - FeatureSnapshot -> FeatureContext
    - OrderBook -> OrderBookContext
    - Portfolio -> PositionContext
    - RiskManager -> RiskContext


不负责：

    - Strategy调用
    - Signal生成
    - Risk判断
    - Order创建
    - Execution


============================================================
"""


from strategy.context import (
    StrategyContext,
    OrderBookContext,
    FeatureContext,
    RegimeContext,
    PositionContext,
    RiskContext,
)


class ContextBuilder:
    """
    StrategyContext 构建器。


    所有策略只能看到：

        StrategyContext


    不直接访问：

        OrderBook
        Portfolio
        RiskManager
        FeatureEngine
    """

    def build(
        self,
        snapshot,
        orderbook,
        portfolio,
        risk_manager,
    ) -> StrategyContext:
        """
        构建 StrategyContext。


        Parameters
        ----------

        snapshot:
            FeatureSnapshot


        orderbook:
            OrderBook


        portfolio:
            Portfolio


        risk_manager:
            RiskManagerV2


        Returns
        -------

        StrategyContext
        """

        context = StrategyContext()


        # ==================================================
        # 基础信息
        # ==================================================

        context.timestamp = getattr(
            snapshot,
            "timestamp",
            0
        )


        context.symbol = getattr(
            snapshot,
            "symbol",
            None
        )


        # ==================================================
        # OrderBook Context
        # ==================================================

        context.orderbook = self._build_orderbook_context(
            orderbook
        )


        # ==================================================
        # Feature Context
        # ==================================================

        context.features = self._build_feature_context(
            snapshot
        )


        # ==================================================
        # Regime Context
        # ==================================================

        context.regime = self._build_regime_context(
            snapshot
        )


        # ==================================================
        # Position Context
        # ==================================================

        context.position = self._build_position_context(
            portfolio,
            context.symbol
        )


        # ==================================================
        # Risk Context
        # ==================================================

        context.risk = self._build_risk_context(
            risk_manager
        )


        return context


    # ======================================================
    # OrderBook
    # ======================================================

    def _build_orderbook_context(
        self,
        orderbook
    ):

        ctx = OrderBookContext()


        if orderbook is None:
            return ctx


        # 正式 OrderBook 接口为方法：
        #
        #     best_bid()
        #     best_ask()

        if hasattr(orderbook, "best_bid"):

            ctx.best_bid = orderbook.best_bid()


        if hasattr(orderbook, "best_ask"):

            ctx.best_ask = orderbook.best_ask()


        if hasattr(orderbook, "bid_volume"):

            ctx.bid_size = orderbook.bid_volume()


        if hasattr(orderbook, "ask_volume"):

            ctx.ask_size = orderbook.ask_volume()


        if (
            ctx.best_bid is not None
            and
            ctx.best_ask is not None
        ):

            ctx.spread = (
                ctx.best_ask
                -
                ctx.best_bid
            )


        ctx.active_orders = len(
            getattr(
                orderbook,
                "orders",
                {}
            )
        )


        return ctx


    # ======================================================
    # Feature
    # ======================================================

    def _build_feature_context(
        self,
        snapshot
    ):

        ctx = FeatureContext()


        if snapshot is None:
            return ctx


        fields = [

            "mid_price",

            "micro_price",

            "obi",

            "ofi",

            "trade_volume",

            "aggressive_buy_volume",

            "aggressive_sell_volume",

            "trade_imbalance",

            "volatility",

            "absorption_ratio",

            "passive_refill",

        ]


        for field in fields:

            if hasattr(snapshot, field):

                setattr(
                    ctx,
                    field,
                    getattr(snapshot, field)
                )


        extra = getattr(
            snapshot,
            "extra",
            {}
        )


        if isinstance(extra, dict):

            ctx.extra.update(extra)


        return ctx


    # ======================================================
    # Regime
    # ======================================================

    def _build_regime_context(
        self,
        snapshot
    ):

        ctx = RegimeContext()


        if snapshot is None:
            return ctx


        volatility = getattr(
            snapshot,
            "volatility_regime",
            "UNKNOWN"
        )


        if volatility != "UNKNOWN":

            ctx.name = volatility


            if volatility == "HIGH":

                ctx.high_volatility = True


        extra = getattr(
            snapshot,
            "extra",
            {}
        )


        if isinstance(extra, dict):

            ctx.extra.update(extra)


        return ctx


    # ======================================================
    # Position
    # ======================================================

    def _build_position_context(
        self,
        portfolio,
        symbol
    ):

        ctx = PositionContext()


        if (
            portfolio is None
            or
            symbol is None
        ):
            return ctx


        position = portfolio.get_position(
            symbol
        )


        ctx.symbol = symbol


        ctx.quantity = getattr(
            position,
            "quantity",
            0
        )


        position_side = getattr(
            position,
            "side",
            "FLAT"
        )


        ctx.side = getattr(
            position_side,
            "value",
            position_side
        )


        ctx.entry_price = getattr(
            position,
            "avg_price",
            0.0
        )


        return ctx


    # ======================================================
    # Risk
    # ======================================================

    def _build_risk_context(
        self,
        risk_manager
    ):

        ctx = RiskContext()


        if risk_manager is None:
            return ctx


        kill_switch = getattr(
            risk_manager,
            "kill_switch",
            None
        )


        if (
            kill_switch is not None
            and
            hasattr(
                kill_switch,
                "is_triggered"
            )
        ):

            ctx.kill_switch = (
                kill_switch.is_triggered()
            )


            ctx.allowed = (
                not ctx.kill_switch
            )


        return ctx
