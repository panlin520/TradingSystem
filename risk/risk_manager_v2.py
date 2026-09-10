"""
risk/risk_manager_v2.py

============================================================
Risk Manager V2
============================================================

职责：

    Strategy signals
          |
          v
    RiskManager
          |
          +----------------+
          |                |
          v                v
    RiskLimits       ExposureEngine
          |
          v
    RiskDecision

============================================================

负责：

    - signals 风控检查
    - Position Limit
    - Total Position Limit
    - Exposure Limit
    - Kill Switch
    - Risk Decision

============================================================

不负责：

    - Order 创建
    - Execution
    - Portfolio 更新
    - PnL 计算
    - Position 保存

============================================================

核心原则：

    Risk 只负责回答：

        "这个交易是否允许进入系统？"

============================================================
"""


from dataclasses import dataclass, field
from typing import Dict


from risk.limits import RiskLimits
from risk.exposure import ExposureEngine
from risk.kill_switch import KillSwitch



# ============================================================
# Risk Decision
# ============================================================


@dataclass
class RiskDecision:
    """
    Risk 检查结果。
    """

    approved: bool

    reason: str

    checks: Dict[str, bool] = field(
        default_factory=dict
    )


    def __bool__(self):

        return self.approved


    def to_dict(self):

        return {

            "approved":
                self.approved,

            "reason":
                self.reason,

            "checks":
                self.checks,

        }





# ============================================================
# Risk Manager V2
# ============================================================


class RiskManagerV2:
    """
    新版 Risk Manager。


    所有风险计算：

        ExposureEngine


    所有限制：

        RiskLimits


    所有紧急停止：

        KillSwitch
    """


    def __init__(
        self,
        limits=None,
        exposure_engine=None,
        kill_switch=None,
    ):


        # ==================================================
        # Risk Limits
        # ==================================================

        self.limits = (

            limits

            if limits is not None

            else RiskLimits()

        )


        # ==================================================
        # Exposure Engine
        # ==================================================

        self.exposure_engine = (

            exposure_engine

            if exposure_engine is not None

            else ExposureEngine()

        )


        # ==================================================
        # Kill Switch
        # ==================================================

        self.kill_switch = (

            kill_switch

            if kill_switch is not None

            else KillSwitch()

        )


        # ==================================================
        # runtime statistics
        # ==================================================

        self.total_checks = 0

        self.total_approved = 0

        self.total_rejected = 0





    # ======================================================
    # Single Signal Check
    # ======================================================

    def check_signal(
        self,
        signal,
        portfolio,
    ):
        """
        单个 Signal 风控入口。

        内部统一调用：

            check_signals()
        """

        return self.check_signals(
            signal,
            portfolio,
        )



    # ======================================================
    # Signals Check
    # ======================================================

    def check_signals(
        self,
        signals,
        portfolio,
    ):
        """
        检查 Strategy signals。

        signals 必须提供：

            symbol
            side
            quantity

        返回：

            RiskDecision
        """


        self.total_checks += 1


        checks = {}


        # ==================================================
        # Kill Switch
        # ==================================================

        if self.kill_switch.is_triggered():


            checks["kill_switch"] = False


            return self._reject(
                "Kill switch triggered",
                checks
            )


        checks["kill_switch"] = True


        # ==================================================
        # signals 基础检查
        # ==================================================

        quantity = getattr(
            signals,
            "quantity",
            0
        )

        side = getattr(
            signals,
            "side",
            None
        )

        symbol = getattr(
            signals,
            "symbol",
            None
        )


        if quantity <= 0:

            checks["quantity"] = False

            return self._reject(
                "Invalid quantity",
                checks
            )


        checks["quantity"] = True


        if symbol is None:

            checks["symbol"] = False

            return self._reject(
                "Missing symbol",
                checks
            )


        checks["symbol"] = True


        # ==================================================
        # Projected Exposure
        # ==================================================

        projected = (

            self.exposure_engine

            .project_signals(

                portfolio,

                symbol,

                side,

                quantity,

            )

        )


        # ==================================================
        # Symbol Position Limit
        # ==================================================
        #
        # Position quantity 是带方向的 signed quantity：
        #
        #     LONG  -> 正数
        #     SHORT -> 负数
        #
        # 单品种最大仓位限制必须约束仓位“绝对大小”，
        # 不能只比较正数，否则 SHORT 会绕过限制。
        #
        # 例如：
        #
        #     max_position_size = 5
        #
        #     +6 -> reject
        #     -6 -> 也必须 reject
        #
        # ==================================================

        if (
            abs(projected.position_quantity)
            >
            self.limits.max_position_size
        ):

            checks["position_limit"] = False

            return self._reject(
                "Position limit exceeded",
                checks
            )


        checks["position_limit"] = True


        # ==================================================
        # Total Position Limit
        # ==================================================

        if (

                projected.total_position

                >

                self.limits.max_total_position

        ):

            checks["total_position_limit"] = False

            return self._reject(
                "Total position limit exceeded",
                checks
            )


        checks["total_position_limit"] = True


        # ==================================================
        # Exposure Limit
        # ==================================================

        if (

                projected.gross_exposure

                >=

                self.limits.max_exposure

        ):

            checks["exposure_limit"] = False

            return self._reject(
                "Exposure Limit exceeded",
                checks
            )


        checks["exposure_limit"] = True


        return self._approve(
            checks
        )


    # ======================================================
    # Fill Update
    # ======================================================

    def on_fill(
        self,
        fill,
        portfolio,
    ):
        """
        成交后更新。

        Position 实际变化由 Portfolio 负责。
        Risk 这里只刷新统计。
        """

        return self.exposure_engine.update(
            portfolio
        )


    # ======================================================
    # Reset
    # ======================================================

    def reset(self):

        self.kill_switch.reset()

        self.total_checks = 0

        self.total_approved = 0

        self.total_rejected = 0


    # ======================================================
    # Helpers
    # ======================================================

    def _approve(
        self,
        checks,
    ):

        self.total_approved += 1

        return RiskDecision(

            approved=True,

            reason="Approved",

            checks=checks,

        )


    def _reject(
        self,
        reason,
        checks,
    ):

        self.total_rejected += 1

        return RiskDecision(

            approved=False,

            reason=reason,

            checks=checks,

        )


    # ======================================================
    # Snapshot
    # ======================================================

    def snapshot(self):

        return {

            "checks":
                self.total_checks,

            "approved":
                self.total_approved,

            "rejected":
                self.total_rejected,

            "kill_switch":
                self.kill_switch.snapshot(),

        }
