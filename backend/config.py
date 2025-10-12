# Configuration constants for OpusFlow AI
import os
from dotenv import load_dotenv

load_dotenv()

# Pricing Configuration
CUSTOMER_MARKUP_PERCENT = float(os.getenv("CUSTOMER_MARKUP_PERCENT", "0.20"))  # 20% default
VAT_RATE = float(os.getenv("VAT_RATE", "0.19"))  # 19% default

# Negotiation Configuration
DEFAULT_DISCOUNT_RATE = float(os.getenv("DEFAULT_DISCOUNT_RATE", "0.08"))  # 8% default
LEAD_TIME_REDUCTION_DAYS = int(os.getenv("LEAD_TIME_REDUCTION_DAYS", "5"))
NEGOTIATION_ACCEPT_THRESHOLD = int(os.getenv("NEGOTIATION_ACCEPT_THRESHOLD", "85"))
NEGOTIATION_REJECT_THRESHOLD = int(os.getenv("NEGOTIATION_REJECT_THRESHOLD", "60"))

# n8n Configuration
N8N_WEBHOOK_BASE = os.getenv("N8N_WEBHOOK_BASE")
N8N_WEBHOOK_SECRET = os.getenv("N8N_WEBHOOK_SECRET")  # Optional webhook authentication
N8N_ENABLED = N8N_WEBHOOK_BASE and N8N_WEBHOOK_BASE != "https://your-n8n-cloud.app.n8n.cloud"

# API Timeouts (in seconds)
UNSTRUCTURED_TIMEOUT = 30
N8N_TIMEOUT = 5
OPENAI_TIMEOUT = 30
