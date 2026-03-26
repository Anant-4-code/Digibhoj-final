from sqlalchemy import Column, Integer, String, ForeignKey, Date, Enum as SAEnum
from sqlalchemy.orm import relationship
from backend.database import Base
import enum


class DeliveryStatus(str, enum.Enum):
    scheduled = "scheduled"
    preparing = "preparing"
    delivered = "delivered"
    cancelled = "cancelled"


class SubscriptionDelivery(Base):
    __tablename__ = "subscription_deliveries"
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(SAEnum(DeliveryStatus), default=DeliveryStatus.scheduled)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)

    subscription = relationship("Subscription", back_populates="deliveries")
    order = relationship("Order")
