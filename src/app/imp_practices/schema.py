
from typing import List
from pydantic import BaseModel
from datetime import datetime

class OrderSummaryResponse(BaseModel):
    username: str
    product_name: List[str]
    date: datetime
    total_spent: float
    products: List[str]

    class Config:
        from_attributes=True
