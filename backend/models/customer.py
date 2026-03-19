from sqlalchemy import Column, Integer, String, ForeignKey, Float, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    phone = Column(String)
    address = Column(Text)
    profile_photo = Column(String, default="/assets/images/avatar-default.jpg")
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="customer")
    orders = relationship("Order", back_populates="customer")
    reviews = relationship("Review", back_populates="customer")
    cart_items = relationship("CartItem", back_populates="customer", cascade="all, delete")
