# n8n Workflows for OpusFlow AI

This folder contains 3 production-ready n8n workflows that orchestrate the entire purchase-to-pay process with parallel stakeholder coordination.

## 📁 Workflows Overview

### 1. **Email Router** (`email_router.json`)
**Purpose:** Monitors customer emails and intelligently routes them to FastAPI for AI processing

**Features:**
- Monitors Gmail inbox every minute for new emails
- Extracts email metadata (from, subject, body, attachments)
- Sends to FastAPI `/api/webhook/email-received` endpoint
- Classifies intent using GPT-4o (new order, supplier response, inquiry)
- Logs processing results

**Triggers:** Gmail polling (every 1 minute)

**Key Nodes:**
- Gmail Trigger → Format Email → Send to FastAPI → Check Success → Log Result

---

### 2. **Parallel Actions** (`actions.json`)
**Purpose:** Coordinates 8 simultaneous actions when an order is confirmed

**Features:**
- Receives webhook trigger from FastAPI after order confirmation
- Sends notifications to 6 departments simultaneously:
  - **Sales:** Order value and customer info
  - **Procurement:** Supplier PO details
  - **Inventory:** Stock reservation instructions
  - **Production:** Manufacturing schedule
  - **Logistics:** Delivery planning
  - **Finance:** Invoice preparation
- Triggers ERP sync (SAP integration)
- Sends customer confirmation email

**Triggers:** Webhook at `/webhook/parallel-actions`

**Key Nodes:**
- Webhook → Respond Immediately → Prepare Messages → [8 Parallel Actions]

**Why Parallel?** All 8 actions execute simultaneously for instant cross-department coordination!

---

### 3. **Intelligence Scheduler** (`intelligence.json`)
**Purpose:** Runs daily procurement intelligence analysis and sends summary reports

**Features:**
- Scheduled execution every day at 2:00 AM
- Manual trigger available for demos
- Calls FastAPI `/api/run-intelligence` endpoint
- Analyzes 180 days of historical data
- Sends comprehensive Slack report with:
  - Number of critical risks detected
  - Cost-saving opportunities identified
  - Supplier performance rankings
  - Top risk and opportunity details

**Triggers:**
- Scheduled: Daily at 2:00 AM (Cron: `0 2 * * *`)
- Manual: For demos and testing

**Key Nodes:**
- Schedule/Manual Trigger → Run Analysis → Check Success → Format Report → Send to Slack

---

## 🚀 Quick Start

### Step 1: Import Workflows

