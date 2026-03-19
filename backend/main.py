import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.database import create_tables
from backend.routers import api_auth, api_customer, api_provider, api_delivery, api_admin, admin_ui_router, ui_router

app = FastAPI(title="DigiBhoj", description="Smart Mess & Tiffin Platform", version="2.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# Static files
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/assets", StaticFiles(directory=os.path.join(base_dir, "assets")), name="assets")

# Create tables on startup
@app.on_event("startup")
def startup():
    create_tables()

# API Router order matters — specific before generic
app.include_router(api_auth.router)
app.include_router(api_provider.router)   # before customer to avoid path collision
app.include_router(api_customer.router)
app.include_router(api_delivery.router)
app.include_router(api_admin.router)
app.include_router(admin_ui_router.router)
app.include_router(ui_router.router)      # SSR last (catches remaining routes)
