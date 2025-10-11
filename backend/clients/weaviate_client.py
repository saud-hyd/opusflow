# Weaviate vector database client configuration
import os
from typing import List, Dict, Any
import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import Filter
from dotenv import load_dotenv

load_dotenv()

# Weaviate connection
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize client
client = weaviate.connect_to_local(
    host=WEAVIATE_URL.replace("http://", "").replace("https://", ""),
    headers={"X-OpenAI-Api-Key": OPENAI_API_KEY}
)


def init_collections():
    """
    Create Product and Supplier collections with text2vec-openai vectorizer.
    """
    try:
        # Create Product collection
        if not client.collections.exists("Product"):
            client.collections.create(
                name="Product",
                vectorizer_config=Configure.Vectorizer.text2vec_openai(),
                properties=[
                    Property(name="name", data_type=DataType.TEXT),
                    Property(name="standard", data_type=DataType.TEXT),
                    Property(name="specifications", data_type=DataType.TEXT),
                    Property(name="in_stock", data_type=DataType.INT),
                    Property(name="unit_price", data_type=DataType.NUMBER),
                    Property(name="lead_time_days", data_type=DataType.INT),
                ]
            )
            print("✓ Product collection created")

        # Create Supplier collection
        if not client.collections.exists("Supplier"):
            client.collections.create(
                name="Supplier",
                vectorizer_config=Configure.Vectorizer.text2vec_openai(),
                properties=[
                    Property(name="name", data_type=DataType.TEXT),
                    Property(name="products", data_type=DataType.TEXT_ARRAY),
                    Property(name="on_time_rate", data_type=DataType.NUMBER),
                    Property(name="quality_score", data_type=DataType.NUMBER),
                    Property(name="negotiation_history", data_type=DataType.TEXT),
                ]
            )
            print("✓ Supplier collection created")

        return {"status": "success", "message": "Collections initialized"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


def search_products(query: str, min_stock: int = 0) -> List[Dict[str, Any]]:
    """
    Hybrid search for products with stock filtering.

    Args:
        query: Search query string
        min_stock: Minimum stock level filter

    Returns:
        List of top 5 products with properties
    """
    try:
        products = client.collections.get("Product")

        # Hybrid search with alpha=0.5 (balanced keyword + vector)
        response = products.query.hybrid(
            query=query,
            alpha=0.5,
            limit=5,
            filters=Filter.by_property("in_stock").greater_or_equal(min_stock)
        )

        results = []
        for item in response.objects:
            results.append({
                "name": item.properties.get("name"),
                "standard": item.properties.get("standard"),
                "specifications": item.properties.get("specifications"),
                "in_stock": item.properties.get("in_stock"),
                "unit_price": item.properties.get("unit_price"),
                "lead_time_days": item.properties.get("lead_time_days"),
            })

        return results

    except Exception as e:
        print(f"Error searching products: {e}")
        return []


def search_suppliers(product: str) -> List[Dict[str, Any]]:
    """
    Find suppliers carrying a specific product.

    Args:
        product: Product name to search for

    Returns:
        List of top 5 suppliers with performance data
    """
    try:
        suppliers = client.collections.get("Supplier")

        # Search suppliers that carry this product
        response = suppliers.query.hybrid(
            query=product,
            alpha=0.5,
            limit=5,
            filters=Filter.by_property("products").contains_any([product])
        )

        results = []
        for item in response.objects:
            results.append({
                "name": item.properties.get("name"),
                "products": item.properties.get("products"),
                "on_time_rate": item.properties.get("on_time_rate"),
                "quality_score": item.properties.get("quality_score"),
                "negotiation_history": item.properties.get("negotiation_history"),
            })

        return results

    except Exception as e:
        print(f"Error searching suppliers: {e}")
        return []


def get_supplier_history(supplier_name: str) -> Dict[str, Any]:
    """
    Get specific supplier's history and metrics.

    Args:
        supplier_name: Name of the supplier

    Returns:
        Dict with negotiation patterns and performance metrics
    """
    try:
        suppliers = client.collections.get("Supplier")

        # Get supplier by exact name match
        response = suppliers.query.fetch_objects(
            limit=1,
            filters=Filter.by_property("name").equal(supplier_name)
        )

        if len(response.objects) == 0:
            return {"error": "Supplier not found"}

        supplier = response.objects[0]
        return {
            "name": supplier.properties.get("name"),
            "products": supplier.properties.get("products"),
            "on_time_rate": supplier.properties.get("on_time_rate"),
            "quality_score": supplier.properties.get("quality_score"),
            "negotiation_history": supplier.properties.get("negotiation_history"),
            "avg_delivery_performance": supplier.properties.get("on_time_rate", 0) * 100,
        }

    except Exception as e:
        print(f"Error getting supplier history: {e}")
        return {"error": str(e)}
