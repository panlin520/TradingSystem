"""
risk/exposure.py

============================================================
Exposure Engine
============================================================
6
职责：

Position / Portfolio
        |
        v
Exposure Calculation

负责：

- 当前 symbol signed position
- 全账户 total position units
- 全账户 gross notional exposure
- 预测 Signal 成交后的风险状态
- 为 RiskManagerV2 提供风险计算结果

不负责：

- 下单
- 成交
- Position 更新
- Strategy
- 从 OrderBook 读取或转换价格

============================================================

价格契约：

RiskMarketValuation 负责：

    Databento raw nano-price
            ↓
    normalized market price

ExposureEngine 只接收 normalized valuation_price。

禁止在这里再次除以 1e9。

============================================================

Notional：

    abs(quantity)
    × normalized_price
    × point_value

例如：

    ES:
        2 × 7571.25 × 50
        = 757125 USD

============================================================

Fail Closed：

只要任意非零仓位无法获得：

    - 有效 normalized market price
    - 有效 point_value

则：

    valuation_valid = False

RiskManagerV2 在启用 dollar exposure 检查时必须拒绝该交易。

============================================================
"""


from dataclasses import dataclass, field
from typing import Optional, Tuple






# ============================================================
# Current Exposure Snapshot
# ============================================================


@dataclass
class ExposureSnapshot:
    """
    单 symbol 当前 Exposure 快照。
    """

    symbol: str

    quantity: int

    exposure: float

    market_price: Optional[float] = None

    point_value: Optional[float] = None

    notional: Optional[float] = None

    valuation_valid: bool = True






# ============================================================
# Projected Exposure
# ============================================================


@dataclass
class ProjectedExposure:
    """
    Signal 成交后的预测风险状态。
    """

    # 当前 signal symbol 的 signed projected position
    position_quantity: int = 0

    # 全账户仓位手数：
    # Σ abs(quantity)
    total_position: int = 0

    # 兼容旧接口。
    # 当前正式定义与 gross_notional 一致。
    gross_exposure: float = 0.0

    # 全账户美元名义暴露：
    # Σ abs(qty) × price × point_value
    gross_notional: float = 0.0

    # 当前 signal 使用的 normalized valuation price
    valuation_price: Optional[float] = None

    # 所有非零仓位是否都成功估值
    valuation_valid: bool = True

    # 无法估值的 symbols
    invalid_symbols: Tuple[str, ...] = field(
        default_factory=tuple
    )








