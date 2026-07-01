"""
Database management module for B-Side Virtual Store POS.
Handles SQLite and MariaDB connections, schemas initialization,
and core transaction operations (stock query and sale registration).
"""

import os
import sqlite3
from urllib.parse import urlparse
import pymysql
import pymysql.cursors

# Get database connection URL from environment or default to SQLite:
DATABASE_URL = os.environ.get("DATABASE_URL", "")

def is_mysql_db():
    """Returns True if MariaDB/MySQL connection URL is provided."""
    return DATABASE_URL.startswith("mysql://") or DATABASE_URL.startswith("mariadb://")

class DatabaseConnection:
    """Context manager for handling DB connection and automatic commit/rollback."""
    def __init__(self):
        self.conn = None
        self.is_mysql = is_mysql_db()

    def __enter__(self):
        if self.is_mysql:
            # Parse connection URL: mysql://user:password@host:port/dbname
            url = urlparse(DATABASE_URL)
            db_name = url.path.lstrip('/')
            port = url.port or 3306
            self.conn = pymysql.connect(
                host=url.hostname,
                port=port,
                user=url.username,
                password=url.password,
                database=db_name,
                autocommit=False,
                cursorclass=pymysql.cursors.DictCursor
            )

        else:
            # SQLite connection
            db_name = "bside_test.db" if os.environ.get("FLASK_ENV") == "testing" else "bside.db"
            self.conn = sqlite3.connect(db_name)
            self.conn.row_factory = sqlite3.Row
            # Enable foreign keys in SQLite
            self.conn.execute("PRAGMA foreign_keys = ON;")

        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            try:
                if exc_type is not None:
                    # An exception occurred, rollback transaction
                    self.conn.rollback()

                else:
                    self.conn.commit()

            finally:
                self.conn.close()

def execute_query(cursor, query, params=None):
    """Executes a query, dynamically adapting placeholder formats for SQLite/MariaDB."""
    if is_mysql_db():
        query = query.replace('?', '%s')

    cursor.execute(query, params or ())

    return cursor

# pylint: disable=too-many-locals,too-many-branches

def init_db(force_recreate=False):
    """Initializes the database schema and inserts seed data if tables do not exist."""
    is_mysql = is_mysql_db()

    # Read schema SQL:
    schema_file = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # Clean comments line by line to prevent block skips
    lines = []

    for line in schema_sql.split('\n'):
        stripped = line.strip()

        if stripped and not stripped.startswith('--'):
            lines.append(line)

    schema_clean = '\n'.join(lines)

    # If it is SQLite, we execute the commands. Since sqlite3.connect().executescript()
    # can run multiple commands, we use that.
    # For MySQL/MariaDB we parse command by command or run them one by one.
    if is_mysql:
        # Connect to MariaDB (without selecting a DB initially to create it)
        url = urlparse(DATABASE_URL)
        db_name = url.path.lstrip('/')
        port = url.port or 3306

        # Connect to MySQL server to ensure DB exists
        conn = pymysql.connect(
            host=url.hostname,
            port=port,
            user=url.username,
            password=url.password,
            autocommit=True
        )

        try:
            with conn.cursor() as cursor:
                if force_recreate:
                    cursor.execute(f"DROP DATABASE IF EXISTS {db_name};")

                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name};")

        finally:
            conn.close()

        # Connect to the database and run schema commands
        with DatabaseConnection() as conn:
            with conn.cursor() as cursor:
                # Split commands by semicolon, ignoring comments and empty lines
                commands = schema_clean.split(';')

                for cmd in commands:
                    clean_cmd = cmd.strip()

                    if not clean_cmd:
                        continue

                    # Remove database creation from script block to prevent conflicts
                    if "CREATE DATABASE" in clean_cmd.upper() or "USE " in clean_cmd.upper():
                        continue

                    cursor.execute(clean_cmd)

    else:
        # SQLite
        db_name = "bside_test.db" if os.environ.get("FLASK_ENV") == "testing" else "bside.db"

        if force_recreate and os.path.exists(db_name):
            os.remove(db_name)

        with DatabaseConnection() as conn:
            # We split the SQL script to remove MariaDB-specific commands like CREATE DATABASE
            commands = []

            for cmd in schema_clean.split(';'):
                clean_cmd = cmd.strip()

                if not clean_cmd:
                    continue

                # Skip MySQL specific commands
                if any(x in clean_cmd.upper() for x in ["CREATE DATABASE", "USE "]):
                    continue

                # Adapt for SQLite (AUTO_INCREMENT -> INTEGER PRIMARY KEY)
                clean_cmd = clean_cmd.replace(
                    "INT AUTO_INCREMENT PRIMARY KEY",
                    "INTEGER PRIMARY KEY"
                )

                clean_cmd = clean_cmd.replace("INSERT IGNORE", "INSERT OR IGNORE")
                commands.append(clean_cmd)

            # Execute queries
            for cmd in commands:
                conn.execute(cmd)


