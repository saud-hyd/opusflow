# 🏭 OpusFlow AI

**Multi-Agent Procurement Automation Platform for B2B Manufacturing**

OpusFlow AI automates complex procurement workflows using three specialized AI agents: an Order Processing Agent that intelligently routes customer orders, a Negotiation Agent that optimizes supplier terms using LangGraph, and an Intelligence Agent that analyzes supply chain risks and opportunities. Built for manufacturing companies to reduce costs, accelerate order fulfillment, and minimize supply chain risks.

## 🚀 Tech Stack

- **Backend:** FastAPI, SQLAlchemy, LangGraph, LangChain
- **AI/ML:** OpenAI GPT-4o (function calling, structured outputs)
- **Vector DB:** Weaviate (semantic search for products/suppliers)
- **Database:** PostgreSQL
- **Analytics:** Pandas, Plotly
- **Dashboard:** Streamlit
- **Integration:** Slack SDK, n8n workflows
- **Infrastructure:** Docker, Docker Compose

## 📦 Quick Start

### 1. Start Infrastructure

```bash
docker-compose up -d
```

This starts PostgreSQL, Weaviate, and n8n.

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Database

```bash
python scripts/setup_db.py
```

### 5. Seed Data

```bash
python scripts/seed_weaviate.py
python scripts/seed_mock_data.py
```

This loads 30 products, 6 suppliers, and 200 historical delivery records.

### 6. Run Backend

```bash
cd backend
python main.py
```

Backend API runs at http://localhost:8000

### 7. Run Dashboard

```bash
cd dashboard
streamlit run app.py
```

Dashboard runs at http://localhost:8501

## 🎯 Demo Scenarios

**Scenario 1 - Internal Fulfillment:**
Process a customer order for Steel Tube DIN 2391 (in stock). Agent 1 automatically confirms the order, calculates pricing with 20% markup + VAT, generates confirmation email using GPT-4o, and sends Slack notifications to all departments.

**Scenario 2 - External Negotiation:**
Order 5000 Steel Pipes (out of stock). Agent 1 searches Weaviate for suppliers and generates offers. Agent 2 uses LangGraph to evaluate offers, generate counter-proposals, simulate negotiation rounds, and create purchase orders with 8-12% cost savings.

**Scenario 3 - Intelligence Analysis:**
Run 180-day analysis to identify that Mueller Industries has 45% on-time rate (high risk), detect material bottlenecks with 45+ day lead times, find consolidation opportunities across 6 suppliers, and generate AI-powered strategic recommendations.

## 📊 Architecture

- **Agent 1 (Order):** Routes orders → internal inventory or external suppliers
- **Agent 2 (Negotiation):** LangGraph workflow → evaluates offers → generates counter-offers → creates POs
- **Agent 3 (Intelligence):** Pandas analysis → risk scoring → OpenAI insights → strategic reports

## 🔗 API Endpoints

- `GET /health` - System health check
- `POST /api/process-quote` - Process customer order (Agent 1)
- `POST /api/negotiate-supplier` - Run negotiation workflow (Agent 2)
- `POST /api/run-intelligence` - Generate intelligence report (Agent 3)

## 📝 License

MIT License
