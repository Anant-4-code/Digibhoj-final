from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from backend.database import get_db
from backend.models import (Provider, Meal, Order, Review, Customer, CartItem,
                            OrderItem, Payment, OrderStatus, PaymentStatus, Notification, NotificationType,
                            Subscription, SubscriptionPlanType, SubscriptionStatus,
                            SubscriptionDelivery, DeliveryStatus, SubscriptionPlan)
from backend.dependencies import get_current_user_from_request

router = APIRouter(prefix="/api", tags=["customer"])

@router.put("/notifications/read-all")
def mark_all_notifications_read(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read == 0).update({Notification.is_read: 1})
    db.commit()
    return {"status": "success"}

@router.get("/notifications")
def list_notifications(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    notifications = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(10).all()
    return [{"id": n.id, "message": n.message, "is_read": n.is_read, "created_at": str(n.created_at)} for n in notifications]

@router.get("/providers")
def list_providers(db: Session = Depends(get_db)):
    from backend.models import VerificationStatus
    providers = db.query(Provider).filter(Provider.verification_status == VerificationStatus.verified).all()
    return [{"id": p.id, "mess_name": p.mess_name, "cuisine_type": p.cuisine_type,
             "location": p.location, "rating": p.rating, "total_reviews": p.total_reviews,
             "image_url": p.image_url, "operating_hours": p.operating_hours,
             "description": p.description} for p in providers]

@router.get("/providers/{provider_id}")
def get_provider(provider_id: int, db: Session = Depends(get_db)):
    p = db.query(Provider).filter(Provider.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"id": p.id, "mess_name": p.mess_name, "cuisine_type": p.cuisine_type,
            "location": p.location, "rating": p.rating, "total_reviews": p.total_reviews,
            "image_url": p.image_url, "operating_hours": p.operating_hours,
            "description": p.description}

@router.get("/meals/provider/{provider_id}")
def get_provider_meals(provider_id: int, db: Session = Depends(get_db)):
    meals = db.query(Meal).filter(Meal.provider_id == provider_id, Meal.is_available == True).all()
    return [{"id": m.id, "name": m.name, "description": m.description, "category": m.category.value,
             "price": m.price, "is_veg": m.is_veg, "image_url": m.image_url} for m in meals]

@router.get("/reviews/provider/{provider_id}")
def get_provider_reviews(provider_id: int, db: Session = Depends(get_db)):
    reviews = db.query(Review).filter(Review.provider_id == provider_id).all()
    return [{"id": r.id, "rating": r.rating, "comment": r.comment,
             "customer_name": r.customer.user.name if r.customer and r.customer.user else "Customer",
             "created_at": str(r.created_at)} for r in reviews]

class CartAddSchema(BaseModel):
    meal_id: int
    quantity: int = 1

@router.post("/cart/add")
def add_to_cart(data: CartAddSchema, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, db)
    if not user or not user.customer:
        raise HTTPException(status_code=401, detail="Login required")
    customer = user.customer
    existing = db.query(CartItem).filter(CartItem.customer_id == customer.id,
                                         CartItem.meal_id == data.meal_id).first()
    if existing:
        existing.quantity += data.quantity
    else:
        item = CartItem(customer_id=customer.id, meal_id=data.meal_id, quantity=data.quantity)
        db.add(item)
    db.commit()
    return {"message": "Added to cart"}

@router.get("/cart")
def get_cart(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, db)
    if not user or not user.customer:
        raise HTTPException(status_code=401, detail="Login required")
    items = db.query(CartItem).filter(CartItem.customer_id == user.customer.id).all()
    cart = []
    total = 0
    for item in items:
        subtotal = item.meal.price * item.quantity
        total += subtotal
        cart.append({"id": item.id, "meal_id": item.meal_id, "meal_name": item.meal.name,
                     "price": item.meal.price, "quantity": item.quantity, "subtotal": subtotal,
                     "image_url": item.meal.image_url, "provider_id": item.meal.provider_id})
    return {"items": cart, "total": total}

@router.delete("/cart/{item_id}")
def remove_cart_item(item_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, db)
    if not user or not user.customer:
        raise HTTPException(status_code=401, detail="Login required")
    item = db.query(CartItem).filter(CartItem.id == item_id,
                                      CartItem.customer_id == user.customer.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"message": "Removed"}

class CheckoutSchema(BaseModel):
    delivery_address: str
    payment_method: str = "Cash"
    notes: str = ""

@router.post("/orders")
def place_order(data: CheckoutSchema, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, db)
    if not user or not user.customer:
        raise HTTPException(status_code=401, detail="Login required")
    customer = user.customer
    cart_items = db.query(CartItem).filter(CartItem.customer_id == customer.id).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Group by provider
    provider_groups = {}
    for item in cart_items:
        pid = item.meal.provider_id
        if pid not in provider_groups:
            provider_groups[pid] = []
        provider_groups[pid].append(item)
    
    created_orders = []
    for provider_id, items in provider_groups.items():
        total = sum(i.meal.price * i.quantity for i in items)
        order = Order(customer_id=customer.id, provider_id=provider_id,
                      total_price=total, delivery_address=data.delivery_address,
                      payment_method=data.payment_method, notes=data.notes,
                      order_status=OrderStatus.created, payment_status=PaymentStatus.pending)
        db.add(order)
        db.flush()
        for item in items:
            oi = OrderItem(order_id=order.id, meal_id=item.meal_id,
                           quantity=item.quantity, unit_price=item.meal.price)
            db.add(oi)
        payment = Payment(order_id=order.id, amount=total,
                          payment_method=data.payment_method, payment_status="paid")
        db.add(payment)
        created_orders.append(order.id)
    
    # Update customer default address
    customer.address = data.delivery_address
    
    # Clear cart
    for item in cart_items:
        db.delete(item)
    db.commit()
    return {"message": "Order placed", "order_ids": created_orders}

@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, db)
    if not user or not user.customer:
        raise HTTPException(status_code=401, detail="Login required")
        
    order = db.query(Order).filter(Order.id == order_id, Order.customer_id == user.customer.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.order_status in [OrderStatus.delivered, OrderStatus.completed, OrderStatus.cancelled]:
        raise HTTPException(status_code=400, detail="Order cannot be cancelled in its current state")
        
    # Determine who to notify
    notify_provider = True
    notify_delivery = False
    
    if order.order_status == OrderStatus.out_for_delivery:
        notify_delivery = True
        
    # Update order state
    order.order_status = OrderStatus.cancelled
    order.cancelled_by = "customer"
    from datetime import datetime
    order.cancel_time = datetime.now()
    
    # Send notifications
    provider_user_id = order.provider.user.id
    prov_notif = Notification(user_id=provider_user_id, message=f"Order #{order.id} has been cancelled by customer.", ntype=NotificationType.order_update)
    db.add(prov_notif)
    
    if notify_delivery and order.assignment and order.assignment.agent:
        deliv_user_id = order.assignment.agent.user.id
        deliv_notif = Notification(user_id=deliv_user_id, message=f"Delivery cancelled for Order #{order.id}.", ntype=NotificationType.delivery_update)
        db.add(deliv_notif)
        
    db.commit()
    return {"message": "Order cancelled successfully"}

@router.get("/orders/customer")
def customer_orders(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, db)
    if not user or not user.customer:
        raise HTTPException(status_code=401, detail="Login required")
    orders = db.query(Order).filter(Order.customer_id == user.customer.id).order_by(Order.created_at.desc()).all()
    result = []
    for o in orders:
        items = []
        for i in o.items:
            meal_name = i.meal.name if i.meal else "Deleted Meal"
            items.append({"name": meal_name, "qty": i.quantity, "price": i.unit_price})
        result.append({"id": o.id, "provider_name": o.provider.mess_name,
                       "total_price": o.total_price, "status": o.order_status.value,
                       "payment_method": o.payment_method, "created_at": str(o.created_at),
                       "items": items})
    return result

@router.get("/providers/{provider_id}/plans")
def get_provider_plans(provider_id: int, db: Session = Depends(get_db)):
    """Fetch active subscription plans for a provider."""
    plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.provider_id == provider_id,
        SubscriptionPlan.is_active == True
    ).all()
    return [{
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "price": p.price,
        "duration": p.duration,
        "duration_days": p.duration_days or (7 if p.duration == "weekly" else 30),
        "meals_per_day": p.meals_per_day or 1,
        "features": p.features or []
    } for p in plans]

