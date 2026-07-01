# B-Side - Independent Artist Merchandise POS

This project is about a basic Point of Sale (POS) web system for the virtual store
"B-Side" that sells merchandise of independent musical artists. It fulfills 2 core
use cases:
1. **Register a Product Sale** (reduces stock, logs transaction details).
2. **Consult Available Stock / Inventory** (queries stock, handles database consistency).

The development incorporates quality software engineering practices specified in
the CI-0140 course requirements:
- **Backend:** Python + Flask, clean architecture.
- **Frontend:** HTML, Vanilla JS, Custom CSS via Bootstrap.
- **Database:** Support for MariaDB/MySQL (via database configuration) and SQLite (used by default for testing and local execution without setup).

---

## Proposed Architecture & File Structure:

A clean, single-page application (SPA) design was implemented to ensure a fluid 
and interactive user experience.

```
B-Side/
├── app.py                  # Flask Application & Route Handlers.
├── database.py             # Database Abstraction & SQL Queries.
├── schema.sql              # MariaDB / MySQL DDL Schema script.
├── requirements.txt        # Python Dependencies.
├── package.json            # Node Dependencies (for ESLint).
├── pylintrc                # Pylint configuration.
├── eslint.config.js        # ESLint configuration.
├── static/
│   ├── css/
│   │   └── style.css       # Custom styles (Dark theme, glassmorphism, animations).
│   └── js/
│       └── app.js          # Frontend Logic & API calls (Bootstrap/Fetch API).
├── templates/
│   └── index.html          # HTML Template (Bootstrap Layout).
└── tests/
    └── test_app.py         # Pytest test suite (covers Use Cases and edge cases).
```

---
