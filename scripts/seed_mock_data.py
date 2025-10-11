# Mock data seeding script for development
import sys
import os
from datetime import datetime, timedelta
import random

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from backend.database import HistoricalDelivery

def main():
    """Generate and insert mock historical delivery data."""
    print("=" * 50)
    print("OpusFlow AI - Mock Data Seeding")
    print("=" * 50)

    # Load environment variables
    load_dotenv()
    print("✓ Environment variables loaded")

    # Database connection
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://opusflow:opusflow@localhost:5432/opusflow")
    print(f"✓ Connecting to database...")

    try:
        engine = create_engine(DATABASE_URL)
        print("✓ Database connection established")
    except Exception as e:
        print(f"❌ Failed to connect to database: {str(e)}")
        sys.exit(1)

    # Generate historical delivery data
    print("\nGenerating 200 historical delivery records...")

    suppliers = [
        {"name": "Schmidt Steel GmbH", "on_time_rate": 0.98, "quality_score": 9.5},
        {"name": "Hoffmann Steel Industries", "on_time_rate": 0.94, "quality_score": 9.0},
        {"name": "Stahlwerk Munich AG", "on_time_rate": 0.89, "quality_score": 8.3},
        {"name": "Mueller Industries KG", "on_time_rate": 0.45, "quality_score": 7.2}
    ]

    delivery_records = []

    # Generate 200 records over the past 180 days
    for i in range(200):
        # Random supplier weighted by quality
        supplier = random.choices(
            suppliers,
            weights=[0.35, 0.30, 0.25, 0.10],  # Schmidt gets most orders
            k=1
        )[0]

        # Generate dates
        days_ago = random.randint(1, 180)
        promised_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

        # Determine if delivery was on time based on supplier's on_time_rate
        is_on_time = random.random() < supplier["on_time_rate"]

        if is_on_time:
            # On time or early
            delay_days = random.randint(-2, 0)  # Could be up to 2 days early
        else:
            # Late - severity depends on supplier reliability
            if supplier["on_time_rate"] > 0.90:
                delay_days = random.randint(1, 5)  # Minor delays
            elif supplier["on_time_rate"] > 0.80:
                delay_days = random.randint(1, 10)  # Moderate delays
            else:
                delay_days = random.randint(5, 30)  # Major delays

        actual_delivery_date = (
            datetime.strptime(promised_date, "%Y-%m-%d") + timedelta(days=delay_days)
        ).strftime("%Y-%m-%d")

        # Quality score with some variance
        quality_score = min(10.0, max(5.0,
            supplier["quality_score"] + random.uniform(-0.5, 0.5)
        ))

        delivery_records.append({
            "supplier_name": supplier["name"],
            "promised_date": promised_date,
            "actual_delivery_date": actual_delivery_date,
            "delay_days": delay_days,
            "quality_score": round(quality_score, 1)
        })

    # Convert to DataFrame
    df = pd.DataFrame(delivery_records)

    print(f"✓ Generated {len(df)} delivery records")
    print(f"\nDistribution by supplier:")
    print(df['supplier_name'].value_counts())

    # Insert into database
    print(f"\nInserting records into historical_deliveries table...")
    try:
        df.to_sql(
            'historical_deliveries',
            engine,
            if_exists='append',
            index=False,
            method='multi'
        )
        print(f"✅ Inserted {len(df)} records successfully")

    except Exception as e:
        print(f"❌ Failed to insert records: {str(e)}")
        sys.exit(1)

    # Summary statistics
    print("\n" + "=" * 50)
    print("Summary Statistics:")
    print("=" * 50)

    for supplier in suppliers:
        supplier_data = df[df['supplier_name'] == supplier['name']]
        if len(supplier_data) > 0:
            on_time = len(supplier_data[supplier_data['delay_days'] <= 0])
            on_time_pct = (on_time / len(supplier_data)) * 100
            avg_delay = supplier_data['delay_days'].mean()
            avg_quality = supplier_data['quality_score'].mean()

            print(f"\n{supplier['name']}:")
            print(f"  Deliveries: {len(supplier_data)}")
            print(f"  On-time rate: {on_time_pct:.1f}%")
            print(f"  Avg delay: {avg_delay:.1f} days")
            print(f"  Avg quality: {avg_quality:.1f}/10")

    print("\n" + "=" * 50)
    print("✅ Mock data seeding completed successfully!")
    print("=" * 50)

if __name__ == "__main__":
    main()
