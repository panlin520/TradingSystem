"""
execution/fill.py

Trade Fill Object

Order Execution Result
"""


from dataclasses import dataclass
from datetime import datetime



@dataclass
class Fill:

    fill_id: str

    order_id: str

    symbol: str

    side: str

    quantity: int

    price: float

    timestamp: datetime = None

