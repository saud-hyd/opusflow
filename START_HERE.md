# OpusFlow AI - Quick Start Guide

## Step-by-Step Startup Instructions

### Step 1: Start Docker Services

Open **PowerShell** or **Command Prompt** and run:

```bash
cd C:\opusflow-ai
docker-compose up -d
```

Wait for all 3 containers to start:
- opusflow-postgres
- opusflow-weaviate
- opusflow-n8n

Verify with:
```bash
docker ps
```

### Step 2: Setup Database

```bash
python scripts/setup_db.py
```

Expected output:
```
==================================================
OpusFlow AI - Database Setup
==================================================
[OK] Environment variables loaded

Creating database tables...

[SUCCESS] Database setup completed successfully!

Tables created:
  - orders
  - supplier_offers
  - negotiations
  - purchase_orders
  - historical_deliveries
  - intelligence_reports
```

### Step 3: Seed Weaviate

```bash
python scripts/seed_weaviate.py
```

Expected output:
```
[OK] Environment variables loaded
[OK] Collections initialized: success
[OK] Loaded 30 products
[SUCCESS] Inserted 30 products
[OK] Loaded 6 suppliers
[SUCCESS] Inserted 6 suppliers

==================================================
[SUCCESS] Weaviate seeding completed successfully!
   Products: 30
   Suppliers: 6
==================================================
```

### Step 4: Seed Mock Data

```bash
python scripts/seed_mock_data.py
```

Expected output:
```
[OK] Environment variables loaded
[OK] Connecting to database...
[OK] Database connection established

Generating 200 historical delivery records...
[OK] Generated 200 delivery records
[SUCCESS] Inserted 200 records successfully

==================================================
Summary Statistics:
==================================================

Schmidt Steel GmbH:
  Deliveries: ~70
  On-time rate: ~98%
  ...
```

### Step 5: Start Backend API

```bash
python backend/main.py
```

Expected output:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Test the API:**
Open browser: http://localhost:8000
You should see:
```json
{
  "name": "OpusFlow AI",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {...}
}
```

### Step 6: Start Dashboard

Open a **NEW terminal** and run:

```bash
streamlit run dashboard/app.py
```

Expected output:
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

Dashboard will automatically open in your browser at http://localhost:8501

---

## Quick Test

### Test Order Processing (Agent 1)

Open browser: http://localhost:8501

1. Go to **"Demo"** tab
2. The sample email is pre-filled
3. Click **"Process Order"** button
4. You should see:
   - Order ID created (ORD-2025-XXXXXX)
   - Status: confirmed or pending_negotiation
   - Supplier offers (if external)

### Test Intelligence (Agent 3)

1. Go to **"Intelligence"** tab
2. Select **"180 days"**
3. Click **"Run Analysis"**
4. Wait 10-20 seconds
5. You should see:
   - Critical Risks (Mueller Industries high-risk)
   - Cost Opportunities
   - Supplier Rankings chart

---

## Troubleshooting

### Docker not starting?

```bash
# Check Docker Desktop is running
# On Windows: Look for Docker icon in system tray

# If issues, restart Docker Desktop
# Then try: docker-compose up -d
```

### Can't connect to database?

```bash
# Check PostgreSQL is running
docker ps | findstr postgres

# Test connection
docker exec -it opusflow-postgres psql -U opusflow -c "SELECT 1;"
```

### Weaviate connection fails?

```bash
# Check Weaviate is running
docker ps | findstr weaviate

# Check health
curl http://localhost:8080/v1/.well-known/ready
```

### Backend won't start?

```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Check .env file has OpenAI key
type .env | findstr OPENAI
```

---

## URLs to Remember

- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs (auto-generated)
- **Dashboard:** http://localhost:8501
- **n8n:** http://localhost:5678
- **Weaviate:** http://localhost:8080

---

## Next Steps

Once everything is running:

1. **Test Demo Scenarios** (see README.md)
2. **Import n8n workflows** (see backend/n8n/README.md)
3. **Configure Slack** (optional)
4. **Review intelligence reports** in dashboard

---

**Need Help?** Check SETUP_CHECKLIST.md for detailed troubleshooting.