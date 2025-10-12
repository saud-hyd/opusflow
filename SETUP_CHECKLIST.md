# OpusFlow AI - Setup Verification Checklist

## ✅ Environment Configuration Status

### **1. OpenAI Configuration**
```bash
OPENAI_API_KEY=sk-proj-qg2G...  ✅ CONFIGURED
```
- **Status:** Valid key present
- **Used by:** All 3 agents for GPT-4o calls
- **Required for:** Order extraction, negotiations, intelligence analysis

### **2. Database Configuration**
```bash
DATABASE_URL=postgresql://opusflow:opusflow@localhost:5432/opusflow  ✅ CONFIGURED
```
- **Status:** Matches docker-compose setup
- **Port:** 5432 (PostgreSQL default)
- **Credentials:** opusflow/opusflow
- **Database:** opusflow

### **3. Weaviate Vector Database**
```bash
WEAVIATE_URL=http://localhost:8080  ✅ CONFIGURED
```
- **Status:** Matches docker-compose setup
- **Port:** 8080 (Weaviate default)
- **Module:** text2vec-openai enabled
- **Used by:** Product/Supplier semantic search

### **4. Slack Integration (Optional)**
```bash
SLACK_BOT_TOKEN=optional  ⚠️ DISABLED
SLACK_ENABLED=false
```
- **Status:** Disabled (this is fine for demo)
- **To enable:**
  1. Get Slack Bot Token from https://api.slack.com/apps
  2. Set SLACK_BOT_TOKEN to actual token
  3. Set SLACK_ENABLED=true

### **5. n8n Workflow Automation (Optional)**
```bash
N8N_WEBHOOK_BASE=http://localhost:5678/webhook  ✅ CONFIGURED
```
- **Status:** Configured for local n8n instance
- **Port:** 5678 (n8n default)
- **Used by:** Email processing, parallel actions, intelligence scheduler

---

## 🐳 Docker Services Configuration

### **PostgreSQL** (opusflow-postgres)
- **Image:** postgres:15
- **Port:** 5432:5432 ✅
- **Credentials:** opusflow/opusflow ✅
- **Database:** opusflow ✅
- **Volume:** postgres_data (persistent) ✅
- **Network:** opusflow-network ✅

### **Weaviate** (opusflow-weaviate)
- **Image:** semitechnologies/weaviate:1.23.0
- **Port:** 8080:8080 ✅
- **Module:** text2vec-openai ✅
- **Auth:** Anonymous enabled ✅
- **Volume:** weaviate_data (persistent) ✅
- **Network:** opusflow-network ✅

### **n8n** (opusflow-n8n)
- **Image:** n8nio/n8n:latest
- **Port:** 5678:5678 ✅
- **Auth:** Disabled (for demo) ✅
- **Volume:** n8n_data (persistent) ✅
- **Network:** opusflow-network ✅

---

## 🔌 Service Connection Map

```
Backend (FastAPI)
  ↓
  ├─→ PostgreSQL:5432     ✅ (localhost:5432)
  ├─→ Weaviate:8080       ✅ (localhost:8080)
  ├─→ OpenAI API          ✅ (via OPENAI_API_KEY)
  ├─→ Slack (optional)    ⚠️ (disabled)
  └─→ n8n:5678 (optional) ✅ (localhost:5678)

Dashboard (Streamlit)
  ↓
  ├─→ Backend API:8000    ✅ (http://localhost:8000)
  └─→ PostgreSQL:5432     ✅ (direct connection)

n8n Workflows
  ↓
  ├─→ Backend API:8000    ✅ (webhooks)
  ├─→ Gmail API           ⚠️ (needs OAuth setup)
  └─→ Slack Webhooks      ⚠️ (needs webhook URL)
```

---

## 🚀 Quick Start Commands

### **1. Start Infrastructure**
```bash
docker-compose up -d
```
Expected output:
- ✅ opusflow-postgres (healthy)
- ✅ opusflow-weaviate (healthy)
- ✅ opusflow-n8n (running)

### **2. Verify Docker Services**
```bash
docker ps
```
All 3 containers should show "Up" status.

