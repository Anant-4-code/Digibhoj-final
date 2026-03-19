from sqlalchemy import Column, Integer, String, ForeignKey, Float, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum

class OrderStatus(str, enum.Enum):
    created = "created"
    confirmed = "confirmed"
    preparing = "preparing"
    ready = "ready"
    picked_up = "picked_up"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    completed = "completed"
    cancelled = "cancelled"

class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    provider_id = Column(Integer, ForeignKey("providers.id"))
    total_price = Column(Float, default=0.0)
    delivery_address = Column(Text)
    payment_method = Column(String, default="Cash")
    order_status = Column(SAEnum(OrderStatus), default=OrderStatus.created)
    payment_status = Column(SAEnum(PaymentStatus), default=PaymentStatus.pending)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    customer = relationship("Customer", back_populates="orders")
    provider = relationship("Provider", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete")
    assignment = relationship("DeliveryAssignment", back_populates="order", uselist=False)
    review = relationship("Review", back_populates="order", uselist=False)
    payment = relationship("Payment", back_populates="order", uselist=False)
