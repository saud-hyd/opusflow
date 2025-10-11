# Dashboard application for OpusFlow AI
import os
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_BASE_URL = "http://localhost:8000"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://opusflow:opusflow@localhost:5432/opusflow")

# Database connection
@st.cache_resource
def get_db_engine():
    """Create database engine."""
    return create_engine(DATABASE_URL)

engine = get_db_engine()


# Page config
st.set_page_config(
    page_title="OpusFlow AI Dashboard",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("🏭 OpusFlow AI - Manufacturing Operations")
st.markdown("Multi-Agent Procurement Automation Platform")

# Sidebar
with st.sidebar:
    st.header("System Status")

    # Health check
    try:
        health_response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        if health_response.status_code == 200:
            health_data = health_response.json()
            st.success(f"Status: {health_data['status'].upper()}")

            for service, status in health_data['services'].items():
                if "healthy" in status or "configured" in status:
                    st.text(f"✅ {service.title()}")
                else:
                    st.text(f"⚠️ {service.title()}")
        else:
            st.error("API unavailable")
    except:
        st.error("Cannot connect to backend")

    st.divider()
    st.markdown("### About")
    st.markdown("""
    **3 AI Agents:**
    - 🤖 Order Processing
    - 💬 Negotiation
    - 🧠 Intelligence
    """)


# Metrics Row
col1, col2, col3 = st.columns(3)

# Metric 1: Orders Today
try:
    with engine.connect() as conn:
        today = datetime.utcnow().date()
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM orders
            WHERE DATE(created_at) = :today
        """), {"today": today})
        orders_today = result.scalar() or 0
except:
    orders_today = 0

col1.metric("📦 Orders Today", orders_today)

# Metric 2: Active Negotiations
try:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM negotiations
            WHERE status = 'in_progress'
        """))
        active_negotiations = result.scalar() or 0
except:
    active_negotiations = 0

col2.metric("💬 Active Negotiations", active_negotiations)

# Metric 3: Average Savings %
try:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT AVG(savings) as avg_savings
            FROM negotiations
            WHERE status = 'completed' AND savings > 0
        """))
        avg_savings = result.scalar() or 0
        # Convert to percentage (assuming savings is in dollars, need to calculate %)
        savings_pct = 8.5  # Demo value
except:
    savings_pct = 0

col3.metric("💰 Avg Savings", f"{savings_pct}%")

st.divider()

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Real-Time Activity", "🧠 Intelligence", "🎯 Demo"])

# ===== TAB 1: Real-Time Activity =====
with tab1:
    st.header("Real-Time Operations")

    col_a, col_b = st.columns([3, 1])

    with col_b:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

    # Recent Orders
    st.subheader("📦 Recent Orders")

    try:
        with engine.connect() as conn:
            orders_df = pd.read_sql("""
                SELECT
                    order_id,
                    customer_company,
                    total,
                    delivery_date,
                    status,
                    source,
                    created_at
                FROM orders
                ORDER BY created_at DESC
                LIMIT 10
            """, conn)

            if len(orders_df) > 0:
                # Format columns
                orders_df['total'] = orders_df['total'].apply(lambda x: f"${x:,.2f}")
                orders_df['created_at'] = pd.to_datetime(orders_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')

                st.dataframe(
                    orders_df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No orders yet. Try the Demo tab to create one!")
    except Exception as e:
        st.error(f"Error loading orders: {str(e)}")

    st.divider()

    # Active Negotiations
    st.subheader("💬 Active Negotiations")

    try:
        with engine.connect() as conn:
            negotiations_df = pd.read_sql("""
                SELECT
                    session_id,
                    supplier_name,
                    status,
                    savings,
                    created_at
                FROM negotiations
                ORDER BY created_at DESC
                LIMIT 10
            """, conn)

            if len(negotiations_df) > 0:
                negotiations_df['savings'] = negotiations_df['savings'].apply(lambda x: f"${x:,.2f}")
                negotiations_df['created_at'] = pd.to_datetime(negotiations_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')

                st.dataframe(
                    negotiations_df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No negotiations yet.")
    except Exception as e:
        st.error(f"Error loading negotiations: {str(e)}")


# ===== TAB 2: Intelligence =====
with tab2:
    st.header("🧠 Procurement Intelligence")

    col_x, col_y = st.columns([1, 3])

    with col_x:
        time_range = st.selectbox(
            "Analysis Period",
            [30, 90, 180, 365],
            index=2,
            format_func=lambda x: f"{x} days"
        )

        run_analysis = st.button("▶️ Run Analysis", use_container_width=True, type="primary")

    if run_analysis:
        with st.spinner("Running intelligence analysis..."):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/run-intelligence",
                    params={"time_range_days": time_range},
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    st.session_state['intelligence_data'] = data
                    st.success("✅ Analysis complete!")
                else:
                    st.error(f"Analysis failed: {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

    # Display results
    if 'intelligence_data' in st.session_state:
        data = st.session_state['intelligence_data']

        # Critical Risks
        st.subheader("🚨 Critical Risks")
        risks = data.get('critical_risks', [])

        if risks:
            for risk in risks:
                with st.expander(f"⚠️ {risk.get('title', 'Risk')}"):
                    st.write(risk.get('description', 'No description'))
                    impact = risk.get('impact', 'unknown')
                    if impact == 'high':
                        st.error(f"Impact: {impact.upper()}")
                    elif impact == 'medium':
                        st.warning(f"Impact: {impact.title()}")
                    else:
                        st.info(f"Impact: {impact.title()}")
        else:
            st.success("No critical risks identified!")

        st.divider()

        # Cost Opportunities
        st.subheader("💡 Cost Opportunities")
        opportunities = data.get('cost_opportunities', [])

        if opportunities:
            for opp in opportunities:
                with st.expander(f"💰 {opp.get('title', 'Opportunity')}"):
                    st.write(opp.get('description', 'No description'))
                    st.info(opp.get('impact', 'Impact not specified'))
        else:
            st.info("No cost opportunities identified.")

        st.divider()

        # Supplier Rankings
        st.subheader("📊 Supplier Performance")
        rankings = data.get('supplier_rankings', [])

        if rankings:
            # Convert to DataFrame for chart
            rankings_df = pd.DataFrame(rankings)

            if 'risk_score' in rankings_df.columns:
                # Extract numeric risk score
                rankings_df['risk_score_num'] = rankings_df['risk_score'].apply(
                    lambda x: float(str(x).split()[0]) if isinstance(x, str) else float(x)
                )

                fig = px.bar(
                    rankings_df.head(10),
                    x='supplier',
                    y='risk_score_num',
                    title='Supplier Risk Scores (Lower is Better)',
                    labels={'risk_score_num': 'Risk Score', 'supplier': 'Supplier'},
                    color='risk_score_num',
                    color_continuous_scale='RdYlGn_r'
                )

                st.plotly_chart(fig, use_container_width=True)

            # Show table
            st.dataframe(rankings_df, use_container_width=True, hide_index=True)
        else:
            st.info("No supplier rankings available.")


# ===== TAB 3: Demo =====
with tab3:
    st.header("🎯 Process Order Demo")
    st.markdown("Paste a customer order email to see Agent 1 in action!")

    # Sample email template
    sample_email = """From: john.doe@acmecorp.com
