"""
features/flow_features.py

============================================================
Order Flow Features
============================================================

职责：

    从Databento MBO Event中提取真实订单流变化。

============================================================

真实ESU6 Ground Truth：

完整日：

    10,417,106 MBO Events

Cancel：

    4,111,285

    全部：

        C.size == current_order.size

Modify：

    1,145,108

    Size Increase:
        93,343

    Size Decrease:
        190,731

    Price Move:
        1,051,814

    Side Change:
        0

============================================================

核心问题：

Databento M：

    event.size

表示：

    修改后的new size

不是：

    liquidity delta

所以：

    old_size
        ↓
    event.size

必须比较前后状态。

============================================================

解决方案：

FlowFeatures内部维护一个轻量Shadow Order State。

只保存：

    order_id
    side
    price
    size

它：

    不替代OrderBook
    不维护FIFO
    不参与best bid/ask
    不参与交易执行

唯一职责：

    保存事件前订单状态，
    用于计算真实Order Flow delta。

============================================================

Directional Flow定义：

Positive：

    Bid Add
    Ask Remove

Negative：

    Ask Add
    Bid Remove


signed_order_flow：

    Bid Added
    +
    Ask Removed
    -
    Ask Added
    -
    Bid Removed


OFI：

    signed_order_flow
    /
    total directional activity

============================================================

Liquidity Balance：

    liquidity_added
    -
    liquidity_removed

        /

    liquidity_added
    +
    liquidity_removed

============================================================

IMPORTANT：

    OFI != Liquidity Balance

============================================================
"""

from dataclasses import dataclass
from typing import Dict, Optional

from features.snapshot import FeatureSnapshot


# ============================================================
# Shadow Order State
# ============================================================


@dataclass
class FlowOrderState:
    """
    FlowFeatures内部轻量订单状态。

    不参与真实OrderBook构建。
    """

    order_id: int

    side: object = None

    price: Optional[int] = None

    size: int = 0


# ============================================================
# Flow Features
# ============================================================


