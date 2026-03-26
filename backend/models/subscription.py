from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum

class SubscriptionPlanType(str, enum.Enum):
    weekly = "weekly"
    monthly = "monthly"

class SubscriptionStatus(str, enum.Enum):
    active = "active"
    cancelled = "cancelled"
    expired = "expired"

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=True)
    meal_id = Column(Integer, ForeignKey("meals.id"), nullable=True)
    plan_type = Column(SAEnum(SubscriptionPlanType), nullable=False)
    payment_method = Column(String, nullable=True) # COD, UPI, Card
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(SAEnum(SubscriptionStatus), default=SubscriptionStatus.active)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    customer = relationship("Customer")
    provider = relationship("Provider")
    plan = relationship("SubscriptionPlan")
    meal = relationship("Meal")
    deliveries = relationship("SubscriptionDelivery", back_populates="subscription", cascade="all, delete")
