# Agent 1: Order Processing Agent
import random
import string
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from backend.models import OrderRequirements, OrderResponse
from backend.database import Order
from backend.clients.weaviate_client import search_products, search_suppliers
from backend.clients.openai_client import generate_order_confirmation
from backend.config import CUSTOMER_MARKUP_PERCENT, VAT_RATE


async def process_order(requirements: OrderRequirements, db: Session) -> Dict[str, Any]:
    """
    Process incoming order requirements and route to internal or external fulfillment.

    Args:
        requirements: OrderRequirements with customer order details
        db: Database session

    Returns:
        Dict with order response or pending negotiation details
    """

    # Step 1: Generate order ID
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    order_id = f"ORD-2025-{random_chars}"

    # Step 2: Search Weaviate for products matching requirements
    query_parts: List[str] = [requirements.product_type]
    if requirements.standard:
        query_parts.append(str(requirements.standard))
    query = " ".join(query_parts)
    products = search_products(query, min_stock=0)

    # Check if we have products and stock
    in_stock_product = None
    for product in products:
        if product.get("in_stock", 0) >= requirements.quantity:
            in_stock_product = product
            break

    # Step 3: If in stock - internal fulfillment
    if in_stock_product:
        source = "internal"

        # Calculate price with markup from config
        cost = in_stock_product.get("unit_price", 0)
        unit_price = cost * (1 + CUSTOMER_MARKUP_PERCENT)

        # Step 6: Calculate pricing
        subtotal = unit_price * requirements.quantity
        vat = subtotal * VAT_RATE
        total = subtotal + vat

        # Step 7: Generate confirmation using OpenAI
        order_data = {
            "order_id": order_id,
            "customer_company": requirements.customer_company or "Unknown Company",
            "customer_email": requirements.customer_email,
            "items": [{
                "product": requirements.product_type,
                "standard": requirements.standard or "N/A",
                "quantity": requirements.quantity,
                "unit_price": unit_price,
            }],
            "total": total,
            "delivery_date": requirements.delivery_date or "TBD",
            "delivery_location": requirements.delivery_location or "Not provided",
        }

        confirmation_email = generate_order_confirmation(order_data)

        # Step 8: Save order to database
        new_order = Order(
            order_id=order_id,
            customer_email=requirements.customer_email,
            customer_company=requirements.customer_company,
            items=[{
                "product_type": requirements.product_type,
                "standard": requirements.standard or "N/A",
                "quantity": requirements.quantity,
                "specifications": requirements.specifications or {},
            }],
            total=total,
            delivery_date=requirements.delivery_date,
            source=source,
            status="confirmed",
            created_at=datetime.utcnow()
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        # Step 9: Return OrderResponse
        return {
            "order_id": order_id,
            "status": "confirmed",
            "source": source,
            "total": total,
            "estimated_delivery": requirements.delivery_date,
            "message": confirmation_email,
            "customer_company": requirements.customer_company or "Unknown Company",
            "customer_email": requirements.customer_email,
            "delivery_location": requirements.delivery_location or "Not provided",
            "delivery_date": requirements.delivery_date,
            "items": order_data["items"],
        }

    # Step 4: Not in stock - external fulfillment
    source = "external"

    # Search for suppliers
    suppliers = search_suppliers(requirements.product_type)

    # Create 3 estimated offers based on supplier data (demo)
    estimated_offers = []
    for i, supplier in enumerate(suppliers[:3]):
        # Generate realistic pricing based on supplier quality
        base_price = 100.0  # Demo base price
        quality_factor = supplier.get("quality_score", 7.0) / 10.0

        estimated_offers.append({
            "supplier_name": supplier.get("name"),
            "unit_price": base_price * (0.8 + quality_factor * 0.4),  # Range: 80-120
            "moq": max(100, requirements.quantity),
            "lead_time_days": supplier.get("lead_time_days", 30) if "lead_time_days" in supplier else 30,
            "payment_terms": "Net 30",
            "on_time_rate": supplier.get("on_time_rate", 0.85),
            "quality_score": supplier.get("quality_score", 7.0),
        })

    # Save order with pending status
    new_order = Order(
        order_id=order_id,
        customer_email=requirements.customer_email,
        customer_company=requirements.customer_company,
        items=[{
            "product_type": requirements.product_type,
            "standard": requirements.standard or "N/A",
            "quantity": requirements.quantity,
            "specifications": requirements.specifications or {},
        }],
        total=0.0,  # Will be calculated after negotiation
        delivery_date=requirements.delivery_date,
        source=source,
        status="pending_negotiation",
        created_at=datetime.utcnow()
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # Step 5: Return with pending status and offers
    return {
        "order_id": order_id,
        "status": "pending_negotiation",
        "source": source,
        "total": 0.0,
        "estimated_delivery": requirements.delivery_date,
        "message": f"Order requires external sourcing. {len(estimated_offers)} supplier offers generated.",
        "customer_company": requirements.customer_company or "Unknown Company",
        "customer_email": requirements.customer_email,
        "delivery_location": requirements.delivery_location or "Not provided",
        "delivery_date": requirements.delivery_date,
        "items": [{
            "product": requirements.product_type,
            "standard": requirements.standard or "N/A",
            "quantity": requirements.quantity,
            "specifications": requirements.specifications or {},
        }],
        "supplier_offers": estimated_offers,
        "next_step": "Agent 2 will handle negotiation",
    }
