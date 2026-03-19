from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base

class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    meal_id = Column(Integer, ForeignKey("meals.id"))
    quantity = Column(Integer, default=1)
    added_at = Column(DateTime, server_default=func.now())

    customer = relationship("Customer", back_populates="cart_items")
    meal = relationship("Meal", back_populates="cart_items")
