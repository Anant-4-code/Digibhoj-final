from sqlalchemy import Column, Integer, String, ForeignKey, Float, Text, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum

class VerificationStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    blocked = "blocked"

class Provider(Base):
    __tablename__ = "providers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    mess_name = Column(String, nullable=False)
    cuisine_type = Column(String)
    location = Column(String)
    phone = Column(String)
    description = Column(Text)
    image_url = Column(String, default="/assets/images/provider-default.jpg")
    operating_hours = Column(String, default="8 AM – 9 PM")
    verification_status = Column(SAEnum(VerificationStatus), default=VerificationStatus.pending)
    rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="provider")
    meals = relationship("Meal", back_populates="provider", cascade="all, delete")
    subscription_plans = relationship("SubscriptionPlan", back_populates="provider", cascade="all, delete")
    orders = relationship("Order", back_populates="provider")
    reviews = relationship("Review", back_populates="provider")
