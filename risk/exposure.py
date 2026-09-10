"""
risk/exposure.py


============================================================

Exposure Engine

============================================================


职责：

Position
    |
    v

Exposure Calculation


负责：

- 当前仓位暴露
- 预测信号后的暴露
- 总仓位计算
- 风险检查辅助
- 接收 Risk valuation price（为后续 Dollar Exposure 准备）


不负责：

- 下单
- 成交
- Position更新
- Strategy
- 从 OrderBook 提取价格


============================================================

"""


from dataclasses import dataclass
from typing import Optional






# ==========================================================
# 当前 Exposure Snapshot
# ==========================================================


@dataclass
class ExposureSnapshot:
    """
    Exposure 状态快照
    """


    symbol: str


    # 当前数量
    quantity: int


    # 风险暴露
    exposure: float






# ==========================================================
# 预测 Exposure
# ==========================================================


@dataclass
class ProjectedExposure:
    """
    Signal执行后的预测风险状态。

    RiskManagerV2 使用。

    注意：

        valuation_price 已经是 normalized price。

        当前阶段仅完成 Risk valuation price 传递链路，
        gross_exposure 仍保持数量型定义，
        暂时不切换 Dollar / Notional Exposure。
    """


    # 当前symbol预测仓位
    position_quantity: int = 0


    # 全账户预测仓位
    total_position: int = 0


    # 当前阶段仍为数量型 Gross Exposure
    gross_exposure: float = 0.0


    # RiskMarketValuation 提供的 normalized price
    valuation_price: Optional[float] = None








class ExposureEngine:
    """
    风险暴露计算器。

    被 RiskManagerV2 调用。
    """


    def __init__(
        self,
        portfolio=None
    ):


        self.portfolio = portfolio


        # update次数统计
        self.update_count = 0







    # ==================================================
    # 获取当前仓位
    # ==================================================


    def get_position_quantity(
        self,
        portfolio,
        symbol
    ):
        """
        获取当前symbol数量
        """


        position = portfolio.get_position(symbol)


        if position is None:

            return 0


        return getattr(
            position,
            "quantity",
            0
        )








    # ==================================================
    # 当前 Exposure
    # ==================================================


    def calculate(
        self,
        portfolio,
        symbol
    ):
        """
        当前风险暴露
        """


        quantity = self.get_position_quantity(
            portfolio,
            symbol
        )


        return abs(quantity)








    # ==================================================
    # 预测 Signal 后 Exposure
    # ==================================================


    def project_signal(
        self,
        portfolio,
        symbol,
        side,
        quantity,
        valuation_price=None,
    ):
        """
        预测Signal成交后的Exposure。

        不修改真实Portfolio。

        参数：

            valuation_price:

                RiskMarketValuation 提供的 normalized price。

                当前阶段只保存到 ProjectedExposure，
                不参与 gross_exposure 限制计算。

        返回：

            ProjectedExposure
        """


        current = self.get_position_quantity(
            portfolio,
            symbol
        )



        # ==================================================
        # Side Normalization
        # ==================================================

        if hasattr(
            side,
            "value"
        ):

            side = side.value


        side = str(
            side
        ).upper()



        if side == "BUY":

            projected = current + quantity



        elif side == "SELL":

            projected = current - quantity



        else:

            projected = current






        # ==================================================
        # 全账户预测仓位
        # ==================================================
        #
        # total_position:
        #
        #     Σ abs(position.quantity)
        #
        # 当前 symbol 使用 projected quantity。
        # ==================================================

        total_position = 0


        positions = getattr(
            portfolio,
            "positions",
            {}
        )


        symbol_found = False


        for sym, pos in positions.items():


            qty = getattr(
                pos,
                "quantity",
                0
            )


            if sym == symbol:

                total_position += abs(
                    projected
                )

                symbol_found = True


            else:

                total_position += abs(
                    qty
                )


        if not symbol_found:

            total_position += abs(
                projected
            )






        # ==================================================
        # 当前阶段 Gross Exposure
        # ==================================================
        #
        # 暂时仍然保持数量型定义：
        #
        #     Σ abs(quantity)
        #
        # 下一阶段才切换到 Dollar / Notional Exposure。
        # ==================================================

        gross_exposure = float(
            total_position
        )






        return ProjectedExposure(

            position_quantity=projected,

            total_position=total_position,

            gross_exposure=gross_exposure,

            valuation_price=valuation_price,

        )



    # ============================================================
    # Compatibility Wrapper
    # ============================================================


    def project_signals(
        self,
        portfolio,
        symbol,
        side,
        quantity,
        valuation_price=None,
    ):
        """
        Compatibility wrapper.

        RiskManagerV2 calls:

            project_signals()

        旧调用仍兼容：

            project_signals(
                portfolio,
                symbol,
                side,
                quantity,
            )

        新调用：

            project_signals(
                portfolio,
                symbol,
                side,
                quantity,
                valuation_price=...
            )
        """


        return self.project_signal(

            portfolio,

            symbol,

            side,

            quantity,

            valuation_price=valuation_price,

        )








    # ==================================================
    # Fill 后刷新
    # ==================================================


    def update(
        self,
        portfolio
    ):
        """
        成交后重新计算Exposure。
        """


        self.update_count += 1


        result = {}


        positions = getattr(
            portfolio,
            "positions",
            {}
        )


        for symbol, position in positions.items():


            qty = getattr(
                position,
                "quantity",
                0
            )


            result[symbol] = abs(qty)


        return result








    # ==================================================
    # Snapshot
    # ==================================================


    def snapshot(
        self,
        portfolio
    ):


        data = {}


        positions = getattr(
            portfolio,
            "positions",
            {}
        )


        for symbol, position in positions.items():


            qty = getattr(
                position,
                "quantity",
                0
            )


            data[symbol] = ExposureSnapshot(

                symbol=symbol,

                quantity=qty,

                exposure=abs(qty)

            )


        return data
