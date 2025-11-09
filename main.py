from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import (
    auth, taxi_orders, delivery_orders, driver,
    admin, ratings, regions, notifications, feedback, websocket
)
from app.config import settings
from app.websocket import manager
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup: Initialize Redis
    print("🚀 Starting up Taxi Service API...")
    await manager.init_redis()
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(taxi_orders.router)
app.include_router(delivery_orders.router)
app.include_router(driver.router)
app.include_router(admin.router)
app.include_router(ratings.router)
app.include_router(regions.router)
app.include_router(notifications.router)
app.include_router(feedback.router)
app.include_router(websocket.router)  # WebSocket router


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
