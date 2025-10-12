# Agent 2: Negotiation Agent
import random
import string
from datetime import datetime
from typing import TypedDict, Literal, Dict, Any
from sqlalchemy.orm import Session

from langgraph.graph import StateGraph, END
from backend.models import NegotiationRequest, NegotiationResponse
from backend.database import Negotiation, PurchaseOrder, Order
from backend.clients.openai_client import generate_negotiation_counter
from backend.clients.weaviate_client import get_supplier_history
from backend.config import DEFAULT_DISCOUNT_RATE, LEAD_TIME_REDUCTION_DAYS, NEGOTIATION_ACCEPT_THRESHOLD, NEGOTIATION_REJECT_THRESHOLD


# Define state
class NegotiationState(TypedDict):
    session_id: str
    supplier: str
    current_offer: Dict[str, Any]
    constraints: Dict[str, Any]
    decision: str
    rounds: list
    final_terms: Dict[str, Any]
    score: int
    levers: list
    savings: float


# Node 1: Evaluate offer against constraints
def evaluate_node(state: NegotiationState) -> NegotiationState:
    """
    Evaluate current offer against constraints and assign score.
    Score: 0-100 based on price gap, MOQ, lead time.
    """
    current_offer = state["current_offer"]
    constraints = state["constraints"]

    # Extract values
    offered_price = current_offer.get("unit_price", 999999)
    max_price = constraints.get("max_price", 0)
    offered_lead_time = current_offer.get("lead_time_days", 999)
    max_lead_time = constraints.get("max_lead_time", 30)
    offered_moq = current_offer.get("moq", 999999)
    required_quantity = constraints.get("required_quantity", 0)

    # Calculate score components (0-100)
    price_score = max(0, 100 - ((offered_price - max_price) / max_price * 100)) if max_price > 0 else 0
    lead_time_score = max(0, 100 - ((offered_lead_time - max_lead_time) / max_lead_time * 100)) if max_lead_time > 0 else 100
    moq_score = 100 if offered_moq <= required_quantity else max(0, 100 - ((offered_moq - required_quantity) / required_quantity * 50))

    # Overall score (weighted average)
    overall_score = int((price_score * 0.5 + lead_time_score * 0.3 + moq_score * 0.2))

    # Make decision using config thresholds
    if overall_score > NEGOTIATION_ACCEPT_THRESHOLD:
        decision = "accept"
    elif overall_score >= NEGOTIATION_REJECT_THRESHOLD:
        decision = "negotiate"
    else:
        decision = "reject"

    state["score"] = overall_score
    state["decision"] = decision

    return state


# Node 2: Select negotiation levers
def select_levers_node(state: NegotiationState) -> NegotiationState:
    """
    Select negotiation levers based on gaps.
    """
    current_offer = state["current_offer"]
    constraints = state["constraints"]

    levers = []

    # Price gap - offer volume commitment
    if current_offer.get("unit_price", 0) > constraints.get("max_price", 0):
        levers.append({
            "type": "volume_commitment",
            "value": "Commit to 12-month contract with quarterly orders",
            "target_discount": "8-12%"
        })

    # Lead time gap - offer early payment
    if current_offer.get("lead_time_days", 0) > constraints.get("max_lead_time", 0):
        levers.append({
            "type": "contract_length",
            "value": "2-year partnership agreement",
            "benefit": "Faster lead times"
        })

    # MOQ gap - propose flexible delivery
    if current_offer.get("moq", 0) > constraints.get("required_quantity", 0):
        levers.append({
            "type": "flexible_delivery",
            "value": "Staged delivery over 3 months",
            "benefit": "Meet MOQ without excess inventory"
        })

    state["levers"] = levers
    return state


