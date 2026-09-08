class PnL:
    def __init__(self) -> None:
        self.realized = 0.0
        self.unrealized_by_symbol: dict[str, float] = {}
    @property
    def unrealized(self) -> float:
        return sum(self.unrealized_by_symbol.values())
    @property
    def total(self) -> float:
        return self.realized + self.unrealized
    def snapshot(self) -> dict:
        return {"realized": self.realized, "unrealized": self.unrealized, "total": self.total}