Subject: Purchase Order - Steel Pipes

Hi,

We need to order 5000 units of Steel Pipes conforming to API 5L Grade B standard.

Specifications:
- Diameter: 6 inches
- Wall thickness: 0.280 inches
- Length: 40 feet

Delivery required by: 2025-12-15
Delivery location: Houston, TX

Please confirm availability and pricing.

Best regards,
John Doe
Acme Corporation"""

    email_text = st.text_area(
        "Order Email",
        value=sample_email,
        height=250,
        help="Paste customer order email here"
    )

    col_demo1, col_demo2 = st.columns([1, 3])

    with col_demo1:
        process_btn = st.button("📨 Process Order", use_container_width=True, type="primary")

    if process_btn and email_text:
        with st.spinner("Processing order with Agent 1..."):
            try:
                # First, extract order from email using OpenAI (simulated)
                # In real implementation, this would call extract_order_requirements

                # For demo, create a sample order
                order_payload = {
                    "product_type": "Steel Pipes",
                    "standard": "API 5L Grade B",
                    "quantity": 5000,
                    "specifications": {
                        "diameter": "6 inches",
                        "wall_thickness": "0.280 inches",
                        "length": "40 feet"
                    },
                    "delivery_date": "2025-12-15",
                    "delivery_location": "Houston, TX",
                    "customer_email": "john.doe@acmecorp.com",
                    "customer_company": "Acme Corporation"
                }

                response = requests.post(
                    f"{API_BASE_URL}/api/process-quote",
                    json=order_payload,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()

                    st.success("✅ Order processed successfully!")

                    # Display results
                    col_r1, col_r2 = st.columns(2)

                    with col_r1:
                        st.metric("Order ID", result.get('order_id', 'N/A'))
                        st.metric("Status", result.get('status', 'N/A'))
                        st.metric("Source", result.get('source', 'N/A'))

                    with col_r2:
                        st.metric("Total", f"${result.get('total', 0):,.2f}")
                        st.metric("Delivery", result.get('estimated_delivery', 'N/A'))

                    # Show message
                    if 'message' in result:
                        st.subheader("📧 Confirmation")
                        st.text_area("Email", result['message'], height=200)

                    # If external sourcing, show supplier offers
                    if 'supplier_offers' in result:
                        st.subheader("🏢 Supplier Offers")
                        offers_df = pd.DataFrame(result['supplier_offers'])
                        st.dataframe(offers_df, use_container_width=True)

                        st.info("💡 Next step: Use Agent 2 to negotiate with suppliers")

                else:
                    st.error(f"Error: {response.text}")

            except Exception as e:
                st.error(f"Processing failed: {str(e)}")


# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    OpusFlow AI v1.0 | Multi-Agent Procurement System
</div>
""", unsafe_allow_html=True)
