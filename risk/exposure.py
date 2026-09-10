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


不负责：

- 下单
- 成交
- Position更新
- Strategy


============================================================

"""


from dataclasses import dataclass






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
    """


    # 当前symbol预测仓位
    position_quantity: int = 0


    # 全账户预测仓位
    total_position: int = 0


    # 全账户Gross Exposure
    gross_exposure: float = 0.0








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
        quantity
    ):
        """
        预测Signal成交后的Exposure。

        不修改真实Portfolio。

        返回：

            ProjectedExposure

        当前 ExposureEngine 没有价格/合约乘数输入，
        因此 exposure 的单位仍然是：

            abs(position.quantity)

        所以：

            gross_exposure

        表示全账户所有 symbol 的绝对仓位暴露之和。
        """


        current = self.get_position_quantity(
            portfolio,
            symbol
        )



        # ==================================================
        # Side Normalization
        # ==================================================
        #
        # Runtime Signal 使用 Enum：
        #
        #     signals.signal.SignalSide.BUY
        #     signals.signal.SignalSide.SELL
        #
        # 必须先读取 Enum.value。
        #
        # 同时兼容字符串：
        #
        #     "BUY"
        #     "SELL"
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
        # 其中当前 symbol 使用 projected quantity。
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
        # Gross Exposure
        # ==================================================
        #
        # 当前 ExposureEngine 的 exposure 定义本身就是：
        #
        #     abs(quantity)
        #
        # 因此账户 Gross Exposure 应当是：
        #
        #     Σ abs(projected_position_i)
        #
        # 不能只返回当前 symbol 的 abs(projected)。
        #
        # 在当前数量型 Exposure 模型下：
        #
        #     gross_exposure == total_position
        #
        # ==================================================

        gross_exposure = float(
            total_position
        )






        return ProjectedExposure(

            position_quantity=projected,

            total_position=total_position,

            gross_exposure=gross_exposure,

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
    ):
        """
        Compatibility wrapper.

        RiskManagerV2 calls:

            project_signals()

        Internally uses:

            project_signal()
        """


        return self.project_signal(

            portfolio,

            symbol,

            side,

            quantity,

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
