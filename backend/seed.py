import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, SessionLocal
from backend.models import Base
from backend.models.user import User, UserRole, UserStatus
from backend.models.customer import Customer
from backend.models.provider import Provider, VerificationStatus
from backend.models.delivery import DeliveryAgent, AgentStatus, DeliveryVerification
from backend.models.meal import Meal, MealCategory
from backend.models.order import Order, OrderStatus, PaymentStatus
from backend.models.order_item import OrderItem
from backend.models.payment import Payment
from backend.models.delivery_assignment import DeliveryAssignment, DeliveryAssignmentStatus
from backend.models.review import Review
from backend.models.cart import CartItem
from backend.models.notification import Notification
from backend.dependencies import hash_password

def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # Admin
        admin = User(name="DigiBhoj Admin", email="admin@digibhoj.com",
                     password_hash=hash_password("pass123"), role=UserRole.admin)
        db.add(admin)
        db.flush()

        # Customers
        customer_data = [
            ("Rahul Sharma", "rahul@test.com", "9876543210", "123, MG Road, Pune"),
            ("Priya Patel", "priya@test.com", "9876543211", "45, Koregaon Park, Pune"),
            ("Amit Verma", "amit@test.com", "9876543212", "78, Aundh Road, Pune"),
        ]
        customers = []
        for name, email, phone, address in customer_data:
            u = User(name=name, email=email, password_hash=hash_password("pass123"), role=UserRole.customer)
            db.add(u)
            db.flush()
            c = Customer(user_id=u.id, phone=phone, address=address)
            db.add(c)
            db.flush()
            customers.append(c)

        # Providers
        provider_data = [
            ("Sharma Tiffin Service", "Ravi Sharma", "provider1@test.com", "North Indian", "Kothrud, Pune", "Homestyle North Indian meals with love", "9am-9pm"),
            ("Royal Kitchen", "Suresh Kumar", "provider2@test.com", "South Indian", "Shivaji Nagar, Pune", "Authentic South Indian cuisine daily", "7am-10pm"),
            ("Ghar Ka Khana", "Sunita Devi", "provider3@test.com", "Gujarati", "Aundh, Pune", "Traditional Gujarati thali experience", "10am-8pm"),
            ("Punjabi Dhaba", "Harpreet Singh", "provider4@test.com", "Punjabi", "Viman Nagar, Pune", "Rich Punjabi flavors with fresh ingredients", "11am-11pm"),
        ]
        providers = []
        for mess_name, owner, email, cuisine, location, desc, hours in provider_data:
            u = User(name=owner, email=email, password_hash=hash_password("pass123"), role=UserRole.provider)
            db.add(u)
            db.flush()
            p = Provider(user_id=u.id, mess_name=mess_name, cuisine_type=cuisine, location=location,
                         description=desc, operating_hours=hours, phone="9800000001",
                         verification_status=VerificationStatus.verified, rating=4.5, total_reviews=12)
            db.add(p)
            db.flush()
            providers.append(p)

        # Meals
        meal_data = [
            (providers[0].id, "Dal Rice Combo", "Freshly cooked yellow dal with steamed rice", MealCategory.lunch, 80, True),
            (providers[0].id, "Roti Sabji", "2 rotis with seasonal vegetable curry", MealCategory.dinner, 60, True),
            (providers[0].id, "Aloo Paratha", "Stuffed potato paratha with curd and butter", MealCategory.breakfast, 50, True),
            (providers[0].id, "Paneer Butter Masala", "Creamy paneer in tomato butter gravy", MealCategory.lunch, 120, True),
            (providers[0].id, "Chicken Curry Rice", "Spicy chicken curry with jeera rice", MealCategory.dinner, 150, False),
            
            (providers[1].id, "Idli Sambar", "4 idlis with sambar and chutneys", MealCategory.breakfast, 60, True),
            (providers[1].id, "Masala Dosa", "Crispy dosa with potato filling", MealCategory.breakfast, 70, True),
            (providers[1].id, "South Indian Thali", "Full meal with rice, dal, sambar, rasam", MealCategory.lunch, 110, True),
            (providers[1].id, "Curd Rice", "Cooling curd rice with tempering", MealCategory.lunch, 50, True),
            (providers[1].id, "Vada Pav", "Mumbai style vada pav", MealCategory.snacks, 30, True),
            
            (providers[2].id, "Gujarati Thali", "Complete thali with 4 veggies, dal, roti", MealCategory.lunch, 130, True),
            (providers[2].id, "Khichdi", "Comforting moong dal khichdi with ghee", MealCategory.dinner, 70, True),
            (providers[2].id, "Dhokla", "Steamed dhokla with green chutney", MealCategory.snacks, 40, True),
            
            (providers[3].id, "Butter Chicken", "Tender chicken in rich butter tomato gravy", MealCategory.dinner, 160, False),
            (providers[3].id, "Dal Makhani", "Slow cooked black lentils in cream", MealCategory.lunch, 100, True),
            (providers[3].id, "Chole Bhature", "Spicy chickpeas with fluffy bhature", MealCategory.lunch, 90, True),
            (providers[3].id, "Lassi (Sweet)", "Thick sweet yogurt drink", MealCategory.snacks, 40, True),
            (providers[3].id, "Punjabi Thali", "Full Punjabi spread with diverse dishes", MealCategory.dinner, 180, False),
            (providers[3].id, "Sarson Saag", "Traditional mustard greens with makki roti", MealCategory.lunch, 110, True),
            (providers[0].id, "Mixed Veg Curry", "Mixed vegetables in tomato gravy", MealCategory.lunch, 75, True),
        ]
        meals = []
        for data in meal_data:
            m = Meal(provider_id=data[0], name=data[1], description=data[2],
                     category=data[3], price=data[4], is_veg=data[5])
            db.add(m)
            db.flush()
            meals.append(m)

        # Delivery Agents
        agent_data = [
            ("Rajesh Driver", "delivery1@test.com", "9900000001", "Bike", "KA-01-1234", "Kothrud, Aundh"),
            ("Sunil Moto", "delivery2@test.com", "9900000002", "Scooter", "MH-14-5678", "Shivaji Nagar"),
            ("Pankaj Rider", "delivery3@test.com", "9900000003", "Bike", "MH-12-9012", "Viman Nagar"),
        ]
        agents = []
        for name, email, phone, vehicle, lic, area in agent_data:
            u = User(name=name, email=email, password_hash=hash_password("pass123"), role=UserRole.delivery)
            db.add(u)
            db.flush()
            a = DeliveryAgent(user_id=u.id, phone=phone, vehicle_type=vehicle, license_number=lic,
                              service_area=area, verification_status=DeliveryVerification.verified,
                              availability=AgentStatus.online)
            db.add(a)
            db.flush()
            agents.append(a)

        # Sample Orders
        order1 = Order(customer_id=customers[0].id, provider_id=providers[0].id,
                       total_price=230, delivery_address="123, MG Road, Pune",
                       payment_method="UPI", order_status=OrderStatus.delivered,
                       payment_status=PaymentStatus.paid)
        db.add(order1)
        db.flush()
        db.add(OrderItem(order_id=order1.id, meal_id=meals[0].id, quantity=2, unit_price=80))
        db.add(OrderItem(order_id=order1.id, meal_id=meals[1].id, quantity=1, unit_price=60))
        db.add(Payment(order_id=order1.id, amount=230, payment_method="UPI", payment_status="paid"))
        asn1 = DeliveryAssignment(order_id=order1.id, agent_id=agents[0].id,
                                   pickup_location=providers[0].location, drop_location="123, MG Road, Pune",
                                   status=DeliveryAssignmentStatus.completed)
        db.add(asn1)
        db.add(Review(customer_id=customers[0].id, provider_id=providers[0].id,
                      order_id=order1.id, rating=4.5, comment="Excellent food! Very fresh and tasty."))
        agents[0].total_earnings += 23

        order2 = Order(customer_id=customers[1].id, provider_id=providers[1].id,
                       total_price=180, delivery_address="45, Koregaon Park, Pune",
                       payment_method="Cash", order_status=OrderStatus.preparing,
                       payment_status=PaymentStatus.pending)
        db.add(order2)
        db.flush()
        db.add(OrderItem(order_id=order2.id, meal_id=meals[7].id, quantity=1, unit_price=110))
        db.add(OrderItem(order_id=order2.id, meal_id=meals[6].id, quantity=1, unit_price=70))

        order3 = Order(customer_id=customers[2].id, provider_id=providers[3].id,
                       total_price=340, delivery_address="78, Aundh Road, Pune",
                       payment_method="Card", order_status=OrderStatus.confirmed,
                       payment_status=PaymentStatus.paid)
        db.add(order3)
        db.flush()
        db.add(OrderItem(order_id=order3.id, meal_id=meals[13].id, quantity=1, unit_price=160))
        db.add(OrderItem(order_id=order3.id, meal_id=meals[15].id, quantity=2, unit_price=90))

        # Update provider ratings
        for p in providers:
            if p.reviews:
                p.rating = round(sum(r.rating for r in p.reviews) / len(p.reviews), 1)
                p.total_reviews = len(p.reviews)

        db.commit()
        print("✅ Database seeded successfully!")
        print("📧 Login credentials (password: pass123):")
        print("   Admin:    admin@digibhoj.com")
        print("   Customer: rahul@test.com | priya@test.com | amit@test.com")
        print("   Provider: provider1@test.com | provider2@test.com | provider3@test.com | provider4@test.com")
        print("   Delivery: delivery1@test.com | delivery2@test.com | delivery3@test.com")
    except Exception as e:
        db.rollback()
        print(f"❌ Seeding failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()
