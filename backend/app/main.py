from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.endpoints import router as core_router
from app.api.analytics import router as analytics_router
from app.api.cart import router as cart_router
from app.api.agent import router as agent_router
from app.api.tools import router as tools_router
from app.api.revenue import router as revenue_router
from app.api.policy import router as policy_router
from app.api.consent import router as consent_router
import app.db.base  # Load models for SQLAlchemy registry

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
