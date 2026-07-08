import os
import sys
import pytest

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)
import database
import database
from app import app

# Set FLASK_ENV to testing before importing database connections
os.environ["FLASK_ENV"] = "testing"

@pytest.fixture(name="client")
def client_fixture():
    """Fixture to set up a test client and clean SQLite database before each test."""
    app.config["TESTING"] = True
    
    # Initialize the test database
    database.init_db(force_recreate=True)
    
    with app.test_client() as client:
        yield client
        
    # Cleanup test database
    db_name = "bside_test.db"
    if os.path.exists(db_name):
        try:
            os.remove(db_name)
        except OSError:
            pass

# ==========================================
# Use Case 2: Consult Stock / Inventory
# ==========================================

def test_get_products_success(client):
    """Test UC-2: Verify product list returns all items and correct properties."""
    response = client.get("/api/products")
    assert response.status_code == 200
    
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 6  # Seed data has 6 products
    
    # Check that a product contains the expected fields
    prod = data[0]
    assert "id" in prod
    assert "name" in prod
    assert "price" in prod
    assert "stock" in prod
    assert "artist_name" in prod
    assert "genre" in prod
    
    # Verify sorting/content is correct
    product_names = [p["name"] for p in data]
    assert "Gravity is a Myth T-Shirt" in product_names

def test_get_products_database_error(client, monkeypatch):
    """Test UC-2: Verify app returns 500 error when database query fails."""
    def mock_get_products():
        raise Exception("Database connection failure")
        
    monkeypatch.setattr(database, "get_products", mock_get_products)
    
    response = client.get("/api/products")
    assert response.status_code == 500
    
    data = response.get_json()
    assert "error" in data
    assert "Error al consultar" in data["error"]


# ==========================================
# Use Case 1: Register Product Sale
# ==========================================

def test_register_sale_success(client):
    """Test UC-1: Verify successful checkout decreases stock and records sale."""
    # Product 1 starts with 50 units (price $25.00)
    # Product 2 starts with 15 units (price $35.00)
    payload = {
        "items": [
            {"product_id": 1, "quantity": 2},
            {"product_id": 2, "quantity": 1}
        ]
    }
    
    response = client.post("/api/sales", json=payload)
    assert response.status_code == 201
    
    data = response.get_json()
    assert "sale" in data
    assert data["message"] == "Venta registrada exitosamente."
    
    sale_data = data["sale"]
    assert sale_data["total"] == 85.00  # (2 * 25) + (1 * 35)
    assert sale_data["items_count"] == 2
    
    # Check that stock decreased
    response_prod = client.get("/api/products")
    products_list = response_prod.get_json()
    
    p1 = next(p for p in products_list if p["id"] == 1)
    p2 = next(p for p in products_list if p["id"] == 2)
    
    assert p1["stock"] == 48  # 50 - 2
    assert p2["stock"] == 14  # 15 - 1

def test_register_sale_insufficient_stock(client):
    """Test UC-1: Verify checkout fails when quantity exceeds available stock."""
    # Product 2 has 15 units
    payload = {
        "items": [
            {"product_id": 2, "quantity": 16}
        ]
    }
    
    response = client.post("/api/sales", json=payload)
    assert response.status_code == 400
    
    data = response.get_json()
    assert "error" in data
    assert "Stock insuficiente" in data["error"]
    
    # Verify stock remained at 15
    response_prod = client.get("/api/products")
    p2 = next(p for p in response_prod.get_json() if p["id"] == 2)
    assert p2["stock"] == 15

def test_register_sale_transaction_rollback(client):
    """Test UC-1: Verify transaction is fully rolled back if one item fails."""
    # Product 1 has 50 units
    # Product 2 has 15 units (requesting 16 should fail checkout)
    payload = {
        "items": [
            {"product_id": 1, "quantity": 5},
            {"product_id": 2, "quantity": 16}
        ]
    }
    
    response = client.post("/api/sales", json=payload)
    assert response.status_code == 400
    
    # Verify Product 1's stock was NOT decremented (rollback of transaction)
    response_prod = client.get("/api/products")
    products_list = response_prod.get_json()
    
    p1 = next(p for p in products_list if p["id"] == 1)
    p2 = next(p for p in products_list if p["id"] == 2)
    
    assert p1["stock"] == 50  # Unchanged
    assert p2["stock"] == 15  # Unchanged

def test_register_sale_invalid_product_id(client):
    """Test UC-1: Verify checkout fails for non-existent product ID."""
    payload = {
        "items": [
            {"product_id": 999, "quantity": 1}
        ]
    }
    
    response = client.post("/api/sales", json=payload)
    assert response.status_code == 400
    
    data = response.get_json()
    assert "error" in data
    assert "not found" in data["error"]

def test_register_sale_invalid_payloads(client):
    """Test UC-1: Verify bad payload inputs are rejected with 400."""
    # 1. Missing items key
    response = client.post("/api/sales", json={})
    assert response.status_code == 400
    
    # 2. Empty items list
    response = client.post("/api/sales", json={"items": []})
    assert response.status_code == 400
    
    # 3. Invalid items type
    response = client.post("/api/sales", json={"items": "not a list"})
    assert response.status_code == 400
    
    # 4. Zero/Negative quantity
    response = client.post("/api/sales", json={"items": [{"product_id": 1, "quantity": 0}]})
    assert response.status_code == 400
    
    response = client.post("/api/sales", json={"items": [{"product_id": 1, "quantity": -5}]})
    assert response.status_code == 400

def test_index_route(client):
    """Test that the index route renders the HTML page."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"B-SIDE" in response.data
    assert b"Merch POS" in response.data

def test_register_sale_internal_server_error(client, monkeypatch):
    """Test UC-1: Verify that server returns 500 when an unexpected DB exception occurs."""
    def mock_register_sale(cart_items):
        raise RuntimeError("Unexpected DB failure")
        
    monkeypatch.setattr(database, "register_sale", mock_register_sale)
    
    payload = {
        "items": [
            {"product_id": 1, "quantity": 1}
        ]
    }
    response = client.post("/api/sales", json=payload)
    assert response.status_code == 500
    
    data = response.get_json()
    assert "error" in data
    assert "Error interno del servidor" in data["error"]
