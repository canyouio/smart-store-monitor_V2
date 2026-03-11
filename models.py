from dataclasses import dataclass
from datetime import datetime

@dataclass
class Order:
    """订单实体类：用于离线营收分析"""
    id: int
    category: str      # 商品品类，如'鲜食便当'
    amount: float      # 订单金额
    timestamp: datetime

@dataclass
class Visit:
    """进出记录实体类：用于实时客流监控"""
    id: int
    action: str        # 'enter' 进店 或 'exit' 出店
    timestamp: datetime