from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import (User, Customer, Provider, DeliveryAgent, Order, Review,
                            UserStatus, VerificationStatus, DeliveryVerification, Meal, CartItem, 
                            OrderItem, Payment, Notification, DeliveryAssignment)

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    from sqlalchemy import func
    
    # Efficiently count entities
    customers_count = db.query(Customer).count()
    providers_count = db.query(Provider).count()
    agents_count = db.query(DeliveryAgent).count()
    orders_count = db.query(Order).count()
    
    # Sum revenue using SQL-side aggregate
    revenue = db.query(func.sum(Order.total_price)).filter(
        Order.order_status.in_(["delivered", "completed"])
    ).scalar() or 0.0
    
    pending_providers = db.query(Provider).filter(
        Provider.verification_status == VerificationStatus.pending
    ).count()
    
    pending_agents = db.query(DeliveryAgent).filter(
        DeliveryAgent.verification_status == DeliveryVerification.pending
    ).count()

    return {
        "total_customers": customers_count,
        "total_providers": providers_count,
        "total_delivery_agents": agents_count,
        "total_orders": orders_count,
        "total_revenue": float(revenue),
        "pending_provider_verifications": pending_providers,
        "pending_delivery_verifications": pending_agents,
    }

@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{"id": u.id, "name": u.name, "email": u.email,
             "role": u.role.value, "status": u.status.value,
             "created_at": str(u.created_at)} for u in users]

@router.put("/users/block/{user_id}")
def block_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = UserStatus.blocked
    db.commit()
    return {"message": "User blocked"}

@router.put("/users/unblock/{user_id}")
def unblock_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = UserStatus.active
    db.commit()
    return {"message": "User unblocked"}

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}

@router.get("/providers")
def list_providers(db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    providers = db.query(Provider).options(joinedload(Provider.user)).all()
    result = []
    for p in providers:
        # Defensive check for broken user relationships during transition
        if not p.user: continue
        result.append({
            "id": p.id, "mess_name": p.mess_name, "owner_name": p.user.name,
            "location": p.location, "cuisine_type": p.cuisine_type,
            "verification_status": p.verification_status.value,
            "rating": p.rating, "created_at": str(p.created_at)
        })
    return result

@router.put("/providers/verify/{provider_id}")
def verify_provider(provider_id: int, db: Session = Depends(get_db)):
    p = db.query(Provider).filter(Provider.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Provider not found")
    p.verification_status = VerificationStatus.verified
    db.commit()
    return {"message": "Provider verified"}

@router.put("/providers/reject/{provider_id}")
def reject_provider(provider_id: int, db: Session = Depends(get_db)):
    p = db.query(Provider).filter(Provider.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Provider not found")
    p.verification_status = VerificationStatus.blocked
    db.commit()
    return {"message": "Provider rejected"}

@router.get("/delivery")
def list_delivery_agents(db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    agents = db.query(DeliveryAgent).options(joinedload(DeliveryAgent.user)).all()
    return [{"id": a.id, "name": a.user.name, "phone": a.phone,
             "vehicle_type": a.vehicle_type, "license_number": a.license_number,
             "service_area": a.service_area,
             "verification_status": a.verification_status.value,
             "availability": a.availability.value} for a in agents]

@router.put("/delivery/verify/{agent_id}")
def verify_agent(agent_id: int, db: Session = Depends(get_db)):
    a = db.query(DeliveryAgent).filter(DeliveryAgent.id == agent_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    a.verification_status = DeliveryVerification.verified
    db.commit()
    return {"message": "Agent verified"}

@router.get("/orders")
def list_orders(db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    orders = db.query(Order).options(
        joinedload(Order.customer).joinedload(Customer.user),
        joinedload(Order.provider)
    ).order_by(Order.created_at.desc()).all()
    
    result = []
    for o in orders:
        if not o.customer or not o.customer.user or not o.provider:
            continue
        result.append({
            "id": o.id, "customer_name": o.customer.user.name,
            "provider_name": o.provider.mess_name,
            "total_price": o.total_price, "status": o.order_status.value,
            "created_at": str(o.created_at)
        })
    return result

@router.put("/orders/cancel/{order_id}")
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    from backend.models import OrderStatus as OS
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    o.order_status = OS.cancelled
    db.commit()
    return {"message": "Order forcibly cancelled"}

@router.get("/reviews")
def list_reviews(db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    reviews = db.query(Review).options(
        joinedload(Review.customer).joinedload(Customer.user),
        joinedload(Review.provider)
    ).all()
    
    result = []
    for r in reviews:
        if not r.customer or not r.customer.user or not r.provider:
            continue
        result.append({
            "id": r.id, "customer": r.customer.user.name,
            "provider": r.provider.mess_name, "rating": r.rating,
            "comment": r.comment, "created_at": str(r.created_at)
        })
    return result

@router.delete("/reviews/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db)):
    r = db.query(Review).filter(Review.id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    db.delete(r)
    db.commit()
    return {"message": "Review deleted"}

@router.get("/analytics")
def admin_analytics(db: Session = Depends(get_db)):
    from sqlalchemy import func
    from backend.models import OrderStatus as OS
    
    # Get daily counts and revenue using group-by
    # Formatting date depends on SQL flavor; SQLite uses strftime
    daily_stats = db.query(
        func.date(Order.created_at).label('day'),
        func.count(Order.id).label('count'),
        func.sum(Order.total_price).label('revenue')
    ).group_by(func.date(Order.created_at)).all()
    
    daily_data = {}
    for day, count, revenue in daily_stats:
        # Filter revenue for only completed orders in Python (or more complex SQL)
        # For simplicity in this SQLite context:
        completed_rev = db.query(func.sum(Order.total_price)).filter(
            func.date(Order.created_at) == day,
            Order.order_status.in_(["delivered", "completed"])
        ).scalar() or 0.0
        
        daily_data[str(day)] = {
            "count": count,
            "revenue": float(completed_rev)
        }
    
    total_rev = db.query(func.sum(Order.total_price)).filter(
        Order.order_status.in_(["delivered", "completed"])
    ).scalar() or 0.0

    return {
        "total_orders": db.query(Order).count(),
        "total_revenue": float(total_rev),
        "total_users": db.query(User).count(),
        "daily_data": daily_data
    }

@router.get("/database/{table}")
def view_table(table: str, db: Session = Depends(get_db)):
    allowed = {"users": User, "customers": Customer, "providers": Provider,
               "delivery_agents": DeliveryAgent, "meals": Meal, "orders": Order,
               "reviews": Review, "payments": Payment}
    if table not in allowed:
        raise HTTPException(status_code=400, detail="Table not accessible")
    model = allowed[table]
    rows = db.query(model).limit(100).all()
    result = []
    for r in rows:
        row_dict = {}
        for col in r.__table__.columns:
            val = getattr(r, col.name)
            row_dict[col.name] = str(val) if val is not None else None
        result.append(row_dict)
    return {"table": table, "rows": result}
