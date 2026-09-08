"""
core/clock.py

============================================================
Trading System Clock
============================================================

职责：

    提供交易系统统一时间管理。


设计目标：

    Backtest
        使用历史行情时间推进


    Paper Trading
        使用模拟市场时间


    Live Trading
        使用真实系统时间


所有模块：

    Strategy
    Risk
    Execution
    Portfolio
    Analytics


禁止直接：

    datetime.now()


必须：

    clock.now()


============================================================


时间流：

Databento MBO

      |
      v

MarketEvent.ts_event

      |
      v

Trading Clock

      |
      v

System State


============================================================

"""


from enum import Enum
from datetime import datetime, timezone
from typing import Optional



# ============================================================
# Clock Mode
# ============================================================

class ClockMode(Enum):
    """
    系统运行时间模式。

    """

    # ----------------------------------------
    # 回测时间
    #
    # 时间来自历史数据
    # ----------------------------------------

    BACKTEST = "BACKTEST"



    # ----------------------------------------
    # 模拟交易时间
    #
    # 可以使用实时行情
    # 但是系统时间由模拟控制
    # ----------------------------------------

    PAPER = "PAPER"



    # ----------------------------------------
    # 实盘时间
    #
    # 使用真实系统UTC时间
    # ----------------------------------------

    LIVE = "LIVE"




# ============================================================
# Clock
# ============================================================

class Clock:
    """
    交易系统统一时钟。


    ========================================================

    不同模式：

    --------------------------------------------------------

    BACKTEST:

        MarketEvent.ts_event

                |
                v

              clock


        时间严格按照历史推进。



    --------------------------------------------------------

    PAPER:

        实时行情

                |

        模拟系统时间



    --------------------------------------------------------

    LIVE:

        datetime.now()



    ========================================================


    """



    def __init__(
        self,
        mode: ClockMode = ClockMode.BACKTEST
    ):

        # 当前运行模式

        self.mode = mode



        # 当前系统时间

        self._current_time: Optional[int] = None



        # 启动时间

        self._start_time: Optional[int] = None



        # 最后更新时间

        self._last_update: Optional[int] = None



    # ========================================================
    # 设置时间
    # ========================================================

    def update(
        self,
        timestamp: int
    ):
        """
        更新时间。


        参数：

            timestamp:

                纳秒时间戳


        主要用于：

            BACKTEST


        例如：

            Databento:

            ts_event


        """

        self._current_time = timestamp



        if self._start_time is None:

            self._start_time = timestamp



        self._last_update = timestamp



    # ========================================================
    # 获取当前时间
    # ========================================================

    def now(self) -> int:
        """
        获取当前系统时间。


        返回：

            纳秒时间戳



        """

        # ----------------------------------------
        # 回测
        # ----------------------------------------

        if self.mode == ClockMode.BACKTEST:

            if self._current_time is None:

                raise RuntimeError(
                    "Backtest clock has no timestamp"
                )


            return self._current_time



        # ----------------------------------------
        # 模拟交易
        # ----------------------------------------

        elif self.mode == ClockMode.PAPER:


            if self._current_time is not None:

                return self._current_time



        # ----------------------------------------
        # 实盘
        # ----------------------------------------

        if self.mode == ClockMode.LIVE:

            return int(
                datetime.now(
                    timezone.utc
                ).timestamp()
                *
                1_000_000_000
            )



        # fallback

        if self._current_time is not None:

            return self._current_time



        raise RuntimeError(
            "Clock has no available time"
        )



    # ========================================================
    # 获取datetime格式
    # ========================================================

    def datetime(
        self
    ) -> datetime:
        """
        返回Python datetime对象。

        """

        timestamp = self.now()


        return datetime.fromtimestamp(
            timestamp / 1_000_000_000,
            tz=timezone.utc
        )



    # ========================================================
    # 重置
    # ========================================================

    def reset(self):
        """
        重置Clock状态。

        """

        self._current_time = None

        self._start_time = None

        self._last_update = None



    # ========================================================
    # 状态
    # ========================================================

    def is_backtest(self) -> bool:
        """
        是否回测模式。
        """

        return self.mode == ClockMode.BACKTEST



    def is_paper(self) -> bool:
        """
        是否模拟交易。
        """

        return self.mode == ClockMode.PAPER



    def is_live(self) -> bool:
        """
        是否实盘。
        """

        return self.mode == ClockMode.LIVE



    # ========================================================
    # 信息
    # ========================================================

    def status(self) -> dict:
        """
        返回Clock状态。
        """

        return {

            "mode":
                self.mode.value,


            "current_time":
                self._current_time,


            "start_time":
                self._start_time,


            "last_update":
                self._last_update,

        }