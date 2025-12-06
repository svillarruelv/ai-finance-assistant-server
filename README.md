# Backend - AI Finance Assistant

## 🚀 Quick Start

Get the project running in 3 steps:

```bash
# 1. Start the containers
docker compose up --build -d

# 2. Apply database migrations
docker exec finance-server alembic upgrade head

# 3. Seed the database with sample data
docker exec finance-server python scripts/db_seed.py
```

The API will be available at: **http://localhost:8000**

- Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

---

## 🔌 API Endpoints

### 🏦 Bank Offers (`/api/v1/offers`)
- **GET** `/eligibility/{customer_id}`
  - Checks if a customer is eligible for consolidation offers based on credit score and past due status.
- **GET** `/simulation/{customer_id}`
  - Runs comprehensive consolidation simulations.
  - **Standard**: Consolidates eligible debts at the offer rate/term.
  - **Optimized**: Uses customer's max cash flow to pay down the consolidated loan faster.

### 💳 Simulations (`/api/v1/simulations`)
- **GET** `/cards/{customer_id}`
  - Simulates paying off credit cards using specific monthly payments or minimums.
- **GET** `/loans/{customer_id}`
  - Simulates loan amortization schedules.

### 📉 Strategies (`/api/v1/strategies`)
- **GET** `/strategies/{customer_id}`
  - Generates **Avalanche** (Highest Interest First) and **Snowball** (Lowest Balance First) payoff plans.
  - Compares results under "Base" and "Conservative" income scenarios.

### 💓 Health
- **GET** `/api/v1/health`
  - Service health check.

---

## 🧠 Services & Business Logic

Core business logic is encapsulated in `app/services/`:

| Service | Description |
|---------|-------------|
| **`consolidation.py`** | **OFFER ENGINE**: Handles filtering debts, checking offer constraints (balance limits), and running "Standard" vs "Optimized" consolidation scenarios. |
| **`strategy_simulation.py`** | **PAYOFF ALGORITHMS**: Implements `Avalanche` and `Snowball` logic. Handles detailed month-by-month payment allocation across multiple debts. |
| **`loan_simulation.py`** | **AMORTIZATION**: Calculates PMT (Monthly Payment), interest schedules, and prepayment impacts for fixed-term loans. |
| **`card_simulation.py`** | **REVOLVING CREDIT**: Simulates credit card payoffs based on minimum payment percentages or fixed payments. |
| **`offers.py`** | **ELIGIBILITY RULES**: Validates customer eligibility for bank offers (Credit Score > Min, DPD < Max). |

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| **FastAPI** | REST API framework |
| **Python 3.12** | Runtime |
| **uv** | Package management |
| **PostgreSQL** | Database |
| **SQLAlchemy 2.0** | Async ORM |
| **Alembic** | Database migrations |
| **Pydantic** | Data validation |
| **Docker** | Containerization |

## 📁 Project Structure

```
server/
├── app/
│   ├── api/          # API endpoints
│   │   └── v1/
│   │       ├── endpoints/  # Route handlers
│   │       └── router.py   # API router aggregator
│   ├── core/         # Base classes, DB config, exceptions
│   ├── mock/         # Sample data (CSV/JSON)
│   ├── models/       # SQLAlchemy ORM models
│   ├── schemas/      # Pydantic schemas
│   └── services/     # Business logic
├── alembic/          # Database migrations
│   ├── versions/     # Migration files
│   └── env.py        # Alembic configuration
├── Dockerfile
└── docker-compose.yml
```

## 💻 Local Development

1. **Navigate to the server directory:**
   ```bash
   cd server
   ```

2. **Activate environment:**
   ```bash
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   uv sync
   ```