class SubscriptionCreateSchema(BaseModel):
    provider_id: int
    meal_id: Optional[int] = None
    plan_id: Optional[int] = None
    plan_type: str  # 'weekly' or 'monthly'
    payment_method: str = "UPI"

@router.post("/subscriptions/create")
def create_subscription(data: SubscriptionCreateSchema, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, db)
    if not user or not user.customer:
        raise HTTPException(status_code=401, detail="Login required")

    # Validation
    if data.plan_type not in ["weekly", "monthly"]:
        raise HTTPException(status_code=400, detail="Invalid plan type")

    # Enforce Only One Active Subscription Rule
    existing_sub = db.query(Subscription).filter(
        Subscription.customer_id == user.customer.id,
        Subscription.status == SubscriptionStatus.active
    ).first()
    if existing_sub:
        raise HTTPException(status_code=400, detail="You already have an active subscription.")

    provider = db.query(Provider).filter(Provider.id == data.provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Resolve Plan ID if missing (Legacy Support)
    if not data.plan_id:
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.provider_id == data.provider_id,
            SubscriptionPlan.duration == data.plan_type,
            SubscriptionPlan.is_active == True
        ).first()
        if not plan:
            raise HTTPException(status_code=400, detail=f"No active {data.plan_type} plan found for this provider.")
        data.plan_id = plan.id
    else:
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.id == data.plan_id,
            SubscriptionPlan.provider_id == data.provider_id,
            SubscriptionPlan.is_active == True
        ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found or inactive")

    # Resolve Meal ID if missing (Fallback to first available meal for provider)
    meal = None
    if data.meal_id:
        meal = db.query(Meal).filter(Meal.id == data.meal_id, Meal.provider_id == data.provider_id).first()
    
    if not meal:
        # Fallback to any available meal from this provider to satisfy schema/link
        meal = db.query(Meal).filter(Meal.provider_id == data.provider_id, Meal.is_available == True).first()
        if not meal:
             raise HTTPException(status_code=400, detail="This provider currently has no available meals to subscribe to.")
        data.meal_id = meal.id

    from datetime import datetime, timedelta, date

    duration_days = plan.duration_days if getattr(plan, 'duration_days', None) else (7 if plan.duration == "weekly" else 30)
    start_date = datetime.now()
    end_date = start_date + timedelta(days=duration_days)
    plan_enum = SubscriptionPlanType.weekly if plan.duration == "weekly" else SubscriptionPlanType.monthly

    subscription = Subscription(
        customer_id=user.customer.id,
        provider_id=provider.id,
        meal_id=meal.id,
        plan_id=plan.id,
        plan_type=plan_enum,
        payment_method=data.payment_method,
        start_date=start_date,
        end_date=end_date
    )
    db.add(subscription)
    db.flush()  # get subscription.id

    # Generate one SubscriptionDelivery per day in the plan
    for i in range(duration_days):
        delivery_date = (start_date + timedelta(days=i)).date()
        delivery = SubscriptionDelivery(
            subscription_id=subscription.id,
            date=delivery_date,
            status=DeliveryStatus.scheduled
        )
        db.add(delivery)

    db.commit()
    return {"message": f"Successfully subscribed to {meal.name} for {duration_days} days",
            "subscription_id": subscription.id}

