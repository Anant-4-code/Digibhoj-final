from sqlalchemy import Column, Integer, String, ForeignKey, Float, Text, Boolean, DateTime, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum

class MealCategory(str, enum.Enum):
    breakfast = "Breakfast"
    lunch = "Lunch"
    dinner = "Dinner"
    snacks = "Snacks"

class Meal(Base):
    __tablename__ = "meals"
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"))
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(SAEnum(MealCategory), default=MealCategory.lunch)
    price = Column(Float, nullable=False)
    is_veg = Column(Boolean, default=True)
    image_url = Column(String, default="/assets/images/meal-default.jpg")
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    provider = relationship("Provider", back_populates="meals")
    order_items = relationship("OrderItem", back_populates="meal")
    cart_items = relationship("CartItem", back_populates="meal")

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"))
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    duration = Column(String, default="weekly") # "weekly" or "monthly"
    meals_per_day = Column(Integer, default=1)
    duration_days = Column(Integer, default=7)  # 7 for weekly, 30 for monthly
    features = Column(JSON, default=[]) # List of Strings
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    provider = relationship("Provider", back_populates="subscription_plans")