# Node 3: Generate counter-offer using OpenAI
def generate_counter_node(state: NegotiationState) -> NegotiationState:
    """
    Generate counter-offer email using OpenAI.
    """
    current_offer = state["current_offer"]
    constraints = state["constraints"]
    supplier = state["supplier"]

    # Get supplier history
    supplier_history = get_supplier_history(supplier)

    # Generate counter-offer email
    counter_email = generate_negotiation_counter(
        current_offer=current_offer,
        constraints=constraints,
        supplier_history=supplier_history
    )

    # Send counter-offer email to supplier
    from backend.clients.email_client import send_negotiation_email

    supplier_email = current_offer.get("supplier_email", f"procurement@{supplier.lower().replace(' ', '')}.com")
    email_sent = send_negotiation_email(
        to_email=supplier_email,
        subject=f"Re: Quotation - OpusFlow Partnership Opportunity",
        body=counter_email,
        metadata={
            "session_id": state["session_id"],
            "round": len(state["rounds"]) + 1
        }
    )

    # Add round to history
    round_data = {
        "round": len(state["rounds"]) + 1,
        "type": "counter_offer",
        "message": counter_email,
        "levers_used": state.get("levers", []),
        "email_sent": email_sent,
        "timestamp": datetime.utcnow().isoformat()
    }
    state["rounds"].append(round_data)

    # DEMO MODE: Auto-simulate supplier response if email sending is disabled
    # In production with real emails, this would wait for actual supplier response via webhook
    if not email_sent or True:  # Keep simulation active for demo
        improved_offer = current_offer.copy()
        improved_offer["unit_price"] = current_offer["unit_price"] * (1 - DEFAULT_DISCOUNT_RATE)
        improved_offer["lead_time_days"] = max(constraints.get("max_lead_time", 30), current_offer.get("lead_time_days", 30) - LEAD_TIME_REDUCTION_DAYS)

        supplier_response = {
            "round": len(state["rounds"]) + 1,
            "type": "supplier_response_simulated",
            "message": f"We appreciate your partnership proposal. We can offer ${improved_offer['unit_price']:.2f} per unit with {improved_offer['lead_time_days']} days lead time for a 12-month commitment.",
            "updated_offer": improved_offer,
            "timestamp": datetime.utcnow().isoformat()
        }
        state["rounds"].append(supplier_response)
        state["current_offer"] = improved_offer
        state = evaluate_node(state)

    return state


# Node 4: Accept and finalize
def accept_node(state: NegotiationState) -> NegotiationState:
    """
    Accept offer and create final terms.
    """
    current_offer = state["current_offer"]
    constraints = state["constraints"]

    # Calculate savings
    original_price = constraints.get("original_price", current_offer.get("unit_price", 0))
    final_price = current_offer.get("unit_price", 0)
    quantity = constraints.get("required_quantity", 1)
    savings = (original_price - final_price) * quantity

    # Create final terms
    final_terms = {
        "supplier": state["supplier"],
        "unit_price": current_offer.get("unit_price"),
        "quantity": quantity,
        "total_price": current_offer.get("unit_price") * quantity,
        "lead_time_days": current_offer.get("lead_time_days"),
        "payment_terms": current_offer.get("payment_terms", "Net 30"),
        "contract_length": "12 months",
        "delivery_terms": "FOB",
        "accepted_at": datetime.utcnow().isoformat()
    }

    state["final_terms"] = final_terms
    state["savings"] = savings
    state["decision"] = "accepted"

    return state


# Conditional router
def should_continue(state: NegotiationState) -> Literal["accept", "negotiate", "reject"]:
    """Route based on decision."""
    decision = state.get("decision", "reject")

    # After negotiation, check if improved offer is acceptable
    if decision == "negotiate" and len(state.get("rounds", [])) >= 2:
        # Re-evaluate after counter
        state = evaluate_node(state)
        decision = state.get("decision", "reject")

    return decision


# Build LangGraph
def build_negotiation_graph():
    """Build the negotiation state graph."""
    workflow = StateGraph(NegotiationState)

    # Add nodes
    workflow.add_node("evaluate", evaluate_node)
    workflow.add_node("select_levers", select_levers_node)
    workflow.add_node("generate_counter", generate_counter_node)
    workflow.add_node("accept", accept_node)

    # Set entry point
    workflow.set_entry_point("evaluate")

    # Add conditional edges from evaluate
    workflow.add_conditional_edges(
        "evaluate",
        should_continue,
        {
            "accept": "accept",
            "negotiate": "select_levers",
            "reject": END
        }
    )

    # Linear flow for negotiation path
    workflow.add_edge("select_levers", "generate_counter")
    workflow.add_edge("generate_counter", "evaluate")  # Re-evaluate after counter
    workflow.add_edge("accept", END)

    return workflow.compile()


