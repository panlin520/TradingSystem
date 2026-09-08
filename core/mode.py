from enum import Enum


class TradingMode(str, Enum):

    BACKTEST = "BACKTEST"

    PAPER = "PAPER"

    LIVE = "LIVE"