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
    """
    if not SLACK_ENABLED or not slack_client:
        return False

    if channel not in CHANNELS:
        print(f"Warning: Invalid Slack channel '{channel}'")
        return False

    try:
        response = slack_client.chat_postMessage(
            channel=f"#{CHANNELS[channel]}",
            text=message
        )
        return response["ok"]

    except SlackApiError as e:
        print(f"Slack notification failed for {channel}: {e.response['error']}")
        return False

    except Exception as e:
        print(f"Slack notification error: {str(e)}")
        return False


def notify_order_confirmed(order_data: Dict[str, Any]) -> Dict[str, bool]:
    """
    Send order confirmation notifications to all relevant channels.
    """
    if not SLACK_ENABLED or not slack_client:
        return {}

    order_id = order_data.get("order_id", "N/A")
    customer = order_data.get("customer_company", "Unknown")
    total = order_data.get("total", 0)
    items = order_data.get("items", [])
    delivery_date = (
        order_data.get("delivery_date")
        or order_data.get("estimated_delivery")
        or "TBD"
    )

    messages = {
        "sales": (
            "*New Order Confirmed*\n"
            f"Order ID: `{order_id}`\n"
            f"Customer: {customer}\n"
            f"Total Value: ${total:,.2f}\n"
            f"Delivery: {delivery_date}"
        ),
        "procurement": (
            "*Purchase Order Required*\n"
            f"Order ID: `{order_id}`\n"
            f"Items: {len(items)} line items\n"
            f"Total: ${total:,.2f}\n"
            f"Required Delivery: {delivery_date}"
        ),
        "inventory": (
            "*Stock Reservation*\n"
            f"Order ID: `{order_id}`\n"
            f"Items to Reserve: {len(items)}\n"
            f"Delivery Date: {delivery_date}"
        ),
        "production": (
            "*Production Schedule Update*\n"
            f"Order ID: `{order_id}`\n"
            f"Items: {len(items)}\n"
            f"Target Delivery: {delivery_date}"
        ),
        "logistics": (
            "*Shipping Scheduled*\n"
            f"Order ID: `{order_id}`\n"
            f"Destination: {order_data.get('delivery_location', 'TBD')}\n"
            f"Delivery Date: {delivery_date}\n"
            f"Customer: {customer}"
        ),
        "finance": (
            "*Revenue Booked*\n"
            f"Order ID: `{order_id}`\n"
            f"Customer: {customer}\n"
            f"Amount: ${total:,.2f}\n"
            f"Payment Terms: {order_data.get('payment_terms', 'Standard')}"
        ),
    }

    results: Dict[str, bool] = {}
    for channel, message in messages.items():
        results[channel] = send_notification(channel, message)

    return results
