"""
risk/kill_switch.py

============================================================
Kill Switch
============================================================

职责：

    交易系统紧急停止机制。


============================================================


触发原因：


1.

数据异常


例如：

    行情停止

    sequence异常

    盘口异常



2.

订单异常


例如：

    大量拒单

    重复下单



3.

风险异常


例如：

    超最大亏损

    超仓位限制



4.

网络异常


例如：

    Broker断开



5.

人工停止



============================================================


触发后：


Kill Switch

        |

        v


停止产生新订单


        |

        v


通知Execution取消订单


        |

        v


系统进入保护状态



============================================================


"""



from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any




# ============================================================
# Kill Switch State
# ============================================================

class KillSwitchState(Enum):
    """
    Kill Switch状态。

    """

    NORMAL = "NORMAL"


    TRIGGERED = "TRIGGERED"



# ============================================================
# Kill Switch
# ============================================================

class KillSwitch:
    """
    紧急停止控制器。


    """



    def __init__(self):


        # ====================================================
        # 当前状态
        # ====================================================

        self.state = (
            KillSwitchState.NORMAL
        )



        # ====================================================
        # 触发原因
        # ====================================================

        self.reason: Optional[str] = None



        # ====================================================
        # 触发时间
        # ====================================================

        self.trigger_time: Optional[int] = None



        # ====================================================
        # 历史记录
        # ====================================================

        self.history = []




    # ========================================================
    # 触发
    # ========================================================

    def trigger(
        self,
        reason: str
    ):
        """
        触发Kill Switch。


        """

        if self.state == KillSwitchState.TRIGGERED:

            return



        self.state = (
            KillSwitchState.TRIGGERED
        )


        self.reason = reason



        timestamp = int(

            datetime.now(
                timezone.utc
            ).timestamp()

            *

            1_000_000_000

        )


        self.trigger_time = timestamp



        self.history.append(

            {

                "reason":
                    reason,


                "timestamp":
                    timestamp,

            }

        )




    # ========================================================
    # 重置
    # ========================================================

    def reset(
        self
    ):
        """
        恢复交易。


        注意：

        实盘中通常需要人工确认。


        """

        self.state = (
            KillSwitchState.NORMAL
        )


        self.reason = None



    # ========================================================
    # 是否停止
    # ========================================================

    def is_triggered(
        self
    ) -> bool:
        """
        是否已经触发。


        """

        return (

            self.state
            ==
            KillSwitchState.TRIGGERED

        )




    # ========================================================
    # 检查
    # ========================================================

    def check(
        self
    ) -> bool:
        """
        返回是否允许交易。


        True:

            允许


        False:

            禁止



        """

        return not self.is_triggered()




    # ========================================================
    # 状态
    # ========================================================

    def snapshot(
        self
    ) -> Dict[str, Any]:
        """
        状态输出。


        """

        return {


            "state":
                self.state.value,


            "triggered":
                self.is_triggered(),


            "reason":
                self.reason,


            "trigger_time":
                self.trigger_time,


            "history":
                self.history,

        }