def get_products():
    """UC-2: Consult available inventory/stock."""
    query = """
        SELECT p.id, p.name, p.price, p.stock, a.name AS artist_name, a.genre
        FROM products p
        JOIN artists a ON p.artist_id = a.id
        ORDER BY p.name ASC;
    """

    with DatabaseConnection() as conn:
        cursor = conn.cursor()

        try:
            execute_query(cursor, query)
            rows = cursor.fetchall()

            # Normalize list of rows (sqlite3 uses Row objects, PyMySQL uses dicts)
            products = []

            for row in rows:
                if isinstance(row, dict):
                    products.append(row)

                else:

                    # SQLite Row conversion
                    products.append({
                        "id": row[0],
                        "name": row[1],
                        "price": float(row[2]),
                        "stock": row[3],
                        "artist_name": row[4],
                        "genre": row[5]
                    })

            return products

        finally:
            cursor.close()


class OutOfStockError(Exception):
    """Custom exception raised when product stock is insufficient."""

# pylint: disable=too-many-locals

def register_sale(cart_items):
    """
    UC-1: Register sale of products.
    cart_items: list of dicts with keys "product_id" and "quantity".
    """
    if not cart_items:
        raise ValueError("Cart is empty.")

    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        try:
            total_sale = 0.0
            sale_details = []

            # Step 1: Validate and decrement stock for all items
            for item in cart_items:
                product_id = int(item["product_id"])
                quantity = int(item["quantity"])

                if quantity <= 0:
                    raise ValueError("Quantity must be greater than zero.")

                # Fetch stock and price
                q_stock = "SELECT name, price, stock FROM products WHERE id = ?"
                execute_query(cursor, q_stock, (product_id,))
                prod = cursor.fetchone()

                if not prod:
                    raise ValueError(f"Product ID {product_id} not found.")

                # Normalize product row access
                if isinstance(prod, dict):
                    prod_name = prod["name"]
                    prod_price = float(prod["price"])
                    prod_stock = prod["stock"]

                else:
                    prod_name = prod[0]
                    prod_price = float(prod[1])
                    prod_stock = prod[2]

                if prod_stock < quantity:
                    raise OutOfStockError(
                        f"Stock insuficiente para '{prod_name}'. "
                        f"Disponible: {prod_stock}, Solicitado: {quantity}"
                    )

                # Deduct stock
                q_update = "UPDATE products SET stock = stock - ? WHERE id = ?"
                execute_query(cursor, q_update, (quantity, product_id))

                item_total = prod_price * quantity
                total_sale += item_total

                sale_details.append({
                    "product_id": product_id,
                    "quantity": quantity,
                    "price": prod_price
                })

            # Step 2: Insert sale header
            q_sale = "INSERT INTO sales (total) VALUES (?)"
            execute_query(cursor, q_sale, (total_sale,))

            # Get ID of the inserted sale
            if is_mysql_db():
                sale_id = conn.insert_id()

            else:
                sale_id = cursor.lastrowid

            # Step 3: Insert sale details
            q_item = (
                "INSERT INTO sale_items (sale_id, product_id, quantity, price) "
                "VALUES (?, ?, ?, ?)"
            )

            for detail in sale_details:
                execute_query(cursor, q_item, (
                    sale_id,
                    detail["product_id"],
                    detail["quantity"],
                    detail["price"]
                ))

            return {
                "sale_id": sale_id,
                "total": total_sale,
                "items_count": len(sale_details)
            }

        finally:
            cursor.close()
