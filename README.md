# DigiBhoj - Digital Mess Management Platform 🍱

DigiBhoj is a high-performance, full-stack digital platform designed to modernize the traditional mess and tiffin service ecosystem. It serves as a seamless bridge between **Meal Providers**, **Customers**, and **Delivery Riders**, ensuring that healthy, home-style meals reach users efficiently and reliably.

---

## 🌟 Core Stakeholder Roles

### 👤 Customer (The User)
The customer interface is optimized for speed and delightful discovery of local meal options.
- **Dynamic Discovery**: Browse verified messes with real-time ratings and distance-based sorting.
- **Flexible Subscriptions**: weekly and monthly recurring plans with custom meal selections.
- **Delivery Calendar**: Manage your month! Cancel single-day deliveries or pause your entire subscription.
- **Real-Time Tracking**: Follow your rider on a live map with instant status updates via SSE.
- **Secure OTP Flow**: 4-digit OTP verification ensures your meal is delivered safely to the right hands.
- **Interactive Cart**: Premium checkout experience with multi-provider order support and notes.

### 🍳 Provider (The Business)
A robust dashboard for mess owners to scale and monitor their operations.
- **Advanced Analytics**: track revenue growth, subscriber retention, and peak-time demand with dynamic charts.
- **Smart Order Pipeline**: Manage one-time orders and subscription deliveries in a unified queue.
- **Menu CRUD**: Real-time control over meal availability, pricing, and dietary categories (Veg/Non-Veg).
- **Rider Assignment**: Auto-assign or manually pick from available online delivery agents.
- **Business Profile**: Manage bank details, upload documents for verification, and toggle "Vacation Mode".

### 🚴 Delivery (The Rider)
A specialized workspace designed for "on-the-go" efficiency and transparency.
- **Secure Task Management**: View pickup and drop locations with one-tap status updates (Accept -> Picked -> Delivered).
- **Earnings Analytics**: Monitor daily/weekly income with automated bonus calculation based on order value.
- **Real-Time Presence**: Branded availability toggle with background location sync for customer tracking.
- **Document Vault**: Digital upload and status tracking for license, Aadhaar, and profile photos.

---

## 🛠 Technology Stack

- **Backend**: **FastAPI** (Python 3.9+) - High-performance asynchronous execution with automatic OpenAPI (Swagger) docs.
- **Database**: **SQLite** with **SQLAlchemy ORM** - Relational data management with ACID compliance.
- **Frontend**: **Vanilla JS, HTML5, CSS3** - Zero-dependency architecture for ultra-fast performance.
- **Authentication**: **JWT (JSON Web Tokens)** - Secure, stateless sessions handled via HTTP-Only cookies.
- **Templating**: **Jinja2** - Dynamic server-side rendering with clean component structures.
- **Design System**: Modern UI patterns utilizing CSS variables, Glassmorphism, and smooth micro-animations.

---

## 📁 Project Structure

```text
Dijibhojf/
├── api/                        # Vercel Serverless Entry Points
├── backend/                    # Core Application Logic
│   ├── models/                 # SQLAlchemy Data Models (User, Provider, Meal, Order, etc.)
│   ├── routers/                # API (Customer, Provider, Delivery, Admin) and UI Handlers
│   ├── services/               # Background jobs (Subscription cron)
│   ├── templates/              # Jinja2 SSR HTML Templates
│   └── seed.py                 # Demo data seeding logic
├── public/                     # Static Assets
│   ├── assets/                 # CSS, JS, Images, and dynamic User Uploads
├── requirements.txt            # Python Dependencies
├── vercel.json                 # Vercel Cloud Deployment Config
├── digibhoj.db                 # Main SQLite Database
└── README.md                   # Project Overview
```

---

## 🏗 Intelligent Architecture

DigiBhoj goes beyond simple ordering with a specialized engine for recurring growth:
- **Subscription Engine**: Automatically generates daily delivery schedules and manages cancellations.
- **Analytics Engine**: Processes historical order data to provide actionable business insights for providers.
- **Verification System**: Multi-step verification for providers and riders to ensure ecosystem trust.

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
   Navigate to `http://127.0.0.1:8000/docs` to view the comprehensive API documentation.

---

*DigiBhoj is more than an app; it's a community-driven ecosystem for better nutrition and business growth.*