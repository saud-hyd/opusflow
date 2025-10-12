# Weaviate vector database seeding script
import sys
import os
import json

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from backend.clients.weaviate_client import client, init_collections

def main():
    """Seed Weaviate with products and suppliers from JSON files."""
    print("=" * 50)
    print("OpusFlow AI - Weaviate Seeding")
    print("=" * 50)

    # Load environment variables
    load_dotenv()
    print("[OK] Environment variables loaded")

    # Initialize collections
    print("\nInitializing Weaviate collections...")
    try:
        result = init_collections()
        print(f"[OK] Collections initialized: {result.get('status')}")
    except Exception as e:
        print(f"[ERROR] Failed to initialize collections: {str(e)}")
        sys.exit(1)

    # Load and insert products
    print("\nLoading products from data/seed/products.json...")
    try:
        with open('data/seed/products.json', 'r') as f:
            products = json.load(f)

        print(f"[OK] Loaded {len(products)} products")

        # Get Product collection
        product_collection = client.collections.get("Product")

        # Insert products
        print("Inserting products into Weaviate...")
        for product in products:
            product_collection.data.insert(
                properties={
                    "name": product["name"],
                    "standard": product["standard"],
                    "specifications": product["specifications"],
                    "in_stock": product["in_stock"],
                    "unit_price": product["unit_price"],
                    "lead_time_days": product["lead_time_days"]
                }
            )

        print(f"[SUCCESS] Inserted {len(products)} products")

    except FileNotFoundError:
        print("[ERROR] products.json not found in data/seed/")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to insert products: {str(e)}")
        sys.exit(1)

    # Load and insert suppliers
    print("\nLoading suppliers from data/seed/suppliers.json...")
    try:
        with open('data/seed/suppliers.json', 'r') as f:
            suppliers = json.load(f)

        print(f"[OK] Loaded {len(suppliers)} suppliers")

        # Get Supplier collection
        supplier_collection = client.collections.get("Supplier")

        # Insert suppliers
        print("Inserting suppliers into Weaviate...")
        for supplier in suppliers:
            supplier_collection.data.insert(
                properties={
                    "name": supplier["name"],
                    "products": supplier["products"],
                    "on_time_rate": supplier["on_time_rate"],
                    "quality_score": supplier["quality_score"],
                    "negotiation_history": supplier["negotiation_history"]
                }
            )

        print(f"[SUCCESS] Inserted {len(suppliers)} suppliers")

    except FileNotFoundError:
        print("[ERROR] suppliers.json not found in data/seed/")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to insert suppliers: {str(e)}")
        sys.exit(1)

    # Summary
    print("\n" + "=" * 50)
    print("[SUCCESS] Weaviate seeding completed successfully!")
    print(f"   Products: {len(products)}")
    print(f"   Suppliers: {len(suppliers)}")
    print("=" * 50)

if __name__ == "__main__":
    main()
