"""
risk/risk_manager_v2.py

============================================================
Risk Manager V2
============================================================

核心链：

    Runtime Signal
        ↓
    RiskManagerV2
        ↓
    state.orderbook
        ↓
    RiskMarketValuation
        ↓
    normalized valuation price
        ↓
    ExposureEngine
        ↓
    ProjectedExposure
        ↓
    Position Limit
    Total Position Limit
    Dollar Exposure Limit
        ↓
    RiskDecision

============================================================

规则：

1. max_position / max_total_position：
       按 contracts / units 控制。

2. max_exposure：
       按 gross_notional USD 控制。

3. Dollar Exposure：
       Σ abs(qty)
         × normalized market price
         × point_value

4. Fail Closed：
       只要预测后的任意非零仓位缺少有效价格或 point_value，
       Risk 拒绝交易。

5. 旧接口兼容：
       check_signal(signal, portfolio)

   仍允许调用，但如果 signal 会产生非零仓位且没有 valuation price，
   在正式 dollar exposure 模式下会 fail closed。

============================================================
"""


from dataclasses import dataclass, field
from typing import Dict


from risk.limits import RiskLimits
from risk.exposure import ExposureEngine
from risk.kill_switch import KillSwitch
from risk.valuation import RiskMarketValuation






@dataclass
class RiskDecision:

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








class RiskManagerV2:
    """
    Runtime Risk Manager。
    """


    supports_state_context = True



    def __init__(
        self,
        limits=None,
        exposure_engine=None,
        kill_switch=None,
        market_valuation=None,
    ):


        self.limits = (

            limits

            if limits is not None

            else RiskLimits()

        )


        self.exposure_engine = (

            exposure_engine

            if exposure_engine is not None

            else ExposureEngine()

        )


        self.kill_switch = (

            kill_switch

            if kill_switch is not None

            else KillSwitch()

        )


        self.market_valuation = (

            market_valuation

            if market_valuation is not None

            else RiskMarketValuation()

        )


        self.total_checks = 0

        self.total_approved = 0

        self.total_rejected = 0


        self.last_valuation_price = None

        self.last_projected_exposure = None






    # ========================================================
    # Single Signal
    # ========================================================


    def check_signal(
        self,
        signal,
        portfolio,
        state=None,
    ):

        return self.check_signals(
            signal,
            portfolio,
            state=state,
        )



    # ========================================================
    # Signal Check
    # ========================================================


    def check_signals(
        self,
        signals,
        portfolio,
        state=None,
    ):


        self.total_checks += 1


        checks = {}


        # ====================================================
        # Kill Switch
        # ====================================================

        if self.kill_switch.is_triggered():

            checks[
                "kill_switch"
            ] = False

            return self._reject(
                "Kill switch triggered",
                checks,
            )


        checks[
            "kill_switch"
        ] = True


        # ====================================================
        # Signal validation
        # ====================================================

        quantity = getattr(
            signals,
            "quantity",
            0,
        )

        side = getattr(
            signals,
            "side",
            None,
        )

        symbol = getattr(
            signals,
            "symbol",
            None,
        )


        if quantity <= 0:

            checks[
                "quantity"
            ] = False

            return self._reject(
                "Invalid quantity",
                checks,
            )


        checks[
            "quantity"
        ] = True


        if symbol is None:

            checks[
                "symbol"
            ] = False

            return self._reject(
                "Missing symbol",
                checks,
            )


        checks[
            "symbol"
        ] = True


        # ====================================================
        # Risk Valuation Price
        # ====================================================

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


        # ====================================================
        # Projected Exposure
        # ====================================================

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


        self.last_projected_exposure = (
            projected
        )


        # ====================================================
        # Valuation Fail Closed
        # ====================================================

        if not projected.valuation_valid:

            checks[
                "valuation"
            ] = False

            return self._reject(
                (
                    "Missing or invalid valuation data: "
                    +
                    ", ".join(
                        projected.invalid_symbols
                    )
                ),
                checks,
            )


        checks[
            "valuation"
        ] = True


        # ====================================================
        # Symbol Position Limit
        # ====================================================

        if (
            abs(
                projected.position_quantity
            )
            >
            self.limits.max_position_size
        ):

            checks[
                "position_limit"
            ] = False

            return self._reject(
                "Position limit exceeded",
                checks,
            )


        checks[
            "position_limit"
        ] = True


        # ====================================================
        # Total Position Limit
        # ====================================================

        if (
            projected.total_position
            >
            self.limits.max_total_position
        ):

            checks[
                "total_position_limit"
            ] = False

            return self._reject(
                "Total position limit exceeded",
                checks,
            )


        checks[
            "total_position_limit"
        ] = True


        # ====================================================
        # Dollar Exposure Limit
        # ====================================================
        #
        # Preserve existing boundary semantics:
        #
        #     gross_notional >= max_exposure
        #         -> reject
        #
        # ====================================================

        if (
            projected.gross_notional
            >=
            self.limits.max_exposure
        ):

            checks[
                "exposure_limit"
            ] = False

            return self._reject(
                "Exposure Limit exceeded",
                checks,
            )


        checks[
            "exposure_limit"
        ] = True


        return self._approve(
            checks
        )



    # ========================================================
    # Fill Update
    # ========================================================


    def on_fill(
        self,
        fill,
        portfolio,
    ):

        return self.exposure_engine.update(
            portfolio
        )



    # ========================================================
    # Reset
    # ========================================================


    def reset(
        self
    ):

        self.kill_switch.reset()

        self.total_checks = 0

        self.total_approved = 0

        self.total_rejected = 0

        self.last_valuation_price = None

        self.last_projected_exposure = None



    # ========================================================
    # Helpers
    # ========================================================


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



    # ========================================================
    # Snapshot
    # ========================================================


    def snapshot(
        self
    ):

        projected = (
            self.last_projected_exposure
        )


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

            "last_projected_exposure": (
                None
                if projected is None
                else {
                    "position_quantity":
                        projected.position_quantity,

                    "total_position":
                        projected.total_position,

                    "gross_exposure":
                        projected.gross_exposure,

                    "gross_notional":
                        projected.gross_notional,

                    "valuation_price":
                        projected.valuation_price,

                    "valuation_valid":
                        projected.valuation_valid,

                    "invalid_symbols":
                        list(
                            projected.invalid_symbols
                        ),
                }
            ),

        }
