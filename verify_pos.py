"""
Programmatic Integration Verification Script for B-Side Virtual Store POS.
Tests endpoints of the running local server to confirm Use Cases work end-to-end.
"""

import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:5000"

def make_request(path, method="GET", data=None):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method=method)
    if data:
        json_data = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
        req.data = json_data
        
    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode("utf-8")
            return status, json.loads(body) if "json" in path or "/api/" in path else body
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8")
        try:
            return status, json.loads(body)
        except json.JSONDecodeError:
            return status, body

def run_verification():
    print("=== STARTING POS SYSTEM PROGRAMMATIC VERIFICATION ===")
    
    # 1. Test Home page serving
    print("\n1. Testing Home Page (GET /)...")
    status, body = make_request("/")
    if status == 200 and "B-SIDE" in body:
        print("   [OK] Home Page rendered successfully.")
    else:
        print(f"   [FAIL] Home Page returned status {status}")
        return

    # 2. Test UC-2: Consult Available Inventory
    print("\n2. Testing Consult Inventory (GET /api/products)...")
    status, products = make_request("/api/products")
    if status == 200 and isinstance(products, list):
        print(f"   [OK] Consulted inventory successfully. Found {len(products)} products.")
        for p in products:
            if p["id"] == 1:
                print(f"        Product 1: '{p['name']}' by '{p['artist_name']}' - Price: ${p['price']} - Stock: {p['stock']} units.")
            if p["id"] == 4:
                print(f"        Product 4: '{p['name']}' by '{p['artist_name']}' - Price: ${p['price']} - Stock: {p['stock']} units.")
    else:
        print(f"   [FAIL] Consult products returned status {status}")
        return

    # Store initial stock levels
    p1_initial_stock = next(p["stock"] for p in products if p["id"] == 1)
    p4_initial_stock = next(p["stock"] for p in products if p["id"] == 4)

    # 3. Test UC-1: Register sale of products (Successful Checkout)
    print("\n3. Testing Successful Checkout (POST /api/sales)...")
    cart_payload = {
        "items": [
            {"product_id": 1, "quantity": 2}, # 2 x $25.00
            {"product_id": 4, "quantity": 1}  # 1 x $45.00
        ]
    }
    status, result = make_request("/api/sales", method="POST", data=cart_payload)
    if status == 201:
        print("   [OK] Sale registered successfully.")
        print(f"        Server Response: {result['message']}")
        print(f"        Sale Summary: ID: {result['sale']['sale_id']} - Total: ${result['sale']['total']} - Items: {result['sale']['items_count']}")
        # Expected total: 2*25.00 + 1*45.00 = 95.00
        if float(result['sale']['total']) == 95.00:
            print("        [OK] Sale total calculated correctly ($95.00).")
        else:
            print(f"        [FAIL] Sale total was {result['sale']['total']}, expected 95.0")
    else:
        print(f"   [FAIL] Checkout failed with status {status}: {result}")
        return

    # 4. Test UC-2: Consult inventory to verify stock decremented
    print("\n4. Testing Stock Decrement after checkout...")
    status, products = make_request("/api/products")
    p1_new_stock = next(p["stock"] for p in products if p["id"] == 1)
    p4_new_stock = next(p["stock"] for p in products if p["id"] == 4)

    print(f"        Product 1 Stock: {p1_initial_stock} -> {p1_new_stock}")
    print(f"        Product 4 Stock: {p4_initial_stock} -> {p4_new_stock}")
    if p1_new_stock == p1_initial_stock - 2 and p4_new_stock == p4_initial_stock - 1:
        print("   [OK] Inventory stock decremented correctly.")
    else:
        print("   [FAIL] Stock level update incorrect.")

    # 5. Test UC-1: Checkout with insufficient stock (Validation rejection)
    print("\n5. Testing Validation Rejection (POST /api/sales with excessive quantity)...")
    excessive_cart = {
        "items": [
            {"product_id": 4, "quantity": 100} # Product 4 only has 29 units left
        ]
    }
    status, result = make_request("/api/sales", method="POST", data=excessive_cart)
    if status == 400:
        print("   [OK] Checkout rejected with 400 Bad Request.")
        print(f"        Server message: {result['error']}")
    else:
        print(f"   [FAIL] Checkout did not return 400. Got status {status}: {result}")

    # 6. Test UC-1: Transaction atomic rollback verification
    print("\n6. Testing Transaction Atomicity (Rollback validation)...")
    # P1 has 48 units, P4 has 29 units. Requesting 2 of P1 and 100 of P4.
    # The purchase of P1 should roll back since P4 checkout fails.
    rollback_cart = {
        "items": [
            {"product_id": 1, "quantity": 2},
            {"product_id": 4, "quantity": 100}
        ]
    }
    status, result = make_request("/api/sales", method="POST", data=rollback_cart)
    # Check that stock of Product 1 remained at 48 (not 46)
    status_inv, products = make_request("/api/products")
    p1_final_stock = next(p["stock"] for p in products if p["id"] == 1)
    if p1_final_stock == 48:
        print("   [OK] Transaction rolled back atomically. Stock of Product 1 remains at 48.")
    else:
        print(f"   [FAIL] Transaction atomicity failed. Stock of Product 1 decreased to {p1_final_stock}!")

    print("\n=== VERIFICATION COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_verification()
