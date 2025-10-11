# Data models and schemas
from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ============= INPUT MODELS =============

class OrderRequirements(BaseModel):
    """Customer order requirements input"""
    product_type: str
    standard: str
    quantity: int
    specifications: Dict[str, Any]
    delivery_date: str
    delivery_location: str
    customer_email: str
    customer_company: str


class SupplierOfferModel(BaseModel):
    """Supplier offer details"""
    supplier_name: str
    unit_price: float
    moq: int
    lead_time_days: int
    payment_terms: str


class NegotiationRequest(BaseModel):
    """Negotiation request with constraints"""
    customer_order_id: str
    supplier_offers: List[SupplierOfferModel]
    selected_supplier: str
    constraints: Dict[str, Any] = Field(
        description="Constraints like max_price, required_quantity, max_lead_time"
    )


# ============= OUTPUT MODELS =============

class OrderResponse(BaseModel):
    """Order creation response"""
    order_id: str
    status: str
    total: float
    estimated_delivery: str
    message: str
    source: str


class NegotiationResponse(BaseModel):
    """Negotiation session response"""
    session_id: str
    status: str
    final_terms: Optional[Dict[str, Any]] = None
    savings: float
    rounds: int


class IntelligenceResponse(BaseModel):
    """Intelligence report response"""
    critical_risks: List[Dict[str, Any]]
    cost_opportunities: List[Dict[str, Any]]
    supplier_rankings: List[Dict[str, Any]]
    generated_at: datetime
