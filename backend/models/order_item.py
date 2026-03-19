from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    meal_id = Column(Integer, ForeignKey("meals.id"))
    quantity = Column(Integer, default=1)
    unit_price = Column(Float)

    order = relationship("Order", back_populates="items")
    meal = relationship("Meal", back_populates="order_items")
