from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import (DeliveryAgent, DeliveryAssignment, Order, OrderStatus, 
                            DeliveryAssignmentStatus, AgentStatus)
from backend.dependencies import get_current_user_from_request

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
    order.order_status = OrderStatus.out_for_delivery
    if order.assignment:
        order.assignment.status = DeliveryAssignmentStatus.out_for_delivery
    db.commit()
    return {"message": "Out for delivery"}

@router.put("/delivered/{order_id}")
def mark_delivered(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.order_status = OrderStatus.delivered
    if order.assignment:
        order.assignment.status = DeliveryAssignmentStatus.completed
        if order.assignment.agent:
            order.assignment.agent.total_earnings += (order.total_price * 0.1)
    db.commit()
    return {"message": "Marked as delivered"}

@router.get("/analytics/{agent_id}")
def get_analytics(agent_id: int, db: Session = Depends(get_db)):
    agent = db.query(DeliveryAgent).filter(DeliveryAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Mock some data for the charts based on the agent's history
    completed = db.query(DeliveryAssignment).filter(
        DeliveryAssignment.agent_id == agent_id,
        DeliveryAssignment.status == DeliveryAssignmentStatus.completed
    ).all()
    
    return {
        "earnings": [380, 290, 520, 350, 460, 600, 450], # Sample 7 days
        "performance": [85, 92, 96, 88, 94], # Speed, Accuracy, Rating, Efficiency, Reliability
        "stats": {
            "today_earnings": len(completed) * 50, # Mock 50 per delivery for today
            "today_deliveries": len(completed)
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
