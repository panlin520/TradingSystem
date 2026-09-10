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



    # 总Exposure金额
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
        # 直接执行：
        #
        #     str(SignalSide.BUY)
        #
        # 得到的是：
        #
        #     "SignalSide.BUY"
        #
        # 而不是：
        #
        #     "BUY"
        #
        # 因此必须先读取 Enum.value。
        #
        # 同时继续兼容原来的字符串：
        #
        #     "BUY"
        #     "SELL"
        #
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






        # ==============================
        # 计算总仓位
        # ==============================


        total_position = 0



        positions = getattr(
            portfolio,
            "positions",
            {}
        )



        for sym, pos in positions.items():


            qty = getattr(
                pos,
                "quantity",
                0
            )


            total_position += abs(qty)





        # 新symbol

        if symbol not in positions:


            total_position += abs(quantity)



        else:


            total_position = (

                total_position

                -

                abs(current)

                +

                abs(projected)

            )





        # ==============================
        # 返回预测结果
        # ==============================


        return ProjectedExposure(

            position_quantity=projected,


            total_position=total_position,


            gross_exposure=abs(projected)

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
