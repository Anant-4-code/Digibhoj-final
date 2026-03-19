from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime, String, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum

class PaymentMethod(str, enum.Enum):
    upi = "UPI"
    card = "Card"
    wallet = "Wallet"
    cash = "Cash"

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True)
    amount = Column(Float)
    payment_method = Column(SAEnum(PaymentMethod), default=PaymentMethod.cash)
    payment_status = Column(String, default="paid")
    transaction_id = Column(String)
    created_at = Column(DateTime, server_default=func.now())

    order = relationship("Order", back_populates="payment")
