from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.db.base  # Load models for SQLAlchemy registry before routers

from app.api.health import router as health_router
from app.api.endpoints import router as core_router
from app.api.analytics import router as analytics_router
from app.api.cart import router as cart_router
from app.api.agent import router as agent_router
from app.api.tools import router as tools_router
from app.api.revenue import router as revenue_router
from app.api.policy import router as policy_router
from app.api.consent import router as consent_router
from app.api.payments import router as payments_router
from app.api.webhooks import router as webhooks_router
from app.api.orders import router as orders_router
from app.api.demo import router as demo_router
from app.api.auth import router as auth_router

app = FastAPI(
    title="AI-Native Merchant Commerce Platform",
)

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(core_router, prefix="/api", tags=["Core"])
app.include_router(analytics_router, prefix="/api", tags=["Analytics"])
app.include_router(cart_router, prefix="/api", tags=["Cart"])
app.include_router(agent_router, prefix="/api", tags=["Agent"])
app.include_router(tools_router, prefix="/api", tags=["Commerce Tools"])
app.include_router(revenue_router, prefix="/api", tags=["Revenue"])
app.include_router(policy_router, prefix="/api", tags=["Policy"])
app.include_router(consent_router, prefix="/api", tags=["Consent"])
app.include_router(payments_router, prefix="/api/payments", tags=["Payments"])
app.include_router(webhooks_router, prefix="/api/webhooks", tags=["Webhooks"])
app.include_router(orders_router, prefix="/api/orders", tags=["Orders"])
app.include_router(demo_router, prefix="/api/demo", tags=["Demo"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
