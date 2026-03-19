from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.dependencies import get_current_user_from_request
from backend.models import (Provider, Meal, Order, Customer, CartItem, DeliveryAgent,
                            DeliveryAssignment, Review, Payment, SubscriptionPlan,
                            VerificationStatus, DeliveryVerification, OrderStatus, MealCategory, AgentStatus)
import os

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))

router = APIRouter(tags=["ui"])

def get_user(request: Request, db: Session):
    return get_current_user_from_request(request, db)

# ─── Public Pages ────────────────────────────────────────────────
@router.get("/", response_class=HTMLResponse)
def homepage(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    providers = db.query(Provider).filter(Provider.verification_status == VerificationStatus.verified).limit(6).all()
    meals = db.query(Meal).filter(Meal.is_available == True).limit(8).all()
    return templates.TemplateResponse("home.html", {"request": request, "user": user, "providers": providers, "meals": meals})

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if user:
        if user.role.value == "customer" and user.customer:
            return RedirectResponse(url="/customer/home", status_code=303)
        if user.role.value == "provider" and user.provider:
            return RedirectResponse(url="/provider/dashboard", status_code=303)
        if user.role.value == "delivery" and user.delivery_agent:
            return RedirectResponse(url="/delivery/dashboard", status_code=303)
        if user.role.value == "admin":
            return RedirectResponse(url="/admin/dashboard", status_code=303)
    return templates.TemplateResponse("auth/login.html", {
        "request": request, 
        "error": request.query_params.get("error"),
        "logged_in_user": user
    })

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, role: str = "customer", db: Session = Depends(get_db)):
    user = get_user(request, db)
    if user:
        if user.role.value == "customer" and user.customer:
            return RedirectResponse(url="/customer/home", status_code=303)
        if user.role.value == "provider" and user.provider:
            return RedirectResponse(url="/provider/dashboard", status_code=303)
        if user.role.value == "delivery" and user.delivery_agent:
            return RedirectResponse(url="/delivery/dashboard", status_code=303)
        if user.role.value == "admin":
            return RedirectResponse(url="/admin/dashboard", status_code=303)
    return templates.TemplateResponse("auth/register.html", {
        "request": request, 
        "role": role, 
        "error": None,
        "logged_in_user": user
    })

@router.get("/logout")
def logout_page():
    r = RedirectResponse(url="/login", status_code=302)
    r.delete_cookie("access_token", path="/")
    return r

# ─── Customer Pages ───────────────────────────────────────────────
@router.get("/customer/home", response_class=HTMLResponse)
def customer_home(request: Request, q: str = "", cuisine: str = "", db: Session = Depends(get_db)):
    user = get_user(request, db)
    query = db.query(Provider).filter(Provider.verification_status == VerificationStatus.verified)
    
    rating = request.query_params.get("rating")
    veg_only = request.query_params.get("veg_only")
    
    if q:
        query = query.filter(Provider.mess_name.ilike(f"%{q}%"))
    if cuisine:
        query = query.filter(Provider.cuisine_type.ilike(f"%{cuisine}%"))
    if rating and rating.isdigit():
        query = query.filter(Provider.rating >= float(rating))
    if veg_only:
        from backend.models.meal import Meal
        query = query.filter(~Provider.meals.any(Meal.is_veg == False))
        
    providers = query.all()
    cart_count = 0
    if user and user.customer:
        cart_count = db.query(CartItem).filter(CartItem.customer_id == user.customer.id).count()
    return templates.TemplateResponse("customer/home.html", {
        "request": request, "user": user, "providers": providers, "cart_count": cart_count,
        "q": q, "cuisine": cuisine
    })