### **3. Setup Database**
```bash
python scripts/setup_db.py
```
Expected: Creates 6 tables (orders, supplier_offers, negotiations, purchase_orders, historical_deliveries, intelligence_reports)

### **4. Seed Weaviate**
```bash
python scripts/seed_weaviate.py
```
Expected: 30 products + 6 suppliers inserted

### **5. Seed Mock Data**
```bash
python scripts/seed_mock_data.py
```
Expected: 200 historical delivery records inserted

### **6. Start Backend**
```bash
cd backend
python main.py
```
Expected: Server running at http://0.0.0.0:8000

### **7. Start Dashboard**
```bash
cd dashboard
streamlit run app.py
```
Expected: Dashboard at http://localhost:8501

---

## 🧪 Health Check

### **Option 1: Browser**
Visit: http://localhost:8000/health

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "database": "healthy",
    "weaviate": "healthy",
    "openai": "configured"
  }
}
```

### **Option 2: Command Line**
```bash
curl http://localhost:8000/health | python -m json.tool
```

---

## ⚠️ Common Issues & Solutions

### **Issue 1: Weaviate connection fails**
**Error:** `Cannot connect to Weaviate`

**Solution:**
```bash
# Check if Weaviate is running
docker ps | grep weaviate

# Check Weaviate logs
docker logs opusflow-weaviate

# Restart Weaviate
docker restart opusflow-weaviate
```

### **Issue 2: PostgreSQL connection fails**
**Error:** `could not connect to server`

**Solution:**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Test connection
docker exec -it opusflow-postgres psql -U opusflow -d opusflow -c "SELECT 1;"

# Should return: 1
```

### **Issue 3: Port already in use**
**Error:** `port is already allocated`

**Solution:**
```bash
# Check what's using the port (example for 5432)
netstat -ano | findstr :5432  # Windows
lsof -i :5432                 # Mac/Linux

# Either stop the other service or change port in docker-compose.yml
```

### **Issue 4: OpenAI API errors**
**Error:** `401 Unauthorized` or `429 Rate limit`

**Solution:**
- Verify API key is correct in .env
- Check OpenAI account has credits
- Verify key starts with `sk-proj-` or `sk-`

---

## 🔐 Security Notes

### **For Demo/Development:**
✅ Current configuration is fine:
- Anonymous Weaviate access (for ease of use)
- n8n without authentication (for demos)
- Hardcoded database credentials (matching docker-compose)

### **For Production:**
⚠️ Update these before deploying:
1. Change database password in docker-compose.yml and .env
2. Enable Weaviate authentication
3. Enable n8n basic auth or OAuth
4. Use environment-specific .env files
5. Store OpenAI key in secrets manager
6. Enable SSL/TLS for all services

---

## 📊 Data Flow Verification

### **Test 1: Vector Search**
```python
python -c "
from backend.clients.weaviate_client import search_products
results = search_products('Steel Tube DIN 2391')
print(f'Found {len(results)} products')
"
```
Expected: `Found 3-5 products`

### **Test 2: Database Query**
```bash
docker exec -it opusflow-postgres psql -U opusflow -d opusflow -c "SELECT COUNT(*) FROM historical_deliveries;"
```
Expected: `200` (if mock data seeded)

### **Test 3: OpenAI Connection**
```python
python -c "
from backend.clients.openai_client import client
response = client.chat.completions.create(
    model='gpt-4o',
    messages=[{'role': 'user', 'content': 'Say OK'}]
)
print(response.choices[0].message.content)
"
```
Expected: `OK` (or similar)

---

## ✅ Final Checklist

Before running the full demo:

- [ ] Docker containers running (postgres, weaviate, n8n)
- [ ] Database tables created (6 tables)
- [ ] Weaviate collections seeded (30 products, 6 suppliers)
- [ ] Mock data loaded (200 historical deliveries)
- [ ] Backend API responding at :8000
- [ ] Dashboard running at :8501
- [ ] Health check returns "healthy"
- [ ] OpenAI API key working

**Optional for full demo:**
- [ ] Slack webhook configured
- [ ] n8n workflows imported
- [ ] Gmail OAuth configured for n8n

---

**All core components are properly configured! ✅**

You can now run the complete demo without Slack/n8n, or set them up for the full experience.