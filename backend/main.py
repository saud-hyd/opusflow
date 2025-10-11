# Main entry point for the OpusFlow AI backend
import os
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uvicorn
import requests

from backend.database import init_db, get_db
from backend.models import OrderRequirements, OrderResponse, NegotiationRequest, NegotiationResponse, IntelligenceResponse
from backend.clients.weaviate_client import init_collections
from backend.clients.slack_client import notify_order_confirmed
from backend.agents.agent_1_order import process_order
from backend.agents.agent_2_negotiation import negotiate_with_supplier
from backend.agents.agent_3_intelligence import run_intelligence_analysis

# Configuration
N8N_WEBHOOK_BASE = os.getenv("N8N_WEBHOOK_BASE", "https://your-n8n-cloud.app.n8n.cloud")


# Helper function to trigger n8n workflows
async def trigger_n8n_workflow(webhook_path: str, data: dict):
    """Trigger n8n workflow via webhook"""
    try:
        url = f"{N8N_WEBHOOK_BASE}/{webhook_path}"
        response = requests.post(url, json=data, timeout=5)
        return response.json() if response.ok else None
    except Exception as e:
        print(f"n8n trigger failed: {e}")
        return None


# Initialize FastAPI app
app = FastAPI(
    title="OpusFlow AI",
    description="Multi-agent procurement automation system",
    version="1.0.0"
)

# CORS middleware for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For demo - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database and Weaviate collections on startup."""
    try:
        print("🚀 Starting OpusFlow AI...")

        # Initialize database
        print("📊 Initializing database...")
        init_db()

        # Initialize Weaviate collections
        print("🔍 Initializing Weaviate collections...")
        init_collections()

        print("✅ OpusFlow AI started successfully!")

    except Exception as e:
        print(f"❌ Startup failed: {str(e)}")
        # Don't crash - allow app to start even if some services fail
        pass


# Health check endpoint
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Check health of all services.
    """
    services = {
        "database": "unknown",
        "weaviate": "unknown",
        "openai": "unknown"
    }

    # Check database
    try:
        db.execute("SELECT 1")
        services["database"] = "healthy"
    except Exception as e:
        services["database"] = f"unhealthy: {str(e)}"

    # Check Weaviate
    try:
        from backend.clients.weaviate_client import client
        if client:
            services["weaviate"] = "healthy"
        else:
            services["weaviate"] = "not configured"
    except Exception as e:
        services["weaviate"] = f"unhealthy: {str(e)}"

    # Check OpenAI
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key != "your-key":
            services["openai"] = "configured"
        else:
            services["openai"] = "not configured"
    except Exception as e:
        services["openai"] = f"error: {str(e)}"

    # Overall status
    overall_status = "healthy" if all(
        s in ["healthy", "configured"] for s in services.values()
    ) else "degraded"

    return {
        "status": overall_status,
        "services": services
    }


# Endpoint 1: Process customer order/quote
@app.post("/api/process-quote", response_model=OrderResponse)
async def process_quote(
    requirements: OrderRequirements,
    db: Session = Depends(get_db)
):
    """
    Process customer order requirements through Agent 1.

    This endpoint:
    - Checks inventory for in-stock items
    - Routes to internal or external fulfillment
    - Generates order confirmation
    - Returns order details or supplier offers for negotiation
    """
    try:
        result = await process_order(requirements, db)

        # Send Slack notifications if order confirmed
        if result.get("status") == "confirmed":
            notify_order_confirmed(result)

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order processing failed: {str(e)}"
        )


# Endpoint 2: Negotiate with supplier
@app.post("/api/negotiate-supplier", response_model=NegotiationResponse)
async def negotiate_supplier(
    request: NegotiationRequest,
    db: Session = Depends(get_db)
):
    """
    Run negotiation workflow with selected supplier using Agent 2.

    This endpoint:
    - Evaluates supplier offer against constraints
    - Generates counter-offers using AI
    - Simulates negotiation rounds
    - Creates purchase order if accepted
    - Sends Slack notifications
    """
    try:
        result = await negotiate_with_supplier(request, db)

        # Send Slack notifications if negotiation successful
        if result.get("status") == "completed":
            final_terms = result.get("final_terms", {})
            notify_data = {
                "order_id": request.customer_order_id,
                "customer_company": "External Supplier",
                "items": [{
                    "supplier": final_terms.get("supplier"),
                    "quantity": final_terms.get("quantity"),
                    "unit_price": final_terms.get("unit_price")
                }],
                "total": final_terms.get("total_price", 0),
                "delivery_date": f"{final_terms.get('lead_time_days', 0)} days",
                "delivery_location": "TBD"
            }
            notify_order_confirmed(notify_data)

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Negotiation failed: {str(e)}"
        )


# Endpoint 3: Run intelligence analysis
@app.post("/api/run-intelligence", response_model=IntelligenceResponse)
async def run_intelligence(
    time_range_days: int = 180,
    db: Session = Depends(get_db)
):
    """
    Run comprehensive intelligence analysis using Agent 3.

    This endpoint:
    - Analyzes historical delivery performance
    - Identifies high-risk suppliers
    - Detects material bottlenecks
    - Finds cost optimization opportunities
    - Generates supplier rankings
    """
    try:
        result = await run_intelligence_analysis(time_range_days, db)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intelligence analysis failed: {str(e)}"
        )


# Endpoint 4: Webhook - Receive email from n8n
@app.post("/api/webhook/email-received")
async def handle_incoming_email(
    email_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    n8n sends emails here for processing.

    email_data format:
    {
        "from": "customer@example.com",
        "subject": "Order Request",
        "body": "email text",
        "attachments": []  # optional
    }
    """
    try:
        from backend.clients.openai_client import classify_email_intent, extract_order_requirements

        # Classify email intent
        classification = classify_email_intent(email_data.get('body', ''))

        if classification.get('intent') == 'new_order':
            # Extract requirements
            requirements_dict = extract_order_requirements(email_data.get('body', ''))

            # Add email metadata
            if 'customer_email' not in requirements_dict:
                requirements_dict['customer_email'] = email_data.get('from', 'unknown@example.com')

            # Process order
            requirements = OrderRequirements(**requirements_dict)
            result = await process_order(requirements, db)

            # Trigger parallel actions if confirmed
            if result.get('status') == 'confirmed':
                await trigger_parallel_actions(result)

            return {"status": "processed", "order_id": result.get('order_id'), "intent": "new_order"}

        elif classification.get('intent') == 'supplier_response':
            # Handle supplier negotiation response
            # Extract offer details and continue negotiation
            return {"status": "negotiation_continued", "intent": "supplier_response"}

        return {"status": "processed", "intent": classification.get('intent', 'unknown')}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email processing failed: {str(e)}"
        )


