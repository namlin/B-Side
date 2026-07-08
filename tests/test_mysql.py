import os
import sys
import unittest.mock as mock
import pytest
import pymysql

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)
import database

# Set FLASK_ENV to testing
os.environ["FLASK_ENV"] = "testing"

def test_is_mysql_db():
    """Test is_mysql_db detects mysql and mariadb schemes."""
    # Temporarily override DATABASE_URL module variable
    original_url = database.DATABASE_URL
    try:
        database.DATABASE_URL = "mysql://user:pass@localhost/db"
        assert database.is_mysql_db() is True
        
        database.DATABASE_URL = "mariadb://user:pass@localhost/db"
        assert database.is_mysql_db() is True
        
        database.DATABASE_URL = ""
        assert database.is_mysql_db() is False
    finally:
        database.DATABASE_URL = original_url

def test_execute_query_mysql_placeholder():
    """Test that execute_query translates ? to %s for MySQL queries."""
    original_url = database.DATABASE_URL
    database.DATABASE_URL = "mysql://user:pass@localhost/db"
    try:
        mock_cursor = mock.MagicMock()
        query = "SELECT * FROM products WHERE id = ? AND stock > ?"
        params = (1, 5)
        
        database.execute_query(mock_cursor, query, params)
        
        # Verify query was rewritten and execute was called
        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM products WHERE id = %s AND stock > %s", 
            params
        )
    finally:
        database.DATABASE_URL = original_url

def test_mysql_database_connection(monkeypatch):
    """Test MySQL connection initialization and context management."""
    original_url = database.DATABASE_URL
    database.DATABASE_URL = "mysql://testuser:testpass@testhost:3307/testdb"
    
    mock_connect = mock.MagicMock()
    monkeypatch.setattr(pymysql, "connect", mock_connect)
    
    try:
        with database.DatabaseConnection() as conn:
            assert conn is mock_connect.return_value
            
        # Verify pymysql.connect parameters were correctly parsed
        mock_connect.assert_called_once_with(
            host="testhost",
            port=3307,
            user="testuser",
            password="testpass",
            database="testdb",
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        # Verify commit and close on success
        conn.commit.assert_called_once()
        conn.close.assert_called_once()
    finally:
        database.DATABASE_URL = original_url

def test_mysql_database_connection_error(monkeypatch):
    """Test MySQL rollback is called when an exception is raised inside the context."""
    original_url = database.DATABASE_URL
    database.DATABASE_URL = "mysql://testuser:testpass@testhost:3306/testdb"
    
    mock_connect = mock.MagicMock()
    monkeypatch.setattr(pymysql, "connect", mock_connect)
    
    try:
        with pytest.raises(RuntimeError):
            with database.DatabaseConnection() as conn:
                raise RuntimeError("Db error")
                
        # Verify rollback and close on error
        mock_connect.return_value.rollback.assert_called_once()
        mock_connect.return_value.close.assert_called_once()
    finally:
        database.DATABASE_URL = original_url

def test_mysql_init_db(monkeypatch):
    """Test MySQL database creation and schema initialization logic."""
    original_url = database.DATABASE_URL
    database.DATABASE_URL = "mysql://testuser:testpass@testhost:3306/testdb"
    
    mock_connect = mock.MagicMock()
    mock_cursor = mock_connect.return_value.cursor.return_value.__enter__.return_value
    monkeypatch.setattr(pymysql, "connect", mock_connect)
    
    # Mock DatabaseConnection context manager
    mock_db_conn = mock.MagicMock()
    mock_db_cursor = mock_db_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
    monkeypatch.setattr(database, "DatabaseConnection", mock_db_conn)
    
    try:
        database.init_db(force_recreate=True)
        
        # Verify server connection to create database
        mock_connect.assert_called_once_with(
            host="testhost",
            port=3306,
            user="testuser",
            password="testpass",
            autocommit=True
        )
        # Verify dropping and creating the DB
        mock_cursor.execute.assert_any_call("DROP DATABASE IF EXISTS testdb;")
        mock_cursor.execute.assert_any_call("CREATE DATABASE IF NOT EXISTS testdb;")
        
        # Verify loading schemas
        assert mock_db_cursor.execute.call_count > 0
    finally:
        database.DATABASE_URL = original_url

def test_mysql_register_sale_success(monkeypatch):
    """Test register_sale uses MySQL-specific row parsing and insert ID lookup."""
    original_url = database.DATABASE_URL
    database.DATABASE_URL = "mysql://testuser:testpass@testhost:3306/testdb"
    
    # Mock connection, cursor, and execute
    mock_conn = mock.MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    
    # Mock fetchone to return products as dicts (like PyMySQL does)
    mock_cursor.fetchone.return_value = {
        "name": "Test Vinyl",
        "price": 30.00,
        "stock": 10
    }
    mock_conn.insert_id.return_value = 42  # Mocked sale ID
    
    # Setup DatabaseConnection to return our mock connection
    mock_db_conn_cm = mock.MagicMock()
    mock_db_conn_cm.__enter__.return_value = mock_conn
    monkeypatch.setattr(database, "DatabaseConnection", lambda: mock_db_conn_cm)
    
    try:
        cart = [{"product_id": 3, "quantity": 2}]
        result = database.register_sale(cart)
        
        assert result == {
            "sale_id": 42,
            "total": 60.00,
            "items_count": 1
        }
        
        # Verify update call
        mock_cursor.execute.assert_any_call(
            "UPDATE products SET stock = stock - %s WHERE id = %s",
            (2, 3)
        )
        # Verify sale items insert call
        mock_cursor.execute.assert_any_call(
            "INSERT INTO sale_items (sale_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
            (42, 3, 2, 30.00)
        )
    finally:
        database.DATABASE_URL = original_url
