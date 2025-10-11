# Slack API client configuration and utilities
import os
from typing import Dict, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

# Slack configuration
SLACK_ENABLED = os.getenv("SLACK_ENABLED", "false").lower() == "true"
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

# Initialize client only if enabled
slack_client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_ENABLED and SLACK_BOT_TOKEN else None

# Channel mapping
CHANNELS = {
    "sales": "sales",
    "procurement": "procurement",
    "inventory": "inventory",
    "production": "production",
    "logistics": "logistics",
    "finance": "finance"
}


def send_notification(channel: str, message: str) -> bool:
    """
    Send notification to specific Slack channel.

    Args:
        channel: Channel name (sales, procurement, inventory, production, logistics, finance)
        message: Message text to send

    Returns:
        True if sent successfully, False otherwise
    """
    # Skip if Slack not enabled
    if not SLACK_ENABLED or not slack_client:
        return False

    # Validate channel
    if channel not in CHANNELS:
        print(f"Warning: Invalid Slack channel '{channel}'")
        return False

    try:
        # Send message to channel
        response = slack_client.chat_postMessage(
            channel=f"#{CHANNELS[channel]}",
            text=message
        )
        return response["ok"]

    except SlackApiError as e:
        # Fail silently - don't break the app
        print(f"Slack notification failed for {channel}: {e.response['error']}")
        return False

    except Exception as e:
        # Fail silently for any other errors
        print(f"Slack notification error: {str(e)}")
        return False


def notify_order_confirmed(order_data: Dict[str, Any]) -> Dict[str, bool]:
    """
    Send order confirmation notifications to all relevant channels.

    Args:
        order_data: Order details dictionary

    Returns:
        Dict with channel names and success status
    """
    # Skip if Slack not enabled
    if not SLACK_ENABLED or not slack_client:
        return {}

    results = {}

    # Extract order details
    order_id = order_data.get("order_id", "N/A")
    customer = order_data.get("customer_company", "Unknown")
    total = order_data.get("total", 0)
    items = order_data.get("items", [])
    delivery_date = order_data.get("delivery_date", "TBD")

    # Sales channel - focus on order value
    sales_message = f"""🎉 *New Order Confirmed*
Order ID: `{order_id}`
Customer: {customer}
Total Value: ${total:,.2f}
Delivery: {delivery_date}"""
    results["sales"] = send_notification("sales", sales_message)

    # Procurement channel - focus on PO details
    procurement_message = f"""📋 *Purchase Order Required*
Order ID: `{order_id}`
Items: {len(items)} line items
Total: ${total:,.2f}
Required Delivery: {delivery_date}"""
    results["procurement"] = send_notification("procurement", procurement_message)

    # Inventory channel - focus on stock reservations
    inventory_message = f"""📦 *Stock Reservation*
Order ID: `{order_id}`
Items to Reserve: {len(items)}
Delivery Date: {delivery_date}"""
    results["inventory"] = send_notification("inventory", inventory_message)

    # Production channel - focus on manufacturing schedule
    production_message = f"""🏭 *Production Schedule Update*
Order ID: `{order_id}`
Items: {len(items)}
Target Delivery: {delivery_date}"""
    results["production"] = send_notification("production", production_message)

    # Logistics channel - focus on shipping
    logistics_message = f"""🚚 *Shipping Scheduled*
Order ID: `{order_id}`
Destination: {order_data.get('delivery_location', 'TBD')}
Delivery Date: {delivery_date}
Customer: {customer}"""
    results["logistics"] = send_notification("logistics", logistics_message)

    # Finance channel - focus on revenue
    finance_message = f"""💰 *Revenue Booked*
Order ID: `{order_id}`
Customer: {customer}
Amount: ${total:,.2f}
Payment Terms: {order_data.get('payment_terms', 'Standard')}"""
    results["finance"] = send_notification("finance", finance_message)

    return results
