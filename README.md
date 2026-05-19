# InventoryAI — Inventory Management System

AI-powered inventory management with real-time analytics, demand forecasting (LSTM, XGBoost, Prophet), smart reordering, and risk monitoring.

## Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- MongoDB 6+ running on `localhost:27017`

## Quick Start

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Seed the database (first run only)
uv run python src/database/seed.py

# Launch the app
uv run python main.py
```

## Project Structure

```
inventory_management_system/
├── src/
│   ├── app/
│   │   ├── components/      # Pure, reusable UI widgets
│   │   ├── pages/           # Full-screen page layouts
│   │   ├── services/        # Business logic & DB queries
│   │   └── routes.py        # Navigation & role-based access
│   ├── database/
│   │   ├── mongo_connection.py  # Singleton DB connection
│   │   └── models/          # Data schemas
│   └── utilities/
│       ├── security.py      # Password hashing (bcrypt)
│       ├── chart_utilities.py   # Matplotlib helpers
│       └── math_helpers.py  # Numerical helpers
├── assets/
├── main.py                  # Entry point
└── pyproject.toml           # Dependencies (uv)
```

## Architecture

- **UI Layer** (`components/`, `pages/`): Pure Flet widgets. No business logic.
- **Service Layer** (`services/`): All DB queries and business logic. No Flet imports.
- **Database Layer** (`database/`): Singleton MongoDB connection and schemas.
- **Utilities** (`utilities/`): Stateless helper functions.