# Main function
async def negotiate_with_supplier(request: NegotiationRequest, db: Session) -> Dict[str, Any]:
    """
    Run negotiation workflow with supplier.

    Args:
        request: NegotiationRequest with offers and constraints
        db: Database session

    Returns:
        NegotiationResponse dict
    """
    # Generate session ID
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    session_id = f"NEG-{random_chars}"

    # Find selected supplier offer
    selected_offer = None
    for offer in request.supplier_offers:
        if offer.supplier_name == request.selected_supplier:
            selected_offer = offer.dict()
            break

    if not selected_offer:
        return {
            "session_id": session_id,
            "status": "error",
            "final_terms": None,
            "savings": 0.0,
            "rounds": 0,
            "message": "Selected supplier not found in offers"
        }

    # Initialize state
    initial_state: NegotiationState = {
        "session_id": session_id,
        "supplier": request.selected_supplier,
        "current_offer": selected_offer,
        "constraints": request.constraints,
        "decision": "",
        "rounds": [],
        "final_terms": {},
        "score": 0,
        "levers": [],
        "savings": 0.0
    }

    # Build and run graph
    graph = build_negotiation_graph()
    final_state = graph.invoke(initial_state)

    # Determine status
    status = "completed" if final_state.get("decision") == "accepted" else "failed"

    # Save negotiation to database
    negotiation = Negotiation(
        session_id=session_id,
        supplier_name=request.selected_supplier,
        rounds=final_state.get("rounds", []),
        final_terms=final_state.get("final_terms", {}),
        status=status,
        savings=final_state.get("savings", 0.0),
        created_at=datetime.utcnow()
    )
    db.add(negotiation)

    # If accepted, create Purchase Order
    order_payload = None

    if status == "completed":
        po_id = f"PO-2025-{random_chars}"
        final_terms = final_state["final_terms"]
        final_terms["po_id"] = po_id

        # Update linked customer order if it exists
        order_record = db.query(Order).filter(Order.order_id == request.customer_order_id).first()
        items_payload = [{
            "supplier": final_terms.get("supplier"),
            "quantity": final_terms.get("quantity"),
            "unit_price": final_terms.get("unit_price"),
            "total": final_terms.get("total_price")
        }]

        customer_company = "External Supplier"
        customer_email = None
        if order_record:
            customer_company = order_record.customer_company or customer_company
            customer_email = order_record.customer_email

            existing_items = order_record.items if isinstance(order_record.items, list) else []
            if existing_items:
                existing_items[0]["supplier"] = final_terms.get("supplier")
                existing_items[0]["unit_price"] = final_terms.get("unit_price")
                existing_items[0]["total"] = final_terms.get("total_price")
                items_payload = existing_items

            order_record.items = items_payload
            order_record.total = final_terms.get("total_price", 0)
            order_record.status = "confirmed"
            order_record.source = "external"
            order_record.delivery_date = f"{final_terms.get('lead_time_days', 0)} days"

        order_payload = {
            "order_id": request.customer_order_id,
            "customer_company": customer_company,
            "customer_email": customer_email,
            "total": final_terms.get("total_price", 0),
            "delivery_date": f"{final_terms.get('lead_time_days', 0)} days",
            "delivery_location": "TBD",
            "source": "external",
            "items": items_payload,
            "supplier": final_terms.get("supplier"),
            "supplier_po_id": po_id,
            "payment_terms": final_terms.get("payment_terms", "Net 30"),
        }

        purchase_order = PurchaseOrder(
            po_id=po_id,
            supplier_name=request.selected_supplier,
            items=[{
                "quantity": final_terms.get("quantity"),
                "unit_price": final_terms.get("unit_price"),
                "total": final_terms.get("total_price")
            }],
            total=final_terms.get("total_price", 0),
            linked_customer_order_id=request.customer_order_id,
            created_at=datetime.utcnow()
        )
        db.add(purchase_order)

    db.commit()

    # Return response
    return {
        "session_id": session_id,
        "status": status,
        "final_terms": final_state.get("final_terms"),
        "savings": final_state.get("savings", 0.0),
        "rounds": len(final_state.get("rounds", [])),
        "order_payload": order_payload,
    }
