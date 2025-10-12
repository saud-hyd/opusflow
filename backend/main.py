# Main entry point for the OpusFlow AI backend
import os
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import uvicorn
import requests

from backend.database import init_db, get_db, EmailLog
from backend.models import OrderRequirements, OrderResponse, NegotiationRequest, NegotiationResponse, IntelligenceResponse
from backend.clients.weaviate_client import init_collections
from backend.clients.slack_client import notify_order_confirmed
from backend.agents.agent_1_order import process_order
from backend.agents.agent_2_negotiation import negotiate_with_supplier
from backend.agents.agent_3_intelligence import run_intelligence_analysis

# Configuration
from backend.config import N8N_WEBHOOK_BASE, N8N_WEBHOOK_SECRET, N8N_ENABLED, N8N_TIMEOUT


# Helper function to trigger n8n workflows
async def trigger_n8n_workflow(webhook_path: str, data: dict):
    """Trigger n8n workflow via webhook with validation"""
    if not N8N_ENABLED:
        print(f"[INFO] n8n not configured - skipping workflow: {webhook_path}")
        return {"status": "skipped", "reason": "n8n not configured"}

    try:
        url = f"{N8N_WEBHOOK_BASE}/{webhook_path}"
        headers = {}

        if N8N_WEBHOOK_SECRET:
            headers['Authorization'] = f"Bearer {N8N_WEBHOOK_SECRET}"

        response = requests.post(url, json=data, headers=headers, timeout=N8N_TIMEOUT)

        if response.ok:
            return response.json()
        else:
            print(f"n8n workflow failed: {response.status_code} - {response.text}")
            return {"status": "error", "code": response.status_code}

    except requests.exceptions.Timeout:
        print(f"n8n workflow timeout: {webhook_path}")
        return {"status": "timeout"}
    except Exception as e:
        print(f"n8n trigger failed: {e}")
        return {"status": "error", "message": str(e)}


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
        print("Starting OpusFlow AI...")

        # Initialize database
        print("Initializing database...")
        init_db()

        # Initialize Weaviate collections
        print("Initializing Weaviate collections...")
        init_collections()

        print("OpusFlow AI started successfully!")

    except Exception as e:
        print(f"Startup failed: {str(e)}")
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
        db.execute(text("SELECT 1"))
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
            await trigger_parallel_actions(result)

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
            payload = result.get("order_payload")

            if not payload:
                final_terms = result.get("final_terms", {})
                payload = {
                    "order_id": request.customer_order_id,
                    "customer_company": "External Supplier",
                    "customer_email": None,
                    "items": [{
                        "supplier": final_terms.get("supplier"),
                        "quantity": final_terms.get("quantity"),
                        "unit_price": final_terms.get("unit_price"),
                        "total": final_terms.get("total_price")
                    }],
                    "total": final_terms.get("total_price", 0),
                    "delivery_date": f"{final_terms.get('lead_time_days', 0)} days",
                    "delivery_location": "TBD",
                    "source": "external",
                    "supplier": final_terms.get("supplier"),
                    "supplier_po_id": final_terms.get("po_id"),
                    "payment_terms": final_terms.get("payment_terms", "Net 30"),
                }

            notify_order_confirmed(payload)
            await trigger_parallel_actions(payload)

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

        message_id = email_data.get('message_id') or email_data.get('messageId')
        existing_log = None
        if message_id:
            existing_log = db.query(EmailLog).filter(EmailLog.message_id == message_id).first()
            if existing_log:
                existing_log.status = "duplicate_attempt"
                existing_log.payload = email_data
                db.commit()
                return {"status": "duplicate", "intent": existing_log.intent or "unknown"}

        # Process attachments if present
        email_body = email_data.get('body', '')
        attachments = email_data.get('attachments', [])

        if attachments:
            from backend.clients.unstructured_client import extract_from_attachment
            for attachment in attachments:
                filename = attachment.get('filename', '')
                content_b64 = attachment.get('content', '')
                if content_b64:
                    extracted_text = extract_from_attachment(filename, content_b64)
                    email_body += f"\n\n--- From attachment {filename} ---\n{extracted_text}"

        # Classify email intent
        classification = classify_email_intent(email_body)
        intent = classification.get('intent', 'unknown')

        if classification.get('intent') == 'new_order':
            # Extract requirements
            requirements_dict = extract_order_requirements(email_body)

            # Add email metadata
            if 'customer_email' not in requirements_dict:
                requirements_dict['customer_email'] = email_data.get('from', 'unknown@example.com')
            requirements_dict.setdefault('specifications', {})
            if 'customer_company' not in requirements_dict:
                sender = email_data.get('from', '')
                domain_part = sender.split('@')[1] if '@' in sender else ''
                company_hint = domain_part.split('.')[0].title() if domain_part else "Unknown Company"
                requirements_dict['customer_company'] = company_hint
            requirements_dict.setdefault('delivery_location', email_data.get('delivery_location', 'TBD'))
            requirements_dict.setdefault('delivery_date', None)

            # Process order
            requirements = OrderRequirements(**requirements_dict)
            result = await process_order(requirements, db)

            # AUTOMATED FLOW: Handle based on order status
            if result.get('status') == 'confirmed':
                # STEP 4: Order confirmed from internal inventory
                notify_order_confirmed(result)
                await trigger_parallel_actions(result)

            elif result.get('status') == 'pending_negotiation':
                # STEP 3: No inventory - automatically trigger Agent 2 negotiation
                supplier_offers = result.get('supplier_offers', [])
                print(f"[DEBUG] Agent 2 Auto-Trigger: Found {len(supplier_offers)} supplier offers")

                if supplier_offers:
                    # Auto-select best supplier based on quality score and on-time rate
                    best_supplier = max(
                        supplier_offers,
                        key=lambda s: (s.get('quality_score', 0) * 0.6 + s.get('on_time_rate', 0) * 100 * 0.4)
                    )

                    # Build negotiation request
                    from backend.models import NegotiationRequest, SupplierOfferModel

                    supplier_offer_models = [SupplierOfferModel(**offer) for offer in supplier_offers]

                    negotiation_request = NegotiationRequest(
                        customer_order_id=result.get('order_id'),
                        supplier_offers=supplier_offer_models,
                        selected_supplier=best_supplier['supplier_name'],
                        constraints={
                            "max_price": best_supplier['unit_price'] * 0.95,  # Target 5% reduction
                            "required_quantity": requirements.quantity,
                            "max_lead_time": best_supplier.get('lead_time_days', 30),
                            "original_price": best_supplier['unit_price']
                        }
                    )

                    # Run Agent 2 negotiation automatically
                    negotiation_result = await negotiate_with_supplier(negotiation_request, db)

                    # If negotiation successful, trigger parallel actions
                    if negotiation_result.get('status') == 'completed':
                        order_payload = negotiation_result.get('order_payload')
                        if order_payload:
                            notify_order_confirmed(order_payload)
                            await trigger_parallel_actions(order_payload)

                        result['negotiation'] = {
                            'session_id': negotiation_result.get('session_id'),
                            'status': 'completed',
                            'savings': negotiation_result.get('savings', 0)
                        }

            db.add(EmailLog(
                message_id=message_id,
                intent='new_order',
                status=result.get('status', 'processed'),
                payload={
                    "order_id": result.get('order_id'),
                    "status": result.get('status'),
                    "customer_email": requirements.customer_email
                }
            ))
            db.commit()

            return {"status": "processed", "order_id": result.get('order_id'), "intent": "new_order"}

        elif classification.get('intent') == 'supplier_response':
            # Handle supplier negotiation response
            # Extract session_id from email headers or body
            session_id = email_data.get('headers', {}).get('X-OpusFlow-Session')

            if session_id:
                # Extract updated offer from email
                from backend.clients.openai_client import extract_order_requirements
                offer_data = extract_order_requirements(email_body)

                # Find negotiation session and update
                from backend.database import Negotiation
                negotiation = db.query(Negotiation).filter(Negotiation.session_id == session_id).first()

                if negotiation:
                    # Add supplier response to rounds
                    rounds = negotiation.rounds if isinstance(negotiation.rounds, list) else []
                    rounds.append({
                        "round": len(rounds) + 1,
                        "type": "supplier_response_real",
                        "message": email_body,
                        "offer_data": offer_data,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    negotiation.rounds = rounds
                    db.commit()

                    db.add(EmailLog(
                        message_id=message_id,
                        intent='supplier_response',
                        status='processed',
                        payload={"session_id": session_id, "offer_data": offer_data}
                    ))
                    db.commit()

                    return {"status": "negotiation_updated", "intent": "supplier_response", "session_id": session_id}

            db.add(EmailLog(
                message_id=message_id,
                intent='supplier_response',
                status='routed',
                payload=email_data
            ))
            db.commit()
            return {"status": "negotiation_continued", "intent": "supplier_response"}

        db.add(EmailLog(
            message_id=message_id,
            intent=intent,
            status='processed',
            payload=email_data
        ))
        db.commit()

        return {"status": "processed", "intent": intent}

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
            "delivery_date": order_data.get('delivery_date') or order_data.get('estimated_delivery', 'TBD'),
            "source": order_data.get('source', 'unknown'),
            "items": order_data.get('items', []),
            "customer_email": order_data.get('customer_email'),
            "supplier": order_data.get('supplier'),
            "supplier_po_id": order_data.get('supplier_po_id'),
            "payment_terms": order_data.get('payment_terms')
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
        print(f"ERP Sync: {sap_payload['transactions'][0]['document_id']}")

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
    print(f"Sending email to: {email_data.get('to')}")
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
