"""
Flask Web Application Entry Point for B-Side Virtual Store POS.
Handles HTTP endpoints, renders template index, and delegates database calls.
"""

import os
from flask import Flask, jsonify, request, render_template
import database

app = Flask(__name__, template_folder="templates", static_folder="static")

# Initialise database when application starts.
# We do not call this when testing to allow tests to control database setups
if os.environ.get("FLASK_ENV") != "testing":
    try:
        database.init_db()

    except Exception as e:  # pylint: disable=broad-exception-caught
        app.logger.error("Error initializing the database: %s", e)

@app.route("/")
def index():
    """Serve the main application page."""
    return render_template("index.html")

@app.route("/api/products", methods=["GET"])
def get_products():
    """API endpoint to check available stock / inventory (UC-2):"""
    try:
        products = database.get_products()
        return jsonify(products), 200

    except Exception as e:  # pylint: disable=broad-exception-caught
        app.logger.error("Error fetching products: %s", e)
    return jsonify({"error": "Error while quering the stock."}), 500

# pylint: disable=too-many-return-statements
@app.route("/api/sales", methods=["POST"])
def register_sale():
    """API endpoint to register product sales (UC-1):"""
    data = request.get_json()

    if not data or "items" not in data:
        err_msg = "Invalid request. A list of products is required in 'items'."
        return jsonify({"error": err_msg}), 400

    items = data["items"]

    if not isinstance(items, list):
        return jsonify({"error": "The 'items' field must be a list."}), 400

    if not items:
        return jsonify({"error": "The shopping cart can't be empty."}), 400

    try:
        sale_result = database.register_sale(items)
        return jsonify({
            "message": "Sale registered succesfully.",
            "sale": sale_result
        }), 201

    except database.OutOfStockError as e:
        return jsonify({"error": str(e)}), 400

    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    except Exception as e:  # pylint: disable=broad-exception-caught
        app.logger.error("Error registering sale: %s", e)
        return jsonify({"error": "Internal server error while registering the sale."}), 500

if __name__ == "__main__":
    # Get port from the environment or default to 5000:
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
