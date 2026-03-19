from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from backend.database import get_db
from backend.models import (Provider, Meal, Order, Review, Customer, CartItem, 
                            OrderItem, Payment, OrderStatus, PaymentStatus)
from backend.dependencies import get_current_user_from_request

router = APIRouter(prefix="/api", tags=["customer"])

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
    
    # Clear cart
    for item in cart_items:
        db.delete(item)
    db.commit()
    return {"message": "Order placed", "order_ids": created_orders}

@router.get("/orders/customer")
def customer_orders(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_request(request, db)
    if not user or not user.customer:
        raise HTTPException(status_code=401, detail="Login required")
    orders = db.query(Order).filter(Order.customer_id == user.customer.id).order_by(Order.created_at.desc()).all()
    result = []
    for o in orders:
        items = [{"name": i.meal.name, "qty": i.quantity, "price": i.unit_price} for i in o.items]
        result.append({"id": o.id, "provider_name": o.provider.mess_name,
                       "total_price": o.total_price, "status": o.order_status.value,
                       "payment_method": o.payment_method, "created_at": str(o.created_at),
                       "items": items})
    return result

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
