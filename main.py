from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import (
    auth, taxi_orders, delivery_orders, driver,
    admin, ratings, regions, notifications, feedback, websocket,
    admin_orders, regions_admin, bonus, order_history, pending_time, public_orders
)
from app.config import settings
from app.websocket import manager
from app.tasks import start_background_tasks
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup: Initialize Redis and start background tasks
    print("🚀 Starting up Taxi Service API...")
    await manager.init_redis()
    start_background_tasks()
    yield
    # Shutdown: Cleanup Redis
    print("🛑 Shutting down Taxi Service API...")
    await manager.cleanup()


# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Taxi Service API with comprehensive features for users, drivers, and admins",
    lifespan=lifespan
)

# CORS middleware
cors_origins = settings.CORS_ORIGINS or ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["Authorization"],
)

# Include routers
app.include_router(auth.router)
app.include_router(taxi_orders.router)
app.include_router(delivery_orders.router)
app.include_router(driver.router)
app.include_router(admin.router)
app.include_router(admin_orders.router)  # Admin order management
app.include_router(regions_admin.router)  # Admin regions/districts/pricing
app.include_router(ratings.router)
app.include_router(regions.router)
app.include_router(notifications.router)
app.include_router(feedback.router)
app.include_router(websocket.router)  # WebSocket router
app.include_router(bonus.router)  # Bonus management
app.include_router(order_history.router)  # Order acceptance history
app.include_router(pending_time.router)  # Pending time management
app.include_router(public_orders.router)  # Public orders


@app.get("/")
def root():
    return {
        "message": "Welcome to Taxi Service API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
