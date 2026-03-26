import asyncio
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from backend.database import SessionLocal
from backend.models import (
    Subscription, SubscriptionStatus,
    SubscriptionDelivery, DeliveryStatus,
    Order, OrderItem, OrderStatus, PaymentStatus
)


async def daily_subscription_job():
    """Background task that processes subscriptions daily."""
    while True:
        process_subscriptions()
        await asyncio.sleep(86400)  # 24 hours


def process_subscriptions():
    """
    For each active subscription that has a SubscriptionDelivery scheduled for today:
      1. Create a real Order linked to the delivery
      2. Set delivery status = preparing
    Also expire subscriptions past their end_date.
    """
    db: Session = SessionLocal()
    try:
        today = date.today()
        now = datetime.now()

        # Expire overdue subscriptions
        active_subs = db.query(Subscription).filter(
            Subscription.status == SubscriptionStatus.active
        ).all()
        for sub in active_subs:
            if sub.end_date.date() < today:
                sub.status = SubscriptionStatus.expired

        # Process today's scheduled deliveries
        todays_deliveries = db.query(SubscriptionDelivery).filter(
            SubscriptionDelivery.date == today,
            SubscriptionDelivery.status == DeliveryStatus.scheduled
        ).all()

        created = 0
        for delivery in todays_deliveries:
            sub = delivery.subscription
            if sub.status != SubscriptionStatus.active:
                delivery.status = DeliveryStatus.cancelled
                continue

            provider = sub.provider
            customer = sub.customer

            # Avoid duplicate orders for the same delivery
            if delivery.order_id:
                continue

            # Pick the first available meal from the provider
            available_meals = [m for m in provider.meals if m.is_available]
            if not available_meals:
                continue
            meal = available_meals[0]

            # Create the Order
            order = Order(
                customer_id=customer.id,
                provider_id=provider.id,
                total_price=0.0,  # Prepaid via subscription
                delivery_address=customer.address or "Default Address",
                payment_method="Prepaid via Subscription",
                notes=f"Auto-generated from subscription #{sub.id}",
                order_status=OrderStatus.created,
                payment_status=PaymentStatus.paid
            )
            db.add(order)
            db.flush()

            # Create OrderItem
            oi = OrderItem(
                order_id=order.id,
                meal_id=meal.id,
                quantity=1,
                unit_price=0.0
            )
            db.add(oi)

            # Link delivery to order and mark as preparing
            delivery.order_id = order.id
            delivery.status = DeliveryStatus.preparing
            created += 1

        db.commit()
        print(f"[CRON] Processed {len(todays_deliveries)} deliveries — created {created} orders.")
    except Exception as e:
        db.rollback()
        print(f"[CRON] Error: {e}")
    finally:
        db.close()
