"""
runtime/feature_runtime.py


============================================================
Feature Runtime
============================================================


职责：

    管理 FeatureEngine 运行状态。


数据流：


    OrderBook

        ↓

    FeatureEngine

        ↓

    FeatureSnapshot

        ↓

    FeatureRuntime


============================================================


负责：

    - 调用 FeatureEngine
    - 保存最新 FeatureSnapshot
    - 提供 Snapshot 查询


============================================================


不负责：

    - Strategy

    - Signal

    - Risk

    - Execution

    - Portfolio


============================================================

"""


from typing import Optional


from features.engine import FeatureEngine

from features.snapshot import FeatureSnapshot





class FeatureRuntime:
    """
    Feature运行时管理器。



    作用：

        将 FeatureEngine

        封装成 Runtime Component。



    """



    def __init__(
        self,
        feature_engine: FeatureEngine
    ):
        """
        初始化。


        参数：

            feature_engine:

                FeatureEngine实例


        """

        self.feature_engine = feature_engine



        # 当前最新Snapshot

        self.latest_snapshot: Optional[
            FeatureSnapshot
        ] = None





    # ========================================================
    # Update
    # ========================================================


    def update(
        self,
        timestamp: Optional[int] = None
    ) -> FeatureSnapshot:
        """
        更新Feature。


        调用：

            FeatureEngine.update()


        保存：

            latest_snapshot



        返回：

            FeatureSnapshot


        """

        snapshot = self.feature_engine.update(

            timestamp=timestamp

        )


        self.latest_snapshot = snapshot



        return snapshot





    # ========================================================
    # Latest Snapshot
    # ========================================================


    def get_latest(
        self
    ) -> Optional[FeatureSnapshot]:
        """
        获取最新FeatureSnapshot。


        """

        return self.latest_snapshot





    # ========================================================
    # Reset
    # ========================================================


    def reset(
        self
    ):
        """
        重置Runtime状态。


        不影响：

            OrderBook

            FeatureEngine


        只清除：

            Runtime缓存


        """

        self.latest_snapshot = None





    # ========================================================
    # Status
    # ========================================================


    def has_snapshot(
        self
    ) -> bool:
        """
        是否已经产生Snapshot。


        """

        return self.latest_snapshot is not None





    # ========================================================
    # Dict
    # ========================================================


    def to_dict(
        self
    ) -> dict:
        """
        输出当前Feature状态。


        用于：

            Debug

            Web

            Monitoring


        """

        if self.latest_snapshot is None:

            return {}


        return self.latest_snapshot.to_dict()