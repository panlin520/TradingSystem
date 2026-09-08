"""
risk/limits.py


============================================================

Risk Limits

============================================================


职责：

    - 单品种仓位限制
    - 总仓位限制
    - Exposure限制


不负责：

    - Order
    - Execution
    - Position计算


============================================================

"""


from dataclasses import dataclass, field





@dataclass
class RiskLimits:
    """
    风控限制配置。


    兼容：

        max_position

    和：

        max_position_size


    """



    # ==================================================
    # 单品种最大仓位
    #
    # 测试使用:
    #
    # RiskLimits(max_position=5)
    #
    # ==================================================

    max_position: int = 5




    # ==================================================
    # 总仓位限制
    # ==================================================

    max_total_position: int = 10




    # ==================================================
    # 最大 Exposure
    # ==================================================

    max_exposure: float = 1000000.0




    # ==================================================
    # 初始化后兼容字段
    # ==================================================

    max_position_size: int = field(
        init=False
    )




    def __post_init__(self):
        """
        初始化同步。

        RiskManagerV2 使用:

            max_position_size


        测试使用:

            max_position

        """

        self.max_position_size = self.max_position






    # ==================================================
    # Setter兼容
    # ==================================================

    def set_position_limit(
        self,
        value:int
    ):
        """
        修改仓位限制。

        同时更新两个字段。
        """

        self.max_position = value

        self.max_position_size = value






    # ==================================================
    # Property
    # ==================================================

    @property
    def position_limit(self):
        """
        当前仓位限制。
        """

        return self.max_position_size




    # ==================================================
    # Snapshot
    # ==================================================

    def snapshot(self):

        return {

            "max_position":
                self.max_position,


            "max_position_size":
                self.max_position_size,


            "max_total_position":
                self.max_total_position,


            "max_exposure":
                self.max_exposure,

        }