# Endpoint 5: Trigger parallel actions
@app.post("/api/trigger/parallel-actions")
async def trigger_parallel_actions(order_data: Dict[str, Any]):
    """
    Trigger n8n workflow that notifies all 6 stakeholders + ERP sync.
    Called after order confirmation.
    """
    try:
        payload = {
            "order_id": order_data.get('order_id'),
            "customer_company": order_data.get('customer_company', 'N/A'),
            "total": order_data.get('total', 0),
            "delivery_date": order_data.get('estimated_delivery', 'TBD'),
            "source": order_data.get('source', 'unknown'),
            "items": order_data.get('items', [])
        }

        # If external sourcing, include PO details
        if order_data.get('source') == 'external':
            payload['supplier'] = order_data.get('supplier_name')
            payload['po_id'] = order_data.get('supplier_po_id')

        # Trigger n8n parallel actions workflow
        result = await trigger_n8n_workflow("parallel-actions", payload)

        return {"status": "triggered", "result": result}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Parallel actions trigger failed: {str(e)}"
        )


# Endpoint 6: Mock ERP sync
@app.post("/api/erp-sync")
async def sync_to_erp(erp_data: Dict[str, Any]):
    """
    Mock ERP integration - simulates SAP/ERP sync.
    In real world, this would post to actual ERP system.
    """
    try:
        # Simulate SAP-format transaction
        sap_payload = {
            "system": "SAP_ERP",
            "transactions": [
                {
                    "type": "sales_order",
                    "transaction_code": "VA01",
                    "document_id": f"SO-{erp_data.get('order_id', 'UNKNOWN')[-6:]}",
                    "data": {
                        "customer": erp_data.get('customer_company'),
                        "total": erp_data.get('total'),
                        "items": erp_data.get('items', [])
                    }
                }
            ],
            "status": "posted",
            "timestamp": datetime.utcnow().isoformat()
        }

        # Log for demo
        print(f"📦 ERP Sync: {sap_payload['transactions'][0]['document_id']}")

        # Return success
        return {
            "status": "success",
            "erp_system": "SAP",
            "documents_created": len(sap_payload['transactions']),
            "message": "Successfully synced to ERP",
            "sap_document_id": sap_payload['transactions'][0]['document_id']
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ERP sync failed: {str(e)}"
        )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "OpusFlow AI",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "process_quote": "/api/process-quote",
            "negotiate_supplier": "/api/negotiate-supplier",
            "run_intelligence": "/api/run-intelligence",
            "webhook_email": "/api/webhook/email-received",
            "parallel_actions": "/api/trigger/parallel-actions",
            "erp_sync": "/api/erp-sync"
        }
    }
    
@app.post("/api/send-customer-email")
async def send_customer_email(email_data: dict):
    """
    Mock customer email sending
    In real system, this would use SendGrid/SMTP
    For demo, just log it
    """
    print(f"📧 Sending email to: {email_data.get('to')}")
    print(f"   Subject: {email_data.get('subject')}")
    print(f"   Order: {email_data.get('order_id')}")
    
    return {
        "status": "sent",
        "to": email_data.get('to'),
        "message_id": f"mock-{email_data.get('order_id')}"
    }    


# Run the application
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
