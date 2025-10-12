# Database setup and initialization script
import sys
import os

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from backend.database import init_db

def main():
    """Initialize database tables."""
    print("=" * 50)
    print("OpusFlow AI - Database Setup")
    print("=" * 50)

    # Load environment variables
    load_dotenv()
    print("[OK] Environment variables loaded")

    # Initialize database
    print("\nCreating database tables...")
    try:
        init_db()
        print("\n[SUCCESS] Database setup completed successfully!")
        print("\nTables created:")
        print("  - orders")
        print("  - supplier_offers")
        print("  - negotiations")
        print("  - purchase_orders")
        print("  - historical_deliveries")
        print("  - intelligence_reports")
    except Exception as e:
        print(f"\n[ERROR] Database setup failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
