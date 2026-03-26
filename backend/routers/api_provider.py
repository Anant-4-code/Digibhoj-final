from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from backend.database import get_db
from backend.models import (Provider, Meal, Order, Review, DeliveryAgent,
                            DeliveryAssignment, MealCategory, OrderStatus, DeliveryAssignmentStatus,
                            SubscriptionPlan, Subscription, ProviderDocument, ProviderBank)
from backend.models.provider import DocumentType, DocumentStatus
from backend.dependencies import get_current_user_from_request

def get_user(request: Request, db: Session):
    return get_current_user_from_request(request, db)

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
        items = []
        for i in o.items:
            meal_name = i.meal.name if i.meal else "Deleted Meal"
            items.append({"name": meal_name, "qty": i.quantity})
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
    agent_id: Optional[int] = None
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
    
    agent_id = data.agent_id
    if not agent_id:
        # Find nearest/first available agent
        from backend.models import DeliveryVerification, AgentStatus, DeliveryAgent
        agent = db.query(DeliveryAgent).filter(
            DeliveryAgent.verification_status == DeliveryVerification.verified,
            DeliveryAgent.availability == AgentStatus.online
        ).first()
        if not agent:
            raise HTTPException(status_code=400, detail="No delivery agents available right now")
        agent_id = agent.id
    
    assignment = DeliveryAssignment(order_id=data.order_id, agent_id=agent_id,
                                    pickup_location=data.pickup_location or order.provider.location or "",
                                    drop_location=data.drop_location or order.delivery_address or "")
    db.add(assignment)
    # Don't mark as picked_up yet, let the rider do it. Mark as ready or preparing.
    if order.order_status in [OrderStatus.created, OrderStatus.confirmed]:
        order.order_status = OrderStatus.preparing
    db.commit()
    return {"message": "Delivery assigned"}

@router.get("/available-agents")
def get_available_agents(db: Session = Depends(get_db)):
    from backend.models import DeliveryVerification, AgentStatus
    agents = db.query(DeliveryAgent).filter(
        DeliveryAgent.verification_status == DeliveryVerification.verified,
        DeliveryAgent.availability == AgentStatus.online
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

# ─── Provider Plan Management ────────────────────────────────────

@router.get("/plans/{provider_id}")
def get_plans(provider_id: int, db: Session = Depends(get_db)):
    """List all subscription plans for a provider."""
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.provider_id == provider_id).all()
    from backend.models import Subscription
    return [{
        "id": p.id,
        "name": p.name,
        "description": p.description or "",
        "price": p.price,
        "duration": p.duration,
        "duration_days": p.duration_days or (7 if p.duration == "weekly" else 30),
        "meals_per_day": p.meals_per_day or 1,
        "features": p.features or [],
        "is_active": p.is_active,
        "subscriber_count": db.query(Subscription).filter(
            Subscription.provider_id == provider_id,
            Subscription.plan_id == p.id
        ).count()
    } for p in plans]

class PlanSchema(BaseModel):
    provider_id: int
    name: str
    description: str = ""
    price: float
    duration: str = "weekly"  # 'weekly' or 'monthly'
    meals_per_day: int = 1
    features: list = []

