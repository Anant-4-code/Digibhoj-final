from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from backend.database import get_db
from backend.models import (Provider, Meal, Order, Review, DeliveryAgent, 
                            DeliveryAssignment, MealCategory, OrderStatus, DeliveryAssignmentStatus)
from backend.dependencies import get_current_user_from_request

router = APIRouter(prefix="/api/provider", tags=["provider"])

@router.get("/dashboard/{provider_id}")
def provider_dashboard(provider_id: int, db: Session = Depends(get_db)):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    from datetime import date
    today_orders = db.query(Order).filter(
        Order.provider_id == provider_id,
        Order.order_status != OrderStatus.cancelled
    ).all()
    today_count = len([o for o in today_orders if o.created_at and o.created_at.date() == date.today()])
    pending = len([o for o in today_orders if o.order_status.value in ["created", "confirmed", "preparing"]])
    total_revenue = sum(o.total_price for o in today_orders if o.order_status.value in ["delivered", "completed"])
    top_meal = None
    if provider.meals:
        top_meal = sorted(provider.meals, key=lambda m: len(m.order_items), reverse=True)[0].name
    
    return {"today_orders": today_count, "pending_orders": pending,
            "total_revenue": total_revenue, "top_meal": top_meal or "N/A",
            "provider_name": provider.mess_name, "rating": provider.rating}

@router.get("/menu/{provider_id}")
def get_menu(provider_id: int, db: Session = Depends(get_db)):
    meals = db.query(Meal).filter(Meal.provider_id == provider_id).all()
    return [{"id": m.id, "name": m.name, "description": m.description, "category": m.category.value,
             "price": m.price, "is_veg": m.is_veg, "image_url": m.image_url,
             "is_available": m.is_available} for m in meals]

class MealSchema(BaseModel):
    name: str
    description: str = ""
    category: str = "Lunch"
    price: float
    is_veg: bool = True
    image_url: str = ""
    provider_id: int

@router.post("/meals")
def add_meal(data: MealSchema, db: Session = Depends(get_db)):
    cat_map = {"Breakfast": MealCategory.breakfast, "Lunch": MealCategory.lunch,
               "Dinner": MealCategory.dinner, "Snacks": MealCategory.snacks}
    meal = Meal(provider_id=data.provider_id, name=data.name, description=data.description,
                category=cat_map.get(data.category, MealCategory.lunch),
                price=data.price, is_veg=data.is_veg,
                image_url=data.image_url or "/assets/images/meal-default.jpg")
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return {"id": meal.id, "message": "Meal added"}

class MealUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    is_veg: Optional[bool] = None
    is_available: Optional[bool] = None

@router.put("/meals/{meal_id}")
def update_meal(meal_id: int, data: MealUpdateSchema, db: Session = Depends(get_db)):
    meal = db.query(Meal).filter(Meal.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    if data.name is not None: meal.name = data.name
    if data.description is not None: meal.description = data.description
    if data.price is not None: meal.price = data.price
    if data.is_veg is not None: meal.is_veg = data.is_veg
    if data.is_available is not None: meal.is_available = data.is_available
    db.commit()
    return {"message": "Updated"}

@router.delete("/meals/{meal_id}")
def delete_meal(meal_id: int, db: Session = Depends(get_db)):
    meal = db.query(Meal).filter(Meal.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    db.delete(meal)
    db.commit()
    return {"message": "Deleted"}

@router.get("/orders/{provider_id}")
def get_provider_orders(provider_id: int, db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.provider_id == provider_id).order_by(Order.created_at.desc()).all()
    result = []
    for o in orders:
        items = [{"name": i.meal.name, "qty": i.quantity} for i in o.items]
        result.append({"id": o.id, "customer_name": o.customer.user.name,
                       "total_price": o.total_price, "status": o.order_status.value,
                       "created_at": str(o.created_at), "items": items,
                       "delivery_address": o.delivery_address})
    return result

class OrderStatusSchema(BaseModel):
    status: str

@router.put("/orders/{order_id}/status")
def update_order_status(order_id: int, data: OrderStatusSchema, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    status_map = {"confirmed": OrderStatus.confirmed, "preparing": OrderStatus.preparing,
                  "ready": OrderStatus.ready, "cancelled": OrderStatus.cancelled}
    new_status = status_map.get(data.status)
    if not new_status:
        raise HTTPException(status_code=400, detail="Invalid status")
    order.order_status = new_status
    db.commit()
    return {"message": "Status updated", "status": data.status}

class AssignDeliverySchema(BaseModel):
    order_id: int
    agent_id: int
    pickup_location: str = ""
    drop_location: str = ""

@router.post("/delivery/assign")
def assign_delivery(data: AssignDeliverySchema, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    existing = db.query(DeliveryAssignment).filter(DeliveryAssignment.order_id == data.order_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already assigned")
    
    assignment = DeliveryAssignment(order_id=data.order_id, agent_id=data.agent_id,
                                    pickup_location=data.pickup_location or order.provider.location or "",
                                    drop_location=data.drop_location or order.delivery_address or "")
    db.add(assignment)
    order.order_status = OrderStatus.picked_up
    db.commit()
    return {"message": "Delivery assigned"}

@router.get("/available-agents")
def get_available_agents(db: Session = Depends(get_db)):
    from backend.models import DeliveryVerification, AgentStatus
    agents = db.query(DeliveryAgent).filter(
        DeliveryAgent.verification_status == DeliveryVerification.verified,
        DeliveryAgent.availability.in_([AgentStatus.online, AgentStatus.offline])
    ).all()
    return [{"id": a.id, "name": a.user.name, "phone": a.phone,
             "vehicle_type": a.vehicle_type, "service_area": a.service_area} for a in agents]

@router.get("/analytics/{provider_id}")
def provider_analytics(provider_id: int, db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.provider_id == provider_id,
                                     Order.order_status != OrderStatus.cancelled).all()
    daily = {}
    for o in orders:
        day = str(o.created_at.date()) if o.created_at else "unknown"
        if day not in daily:
            daily[day] = {"count": 0, "revenue": 0}
        daily[day]["count"] += 1
        daily[day]["revenue"] += o.total_price
    
    meals_sold = {}
    for o in orders:
        for item in o.items:
            name = item.meal.name
            if name not in meals_sold:
                meals_sold[name] = 0
            meals_sold[name] += item.quantity
    
    reviews = db.query(Review).filter(Review.provider_id == provider_id).all()
    avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0
    
    return {"daily_data": daily, "meals_sold": meals_sold,
            "total_orders": len(orders),
            "total_revenue": sum(o.total_price for o in orders), "avg_rating": avg_rating}