class FlowFeatures:
    """
    L3 Order Flow特征计算器。

    一个实例对应一个instrument/session。
    """

    def __init__(self):

        # ====================================================
        # Shadow Orders
        # ====================================================

        self.orders: Dict[
            int,
            FlowOrderState,
        ] = {}

    # ========================================================
    # Main Update
    # ========================================================

    def update(
        self,
        event,
        snapshot: Optional[FeatureSnapshot] = None,
    ):
        """
        使用一个MBO event更新FeatureSnapshot。
        """

        if snapshot is None:

            snapshot = FeatureSnapshot()

        action = self._action(
            event
        )

        size = self._size(
            event
        )

        # ====================================================
        # ADD
        # ====================================================

        if action == "A":

            self._handle_add(
                event,
                size,
                snapshot,
            )

        # ====================================================
        # MODIFY
        # ====================================================

        elif action == "M":

            self._handle_modify(
                event,
                size,
                snapshot,
            )

        # ====================================================
        # CANCEL
        # ====================================================

        elif action == "C":

            self._handle_cancel(
                event,
                size,
                snapshot,
            )

        # ====================================================
        # RESET
        # ====================================================

        elif action == "R":

            # RESET只清空Shadow State。
            #
            # 不能把R.size当作cancel volume。
            self.orders.clear()

        # ====================================================
        # TRADE
        # ====================================================

        elif action == "T":

            # TradeFeatures负责。
            #
            # T本身不计入这里的被动挂单流变化。
            pass

        # ====================================================
        # FILL
        # ====================================================

        elif action == "F":

            # 当前冻结系统定义：
            #
            # F不直接修改OrderBook。
            #
            # Flow shadow保持一致，
            # 同样不直接修改。
            pass

        # ====================================================
        # NONE
        # ====================================================

        elif action == "N":

            pass

        # ====================================================
        # Recalculate Metrics
        # ====================================================

        self._update_metrics(
            snapshot
        )

        return snapshot

    # ========================================================
    # ADD
    # ========================================================

    def _handle_add(
        self,
        event,
        size,
        snapshot,
    ):
        """
        A：

            新增流动性。
        """

        snapshot.add_volume += (
            size
        )

        order_id = getattr(
            event,
            "order_id",
            None,
        )

        side = getattr(
            event,
            "side",
            None,
        )

        price = getattr(
            event,
            "price",
            None,
        )

        # ====================================================
        # Flow Accounting
        # ====================================================

        self._record_added(
            snapshot,
            side,
            size,
        )

        # ====================================================
        # Missing ID
        # ====================================================

        if order_id is None:

            self._increment_extra(
                snapshot,
                "flow_missing_add_order_id_count",
            )

            return

        # ====================================================
        # Duplicate ID Diagnostic
        # ====================================================

        if order_id in self.orders:

            self._increment_extra(
                snapshot,
                "flow_duplicate_add_count",
            )

        # ====================================================
        # Shadow State
        # ====================================================

        self.orders[
            order_id
        ] = FlowOrderState(
            order_id=order_id,
            side=side,
            price=price,
            size=size,
        )

    # ========================================================
    # MODIFY
    # ========================================================

    def _handle_modify(
        self,
        event,
        size,
        snapshot,
    ):
        """
        M：

        event.size是new size。

        必须读取Shadow中old state。
        """

        # ====================================================
        # Raw M.size
        # ====================================================

        snapshot.modify_volume += (
            size
        )

        order_id = getattr(
            event,
            "order_id",
            None,
        )

        # ====================================================
        # Missing Order
        # ====================================================

        if (
            order_id is None
            or
            order_id not in self.orders
        ):

            self._increment_extra(
                snapshot,
                "flow_missing_modify_count",
            )

            return

        old = self.orders[
            order_id
        ]

        old_side = old.side

        old_price = old.price

        old_size = old.size

        # ====================================================
        # New State
        # ====================================================

        event_side = getattr(
            event,
            "side",
            None,
        )

        event_price = getattr(
            event,
            "price",
            None,
        )

        event_size = getattr(
            event,
            "size",
            None,
        )

        new_side = (
            event_side
            if event_side is not None
            else old_side
        )

        new_price = (
            event_price
            if event_price is not None
            else old_price
        )

        new_size = (
            self._safe_int(
                event_size,
                old_size,
            )
            if event_size is not None
            else old_size
        )

        # ====================================================
        # Modify Net Size Delta
        #
        # 这是Modify本身的数量变化统计。
        #
        # 与price migration accounting分开。
        # ====================================================

        if new_size > old_size:

            delta = (
                new_size
                -
                old_size
            )

            snapshot.modify_added_volume += (
                delta
            )

        elif new_size < old_size:

            delta = (
                old_size
                -
                new_size
            )

            snapshot.modify_removed_volume += (
                delta
            )

        # ====================================================
        # Location Change
        #
        # Price变化或Side变化意味着：
        #
        # old location:
        #     remove old_size
        #
        # new location:
        #     add new_size
        #
        # ====================================================

        price_changed = (
            new_price
            !=
            old_price
        )

        side_changed = (
            self._side(
                new_side
            )
            !=
            self._side(
                old_side
            )
        )

        location_changed = (
            price_changed
            or
            side_changed
        )

        if location_changed:

            # ------------------------------------------------
            # Remove Old Location
            # ------------------------------------------------

            self._record_removed(
                snapshot,
                old_side,
                old_size,
            )

            # ------------------------------------------------
            # Add New Location
            # ------------------------------------------------

            self._record_added(
                snapshot,
                new_side,
                new_size,
            )

            # ------------------------------------------------
            # Price Migration Diagnostics
            # ------------------------------------------------

            if price_changed:

                snapshot.price_move_count += 1

                snapshot.price_move_removed_volume += (
                    old_size
                )

                snapshot.price_move_added_volume += (
                    new_size
                )

        # ====================================================
        # Same Location
        #
        # 只记录真实size delta。
        # ====================================================

        else:

            if new_size > old_size:

                delta = (
                    new_size
                    -
                    old_size
                )

                self._record_added(
                    snapshot,
                    new_side,
                    delta,
                )

            elif new_size < old_size:

                delta = (
                    old_size
                    -
                    new_size
                )

                self._record_removed(
                    snapshot,
                    old_side,
                    delta,
                )

        # ====================================================
        # Update Shadow
        # ====================================================

        old.side = new_side

        old.price = new_price

        old.size = new_size

    # ========================================================
    # CANCEL
    # ========================================================

    def _handle_cancel(
        self,
        event,
        size,
        snapshot,
    ):
        """
        C：

        当前ESU6完整日：

            C.size == old_size

        但Shadow仍支持partial C，
        保持Feature模块通用性。
        """

        # Raw cancel event volume
        snapshot.cancel_volume += (
            size
        )

        order_id = getattr(
            event,
            "order_id",
            None,
        )

        # ====================================================
        # Missing Shadow Order
        # ====================================================

        if (
            order_id is None
            or
            order_id not in self.orders
        ):

            self._increment_extra(
                snapshot,
                "flow_missing_cancel_count",
            )

            # 不知道旧订单状态，
            # 不猜directional flow。
            return

        state = self.orders[
            order_id
        ]

        old_size = state.size

        # ====================================================
        # Removed Quantity
        # ====================================================

        removed = min(
            max(
                size,
                0,
            ),
            old_size,
        )

        self._record_removed(
            snapshot,
            state.side,
            removed,
        )

        remaining = (
            old_size
            -
            removed
        )

        # ====================================================
        # Full Cancel
        # ====================================================

        if remaining <= 0:

            self.orders.pop(
                order_id,
                None,
            )

        # ====================================================
        # Partial Cancel
        # ====================================================

        else:

            state.size = remaining

    # ========================================================
    # Record Added
    # ========================================================

    def _record_added(
        self,
        snapshot,
        side,
        size,
    ):
        """
        记录流动性新增。
        """

        size = max(
            self._safe_int(
                size,
                0,
            ),
            0,
        )

        if size == 0:

            return

        snapshot.liquidity_added += (
            size
        )

        normalized = self._side(
            side
        )

        if normalized == "B":

            snapshot.bid_added_volume += (
                size
            )

        elif normalized == "A":

            snapshot.ask_added_volume += (
                size
            )

        else:

            self._increment_extra(
                snapshot,
                "flow_unknown_side_added_count",
            )

    # ========================================================
    # Record Removed
    # ========================================================

    def _record_removed(
        self,
        snapshot,
        side,
        size,
    ):
        """
        记录流动性移除。
        """

        size = max(
            self._safe_int(
                size,
                0,
            ),
            0,
        )

        if size == 0:

            return

        snapshot.liquidity_removed += (
            size
        )

        normalized = self._side(
            side
        )

        if normalized == "B":

            snapshot.bid_removed_volume += (
                size
            )

        elif normalized == "A":

            snapshot.ask_removed_volume += (
                size
            )

        else:

            self._increment_extra(
                snapshot,
                "flow_unknown_side_removed_count",
            )

    # ========================================================
    # Metrics
    # ========================================================

    def _update_metrics(
        self,
        snapshot,
    ):
        """
        更新：

            signed_order_flow
            ofi
            liquidity_balance
        """

        # ====================================================
        # Directional Components
        # ====================================================

        positive = (
            snapshot.bid_added_volume
            +
            snapshot.ask_removed_volume
        )

        negative = (
            snapshot.ask_added_volume
            +
            snapshot.bid_removed_volume
        )

        snapshot.signed_order_flow = (
            positive
            -
            negative
        )

        directional_activity = (
            positive
            +
            negative
        )

        # ====================================================
        # Directional OFI
        # ====================================================

        if directional_activity == 0:

            snapshot.ofi = 0.0

        else:

            snapshot.ofi = (
                snapshot.signed_order_flow
                /
                directional_activity
            )

        # ====================================================
        # Liquidity Balance
        # ====================================================

        total_liquidity_flow = (
            snapshot.liquidity_added
            +
            snapshot.liquidity_removed
        )

        if total_liquidity_flow == 0:

            snapshot.liquidity_balance = 0.0

        else:

            snapshot.liquidity_balance = (
                (
                    snapshot.liquidity_added
                    -
                    snapshot.liquidity_removed
                )
                /
                total_liquidity_flow
            )

    # ========================================================
    # Action
    # ========================================================

    def _action(
        self,
        event,
    ):
        """
        Action统一转换。
        """

        action = getattr(
            event,
            "action",
            None,
        )

        if action is None:

            return ""

        try:

            return str(
                action.value
            ).upper()

        except Exception:

            return str(
                action
            ).upper()

    # ========================================================
    # Side
    # ========================================================

    def _side(
        self,
        side,
    ):
        """
        Side统一为：

            B
            A
            ""
        """

        if side is None:

            return ""

        try:

            value = str(
                side.value
            ).upper()

        except Exception:

            value = str(
                side
            ).upper()

        if value in (
            "B",
            "BID",
            "BUY",
        ):

            return "B"

        if value in (
            "A",
            "ASK",
            "SELL",
        ):

            return "A"

        return ""

    # ========================================================
    # Event Size
    # ========================================================

    def _size(
        self,
        event,
    ):
        """
        安全读取event.size。
        """

        return max(
            self._safe_int(
                getattr(
                    event,
                    "size",
                    0,
                ),
                0,
            ),
            0,
        )

    # ========================================================
    # Safe Int
    # ========================================================

    @staticmethod
    def _safe_int(
        value,
        default=0,
    ):
        """
        安全整数转换。
        """

        if value is None:

            return default

        try:

            return int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return default

    # ========================================================
    # Extra Counter
    # ========================================================

    @staticmethod
    def _increment_extra(
        snapshot,
        key,
    ):
        """
        增加诊断计数。
        """

        snapshot.extra[
            key
        ] = (
            snapshot.extra.get(
                key,
                0,
            )
            +
            1
        )

    # ========================================================
    # Get Shadow Order
    # ========================================================

    def get_order_state(
        self,
        order_id,
    ):
        """
        返回指定Shadow Order State。

        只用于：

            Feature内部
            Debug
            Tests
        """

        return self.orders.get(
            order_id
        )

    # ========================================================
    # Active Orders
    # ========================================================

    def active_order_count(
        self,
    ):
        """
        返回当前Shadow订单数量。
        """

        return len(
            self.orders
        )

    # ========================================================
    # Reset
    # ========================================================

    def reset(
        self,
    ):
        """
        重置Flow内部状态。

        新Session / 新回测周期使用。
        """

        self.orders.clear()