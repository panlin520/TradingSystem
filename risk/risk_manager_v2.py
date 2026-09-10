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
          +-------------------------+
          |                         |
          v                         v
    RiskLimits               ExposureEngine
          |
          v
    RiskDecision

同时：

    SystemState.orderbook
          |
          v
    RiskMarketValuation
          |
          v
    Normalized Valuation Price
          |
          v
    ExposureEngine

============================================================

当前阶段：

    已打通：

        OrderBook
            ↓
        RiskMarketValuation
            ↓
        normalized valuation price
            ↓
        ExposureEngine

    但 max_exposure 暂时仍使用原数量型 gross_exposure。

    Dollar / Notional Exposure 在下一阶段启用。

============================================================
"""


from dataclasses import dataclass, field
from typing import Dict


from risk.limits import RiskLimits
from risk.exposure import ExposureEngine
from risk.kill_switch import KillSwitch
from risk.valuation import RiskMarketValuation



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
    """


    # Engine 可显式识别这个能力，
    # 后续将 state 安全传入 Risk。
    supports_state_context = True



    def __init__(
        self,
        limits=None,
        exposure_engine=None,
        kill_switch=None,
        market_valuation=None,
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
        # Market Valuation
        # ==================================================

        self.market_valuation = (

            market_valuation

            if market_valuation is not None

            else RiskMarketValuation()

        )


        # ==================================================
        # runtime statistics
        # ==================================================

        self.total_checks = 0

        self.total_approved = 0

        self.total_rejected = 0


        # ==================================================
        # Valuation Diagnostics
        # ==================================================

        self.last_valuation_price = None





    # ======================================================
    # Single Signal Check
    # ======================================================

    def check_signal(
        self,
        signal,
        portfolio,
        state=None,
    ):
        """
        单个 Signal 风控入口。

        旧接口兼容：

            check_signal(
                signal,
                portfolio,
            )

        新接口：

            check_signal(
                signal,
                portfolio,
                state=state,
            )
        """

        return self.check_signals(
            signal,
            portfolio,
            state=state,
        )



    # ======================================================
    # Signals Check
    # ======================================================

    def check_signals(
        self,
        signals,
        portfolio,
        state=None,
    ):
        """
        检查 Strategy signals。
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
        # Risk Valuation Price
        # ==================================================
        #
        # 当前阶段：
        #
        #     state.orderbook
        #         ↓
        #     RiskMarketValuation
        #         ↓
        #     normalized price
        #
        # 没有 state 时保持旧行为，
        # valuation_price = None。
        #
        # 此阶段不因为缺失 valuation price 拒单，
        # 因为 Dollar Exposure 尚未正式启用。
        # ==================================================

        valuation_price = None


        if state is not None:

            orderbook = getattr(
                state,
                "orderbook",
                None,
            )


            valuation_price = (
                self.market_valuation
                .price_for_side(
                    orderbook,
                    side,
                )
            )


        self.last_valuation_price = (
            valuation_price
        )


        checks["valuation_price"] = (
            valuation_price is not None
            if state is not None
            else True
        )


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

                valuation_price=valuation_price,

            )

        )


        # ==================================================
        # Symbol Position Limit
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
        #
        # 注意：
        #
        # 当前仍然是旧的数量型 gross_exposure。
        #
        # 下一阶段才切换 dollar / notional exposure。
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

        self.last_valuation_price = None


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

            "last_valuation_price":
                self.last_valuation_price,

        }