@router.get("/subscriptions/my")
def get_my_subscriptions(request: Request, db: Session = Depends(get_db)):
    """Get all active subscriptions for the logged-in customer."""
    user = get_current_user_from_request(request, db)
    if not user or not user.customer:
        raise HTTPException(status_code=401, detail="Login required")
    subs = db.query(Subscription).filter(
        Subscription.customer_id == user.customer.id
    ).order_by(Subscription.created_at.desc()).all()
    result = []
    for s in subs:
        result.append({
            "id": s.id,
            "provider_id": s.provider_id,
            "provider_name": s.provider.mess_name,
            "plan_id": s.plan_id,
            "plan_name": s.meal.name if getattr(s, 'meal', None) else (s.plan.name if s.plan else f"{s.plan_type.value.capitalize()} Plan"),
            "plan_type": s.plan_type.value,
            "start_date": str(s.start_date.date()),
            "end_date": str(s.end_date.date()),
            "status": s.status.value,
            "created_at": str(s.created_at)
        })
    return result

@router.post("/subscriptions/{sub_id}/cancel")
def cancel_subscription(sub_id: int, request: Request, db: Session = Depends(get_db)):
    """Cancel an active subscription and stop all future scheduled deliveries."""
    user = get_current_user_from_request(request, db)
    if not user or not user.customer:
        raise HTTPException(status_code=401, detail="Login required")
    sub = db.query(Subscription).filter(
        Subscription.id == sub_id,
        Subscription.customer_id == user.customer.id
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if sub.status != SubscriptionStatus.active:
        raise HTTPException(status_code=400, detail="Subscription is not active")
    sub.status = SubscriptionStatus.cancelled
    # Cancel all future scheduled deliveries
    from datetime import date
    today = date.today()
    for d in sub.deliveries:
        if d.status == DeliveryStatus.scheduled and d.date > today:
            d.status = DeliveryStatus.cancelled
    db.commit()
    return {"message": "Subscription cancelled"}

@router.get("/subscriptions/{sub_id}/calendar")
def get_subscription_calendar(sub_id: int, request: Request, db: Session = Depends(get_db)):
    """Return all delivery entries for a subscription for the calendar view."""
    user = get_current_user_from_request(request, db)
    if not user or not user.customer:
        raise HTTPException(status_code=401, detail="Login required")
    sub = db.query(Subscription).filter(
        Subscription.id == sub_id,
        Subscription.customer_id == user.customer.id
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    deliveries = sorted(sub.deliveries, key=lambda d: d.date)
    return {
        "subscription_id": sub_id,
        "provider_name": sub.provider.mess_name,
        "plan_name": sub.meal.name if getattr(sub, 'meal', None) else (sub.plan.name if sub.plan else f"{sub.plan_type.value.capitalize()} Plan"),
        "plan_type": sub.plan_type.value,
        "start_date": str(sub.start_date.date()),
        "end_date": str(sub.end_date.date()),
        "status": sub.status.value,
        "deliveries": [
            {"id": d.id, "date": str(d.date), "status": d.status.value,
             "order_id": d.order_id}
            for d in deliveries
        ]
    }

@router.post("/subscriptions/deliveries/{delivery_id}/cancel")
def cancel_delivery_day(delivery_id: int, request: Request, db: Session = Depends(get_db)):
    """Cancel a single day's meal delivery."""
    user = get_current_user_from_request(request, db)
    if not user or not user.customer:
        raise HTTPException(status_code=401, detail="Login required")
    delivery = db.query(SubscriptionDelivery).filter(
        SubscriptionDelivery.id == delivery_id
    ).first()
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    # Verify ownership
    if delivery.subscription.customer_id != user.customer.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if delivery.status not in [DeliveryStatus.scheduled]:
        raise HTTPException(status_code=400, detail="Cannot cancel this delivery")
    delivery.status = DeliveryStatus.cancelled
    db.commit()
    return {"message": "Delivery cancelled"}

@router.get("/orders/{order_id}")
def get_order(order_id: int, request: Request, db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    items = [{"name": i.meal.name, "qty": i.quantity, "price": i.unit_price} for i in o.items]
    assignment = None
    if o.assignment:
        assignment = {"agent_name": o.assignment.agent.user.name,
                      "status": o.assignment.status.value}
    return {"id": o.id, "provider_name": o.provider.mess_name,
            "total_price": o.total_price, "status": o.order_status.value,
            "delivery_address": o.delivery_address, "created_at": str(o.created_at),
            "items": items, "assignment": assignment}

class ReviewSchema(BaseModel):
    provider_id: int
    order_id: int
    rating: float
    comment: str = ""

@router.post("/reviews")
def submit_review(data: ReviewSchema, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, db)
    if not user or not user.customer:
        raise HTTPException(status_code=401, detail="Login required")
    existing = db.query(Review).filter(Review.order_id == data.order_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Review already submitted")
    
    review = Review(customer_id=user.customer.id, provider_id=data.provider_id,
                    order_id=data.order_id, rating=data.rating, comment=data.comment)
    db.add(review)
    db.flush()
    
    # Update provider rating
    provider = db.query(Provider).filter(Provider.id == data.provider_id).first()
    if provider:
        all_reviews = db.query(Review).filter(Review.provider_id == data.provider_id).all()
        provider.rating = round(sum(r.rating for r in all_reviews) / len(all_reviews), 1)
        provider.total_reviews = len(all_reviews)
    db.commit()
    return {"message": "Review submitted"}

@router.get("/customer/order/{order_id}/rider-location")
def get_rider_location(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order.assignment or not order.assignment.agent:
        return {"lat": None, "lng": None, "status": "searching"}
    
    agent = order.assignment.agent
    return {
        "lat": agent.current_lat,
        "lng": agent.current_lng,
        "status": order.assignment.status.value,
        "agent_name": agent.user.name
    }
