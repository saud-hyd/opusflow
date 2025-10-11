# OpenAI API client configuration and utilities
import os
import json
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_order_requirements(email_text: str) -> Dict[str, Any]:
    """
    Extract structured order requirements from email text using GPT-4o with function calling.

    Args:
        email_text: Raw email text from customer

    Returns:
        Dict with product_type, quantity, delivery_date, customer info
    """
    function_schema = {
        "name": "extract_order_data",
        "description": "Extract order requirements from customer email",
        "parameters": {
            "type": "object",
            "properties": {
                "product_type": {"type": "string", "description": "Type of product being ordered"},
                "standard": {"type": "string", "description": "Product standard or specification"},
                "quantity": {"type": "integer", "description": "Quantity ordered"},
                "delivery_date": {"type": "string", "description": "Requested delivery date"},
                "delivery_location": {"type": "string", "description": "Delivery location"},
                "customer_email": {"type": "string", "description": "Customer email address"},
                "customer_company": {"type": "string", "description": "Customer company name"},
                "specifications": {"type": "object", "description": "Additional specifications"}
            },
            "required": ["product_type", "quantity", "customer_email"]
        }
    }

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert at extracting structured order information from B2B procurement emails."},
            {"role": "user", "content": f"Extract the order requirements from this email:\n\n{email_text}"}
        ],
        functions=[function_schema],
        function_call={"name": "extract_order_data"}
    )

    function_call = response.choices[0].message.function_call
    return json.loads(function_call.arguments)


def generate_order_confirmation(order_data: Dict[str, Any]) -> str:
    """
    Generate professional B2B order confirmation email.

    Args:
        order_data: Order details including items, pricing, delivery

    Returns:
        Professional confirmation email text
    """
    prompt = f"""Generate a professional B2B order confirmation email with these details:

Order ID: {order_data.get('order_id')}
Customer: {order_data.get('customer_company')}
Items: {order_data.get('items')}
Total: ${order_data.get('total')}
Delivery Date: {order_data.get('delivery_date')}
Delivery Location: {order_data.get('delivery_location')}

Include:
- Professional greeting
- Order confirmation with details
- Next steps
- Contact information
- Professional closing

Keep it concise and business-appropriate."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a professional B2B procurement specialist writing order confirmations."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content


def generate_negotiation_counter(current_offer: Dict[str, Any], constraints: Dict[str, Any], supplier_history: Dict[str, Any]) -> str:
    """
    Generate counter-offer email for supplier negotiation.

    Args:
        current_offer: Current supplier offer details
        constraints: Buyer constraints (max_price, required_quantity, max_lead_time)
        supplier_history: Historical performance data

    Returns:
        Counter-offer email text
    """
    prompt = f"""Generate a professional counter-offer email for B2B procurement negotiation.

Current Offer:
- Supplier: {current_offer.get('supplier_name')}
- Unit Price: ${current_offer.get('unit_price')}
- MOQ: {current_offer.get('moq')}
- Lead Time: {current_offer.get('lead_time_days')} days

Our Constraints:
- Max Price: ${constraints.get('max_price')}
- Required Quantity: {constraints.get('required_quantity')}
- Max Lead Time: {constraints.get('max_lead_time')} days

Supplier History:
{json.dumps(supplier_history, indent=2)}

Generate a counter-offer that:
- Acknowledges the relationship
- References past performance if relevant
- Proposes specific alternative terms
- Explains business rationale
- Maintains professional tone
- Encourages continued negotiation"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert B2B procurement negotiator skilled at crafting persuasive counter-offers."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8
    )

    return response.choices[0].message.content


def synthesize_intelligence_insights(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synthesize intelligence insights from supplier and material metrics.

    Args:
        metrics: Dictionary containing supplier performance, pricing trends, delivery data

    Returns:
        Dict with critical_risks, cost_opportunities, recommendations
    """
    prompt = f"""Analyze this procurement data and generate strategic insights:

{json.dumps(metrics, indent=2)}

Provide:
1. Critical Risks - Supply chain, quality, or delivery risks
2. Cost Opportunities - Ways to reduce costs or improve terms
3. Supplier Rankings - Rank suppliers by overall performance

Return as JSON with keys: critical_risks, cost_opportunities, supplier_rankings
Each should be a list of objects with 'title', 'description', and 'impact' fields."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a strategic procurement analyst providing actionable insights."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.7
    )

    return json.loads(response.choices[0].message.content)


def classify_email_intent(email_text: str) -> Dict[str, Any]:
    """
    Classify the intent of an incoming email.

    Args:
        email_text: Raw email body text

    Returns:
        Dict with intent classification (new_order, supplier_response, inquiry, etc.)
    """
    prompt = f"""Classify the intent of this email:

{email_text}

Determine if this is:
- new_order: Customer placing a new order
- supplier_response: Supplier responding to our negotiation/inquiry
- inquiry: General inquiry or question
- complaint: Complaint or issue
- other: Other type of email

Return JSON with:
{{"intent": "intent_type", "confidence": 0.0-1.0, "summary": "brief summary"}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert at classifying email intents for B2B procurement."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    return json.loads(response.choices[0].message.content)