class ExposureEngine:
    """
    Portfolio Exposure Engine。
    """


    def __init__(
        self,
        portfolio=None,
    ):

        self.portfolio = portfolio

        self.update_count = 0






    # ========================================================
    # Helpers
    # ========================================================


    @staticmethod
    def _normalize_symbol(
        symbol,
    ) -> str:

        return str(
            symbol
        ).upper()



    @staticmethod
    def _valid_positive_number(
        value,
    ) -> bool:

        if value is None:

            return False

        try:

            return float(value) > 0.0

        except (
            TypeError,
            ValueError,
        ):

            return False



    def _get_existing_position(
        self,
        portfolio,
        symbol,
    ):
        """
        优先只读 portfolio.positions，
        避免风险预测无意创建 Position。

        兼容没有 positions dict 的旧测试对象时，
        才回退 get_position()。
        """

        symbol = self._normalize_symbol(
            symbol
        )

        positions = getattr(
            portfolio,
            "positions",
            None,
        )

        if isinstance(
            positions,
            dict,
        ):

            return positions.get(
                symbol
            )


        getter = getattr(
            portfolio,
            "get_position",
            None,
        )

        if callable(
            getter
        ):

            return getter(
                symbol
            )


        return None



    def _get_point_value(
        self,
        portfolio,
        symbol,
        position=None,
    ) -> Optional[float]:
        """
        point value 优先级：

        1. position.point_value
        2. portfolio.point_values[symbol]

        不在 Risk 层猜默认合约乘数。
        """

        if position is not None:

            value = getattr(
                position,
                "point_value",
                None,
            )

            if self._valid_positive_number(
                value
            ):

                return float(
                    value
                )


        point_values = getattr(
            portfolio,
            "point_values",
            {},
        )

        if isinstance(
            point_values,
            dict,
        ):

            value = point_values.get(
                self._normalize_symbol(
                    symbol
                )
            )

            if self._valid_positive_number(
                value
            ):

                return float(
                    value
                )


        return None



    @staticmethod
    def _get_market_price(
        portfolio,
        symbol,
    ) -> Optional[float]:
        """
        Existing position valuation price。

        Portfolio.market_prices 中保存 normalized price。
        """

        prices = getattr(
            portfolio,
            "market_prices",
            {},
        )

        if not isinstance(
            prices,
            dict,
        ):

            return None


        value = prices.get(
            str(symbol).upper()
        )


        if value is None:

            return None


        try:

            value = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return None


        if value <= 0.0:

            return None


        return value



    # ========================================================
    # Current Quantity
    # ========================================================


    def get_position_quantity(
        self,
        portfolio,
        symbol,
    ):
        """
        获取当前 symbol signed quantity。
        """

        position = self._get_existing_position(
            portfolio,
            symbol,
        )


        if position is None:

            return 0


        return int(
            getattr(
                position,
                "quantity",
                0,
            )
        )



    # ========================================================
    # Current Quantity Exposure Compatibility
    # ========================================================


    def calculate(
        self,
        portfolio,
        symbol,
    ):
        """
        保留旧接口：

            当前单 symbol absolute quantity exposure。
        """

        quantity = self.get_position_quantity(
            portfolio,
            symbol,
        )


        return abs(
            quantity
        )



    # ========================================================
    # Project Signal
    # ========================================================


    def project_signal(
        self,
        portfolio,
        symbol,
        side,
        quantity,
        valuation_price=None,
    ):
        """
        预测 Signal 成交后的：

            position_quantity
            total_position
            gross_notional

        不修改真实 Portfolio。
        """

        symbol = self._normalize_symbol(
            symbol
        )


        current = self.get_position_quantity(
            portfolio,
            symbol,
        )


        # ====================================================
        # Side normalization
        # ====================================================

        if hasattr(
            side,
            "value",
        ):

            side = side.value


        side = str(
            side
        ).upper()


        if side == "BUY":

            projected = (
                current
                +
                int(quantity)
            )


        elif side == "SELL":

            projected = (
                current
                -
                int(quantity)
            )


        else:

            projected = current


        # ====================================================
        # Build projected quantities without mutating Portfolio
        # ====================================================

        positions = getattr(
            portfolio,
            "positions",
            {},
        )


        projected_quantities = {}


        if isinstance(
            positions,
            dict,
        ):

            for sym, pos in positions.items():

                sym_key = self._normalize_symbol(
                    sym
                )

                projected_quantities[
                    sym_key
                ] = int(
                    getattr(
                        pos,
                        "quantity",
                        0,
                    )
                )


        projected_quantities[
            symbol
        ] = projected


        # ====================================================
        # Total Position Units
        # ====================================================

        total_position = sum(

            abs(qty)

            for qty in projected_quantities.values()

        )


        # ====================================================
        # Gross Notional
        # ====================================================

        gross_notional = 0.0

        invalid_symbols = []


        for sym, qty in projected_quantities.items():

            if qty == 0:

                continue


            position = None

            if isinstance(
                positions,
                dict,
            ):

                position = positions.get(
                    sym
                )


            point_value = self._get_point_value(
                portfolio,
                sym,
                position=position,
            )


            # 当前 signal symbol：
            # 使用 RiskMarketValuation 传入的稳定盘口估值价。
            if sym == symbol:

                price = valuation_price

            else:

                price = self._get_market_price(
                    portfolio,
                    sym,
                )


            if not self._valid_positive_number(
                price
            ):

                invalid_symbols.append(
                    sym
                )

                continue


            if not self._valid_positive_number(
                point_value
            ):

                invalid_symbols.append(
                    sym
                )

                continue


            gross_notional += (

                abs(
                    qty
                )

                *

                float(
                    price
                )

                *

                float(
                    point_value
                )

            )


        invalid_symbols = tuple(
            sorted(
                set(
                    invalid_symbols
                )
            )
        )


        valuation_valid = (
            len(
                invalid_symbols
            )
            ==
            0
        )


        return ProjectedExposure(

            position_quantity=projected,

            total_position=total_position,

            gross_exposure=gross_notional,

            gross_notional=gross_notional,

            valuation_price=(
                float(valuation_price)
                if self._valid_positive_number(
                    valuation_price
                )
                else None
            ),

            valuation_valid=valuation_valid,

            invalid_symbols=invalid_symbols,

        )



    # ========================================================
    # Compatibility Wrapper
    # ========================================================


    def project_signals(
        self,
        portfolio,
        symbol,
        side,
        quantity,
        valuation_price=None,
    ):
        """
        RiskManagerV2 compatibility wrapper。
        """

        return self.project_signal(

            portfolio,

            symbol,

            side,

            quantity,

            valuation_price=valuation_price,

        )



    # ========================================================
    # Fill Update
    # ========================================================


    def update(
        self,
        portfolio,
    ):
        """
        Fill 后刷新 quantity exposure snapshot。

        保留旧返回结构：
            symbol -> abs(quantity)
        """

        self.update_count += 1


        result = {}


        positions = getattr(
            portfolio,
            "positions",
            {},
        )


        if not isinstance(
            positions,
            dict,
        ):

            return result


        for symbol, position in positions.items():

            qty = int(
                getattr(
                    position,
                    "quantity",
                    0,
                )
            )

            result[
                symbol
            ] = abs(
                qty
            )


        return result



    # ========================================================
    # Snapshot
    # ========================================================


    def snapshot(
        self,
        portfolio,
    ):

        data = {}


        positions = getattr(
            portfolio,
            "positions",
            {},
        )


        if not isinstance(
            positions,
            dict,
        ):

            return data


        for symbol, position in positions.items():

            symbol_key = self._normalize_symbol(
                symbol
            )

            qty = int(
                getattr(
                    position,
                    "quantity",
                    0,
                )
            )


            market_price = self._get_market_price(
                portfolio,
                symbol_key,
            )

            point_value = self._get_point_value(
                portfolio,
                symbol_key,
                position=position,
            )


            valuation_valid = True

            notional = 0.0


            if qty != 0:

                if (
                    not self._valid_positive_number(
                        market_price
                    )
                    or
                    not self._valid_positive_number(
                        point_value
                    )
                ):

                    valuation_valid = False

                    notional = None

                else:

                    notional = (

                        abs(
                            qty
                        )

                        *

                        market_price

                        *

                        point_value

                    )


            data[
                symbol_key
            ] = ExposureSnapshot(

                symbol=symbol_key,

                quantity=qty,

                exposure=(
                    notional
                    if notional is not None
                    else 0.0
                ),

                market_price=market_price,

                point_value=point_value,

                notional=notional,

                valuation_valid=valuation_valid,

            )


        return data
