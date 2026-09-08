from core.mode import TradingMode
from execution.fill import Fill
from .pnl import PnL
from .position import Position

class Portfolio:
    def __init__(self, initial_capital: float = 0.0, mode: TradingMode = TradingMode.BACKTEST, point_values: dict[str, float] | None = None) -> None:
        self.initial_capital, self.mode = initial_capital, TradingMode(mode)
        self.point_values = point_values or {}
        self.positions: dict[str, Position] = {}
        self.market_prices: dict[str, float] = {}
        self.fills: list[Fill] = []
        self.pnl = PnL()
        self.trade_count = 0
        self.volume = 0
        self.last_fill = None

    def get_position(self, symbol: str) -> Position:
        symbol = symbol.upper()
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol, self.point_values.get(symbol, 50.0))
        return self.positions[symbol]

    def on_fill(self, fill: Fill) -> None:
        update = self.get_position(fill.symbol).update(fill.side, fill.quantity, fill.price)
        self.pnl.realized += update.realized_pnl
        self.fills.append(fill)
        self.update_market_price(fill.symbol, fill.price)
        self.trade_count += 1
        self.volume += fill.quantity
        self.last_fill = fill

    def update_market_price(self, symbol: str, price: float) -> None:
        symbol = symbol.upper()
        self.market_prices[symbol] = price
        if symbol in self.positions:
            self.pnl.unrealized_by_symbol[symbol] = self.positions[symbol].unrealized_pnl(price)

    @property
    def equity(self) -> float:
        return self.initial_capital + self.pnl.total

    def snapshot(self) -> dict:
        return {"mode": self.mode.value, "capital": self.initial_capital, "equity": self.equity,
                "pnl": self.pnl.snapshot(), "positions": {s: p.snapshot(self.market_prices.get(s)) for s, p in self.positions.items()},
                "fills": len(self.fills)}