4. **Run the application:**
   ```bash
   python run.py
   # or
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## 🐳 Docker

To run the server with Docker Compose:

```bash
docker compose up -d
```

To view logs:
```bash
docker compose logs -f
```

---

## 🗃️ Database Migrations

Migrations are managed using **Alembic** and should be run inside the Docker container to ensure connectivity to the database.

### Generate a New Migration

After modifying models in `app/models/`, generate a new migration:

```bash
docker exec finance-server alembic revision --autogenerate -m "description_of_changes"
```

### Apply Migrations

Run all pending migrations:

```bash
docker exec finance-server alembic upgrade head
```

### Rollback Last Migration

```bash
docker exec finance-server alembic downgrade -1
```

### View Migration History

```bash
docker exec finance-server alembic history
```

---

## 🌱 Database Seeding

Populate the database with sample data from `app/mock/` files.

### Run the Seeder

```bash
docker exec finance-server python scripts/db_seed.py
```

The seeder is **idempotent** - running it multiple times will skip existing records.

### Mock Data Files

| File | Description |
|------|-------------|
| `customer_cashflow.csv` | Customer financial profiles |
| `loans.csv` | Loan products |
| `cards.csv` | Credit card products |
| `payments_history.csv` | Payment transactions |
| `credit_score_history.csv` | Credit score records |
| `bank_offers.json` | Consolidation offers |

---

## 📊 Entity Relationship Diagram

The database uses **Joined Table Inheritance** for the Product hierarchy (Loan, Card extend Product).

```mermaid
erDiagram
    customers ||--o{ products : "has"
    customers ||--o{ payments : "makes"
    customers ||--o{ credit_score_history : "has"
    products ||--o{ payments : "receives"
    products ||--|| loans : "is a"
    products ||--|| cards : "is a"

    customers {
        uuid id PK
        string external_id UK "e.g. CU-001"
        decimal monthly_income_avg "Numeric(12,2)"
        decimal income_variability_pct "Numeric(5,2)"
        decimal essential_expenses_avg "Numeric(12,2)"
        datetime created_at
        datetime updated_at
    }

    products {
        uuid id PK
        string external_id UK "e.g. L-101, C-201"
        uuid customer_id FK
        string product_type "loan or card (discriminator)"
        decimal annual_rate_pct "Numeric(5,2)"
        int days_past_due
        datetime created_at
        datetime updated_at
    }

    loans {
        uuid id PK_FK "FK to products.id"
        string loan_type "personal or micro"
        decimal principal "Numeric(12,2)"
        int remaining_term_months
        boolean collateral
    }

    cards {
        uuid id PK_FK "FK to products.id"
        decimal balance "Numeric(12,2)"
        decimal min_payment_pct "Numeric(5,2)"
        int payment_due_day
    }

    payments {
        uuid id PK
        uuid product_id FK
        uuid customer_id FK
        date payment_date
        decimal amount "Numeric(12,2)"
        datetime created_at
        datetime updated_at
    }

    credit_score_history {
        uuid id PK
        uuid customer_id FK
        date score_date
        int credit_score
        datetime created_at
        datetime updated_at
    }

    bank_offers {
        uuid id PK
        string offer_id UK "e.g. OF-CONSO-24M"
        array product_types_eligible "ARRAY of strings"
        decimal max_consolidated_balance "Numeric(12,2)"
        decimal new_rate_pct "Numeric(5,2)"
        int max_term_months
        string conditions
        datetime created_at
        datetime updated_at
    }
```

---

## 🏗️ Entity Descriptions

### Customer
Represents a bank customer with their financial profile (cashflow data).

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `external_id` | String | External identifier (e.g., `CU-001`) |
| `monthly_income_avg` | Decimal | Average monthly income |
| `income_variability_pct` | Decimal | Income variability percentage |
| `essential_expenses_avg` | Decimal | Average essential expenses |

### Product (Base)
Abstract base entity for financial products. Uses **Joined Table Inheritance**.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `external_id` | String | External identifier (e.g., `L-101`) |
| `customer_id` | UUID | FK to `customers` |
| `product_type` | String | Discriminator: `loan` or `card` |
| `annual_rate_pct` | Decimal | Annual interest rate |
| `days_past_due` | Integer | Days past due |

### Loan (extends Product)
Loan product with additional loan-specific fields.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK & FK to `products.id` |
| `loan_type` | String | `personal` or `micro` |
| `principal` | Decimal | Loan principal amount |
| `remaining_term_months` | Integer | Remaining months to pay |
| `collateral` | Boolean | Whether loan has collateral |

### Card (extends Product)
Credit card product with card-specific fields.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | PK & FK to `products.id` |
| `balance` | Decimal | Current balance |
| `min_payment_pct` | Decimal | Minimum payment percentage |
| `payment_due_day` | Integer | Day of month payment is due |

### Payment
Payment transactions linked to products and customers.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `product_id` | UUID | FK to `products` |
| `customer_id` | UUID | FK to `customers` |
| `payment_date` | Date | Date of payment |
| `amount` | Decimal | Payment amount |

### Credit Score History
Historical credit scores for customers.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `customer_id` | UUID | FK to `customers` |
| `score_date` | Date | Date of score |
| `credit_score` | Integer | Credit score value |

### Bank Offer
Consolidation offers from the bank.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `offer_id` | String | External offer identifier |
| `product_types_eligible` | Array | Eligible product types (e.g., `["card", "personal"]`) |
| `max_consolidated_balance` | Decimal | Maximum balance to consolidate |
| `new_rate_pct` | Decimal | New interest rate offered |
| `max_term_months` | Integer | Maximum term in months |
| `conditions` | String | Eligibility conditions |

---

## 📄 Environment Variables

Required environment variables (in `.env` or environment):

```env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=finance_assistant
POSTGRES_SERVER=localhost  # Use 'db' when running in Docker

# Server
DEBUG=true
```
