# Database connection and configuration
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://opusflow:opusflow@localhost:5432/opusflow")

# SQLAlchemy setup
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Models
class Order(Base):
    """Customer orders table"""
    __tablename__ = "orders"

    order_id = Column(String, primary_key=True, index=True)
    customer_email = Column(String, nullable=False)
    customer_company = Column(String)
    items = Column(JSON, nullable=False)  # List of items with quantities
    total = Column(Float, nullable=False)
    delivery_date = Column(String)
    source = Column(String)  # e.g., 'email', 'slack', 'api'
    status = Column(String, default='pending')  # pending, processing, completed
    created_at = Column(DateTime, default=datetime.utcnow)


class SupplierOffer(Base):
    """Supplier offers and pricing table"""
    __tablename__ = "supplier_offers"

    offer_id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_name = Column(String, nullable=False, index=True)
    product = Column(String, nullable=False)
    unit_price = Column(Float, nullable=False)
    moq = Column(Integer)  # Minimum Order Quantity
    lead_time_days = Column(Integer)
    status = Column(String, default='active')  # active, expired, superseded
    created_at = Column(DateTime, default=datetime.utcnow)


class Negotiation(Base):
    """AI negotiation sessions table"""
    __tablename__ = "negotiations"

    session_id = Column(String, primary_key=True, index=True)
    supplier_name = Column(String, nullable=False)
    rounds = Column(JSON)  # List of negotiation rounds with messages
    final_terms = Column(JSON)  # Final agreed terms
    status = Column(String, default='in_progress')  # in_progress, completed, failed
    savings = Column(Float, default=0.0)  # Cost savings achieved
    created_at = Column(DateTime, default=datetime.utcnow)


class PurchaseOrder(Base):
    """Purchase orders sent to suppliers table"""
    __tablename__ = "purchase_orders"

    po_id = Column(String, primary_key=True, index=True)
    supplier_name = Column(String, nullable=False)
    items = Column(JSON, nullable=False)  # Items and quantities
    total = Column(Float, nullable=False)
    linked_customer_order_id = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class HistoricalDelivery(Base):
    """Historical delivery performance table"""
    __tablename__ = "historical_deliveries"

    delivery_id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_name = Column(String, nullable=False, index=True)
    promised_date = Column(String, nullable=False)
    actual_delivery_date = Column(String, nullable=False)
    delay_days = Column(Integer, default=0)
    quality_score = Column(Float)  # 0-10 scale


class IntelligenceReport(Base):
    """AI-generated intelligence reports table"""
    __tablename__ = "intelligence_reports"

    report_id = Column(Integer, primary_key=True, autoincrement=True)
    critical_risks = Column(JSON)  # List of identified risks
    cost_opportunities = Column(JSON)  # Cost saving opportunities
    supplier_rankings = Column(JSON)  # Supplier performance rankings
    generated_at = Column(DateTime, default=datetime.utcnow)


# Database initialization
def init_db():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


# FastAPI dependency
def get_db():
    """
    FastAPI dependency to get database session.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
