from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.orm import Session
from backend.database import get_db
import os
import secrets

from backend.models import (DeliveryAgent, DeliveryAssignment, Order, OrderStatus, 
                            DeliveryAssignmentStatus, AgentStatus, Notification, NotificationType)
from backend.dependencies import get_current_user_from_request
from fastapi import Query
import random

router = APIRouter(prefix="/api/delivery", tags=["delivery"])

@router.get("/tasks/{agent_id}")
def get_tasks(agent_id: int, db: Session = Depends(get_db)):
    assignments = db.query(DeliveryAssignment).filter(
        DeliveryAssignment.agent_id == agent_id
    ).order_by(DeliveryAssignment.assigned_at.desc()).all()
    result = []
    for a in assignments:
        o = a.order
        result.append({"id": a.id, "order_id": o.id,
                       "customer_name": o.customer.user.name,
                       "provider_name": o.provider.mess_name,
                       "pickup_location": a.pickup_location,
                       "drop_location": a.drop_location,
                       "status": a.status.value,
                       "total_price": o.total_price,
                       "assigned_at": str(a.assigned_at)})
    return result

@router.put("/accept/{assignment_id}")
def accept_assignment(assignment_id: int, db: Session = Depends(get_db)):
    assignment = db.query(DeliveryAssignment).filter(DeliveryAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    assignment.status = DeliveryAssignmentStatus.accepted
    db.commit()
    return {"message": "Assignment accepted"}

@router.put("/picked/{order_id}")
def mark_picked(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.order_status = OrderStatus.picked_up
    if order.assignment:
        order.assignment.status = DeliveryAssignmentStatus.picked_up
    db.commit()
    return {"message": "Marked as picked up"}

@router.put("/out-for-delivery/{order_id}")
def mark_out_for_delivery(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Generate 4-digit OTP
    otp = str(random.randint(1000, 9999))
    print(f"[DEBUG] Generated OTP {otp} for Order {order_id}")
    order.delivery_otp = otp
    order.order_status = OrderStatus.out_for_delivery
    
    if order.assignment:
        order.assignment.status = DeliveryAssignmentStatus.out_for_delivery
        
    db.add(order) 
    
    # Notify customer
    try:
        notification = Notification(
            user_id=order.customer.user_id,
            message=f"Your order #{order_id} is out for delivery! Share OTP {otp} with the rider to confirm delivery.",
            ntype=NotificationType.order_update
        )
        db.add(notification)
        print(f"[DEBUG] Created notification for user {order.customer.user_id}")
    except Exception as e:
        print(f"[ERROR] Failed to create notification: {e}")

    db.commit()
    return {"message": "Out for delivery", "otp": otp}

@router.put("/delivered/{order_id}")
def mark_delivered(order_id: int, otp: str = Query(None), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # OTP Verification (Strict)
    if not order.delivery_otp:
         # Log this anomaly
         print(f"[WARNING] Order {order_id} is in status {order.order_status} but has NO delivery_otp! Generating one now.")
         import random
         order.delivery_otp = str(random.randint(1000, 9999))
         db.commit()
         raise HTTPException(status_code=400, detail=f"OTP was missing for this order but has now been generated. Please refresh customer dashboard and provide OTP: {order.delivery_otp}")

    if str(order.delivery_otp) != str(otp):
        raise HTTPException(status_code=400, detail="Invalid OTP for delivery confirmation")
    
    order.order_status = OrderStatus.delivered
    if order.assignment:
        # Calculate Earnings dynamically
        base_fee = 15.0
        distance_fee = 10.0 # Fixed mock distance rate
        bonus = float(order.total_price) * 0.05 # 5% bonus for order value
        total = base_fee + distance_fee + bonus
        
        order.assignment.status = DeliveryAssignmentStatus.completed
        order.assignment.base_fee = base_fee
        order.assignment.distance_fee = distance_fee
        order.assignment.bonus = bonus
        order.assignment.total_amount = total
        
        if order.assignment.agent:
            order.assignment.agent.total_earnings += total
    db.commit()
    return {"message": "Marked as delivered"}

from datetime import datetime, timedelta

@router.get("/analytics/{agent_id}")
def get_analytics(agent_id: int, db: Session = Depends(get_db)):
    agent = db.query(DeliveryAgent).filter(DeliveryAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    completed = db.query(DeliveryAssignment).filter(
        DeliveryAssignment.agent_id == agent_id,
        DeliveryAssignment.status == DeliveryAssignmentStatus.completed
    ).all()
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = [a for a in completed if a.assigned_at and a.assigned_at >= today_start]
    today_earnings = sum(a.total_amount for a in completed_today)
    
    earnings_trend = []
    for i in range(6, -1, -1):
        day_start = today_start - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        day_completed = [a for a in completed if a.assigned_at and day_start <= a.assigned_at < day_end]
        earnings_trend.append(sum(a.total_amount for a in day_completed))
        
    return {
        "earnings": earnings_trend, # 7 days
        "performance": [85, 92, 96, 88, 94], # Mock performance markers
        "stats": {
            "today_earnings": today_earnings,
            "today_deliveries": len(completed_today)
        }
    }

@router.get("/earnings/{agent_id}")
def get_earnings(agent_id: int, db: Session = Depends(get_db)):
    agent = db.query(DeliveryAgent).filter(DeliveryAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    completed = db.query(DeliveryAssignment).filter(
        DeliveryAssignment.agent_id == agent_id,
        DeliveryAssignment.status == DeliveryAssignmentStatus.completed
    ).all()
    return {"total_earnings": agent.total_earnings,
            "completed_deliveries": len(completed),
            "agent_name": agent.user.name}

@router.put("/availability/{agent_id}")
def update_availability(agent_id: int, status: str, db: Session = Depends(get_db)):
    agent = db.query(DeliveryAgent).filter(DeliveryAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    status_map = {"online": AgentStatus.online, "offline": AgentStatus.offline}
    agent.availability = status_map.get(status, AgentStatus.offline)
    db.commit()
    return {"message": f"Status set to {status}"}

from pydantic import BaseModel

class LocationUpdate(BaseModel):
    lat: float
    lng: float

@router.post("/location/{agent_id}")
def update_location(agent_id: int, data: LocationUpdate, db: Session = Depends(get_db)):
    agent = db.query(DeliveryAgent).filter(DeliveryAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.current_lat = data.lat
    agent.current_lng = data.lng
    db.commit()
    return {"message": "Location updated"}

UPLOAD_DIR = "public/uploads/delivery_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/profile/upload")
async def upload_document(
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    agent_id: int = Form(...),
    db: Session = Depends(get_db)
):
    agent = db.query(DeliveryAgent).filter(DeliveryAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    if doc_type not in ["aadhaar", "dl", "photo"]:
        raise HTTPException(status_code=400, detail="Invalid doc type")

    ext = file.filename.split(".")[-1]
    filename = f"{agent_id}_{doc_type}_{secrets.token_hex(4)}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    with open(filepath, "wb") as f:
        f.write(await file.read())
        
    db_url = f"/assets/uploads/delivery_docs/{filename}"
    
    if doc_type == "aadhaar":
        agent.aadhaar_url = db_url
    elif doc_type == "dl":
        agent.dl_url = db_url
    elif doc_type == "photo":
        agent.profile_photo_url = db_url
        
    db.commit()
    return {"message": f"{doc_type} uploaded successfully", "url": db_url}
