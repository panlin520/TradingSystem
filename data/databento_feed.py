"""
data/databento_feed.py

============================================================
Databento MBO Feed
============================================================

职责：

    读取 Databento MBO 数据


支持：

    DBN
    DBN.ZST


输出：

    core.event.MarketEvent


============================================================

核心原则：

1.
保持 Databento 原始事件顺序。


2.
不重新排序：

    不使用：
        order_id
        timestamp
        price


3.
sequence 原样传递。


4.
本模块不修改 OrderBook。


============================================================

"""



from typing import Iterator, Optional, Any



from core.event import (
    MarketEvent,
    OrderAction,
    OrderSide,
)





class DatabentoFeed:


    """
    Databento MBO 数据读取器

    数据流程：

        Databento Record

              |

              v

        DatabentoFeed

              |

              v

        MarketEvent

              |

              v

        TradingEngine


    """



    def __init__(
        self,
        file_path: str,
        symbol: str = "ESU6",
    ):


        self.file_path = file_path


        # Databento MBOMsg 不提供 symbol
        # 使用外部传入
        self.symbol = symbol



        self.store = None


        self._initialized = False


        self.event_count = 0





    # ========================================================
    # 初始化 Databento
    # ========================================================

    def _initialize(self):


        if self._initialized:
            return



        try:

            import databento as db


        except ImportError:


            raise ImportError(
                "Please install databento package"
            )



        self.store = db.DBNStore.from_file(
            self.file_path
        )



        self._initialized = True






    # ========================================================
    # Action 转换
    # ========================================================


    @staticmethod
    def _convert_action(
        action: str
    ) -> OrderAction:


        mapping = {


            "A":
                OrderAction.ADD,


            "M":
                OrderAction.MODIFY,


            "C":
                OrderAction.CANCEL,


            "R":
                OrderAction.RESET,


            "T":
                OrderAction.TRADE,


            "F":
                OrderAction.FILL,


            "N":
                OrderAction.NONE,


        }



        return mapping.get(
            action,
            OrderAction.NONE
        )






    # ========================================================
    # Side 转换
    # ========================================================


    @staticmethod
    def _convert_side(
        side: str
    ) -> Optional[OrderSide]:


        if side == "B":

            return OrderSide.BID



        if side == "A":

            return OrderSide.ASK



        return None






    # ========================================================
    # 安全转换函数
    # ========================================================


    @staticmethod
    def _safe_int(
        value
    ):


        """
        防止：

        NaN

        None

        空值

        """

        try:

            if value is None:

                return None


            return int(value)


        except:


            return None






    # ========================================================
    # Record 转换
    # ========================================================


    def _convert_record(
        self,
        record: Any
    ) -> MarketEvent:



        return MarketEvent(



            # 时间

            ts_event=self._safe_int(
                record.ts_event
            ),



            ts_recv=self._safe_int(
                record.ts_recv
            ),




            # 原始顺序

            sequence=self._safe_int(
                record.sequence
            ),




            # Action

            action=self._convert_action(
                record.action
            ),




            # Side

            side=self._convert_side(
                record.side
            ),




            # Order

            order_id=self._safe_int(
                record.order_id
            ),




            price=self._safe_int(
                record.price
            ),




            size=self._safe_int(
                record.size
            ),




            # Databento MBOMsg 没有 symbol

            symbol=self.symbol,




            channel_id=self._safe_int(
                record.channel_id
            ),




            publisher_id=self._safe_int(
                record.publisher_id
            ),




            instrument_id=self._safe_int(
                record.instrument_id
            ),




            flags=self._safe_int(
                record.flags
            ),


        )








    # ========================================================
    # Iterator
    # ========================================================


    def __iter__(
        self
    ) -> Iterator[MarketEvent]:


        """
        输出事件流


        保持 Databento 原始顺序。


        不排序。


        """


        self._initialize()



        for record in self.store:


            event = self._convert_record(
                record
            )



            self.event_count += 1



            yield event







    # ========================================================
    # 状态
    # ========================================================


    def status(
        self
    ) -> dict:



        return {


            "file":

                self.file_path,


            "symbol":

                self.symbol,



            "initialized":

                self._initialized,



            "events":

                self.event_count,


        }