@router.get("/customer/provider/{provider_id}", response_class=HTMLResponse)
def customer_provider_detail(provider_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    meals = db.query(Meal).filter(Meal.provider_id == provider_id, Meal.is_available == True).all()
    reviews = provider.reviews[-5:] if provider.reviews else []
    cart_count = 0
    if user and user.customer:
        cart_count = db.query(CartItem).filter(CartItem.customer_id == user.customer.id).count()
    return templates.TemplateResponse("customer/provider_detail.html", {
        "request": request, "user": user, "provider": provider, "meals": meals,
        "reviews": reviews, "cart_count": cart_count
    })

@router.post("/customer/action/cart/add")
async def cart_add_action(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.customer:
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    meal_id = int(form.get("meal_id", 0))
    quantity = int(form.get("quantity", 1))
    provider_id = int(form.get("provider_id", 0))

    existing = db.query(CartItem).filter(CartItem.customer_id == user.customer.id,
                                          CartItem.meal_id == meal_id).first()
    if existing:
        existing.quantity += quantity
    else:
        item = CartItem(customer_id=user.customer.id, meal_id=meal_id, quantity=quantity)
        db.add(item)
    db.commit()
    return RedirectResponse(f"/customer/provider/{provider_id}?added=1", status_code=302)

@router.get("/customer/cart", response_class=HTMLResponse)
def cart_page(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.customer:
        return RedirectResponse("/login")
    items = db.query(CartItem).filter(CartItem.customer_id == user.customer.id).all()
    total = sum(i.meal.price * i.quantity for i in items)
    return templates.TemplateResponse("customer/cart.html", {
        "request": request, "user": user, "items": items, "total": total,
        "cart_count": len(items)
    })

@router.post("/customer/action/cart/update")
async def cart_update(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.customer:
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    item_id = int(form.get("item_id", 0))
    action = form.get("action", "")
    item = db.query(CartItem).filter(CartItem.id == item_id,
                                      CartItem.customer_id == user.customer.id).first()
    if item:
        if action == "increase":
            item.quantity += 1
        elif action == "decrease":
            if item.quantity > 1:
                item.quantity -= 1
            else:
                db.delete(item)
        elif action == "remove":
            db.delete(item)
        db.commit()
    return RedirectResponse("/customer/cart", status_code=302)

@router.get("/customer/checkout", response_class=HTMLResponse)
def checkout_page(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.customer:
        return RedirectResponse("/login")
    items = db.query(CartItem).filter(CartItem.customer_id == user.customer.id).all()
    total = sum(i.meal.price * i.quantity for i in items)
    return templates.TemplateResponse("customer/checkout.html", {
        "request": request, "user": user, "items": items, "total": total,
        "address": user.customer.address or ""
    })

@router.post("/customer/action/checkout")
async def checkout_action(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.customer:
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    delivery_address = form.get("delivery_address", "")
    payment_method = form.get("payment_method", "Cash")
    customer = user.customer
    cart_items = db.query(CartItem).filter(CartItem.customer_id == customer.id).all()
    if not cart_items:
        return RedirectResponse("/customer/cart", status_code=302)
    
    from backend.models import OrderStatus, PaymentStatus, Order, OrderItem, Payment
    provider_groups = {}
    for item in cart_items:
        pid = item.meal.provider_id
        provider_groups.setdefault(pid, []).append(item)
    
    last_order_id = None
    for provider_id, items in provider_groups.items():
        total = sum(i.meal.price * i.quantity for i in items)
        order = Order(customer_id=customer.id, provider_id=provider_id,
                      total_price=total, delivery_address=delivery_address,
                      payment_method=payment_method, order_status=OrderStatus.created,
                      payment_status=PaymentStatus.paid)
        db.add(order)
        db.flush()
        for item in items:
            oi = OrderItem(order_id=order.id, meal_id=item.meal_id,
                           quantity=item.quantity, unit_price=item.meal.price)
            db.add(oi)
        payment = Payment(order_id=order.id, amount=total,
                          payment_method=payment_method, payment_status="paid")
        db.add(payment)
        last_order_id = order.id
    for item in cart_items:
        db.delete(item)
    db.commit()
    return RedirectResponse(f"/customer/order/{last_order_id}?success=1", status_code=302)

@router.get("/customer/orders", response_class=HTMLResponse)
def customer_orders(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.customer:
        return RedirectResponse("/login")
    orders = db.query(Order).filter(Order.customer_id == user.customer.id).order_by(Order.created_at.desc()).all()
    cart_count = db.query(CartItem).filter(CartItem.customer_id == user.customer.id).count()
    return templates.TemplateResponse("customer/orders.html", {
        "request": request, "user": user, "orders": orders, "cart_count": cart_count
    })

@router.get("/customer/order/{order_id}", response_class=HTMLResponse)
def order_detail(order_id: int, request: Request, success: str = "", db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.customer:
        return RedirectResponse("/login")
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    cart_count = db.query(CartItem).filter(CartItem.customer_id == user.customer.id).count()
    return templates.TemplateResponse("customer/order_detail.html", {
        "request": request, "user": user, "order": order,
        "cart_count": cart_count, "success": success
    })

@router.get("/customer/profile", response_class=HTMLResponse)
def customer_profile(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.customer:
        return RedirectResponse("/login")
    cart_count = db.query(CartItem).filter(CartItem.customer_id == user.customer.id).count()
    return templates.TemplateResponse("customer/profile.html", {
        "request": request, "user": user, "customer": user.customer, "cart_count": cart_count
    })

@router.post("/customer/action/profile/update")
async def update_customer_profile(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.customer:
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    user.name = form.get("name", user.name)
    user.customer.phone = form.get("phone", user.customer.phone)
    user.customer.address = form.get("address", user.customer.address)
    db.commit()
    return RedirectResponse("/customer/profile?updated=1", status_code=302)

# ─── Provider Pages ───────────────────────────────────────────────
@router.get("/provider/dashboard", response_class=HTMLResponse)
def provider_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        return RedirectResponse("/login")
    p = user.provider
    from datetime import date
    orders = db.query(Order).filter(Order.provider_id == p.id).all()
    today_orders = [o for o in orders if o.created_at and o.created_at.date() == date.today()]
    pending = [o for o in orders if o.order_status.value in ["created", "confirmed", "preparing"]]
    total_revenue = sum(o.total_price for o in orders if o.order_status.value in ["delivered", "completed"])
    top_meal = sorted(p.meals, key=lambda m: len(m.order_items), reverse=True)[0].name if p.meals else "N/A"
    recent_orders = sorted(orders, key=lambda o: o.created_at, reverse=True)[:5]
    return templates.TemplateResponse("provider/dashboard.html", {
        "request": request, "user": user, "provider": p,
        "today_orders": len(today_orders), "pending_orders": len(pending),
        "total_revenue": total_revenue, "top_meal": top_meal, "recent_orders": recent_orders
    })

@router.get("/provider/menu", response_class=HTMLResponse)
def provider_menu(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        return RedirectResponse("/login")
    meals = db.query(Meal).filter(Meal.provider_id == user.provider.id).all()
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.provider_id == user.provider.id).all()
    return templates.TemplateResponse("provider/menu.html", {
        "request": request, "user": user, "provider": user.provider, "meals": meals, "plans": plans
    })

@router.post("/provider/action/meal/add")
async def add_meal_action(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    from backend.models import MealCategory
    cat_map = {"Breakfast": MealCategory.breakfast, "Lunch": MealCategory.lunch,
               "Dinner": MealCategory.dinner, "Snacks": MealCategory.snacks}
    meal = Meal(provider_id=user.provider.id, name=form.get("name"),
                description=form.get("description", ""),
                category=cat_map.get(form.get("category", "Lunch"), MealCategory.lunch),
                price=float(form.get("price", 0)),
                is_veg=form.get("is_veg") == "true",
                image_url=form.get("image_url") or "/assets/images/meal-default.jpg")
    db.add(meal)
    db.commit()
    return RedirectResponse("/provider/menu?success=Meal added successfully! 🎉", status_code=302)

@router.post("/provider/action/meal/delete/{meal_id}")
def delete_meal_action(meal_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        return RedirectResponse("/login", status_code=302)
    meal = db.query(Meal).filter(Meal.id == meal_id, Meal.provider_id == user.provider.id).first()
    if meal:
        db.delete(meal)
        db.commit()
    return RedirectResponse("/provider/menu?success=Meal deleted successfully!", status_code=302)

@router.post("/provider/action/meal/update/{meal_id}")
async def update_meal_action(meal_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        return RedirectResponse("/login", status_code=302)
    
    form = await request.form()
    meal = db.query(Meal).filter(Meal.id == meal_id, Meal.provider_id == user.provider.id).first()
    if meal:
        meal.name = form.get("name")
        meal.price = float(form.get("price"))
        meal.description = form.get("description")
        meal.image_url = form.get("image_url")
        meal.category = MealCategory(form.get("category"))
        meal.is_veg = form.get("is_veg") == "true"
        db.commit()
    return RedirectResponse("/provider/menu?success=Meal updated successfully!", status_code=302)

@router.post("/provider/action/plan/add")
async def add_plan_action(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    features_raw = form.get("features", "")
    features_list = [f.strip() for f in features_raw.split(",") if f.strip()]
    
    plan = SubscriptionPlan(
        provider_id=user.provider.id,
        name=form.get("name"),
        description=form.get("description", ""),
        price=float(form.get("price", 0)),
        duration=form.get("duration", "weekly"),
        features=features_list,
        is_active=True
    )
    db.add(plan)
    db.commit()
    return RedirectResponse("/provider/menu?success=Subscription plan added! 🚀", status_code=302)

@router.post("/provider/action/plan/update/{plan_id}")
async def update_plan_action(plan_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        return RedirectResponse("/login", status_code=302)
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id, SubscriptionPlan.provider_id == user.provider.id).first()
    if plan:
        form = await request.form()
        features_raw = form.get("features", "")
        plan.name = form.get("name")
        plan.description = form.get("description")
        plan.price = float(form.get("price"))
        plan.duration = form.get("duration")
        plan.features = [f.strip() for f in features_raw.split(",") if f.strip()]
        db.commit()
    return RedirectResponse("/provider/menu?success=Plan updated!", status_code=302)

@router.post("/provider/action/plan/toggle/{plan_id}")
async def toggle_plan_action(plan_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        return RedirectResponse("/login", status_code=302)
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id, SubscriptionPlan.provider_id == user.provider.id).first()
    if plan:
        plan.is_active = not plan.is_active
        db.commit()
    return RedirectResponse("/provider/menu?success=Plan status updated!", status_code=302)

@router.get("/provider/orders", response_class=HTMLResponse)
def provider_orders(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        return RedirectResponse("/login")
    orders = db.query(Order).filter(Order.provider_id == user.provider.id).order_by(Order.created_at.desc()).all()
    return templates.TemplateResponse("provider/orders.html", {
        "request": request, "user": user, "provider": user.provider, "orders": orders
    })

@router.post("/provider/action/order/status/{order_id}")
async def update_order_status_action(order_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    status_map = {"confirmed": OrderStatus.confirmed, "preparing": OrderStatus.preparing,
                  "ready": OrderStatus.ready, "cancelled": OrderStatus.cancelled}
    order = db.query(Order).filter(Order.id == order_id, Order.provider_id == user.provider.id).first()
    if order:
        new_s = status_map.get(form.get("status"))
        if new_s:
            order.order_status = new_s
            db.commit()
    return RedirectResponse("/provider/orders", status_code=302)

@router.get("/provider/delivery", response_class=HTMLResponse)
def provider_delivery(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        return RedirectResponse("/login")
    ready_orders = db.query(Order).filter(Order.provider_id == user.provider.id,
                                           Order.order_status == OrderStatus.ready).all()
    agents = db.query(DeliveryAgent).filter(
        DeliveryAgent.verification_status == DeliveryVerification.verified).all()
    return templates.TemplateResponse("provider/delivery.html", {
        "request": request, "user": user, "provider": user.provider,
        "ready_orders": ready_orders, "agents": agents
    })

@router.post("/provider/action/delivery/assign")
async def assign_delivery_action(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    order_id = int(form.get("order_id", 0))
    agent_id = int(form.get("agent_id", 0))
    order = db.query(Order).filter(Order.id == order_id).first()
    existing = db.query(DeliveryAssignment).filter(DeliveryAssignment.order_id == order_id).first() if order else None
    if order and not existing:
        assignment = DeliveryAssignment(order_id=order_id, agent_id=agent_id,
                                        pickup_location=order.provider.location or "",
                                        drop_location=order.delivery_address or "")
        db.add(assignment)
        # Order stays 'ready' until agent accepts or picks up
        db.commit()
    return RedirectResponse("/provider/delivery", status_code=302)

@router.get("/provider/analytics", response_class=HTMLResponse)
def provider_analytics(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        return RedirectResponse("/login")
    p = user.provider
    orders = db.query(Order).filter(Order.provider_id == p.id,
                                     Order.order_status != OrderStatus.cancelled).all()
    total_revenue = sum(o.total_price for o in orders if o.order_status.value in ["delivered", "completed"])
    return templates.TemplateResponse("provider/analytics.html", {
        "request": request, "user": user, "provider": p,
        "total_orders": len(orders), "total_revenue": total_revenue,
        "avg_rating": p.rating, "orders": orders
    })

@router.get("/provider/profile", response_class=HTMLResponse)
def provider_profile(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        return RedirectResponse("/login")
    return templates.TemplateResponse("provider/profile.html", {
        "request": request, "user": user, "provider": user.provider
    })

@router.post("/provider/action/profile/update")
async def update_provider_profile(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.provider:
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    p = user.provider
    p.mess_name = form.get("mess_name", p.mess_name)
    p.phone = form.get("phone", p.phone)
    p.location = form.get("location", p.location)
    p.cuisine_type = form.get("cuisine_type", p.cuisine_type)
    p.operating_hours = form.get("operating_hours", p.operating_hours)
    p.description = form.get("description", p.description)
    db.commit()
    return RedirectResponse("/provider/profile?updated=1", status_code=302)

# ─── Delivery Pages ───────────────────────────────────────────────
@router.get("/delivery/dashboard", response_class=HTMLResponse)
def delivery_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.delivery_agent:
        return RedirectResponse("/login")
    agent = user.delivery_agent
    assignments = db.query(DeliveryAssignment).filter(DeliveryAssignment.agent_id == agent.id).all()
    active = [a for a in assignments if a.status.value not in ["completed"]]
    completed = [a for a in assignments if a.status.value == "completed"]
    return templates.TemplateResponse("delivery/dashboard.html", {
        "request": request, "user": user, "agent": agent,
        "active_tasks": active, "completed_tasks": completed,
        "total_earnings": agent.total_earnings
    })

@router.post("/delivery/action/accept/{assignment_id}")
def accept_task_action(assignment_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.delivery_agent:
        return RedirectResponse("/login", status_code=302)
    from backend.models import DeliveryAssignmentStatus
    assignment = db.query(DeliveryAssignment).filter(DeliveryAssignment.id == assignment_id).first()
    if assignment:
        assignment.status = DeliveryAssignmentStatus.accepted
        # Keep order_status as ready until actually picked up
        db.commit()
    return RedirectResponse("/delivery/dashboard", status_code=302)

@router.post("/delivery/action/reject/{assignment_id}")
def reject_task_action(assignment_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.delivery_agent:
        return RedirectResponse("/login", status_code=302)
    assignment = db.query(DeliveryAssignment).filter(DeliveryAssignment.id == assignment_id).first()
    if assignment:
        # We delete the assignment so the order becomes re-assignable by the provider
        db.delete(assignment)
        db.commit()
    return RedirectResponse("/delivery/dashboard", status_code=302)

@router.post("/delivery/action/deliver/{assignment_id}")
def deliver_task_action(assignment_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.delivery_agent:
        return RedirectResponse("/login", status_code=302)
    from backend.models import DeliveryAssignmentStatus
    assignment = db.query(DeliveryAssignment).filter(DeliveryAssignment.id == assignment_id).first()
    if assignment:
        assignment.status = DeliveryAssignmentStatus.completed
        assignment.order.order_status = OrderStatus.delivered
        user.delivery_agent.total_earnings += (assignment.order.total_price * 0.1)
        db.commit()
    return RedirectResponse("/delivery/dashboard", status_code=302)

@router.get("/delivery/profile", response_class=HTMLResponse)
def delivery_profile(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.delivery_agent:
        return RedirectResponse("/login")
    return templates.TemplateResponse("delivery/profile.html", {
        "request": request, "user": user, "agent": user.delivery_agent
    })

@router.post("/delivery/action/profile/update")
async def update_delivery_profile_action(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.delivery_agent:
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    agent = user.delivery_agent
    agent.phone = form.get("phone", agent.phone)
    agent.vehicle_type = form.get("vehicle_type", agent.vehicle_type)
    agent.license_number = form.get("license_number", agent.license_number)
    agent.service_area = form.get("service_area", agent.service_area)
    db.commit()
    return RedirectResponse("/delivery/profile?updated=1", status_code=303)

@router.post("/delivery/action/availability/toggle")
def toggle_availability_action(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or not user.delivery_agent:
        return RedirectResponse("/login", status_code=302)
    agent = user.delivery_agent
    if agent.availability == AgentStatus.online:
        agent.availability = AgentStatus.offline
    else:
        agent.availability = AgentStatus.online
    db.commit()
    return RedirectResponse("/delivery/dashboard", status_code=303)

# ─── Admin Pages ──────────────────────────────────────────────────
@router.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse("/login")
    from backend.models import User as UserModel
    stats = {
        "total_customers": db.query(Customer).count(),
        "total_providers": db.query(Provider).count(),
        "total_delivery_agents": db.query(DeliveryAgent).count(),
        "total_orders": db.query(Order).count(),
        "total_revenue": sum(o.total_price for o in db.query(Order).filter(
            Order.order_status.in_(["delivered", "completed"])).all()),
        "pending_providers": db.query(Provider).filter(
            Provider.verification_status == VerificationStatus.pending).count(),
        "pending_agents": db.query(DeliveryAgent).filter(
            DeliveryAgent.verification_status == DeliveryVerification.pending).count(),
    }
    recent_orders = db.query(Order).order_by(Order.created_at.desc()).limit(5).all()
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, "user": user, "stats": stats, "recent_orders": recent_orders
    })

@router.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse("/login")
    from backend.models import User as UserModel
    users = db.query(UserModel).all()
    return templates.TemplateResponse("admin/users.html", {
        "request": request, "user": user, "users": users
    })

@router.post("/admin/action/user/block/{user_id}")
def admin_block_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse("/login", status_code=302)
    from backend.models import User as UserModel, UserStatus
    u = db.query(UserModel).filter(UserModel.id == user_id).first()
    if u:
        u.status = UserStatus.blocked
        db.commit()
    return RedirectResponse("/admin/users", status_code=302)

@router.post("/admin/action/user/unblock/{user_id}")
def admin_unblock_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse("/login", status_code=302)
    from backend.models import User as UserModel, UserStatus
    u = db.query(UserModel).filter(UserModel.id == user_id).first()
    if u:
        u.status = UserStatus.active
        db.commit()
    return RedirectResponse("/admin/users", status_code=302)

@router.get("/admin/providers", response_class=HTMLResponse)
def admin_providers(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse("/login")
    providers = db.query(Provider).all()
    return templates.TemplateResponse("admin/providers.html", {
        "request": request, "user": user, "providers": providers
    })

@router.post("/admin/action/verify/provider/{provider_id}")
async def admin_verify_provider_action(provider_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    status_choice = form.get("status") # 'verified' or 'blocked'
    p = db.query(Provider).filter(Provider.id == provider_id).first()
    if p:
        if status_choice == "verified":
            p.verification_status = VerificationStatus.verified
        elif status_choice == "blocked":
            p.verification_status = VerificationStatus.blocked
        db.commit()
    return RedirectResponse("/admin/verification", status_code=303)

@router.post("/admin/action/verify/delivery/{agent_id}")
async def admin_verify_delivery_action(agent_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse("/login", status_code=302)
    form = await request.form()
    status_choice = form.get("status")
    a = db.query(DeliveryAgent).filter(DeliveryAgent.id == agent_id).first()
    if a:
        if status_choice == "verified":
            a.verification_status = DeliveryVerification.verified
        elif status_choice == "blocked":
            a.verification_status = DeliveryVerification.blocked
        db.commit()
    return RedirectResponse("/admin/verification", status_code=303)

@router.get("/admin/delivery", response_class=HTMLResponse)
def admin_delivery(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse("/login")
    agents = db.query(DeliveryAgent).all()
    return templates.TemplateResponse("admin/delivery.html", {
        "request": request, "user": user, "agents": agents
    })

# Removed old individual verification routes in favor of consolidated ones above

@router.get("/admin/orders", response_class=HTMLResponse)
def admin_orders(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse("/login")
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    return templates.TemplateResponse("admin/orders.html", {
        "request": request, "user": user, "orders": orders
    })

@router.get("/admin/reviews", response_class=HTMLResponse)
def admin_reviews(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse("/login")
    from backend.models import Review
    reviews = db.query(Review).order_by(Review.created_at.desc()).all()
    return templates.TemplateResponse("admin/reviews.html", {
        "request": request, "user": user, "reviews": reviews
    })

@router.post("/admin/action/review/delete/{review_id}")
def admin_delete_review(review_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse("/login", status_code=302)
    from backend.models import Review
    r = db.query(Review).filter(Review.id == review_id).first()
    if r:
        db.delete(r)
        db.commit()
    return RedirectResponse("/admin/reviews", status_code=302)

@router.get("/admin/analytics", response_class=HTMLResponse)
def admin_analytics(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse("/login")
    orders = db.query(Order).all()
    total_revenue = sum(o.total_price for o in orders if o.order_status.value in ["delivered", "completed"])
    return templates.TemplateResponse("admin/analytics.html", {
        "request": request, "user": user, "orders": orders,
        "total_revenue": total_revenue, "total_orders": len(orders)
    })

@router.get("/admin/database", response_class=HTMLResponse)
def admin_database(request: Request, table: str = "users", db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "admin":
        return RedirectResponse("/login")
    from backend.models import User as UserModel, Meal, CartItem, DeliveryAssignment, Payment
    allowed = {"users": UserModel, "customers": Customer, "providers": Provider,
               "delivery_agents": DeliveryAgent, "meals": Meal, "orders": Order,
               "reviews": Review, "payments": Payment}
    selected_model = allowed.get(table, UserModel)
    rows = db.query(selected_model).limit(50).all()
    columns = [col.name for col in selected_model.__table__.columns]
    data = [[str(getattr(r, col)) for col in columns] for r in rows]
    return templates.TemplateResponse("admin/database.html", {
        "request": request, "user": user, "table": table,
        "tables": list(allowed.keys()), "columns": columns, "data": data
    })

@router.post("/customer/action/order/review")
async def customer_review_action(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if not user or user.role.value != "customer":
        return RedirectResponse("/login", status_code=302)
    
    form = await request.form()
    order_id = int(form.get("order_id"))
    rating = int(form.get("rating"))
    comment = form.get("comment", "")
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or order.customer_id != user.customer.id:
        return RedirectResponse("/customer/orders", status_code=303)
    
    # Check if already reviewed
    existing = db.query(Review).filter(Review.order_id == order_id).first()
    if existing:
        return RedirectResponse("/customer/orders", status_code=303)
    
    # Create Review
    new_review = Review(
        order_id=order_id,
        provider_id=order.provider_id,
        customer_id=user.customer.id,
        rating=rating,
        comment=comment
    )
    db.add(new_review)
    
    # Update Provider Stats
    provider = order.provider
    current_total = provider.total_reviews or 0
    current_rating = provider.rating or 0
    
    new_total = current_total + 1
    new_rating = ((current_rating * current_total) + rating) / new_total
    
    provider.total_reviews = new_total
    provider.rating = round(new_rating, 1)
    
    db.commit()
    return RedirectResponse("/customer/orders", status_code=303)
