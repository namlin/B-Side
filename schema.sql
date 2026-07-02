-- SQLite Database Schema for the B-Side Virtual Store

-- 1. Artists Table
CREATE TABLE IF NOT EXISTS artists (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  genre TEXT
);

-- 2. Products Table
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  artist_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  price REAL NOT NULL,
  stock INTEGER NOT NULL CHECK (stock >= 0),
  FOREIGN KEY (artist_id) REFERENCES artists(id) ON DELETE CASCADE
);

-- 3. Sales Table
CREATE TABLE IF NOT EXISTS sales (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sale_date TEXT DEFAULT CURRENT_TIMESTAMP,
  total REAL NOT NULL
);

-- 4. Sale Items Table
CREATE TABLE IF NOT EXISTS sale_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sale_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  price REAL NOT NULL,
  FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Seed Data (Initial inserts):
INSERT OR IGNORE INTO artists (id, name, genre) VALUES
(1, 'SEATBELTS', 'Bebop'),
(2, 'Gorillaz', 'Alternative'),
(3, 'Machine Girl', 'Breakcore'),
(4, 'Madonna', 'House');

INSERT OR IGNORE INTO products (id, artist_id, name, price, stock) VALUES
(1, 1, 'SEATBELTS - Cowboy Bebop Soundtrack Vinyl', 25.00, 3),
(2, 2, 'Gorillaz - Demon Days Vinyl', 12.50, 3),
(3, 3, 'Machine Girl - Gemini CD', 45.00, 2),
(4, 4, 'Madonna - Drowned World Tour DVD', 35.00, 1);