@router.post("/plans")
def create_plan(data: PlanSchema, db: Session = Depends(get_db)):
    duration_days = 7 if data.duration == "weekly" else 30
    plan = SubscriptionPlan(
        provider_id=data.provider_id,
        name=data.name,
        description=data.description,
        price=data.price,
        duration=data.duration,
        duration_days=duration_days,
        meals_per_day=data.meals_per_day,
        features=data.features,
        is_active=True
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return {"id": plan.id, "message": "Plan created"}

class PlanUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    meals_per_day: Optional[int] = None
    features: Optional[list] = None
    is_active: Optional[bool] = None

@router.put("/plans/{plan_id}")
def update_plan(plan_id: int, data: PlanUpdateSchema, db: Session = Depends(get_db)):
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if data.name is not None: plan.name = data.name
    if data.description is not None: plan.description = data.description
    if data.price is not None: plan.price = data.price
    if data.meals_per_day is not None: plan.meals_per_day = data.meals_per_day
    if data.features is not None: plan.features = data.features
    if data.is_active is not None: plan.is_active = data.is_active
    db.commit()
    return {"message": "Plan updated"}

from datetime import datetime, timedelta

@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.is_active = False
    db.commit()
    return {"message": "Plan deleted"}

@router.get("/analytics/data")
def provider_analytics_data(request: Request, range: str = "week", db: Session = Depends(get_db)):
    """Returns comprehensive analytics for the advanced dashboard."""
    user = get_user(request, db)
    if not user or not user.provider:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    p_id = user.provider.id
    now = datetime.now()
    
    # Range filtering
    if range == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        prev_start = start_date - timedelta(days=1)
    elif range == "month":
        start_date = now - timedelta(days=30)
        prev_start = start_date - timedelta(days=30)
    elif range == "all":
        start_date = now - timedelta(days=3650)
        prev_start = start_date
    else: # default week
        start_date = now - timedelta(days=7)
        prev_start = start_date - timedelta(days=7)

    # 1. Orders Data
    curr_orders = db.query(Order).filter(
        Order.provider_id == p_id, 
        Order.order_status != OrderStatus.cancelled,
        Order.created_at >= start_date
    ).all()
    
    prev_orders = db.query(Order).filter(
        Order.provider_id == p_id,
        Order.order_status != OrderStatus.cancelled,
        Order.created_at >= prev_start,
        Order.created_at < start_date
    ).all()
    
    all_orders_count = db.query(Order).filter(Order.provider_id == p_id).count() # For context if needed
    
    # 1.1 Revenue & Breakdowns
    curr_revenue = sum(o.total_price for o in curr_orders if o.order_status.value in ["delivered", "completed"])
    prev_revenue = sum(o.total_price for o in prev_orders if o.order_status.value in ["delivered", "completed"])
    
    # Simple split estimate for now (Orders vs Subscriptions if tagged)
    subs_revenue = sum(o.total_price for o in curr_orders if 'subscription' in (o.payment_method or '').lower()) 
    one_time_revenue = curr_revenue - subs_revenue
    if subs_revenue == 0 and curr_revenue > 0:
        # Fallback simulation if no tags exist
        subs_revenue = curr_revenue * 0.45
        one_time_revenue = curr_revenue * 0.55

    # 2. Subscriptions Data
    subs = db.query(Subscription).filter(Subscription.provider_id == p_id).all()
    active_subs = [s for s in subs if s.status.value == "active"]
    curr_new_subs = [s for s in subs if s.created_at and s.created_at >= start_date]
    prev_new_subs = [s for s in subs if s.created_at and prev_start <= s.created_at < start_date]
    cancelled_subs = [s for s in subs if s.status.value == "cancelled" and s.updated_at and s.updated_at >= start_date]

    # 3. Customer Insights
    unique_customers = set(o.customer_id for o in curr_orders)
    returning_customers = []
    for c_id in unique_customers:
        count = db.query(Order).filter(Order.customer_id == c_id, Order.provider_id == p_id).count()
        if count > 1:
            returning_customers.append(c_id)
    retention_rate = (len(returning_customers) / len(unique_customers) * 100) if unique_customers else 0

    # 4. Top Items
    item_counts = {}
    for o in curr_orders:
        for i in o.items:
            name = i.meal.name if i.meal else "Unknown"
            item_counts[name] = item_counts.get(name, 0) + i.quantity
    top_items = sorted([{"name": k, "orders": v} for k, v in item_counts.items()], key=lambda x: x['orders'], reverse=True)[:3]

    # 5. Order Status Distribution
    status_dist = {"completed": 0, "pending": 0, "cancelled": 0}
    raw_status_orders = db.query(Order).filter(Order.provider_id == p_id, Order.created_at >= start_date).all()
    for o in raw_status_orders:
        if o.order_status.value in ['delivered', 'completed']: status_dist['completed'] += 1
        elif o.order_status.value == 'cancelled': status_dist['cancelled'] += 1
        else: status_dist['pending'] += 1

    # 6. Peak Time Analysis
    hour_counts = {}
    for o in curr_orders:
        h = o.created_at.hour if o.created_at else 12
        hour_counts[h] = hour_counts.get(h, 0) + 1
    
    peak_str = "No data"
    if hour_counts:
        best_hour = max(hour_counts, key=hour_counts.get)
        if 8 <= best_hour <= 11: peak_str = f"Breakfast ({best_hour}:00 - {best_hour+1}:00)"
        elif 12 <= best_hour <= 15: peak_str = f"Lunch ({best_hour}:00 - {best_hour+1}:00)"
        elif 18 <= best_hour <= 22: peak_str = f"Dinner ({best_hour}:00 - {best_hour+1}:00)"
        else: peak_str = f"Late Night ({best_hour}:00 - {best_hour+1}:00)"

    # 7. Earnings Trend (Bar Chart Data)
    trend_labels = []
    trend_data = []
    if range == "today":
        for i in range(24):
            trend_labels.append(f"{i:02d}:00")
            trend_data.append(sum(o.total_price for o in curr_orders if o.created_at.hour == i and o.order_status.value in ["delivered", "completed"]))
    elif range == "month":
        for i in range(4):
            trend_labels.append(f"Week {i+1}")
            trend_data.append(sum(o.total_price for o in curr_orders if o.created_at.day // 7 == i and o.order_status.value in ["delivered", "completed"]))
    else: # week
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        d_map = {d: 0 for d in days}
        for o in curr_orders:
            if o.order_status.value in ["delivered", "completed"]:
                d_map[days[o.created_at.weekday()]] += o.total_price
        trend_labels = days
        trend_data = [d_map[d] for d in days]

    # Calculate percentages safely
    rev_growth = ((curr_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue else (100 if curr_revenue else 0)
    order_growth = ((len(curr_orders) - len(prev_orders)) / len(prev_orders) * 100) if prev_orders else (100 if len(curr_orders) else 0)
    subs_growth = len(curr_new_subs) - len(prev_new_subs) # absolute change for subscriptions

    # Smart Insights Generation
    smart_insights = []
    if subs_revenue > one_time_revenue:
        smart_insights.append("Subscriptions are your main revenue driver. Consider adding premium monthly plans.")
    if retention_rate > 50:
        smart_insights.append(f"Great customer loyalty! {retention_rate:.0f}% of your customers are returning.")
    if top_items:
        smart_insights.append(f"'{top_items[0]['name']}' is highly requested. Prepare extra inventory.")

    return {
        "overview": {
            "earnings": curr_revenue,
            "earnings_growth": round(rev_growth, 1),
            "orders": len(curr_orders),
            "orders_growth": round(order_growth, 1),
            "rating": round(user.provider.rating, 1) if user.provider.rating else 0.0,
            "reviews_count": len(user.provider.reviews) if user.provider.reviews else 0
        },
        "revenue_breakdown": {
            "subscriptions": subs_revenue,
            "one_time": one_time_revenue
        },
        "subscriptions": {
            "active": len(active_subs),
            "new": len(curr_new_subs),
            "cancelled": len(cancelled_subs),
            "growth": subs_growth
        },
        "customer_insights": {
            "new_count": len(unique_customers) - len(returning_customers),
            "retention_rate": round(retention_rate, 1)
        },
        "order_overview": status_dist,
        "top_items": top_items,
        "peak_time": peak_str,
        "insights": smart_insights,
        "chart": {
            "labels": trend_labels,
            "data": trend_data
        }
    }

# ─── Provider Profile Management ────────────────────────────────────

from pathlib import Path
import shutil
import uuid
from fastapi import UploadFile, File, Form

@router.get("/profile/data")
def get_provider_profile(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    provider = user.provider
    fields_checked = [
        provider.mess_name,
        provider.phone,
        provider.location,
        provider.latitude,
        provider.bank_details,
        bool(provider.documents),
    ]
    filled = sum(1 for f in fields_checked if f)
    completion = int((filled / len(fields_checked)) * 100)
    
    docs = [{"id": d.id, "type": d.document_type.value, "url": d.file_url, "status": d.status.value, "note": d.admin_note} for d in provider.documents]
    bank = None
    if provider.bank_details:
        b = provider.bank_details
        bank = {
            "account_name": b.account_name,
            "account_number": f"****{b.account_number[-4:]}" if len(b.account_number) > 4 else b.account_number,
            "ifsc_code": b.ifsc_code,
            "bank_name": b.bank_name
        }

    return {
        "status": provider.verification_status.value,
        "completion_percentage": completion,
        "basic_info": {
            "mess_name": provider.mess_name,
            "phone": provider.phone,
            "cuisine_type": provider.cuisine_type,
            "description": provider.description,
            "operating_hours": provider.operating_hours,
            "location": provider.location,
            "latitude": provider.latitude,
            "longitude": provider.longitude
        },
        "settings": {
            "vacation_mode": provider.vacation_mode,
            "auto_accept_orders": provider.auto_accept_orders,
            "email_notifications": provider.email_notifications,
            "sms_notifications": provider.sms_notifications
        },
        "documents": docs,
        "bank": bank
    }

class BasicInfoSchema(BaseModel):
    mess_name: str
    phone: str
    cuisine_type: str = ""
    description: str = ""
    operating_hours: str = ""
    location: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@router.post("/profile/basic")
def update_provider_basic_info(data: BasicInfoSchema, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    p = user.provider
    p.mess_name = data.mess_name
    p.phone = data.phone
    p.cuisine_type = data.cuisine_type
    p.description = data.description
    p.operating_hours = data.operating_hours
    p.location = data.location
    p.latitude = data.latitude
    p.longitude = data.longitude
    db.commit()
    return {"message": "Profile updated"}

class SettingsSchema(BaseModel):
    vacation_mode: bool
    auto_accept_orders: bool
    email_notifications: bool
    sms_notifications: bool

@router.post("/profile/settings")
def update_provider_settings(data: SettingsSchema, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    p = user.provider
    p.vacation_mode = data.vacation_mode
    p.auto_accept_orders = data.auto_accept_orders
    p.email_notifications = data.email_notifications
    p.sms_notifications = data.sms_notifications
    db.commit()
    return {"message": "Settings updated"}

class BankSchema(BaseModel):
    account_name: str
    account_number: Optional[str] = None
    ifsc_code: str
    bank_name: str

@router.post("/profile/bank")
def update_provider_bank(data: BankSchema, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    p = user.provider
    if not p.bank_details:
        if not data.account_number:
            raise HTTPException(status_code=400, detail="Account number required for first-time setup")
        p.bank_details = ProviderBank(
            provider_id=p.id,
            account_name=data.account_name,
            account_number=data.account_number,
            ifsc_code=data.ifsc_code,
            bank_name=data.bank_name
        )
        db.add(p.bank_details) # Add the new bank details object to the session
    else:
        p.bank_details.account_name = data.account_name
        # Only update if a real account number is provided (not masks or empty)
        if data.account_number and "*" not in data.account_number:
            p.bank_details.account_number = data.account_number
        p.bank_details.ifsc_code = data.ifsc_code
        p.bank_details.bank_name = data.bank_name
    
    db.commit()
    return {"message": "Bank details updated"}

@router.post("/profile/document")
def upload_provider_document(
    request: Request,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = get_user(request, db)
    if not user or not user.provider:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    filename = f"{uuid.uuid4()}_{file.filename}"
    upload_dir = Path("public/assets/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_url = f"/assets/uploads/{filename}"
    
    p = user.provider
    doc = db.query(ProviderDocument).filter(
        ProviderDocument.provider_id == p.id,
        ProviderDocument.document_type == document_type
    ).first()
    
    if doc:
        doc.file_url = file_url
        doc.status = DocumentStatus.pending
        doc.admin_note = None
    else:
        new_doc = ProviderDocument(
            provider_id=p.id,
            document_type=DocumentType(document_type),
            file_url=file_url,
            status=DocumentStatus.pending
        )
        db.add(new_doc)
    
    db.commit()
    return {"message": "Document uploaded successfully", "url": file_url}

@router.delete("/account/delete")
def delete_provider_account(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    db.delete(user)
    db.commit()
    return {"message": "Account deleted forever"}
