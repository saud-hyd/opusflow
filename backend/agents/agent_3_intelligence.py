# Agent 3: Intelligence Agent
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
import pandas as pd

from backend.database import HistoricalDelivery, IntelligenceReport, SupplierOffer
from backend.clients.openai_client import synthesize_intelligence_insights


async def run_intelligence_analysis(time_range_days: int, db: Session) -> Dict[str, Any]:
    """
    Run comprehensive intelligence analysis on procurement data.

    Args:
        time_range_days: Number of days to analyze
        db: Database session

    Returns:
        IntelligenceResponse dict with risks, opportunities, rankings
    """

    # Step 1: Query database for historical deliveries
    cutoff_date = datetime.utcnow() - timedelta(days=time_range_days)

    deliveries = db.query(HistoricalDelivery).all()

    def parse_date(date_str: Any):
        if not date_str:
            return None
        try:
            return datetime.strptime(str(date_str), "%Y-%m-%d")
        except ValueError:
            return None

    deliveries = [
        d for d in deliveries
        if (parsed := parse_date(d.promised_date)) and parsed >= cutoff_date
    ]

    # Convert to pandas DataFrame
    if len(deliveries) == 0:
        # No data - return empty analysis
        return {
            "critical_risks": [{"title": "No Data", "description": "No historical delivery data available", "impact": "high"}],
            "cost_opportunities": [],
            "supplier_rankings": [],
            "generated_at": datetime.utcnow()
        }

    # Load into DataFrame
    delivery_data = []
    for d in deliveries:
        delivery_data.append({
            "supplier_name": d.supplier_name,
            "promised_date": d.promised_date,
            "actual_delivery_date": d.actual_delivery_date,
            "delay_days": d.delay_days,
            "quality_score": d.quality_score if d.quality_score else 7.0
        })

    df = pd.DataFrame(delivery_data)

    # Step 2: Supplier analysis
    supplier_metrics = df.groupby('supplier_name').agg({
        'delay_days': ['mean', 'std', 'count'],
        'quality_score': 'mean'
    }).reset_index()

    supplier_metrics.columns = ['supplier_name', 'avg_delay', 'delay_std', 'delivery_count', 'avg_quality']

    # Calculate on-time rate (deliveries with delay <= 0)
    on_time_counts = df[df['delay_days'] <= 0].groupby('supplier_name').size().reset_index(name='on_time_count')
    supplier_metrics = supplier_metrics.merge(on_time_counts, on='supplier_name', how='left')
    supplier_metrics['on_time_count'] = supplier_metrics['on_time_count'].fillna(0)
    supplier_metrics['on_time_rate'] = supplier_metrics['on_time_count'] / supplier_metrics['delivery_count']

    # Calculate risk score: (1 - on_time_rate) * 60 + (10 - avg_quality) * 4
    supplier_metrics['risk_score'] = (1 - supplier_metrics['on_time_rate']) * 60 + (10 - supplier_metrics['avg_quality']) * 4

    # Flag high risk suppliers
    high_risk_suppliers = supplier_metrics[supplier_metrics['risk_score'] > 50]

    # Step 3: Material trends analysis
    # Get supplier offers to analyze materials
    supplier_offers = [
        offer for offer in db.query(SupplierOffer).all()
        if offer.created_at and offer.created_at >= cutoff_date
    ]

    material_data = []
    for offer in supplier_offers:
        material_data.append({
            "product": offer.product,
            "supplier": offer.supplier_name,
            "lead_time_days": offer.lead_time_days,
            "unit_price": offer.unit_price,
            "created_at": offer.created_at
        })

    bottlenecks = []
    consolidation_opportunities = []

    if len(material_data) > 0:
        materials_df = pd.DataFrame(material_data)

        # Group by product to detect bottlenecks
        material_summary = materials_df.groupby('product').agg({
            'lead_time_days': 'mean',
            'unit_price': 'mean',
            'supplier': 'count'
        }).reset_index()
        material_summary.columns = ['product', 'avg_lead_time', 'avg_price', 'supplier_count']

        # Detect bottlenecks (long lead times)
        bottlenecks = material_summary[material_summary['avg_lead_time'] > 45].to_dict('records')

        # Step 4: Cost opportunities - products with multiple suppliers
        multi_supplier_products = material_summary[material_summary['supplier_count'] > 1]

        for _, row in multi_supplier_products.iterrows():
            product = row['product']
            suppliers = materials_df[materials_df['product'] == product]
            price_range = suppliers['unit_price'].max() - suppliers['unit_price'].min()

            if price_range > 0:
                potential_savings = price_range * 1000  # Assume 1000 units
                consolidation_opportunities.append({
                    "product": product,
                    "supplier_count": int(row['supplier_count']),
                    "price_range": float(price_range),
                    "potential_savings": float(potential_savings),
                    "recommendation": f"Consolidate purchases of {product} with lowest-cost supplier"
                })

    # Prepare metrics for OpenAI synthesis
    metrics = {
        "supplier_performance": supplier_metrics.to_dict('records'),
        "high_risk_suppliers": high_risk_suppliers.to_dict('records'),
        "bottleneck_materials": bottlenecks,
        "consolidation_opportunities": consolidation_opportunities,
        "time_range_days": time_range_days,
        "total_deliveries": len(df),
        "analysis_date": datetime.utcnow().isoformat()
    }

    # Step 5: Use OpenAI to synthesize insights
    ai_insights = synthesize_intelligence_insights(metrics)

    # Extract insights
    critical_risks = ai_insights.get("critical_risks", [])
    cost_opportunities = ai_insights.get("cost_opportunities", [])
    supplier_rankings = ai_insights.get("supplier_rankings", [])

    # Add computed data to risks if high-risk suppliers found
    if len(high_risk_suppliers) > 0:
        for _, supplier in high_risk_suppliers.iterrows():
            critical_risks.append({
                "title": f"High Risk Supplier: {supplier['supplier_name']}",
                "description": f"On-time rate: {supplier['on_time_rate']:.1%}, Avg delay: {supplier['avg_delay']:.1f} days, Quality: {supplier['avg_quality']:.1f}/10",
                "impact": "high" if supplier['risk_score'] > 70 else "medium"
            })

    # Add consolidation opportunities to cost_opportunities
    for opp in consolidation_opportunities:
        cost_opportunities.append({
            "title": f"Consolidate {opp['product']} Purchases",
            "description": f"{opp['supplier_count']} suppliers with ${opp['price_range']:.2f} price difference",
            "impact": f"Potential savings: ${opp['potential_savings']:.2f}",
            "savings_estimate": opp['potential_savings']
        })

    # Create supplier rankings from metrics
    ranked_suppliers = supplier_metrics.sort_values('risk_score').head(10)
    for _, supplier in ranked_suppliers.iterrows():
        supplier_rankings.append({
            "rank": len(supplier_rankings) + 1,
            "supplier": supplier['supplier_name'],
            "on_time_rate": f"{supplier['on_time_rate']:.1%}",
            "avg_quality": f"{supplier['avg_quality']:.1f}/10",
            "risk_score": f"{supplier['risk_score']:.1f}",
            "performance": "Excellent" if supplier['risk_score'] < 20 else "Good" if supplier['risk_score'] < 40 else "Fair"
        })

    # Step 6: Save to intelligence_reports table
    report = IntelligenceReport(
        critical_risks=critical_risks,
        cost_opportunities=cost_opportunities,
        supplier_rankings=supplier_rankings,
        generated_at=datetime.utcnow()
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Step 7: Return IntelligenceResponse
    return {
        "critical_risks": critical_risks,
        "cost_opportunities": cost_opportunities,
        "supplier_rankings": supplier_rankings,
        "generated_at": datetime.utcnow(),
        "report_id": report.report_id
    }