1. Open your n8n instance (http://localhost:5678 or n8n Cloud)
2. Click **"Workflows"** → **"Add Workflow"**
3. Click the three dots menu → **"Import from File"**
4. Import each workflow:
   - `email_router.json`
   - `actions.json`
   - `intelligence.json`

### Step 2: Configure Environment Variables

In n8n, go to **Settings → Environments** and add:

```bash
# Required
BACKEND_URL=http://host.docker.internal:8000
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Alternative for non-Docker n8n
BACKEND_URL=http://localhost:8000
```

**Note:** If n8n is running in Docker, use `host.docker.internal` to access localhost services.

### Step 3: Configure Credentials

#### Gmail OAuth2 (Required for Email Router & Customer Emails)
1. Go to **Credentials** → **Add Credential**
2. Select **"Gmail OAuth2"**
3. Follow Google OAuth setup:
   - Create project in Google Cloud Console
   - Enable Gmail API
   - Create OAuth 2.0 Client ID
   - Add authorized redirect URI: `https://your-n8n-url/rest/oauth2-credential/callback`
4. Name it **"Gmail account"** (workflows reference this name)

#### Slack Webhook (Required for All Workflows)
1. Go to https://api.slack.com/apps
2. Create new app → "From scratch"
3. Enable **Incoming Webhooks**
4. Add webhook to your workspace
5. Copy webhook URL to `SLACK_WEBHOOK_URL` environment variable

### Step 4: Activate Workflows

1. Open each workflow
2. Click **"Active"** toggle in top-right corner
3. Verify webhook URLs:
   - Email Router: Should start polling Gmail
   - Parallel Actions: Note the webhook URL (shown when activated)
   - Intelligence: Next scheduled run shown

---

## 🔧 Configuration Details

### Email Router Configuration

**Line 84:** FastAPI endpoint URL
```json
"url": "={{ $env.BACKEND_URL }}/api/webhook/email-received"
```

**Customize polling frequency:**
- Current: Every minute
- Edit line 9: `"mode": "everyMinute"`
- Options: everyMinute, everyHour, everyDay, custom cron

### Parallel Actions Configuration

**Webhook Path:** `/webhook/parallel-actions`

**To get webhook URL after activation:**
1. Open workflow
2. Click **"Webhook: Order Confirmed"** node
3. Copy **"Production Webhook URL"**
4. Update `.env` in FastAPI:
```bash
N8N_WEBHOOK_BASE=https://your-n8n-url.app.n8n.cloud/webhook
```

**Slack notifications (Lines 83-168):**
- All 6 departments send to same webhook
- To separate channels: Create 6 different Slack webhooks and update URLs

**ERP Sync (Line 173):**
```json
"url": "={{ $env.BACKEND_URL }}/api/erp-sync"
```

### Intelligence Scheduler Configuration

**Schedule:** Daily at 2 AM UTC
- Edit line 10: `"expression": "0 2 * * *"`
- Cron format: minute hour day month weekday

**Analysis timeframe (Line 62):**
```json
"jsonBody": "={ \"time_range_days\": 180 }"
```
- Current: 180 days (6 months)
- Adjust as needed: 30, 90, 180, 365

**Manual trigger:**
- Available for demos
- Click **"Test Workflow"** → **"Manual Trigger (Demo)"**

---

## 🔍 Testing

### Test Email Router

1. Send test email to configured Gmail account
2. Include keywords: "order", "purchase", "quote"
3. Check workflow execution in n8n
4. Verify order created in FastAPI dashboard

### Test Parallel Actions

**Option 1: Via Email Router**
- Send order email → Triggers Email Router → Creates order → Triggers Parallel Actions

**Option 2: Direct API Call**
```bash
curl -X POST http://localhost:8000/api/trigger/parallel-actions \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD-2025-TEST01",
    "customer_company": "Test Corp",
    "total": 10000,
    "delivery_date": "2025-12-31",
    "source": "internal"
  }'
```

**Option 3: Via n8n Webhook**
```bash
curl -X POST https://your-n8n-url/webhook/parallel-actions \
  -H "Content-Type: application/json" \
  -d '{"body": {...order_data...}}'
```

### Test Intelligence Scheduler

**Manual Test:**
1. Open Intelligence workflow
2. Click **"Test Workflow"**
3. Click **"Manual Trigger (Demo)"** button
4. Wait 30 seconds for analysis
5. Check Slack for report

**Verify Schedule:**
- Check **"Executions"** tab in n8n
- Next run should show "Scheduled for 02:00"

---

## 🐛 Troubleshooting

### Email Router Issues

**Problem:** Emails not being detected
- **Solution:** Check Gmail API quota limits
- **Solution:** Verify Gmail OAuth credentials
- **Solution:** Check spam/trash filters (line 14)

**Problem:** FastAPI endpoint not reachable
- **Solution:** Verify `BACKEND_URL` environment variable
- **Solution:** Use `host.docker.internal` if n8n is in Docker
- **Solution:** Check FastAPI is running on port 8000

### Parallel Actions Issues

**Problem:** Webhook not triggering
- **Solution:** Verify webhook URL in FastAPI `.env`
- **Solution:** Check webhook path is `/webhook/parallel-actions`
- **Solution:** Ensure workflow is **Active**

**Problem:** Slack notifications failing
- **Solution:** Verify `SLACK_WEBHOOK_URL` is correct
- **Solution:** Test webhook with curl:
```bash
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"text": "Test message"}'
```

### Intelligence Scheduler Issues

**Problem:** Analysis fails
- **Solution:** Ensure historical data exists in database
- **Solution:** Run `python scripts/seed_mock_data.py`
- **Solution:** Check FastAPI logs for errors

**Problem:** Schedule not running
- **Solution:** Verify workflow is **Active**
- **Solution:** Check n8n timezone settings
- **Solution:** Wait until 02:00 UTC or trigger manually

---

## 📊 Workflow Architecture

```
Customer Email
      ↓
[1] Email Router (n8n)
      ↓
   FastAPI /webhook/email-received
      ↓
   Agent 1: Process Order
      ↓
   FastAPI /trigger/parallel-actions
      ↓
[2] Parallel Actions (n8n)
      ↓
   ├─ Slack: Sales
   ├─ Slack: Procurement
   ├─ Slack: Inventory
   ├─ Slack: Production
   ├─ Slack: Logistics
   ├─ Slack: Finance
   ├─ ERP Sync (SAP)
   └─ Email: Customer

[3] Intelligence Scheduler (n8n)
   Daily 2 AM
      ↓
   FastAPI /run-intelligence
      ↓
   Agent 3: Analysis
      ↓
   Slack: Report
```

---

## 🎯 Demo Scenarios

### Scenario 1: End-to-End Order Processing
1. Send email to Gmail: "We need 5000 Steel Tubes DIN 2391 by Dec 15"
2. Watch Email Router classify and process
3. See Parallel Actions trigger 8 simultaneous notifications
4. Check Slack for all 6 department notifications
5. Verify ERP sync created SAP document

### Scenario 2: Intelligence Report
1. Trigger Intelligence workflow manually
2. Agent 3 analyzes 180 days of data
3. Identifies Mueller Industries as high-risk (45% on-time)
4. Sends comprehensive Slack report
5. View full details in dashboard

### Scenario 3: External Supplier Negotiation
1. Email Router processes order for out-of-stock item
2. Agent 1 generates supplier offers
3. Agent 2 negotiates with suppliers (LangGraph)
4. Parallel Actions triggers after successful negotiation
5. ERP sync creates PO to supplier

---

## 📝 Notes

- **Security:** Workflows use environment variables for sensitive data
- **Scalability:** Parallel execution handles high volumes
- **Monitoring:** All executions logged in n8n
- **Extensibility:** Easy to add more parallel actions or departments
- **Production Ready:** Error handling and retry logic included

## 🔗 Related Documentation

- [FastAPI Backend Documentation](../../README.md)
- [n8n Official Docs](https://docs.n8n.io/)
- [Slack Webhooks Guide](https://api.slack.com/messaging/webhooks)
- [Gmail API Setup](https://developers.google.com/gmail/api/quickstart/python)

---

**Questions?** Check the main [README.md](../../README.md) or open an issue on GitHub.