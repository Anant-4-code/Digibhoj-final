from sqlalchemy import Column, Integer, ForeignKey, Float, Text, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    provider_id = Column(Integer, ForeignKey("providers.id"))
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True)
    rating = Column(Float, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    customer = relationship("Customer", back_populates="reviews")
    provider = relationship("Provider", back_populates="reviews")
    order = relationship("Order", back_populates="review")
