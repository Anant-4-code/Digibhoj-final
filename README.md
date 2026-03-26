# DigiBhoj - Digital Mess Management Platform 🍱

DigiBhoj is a high-performance, full-stack digital platform designed to modernize the traditional mess and tiffin service ecosystem. It serves as a seamless bridge between **Meal Providers**, **Customers**, and **Delivery Riders**, ensuring that healthy, home-style meals reach users efficiently and reliably.

---

## 🌟 Core Stakeholder Roles

### 👤 Customer (The User)
The customer interface is optimized for speed and delightful discovery of local meal options.
- **Dynamic Browsing**: Discover nearby messes based on location and rating.
- **Flexible Subscriptions**: Options for daily, weekly, or monthly meal plans.
- **Real-Time Tracking**: Monitor orders from preparation to doorstep delivery.
- **Responsive Cart**: A premium shopping experience with quick-add and checkout flows.
- **Feedback Loop**: Rate and review meals to help maintain high quality across the platform.

### 🍳 Provider (The Business)
A robust dashboard for mess owners to scale their operations.
- **Menu Management**: Easily add, edit, or remove meal offerings with price and category.
- **Order Pipeline**: View and manage incoming orders in real-time.
- **Business Analytics**: Track earnings, popular meals, and customer growth.
- **Profile Customization**: Manage business hours, contact details, and service areas.

### 🚴 Delivery (The Rider)
A specialized workspace designed for "on-the-go" efficiency.
- **Premium Profile**: A tabbed personal dashboard for vehicle details, security, and alerts.
- **Real-Time Stats**: Animated earnings counters with "Live" data simulation.
- **Task Management**: View assigned deliveries and update status with a single tap.
- **Availability Toggle**: A branded "Online/Offline" switch with visual pulse indicators.

### 🔑 Admin (The Overseer)
Complete control over the ecosystem stability and user management.

---

## 📁 Detailed Project Structure

```text
Dijibhojf/
├── api/                        # Vercel Serverless Entry Points
│   └── index.py                # Main entry for serverless functions
├── backend/                    # Core Application Logic
│   ├── main.py                 # FastAPI initialization & config
│   ├── models/                 # SQLAlchemy Data Models (agent.py, customer.py, provider.py, order.py)
│   ├── routers/                # API and UI Route Handlers
│   │   ├── ui_router.py        # Main HTML page routes
│   │   ├── api_customer.py     # Customer-specific API endpoints (polling, notifications)
│   │   ├── api_delivery.py     # Delivery-specific API endpoints (OTP, tracking)
│   │   └── api_provider.py     # Provider-specific API endpoints (meal management)
│   └── templates/              # Jinja2 HTML Templates
│       ├── base.html           # Main shared layout
│       ├── customer/           # Customer pages (home, checkout)
│       ├── delivery/           # Rider pages (dashboard, profile)
│       └── provider/           # Provider pages (dashboard, menu)
├── public/                     # Static Assets
│   ├── assets/
│   │   ├── css/                # Design-system and component styles
│   │   └── js/                 # Client scripts (order-polling.js, address-selector.js)
│   └── uploads/                # Dynamic user uploads
├── requirements.txt            # Python Dependencies
├── vercel.json                 # Vercel Configuration
├── digibhoj.db                 # Main SQLite Database
└── README.md                   # Project Overview
```

---

## 🛠 Technology Stack

- **Backend**: **FastAPI** (Python 3.9+) - Selected for its high performance, automatic documentation (Swagger), and asynchronous capabilities.
- **Database**: **SQLite** with **SQLAlchemy ORM** - Provides a lightweight yet powerful data layer for relational management.
- **Frontend**: **Vanilla JS, HTML5, CSS3** - Zero-dependency frontend ensures ultra-fast load times and maximum compatibility.
- **Templating**: **Jinja2** - Allows for dynamic server-side rendering while maintaining clean HTML structures.
- **Authentication**: Secure **JWT (JSON Web Tokens)** for stateless, secure user sessions.
- **Design Strategy**: Custom CSS variables and modern UI patterns (Glassmorphism, Micro-animations, Responsive Grids).

---

## 🏗 Database Architecture

DigiBhoj utilizes a relational database schema designed for consistency and scalability.

### Core Entities:
- **Users**: Base entity for authentication, shared across all roles.
- **Customers**: Linked to Users; manages address, orders, and favorites.
- **Providers**: Linked to Users; manages mess details, meal listings, and availability.
- **Delivery Agents (Riders)**: Linked to Users; contains vehicle info, earnings data, and real-time availability.
- **Meals**: Created by Providers; includes pricing, nutrition info, and categories.
- **Orders & OrderItems**: Bridges Customers and Providers; tracks transaction history.
- **Delivery Assignments**: Links Orders to Delivery Agents for real-time tracking.
- **Subscriptions**: Manages recurring meal plans for consistent customer engagement.

---

## 🚀 Setup & Development

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Local Environment**:
   ```bash
   uvicorn backend.main:app --reload
   ```

3. **Access Interactive Docs**:
   Navigate to `http://127.0.0.1:8000/docs` to view the auto-generated API documentation.

---

*DigiBhoj is more than an app; it's a community-driven ecosystem for better nutrition and business growth.*