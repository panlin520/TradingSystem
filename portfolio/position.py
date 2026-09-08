from dataclasses import dataclass
from enum import Enum

class PositionSide(str, Enum):
    FLAT = "FLAT"
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass(slots=True)
class PositionUpdate:
    closed_quantity: float
    realized_pnl: float

class Position:
    def __init__(self, symbol: str, point_value: float = 50.0) -> None:
        self.symbol, self.point_value = symbol.upper(), point_value
        self.quantity = self.avg_price = 0.0

    @property
    def side(self) -> PositionSide:
        return PositionSide.LONG if self.quantity > 0 else PositionSide.SHORT if self.quantity < 0 else PositionSide.FLAT

    def update(self, side: str, quantity: float, price: float) -> PositionUpdate:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if hasattr(side, "value"):
            side = side.value

        side = str(side).upper()

        signed = (
            quantity
            if side == "BUY"
            else -quantity
        )
        old_qty, old_avg = self.quantity, self.avg_price
        if old_qty == 0 or old_qty * signed > 0:
            new_qty = old_qty + signed
            self.avg_price = (abs(old_qty) * old_avg + quantity * price) / abs(new_qty)
            self.quantity = new_qty
            return PositionUpdate(0.0, 0.0)
        closed = min(abs(old_qty), quantity)
        direction = 1.0 if old_qty > 0 else -1.0
        realized = (price - old_avg) * closed * direction * self.point_value
        self.quantity = old_qty + signed
        if self.quantity == 0:
            self.avg_price = 0.0
        elif old_qty * self.quantity < 0:
            self.avg_price = price
        return PositionUpdate(closed, realized)

    def unrealized_pnl(self, market_price: float) -> float:
        direction = 1.0 if self.quantity > 0 else -1.0
        return (market_price - self.avg_price) * abs(self.quantity) * direction * self.point_value if self.quantity else 0.0

    def snapshot(self, market_price: float | None = None) -> dict:
        return {"symbol": self.symbol, "side": self.side.value, "quantity": self.quantity,
                "avg_price": self.avg_price, "unrealized_pnl": self.unrealized_pnl(market_price) if market_price is not None else 0.0}

