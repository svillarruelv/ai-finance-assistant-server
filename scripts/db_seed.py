"""Database seeder script.

Reads mock data from CSV/JSON files and populates the database.
Run with: docker exec finance-server python scripts/db_seed.py
"""

import asyncio
import csv
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import BankOffer, Card, CreditScoreHistory, Customer, Loan, Payment, Product


MOCK_DIR = Path(__file__).parent.parent / "app" / "mock"


def parse_bool(value: str) -> bool:
    """Parse boolean from CSV string."""
    return value.lower() in ("true", "1", "yes")


def parse_date(value: str) -> datetime:
    """Parse date from CSV string."""
    return datetime.strptime(value, "%Y-%m-%d").date()


async def get_or_create_customer(session, external_id: str) -> Customer:
    """Get existing customer or return None if not found."""
    result = await session.execute(
        select(Customer).where(Customer.external_id == external_id)
    )
    return result.scalar_one_or_none()


async def get_product_by_external_id(session, external_id: str) -> Product:
    """Get product by external_id."""
    result = await session.execute(
        select(Product).where(Product.external_id == external_id)
    )
    return result.scalar_one_or_none()


async def seed_customers(session) -> dict[str, Customer]:
    """Seed customers from customer_cashflow.csv."""
    print("📥 Seeding customers...")
    customers = {}
    
    with open(MOCK_DIR / "customer_cashflow.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            external_id = row["customer_id"]
            
            # Check if exists
            existing = await get_or_create_customer(session, external_id)
            if existing:
                print(f"  ⏭️  Customer {external_id} already exists")
                customers[external_id] = existing
                continue
            
            customer = Customer(
                external_id=external_id,
                monthly_income_avg=Decimal(row["monthly_income_avg"]),
                income_variability_pct=Decimal(row["income_variability_pct"]),
                essential_expenses_avg=Decimal(row["essential_expenses_avg"]),
            )
            session.add(customer)
            customers[external_id] = customer
            print(f"  ✅ Created customer {external_id}")
    
    await session.flush()
    return customers


async def seed_bank_offers(session) -> None:
    """Seed bank offers from bank_offers.json."""
    print("📥 Seeding bank offers...")
    
    with open(MOCK_DIR / "bank_offers.json") as f:
        offers = json.load(f)
    
    for offer_data in offers:
        offer_id = offer_data["offer_id"]
        
        # Check if exists
        result = await session.execute(
            select(BankOffer).where(BankOffer.offer_id == offer_id)
        )
        if result.scalar_one_or_none():
            print(f"  ⏭️  Bank offer {offer_id} already exists")
            continue
        
        offer = BankOffer(
            offer_id=offer_id,
            product_types_eligible=offer_data["product_types_eligible"],
            max_consolidated_balance=Decimal(str(offer_data["max_consolidated_balance"])),
            new_rate_pct=Decimal(str(offer_data["new_rate_pct"])),
            max_term_months=offer_data["max_term_months"],
            conditions=offer_data.get("conditions"),
        )
        session.add(offer)
        print(f"  ✅ Created bank offer {offer_id}")
    
    await session.flush()


async def seed_loans(session, customers: dict[str, Customer]) -> dict[str, Product]:
    """Seed loans from loans.csv."""
    print("📥 Seeding loans...")
    products = {}
    
    with open(MOCK_DIR / "loans.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            external_id = row["loan_id"]
            customer_external_id = row["customer_id"]
            
            # Check if exists
            existing = await get_product_by_external_id(session, external_id)
            if existing:
                print(f"  ⏭️  Loan {external_id} already exists")
                products[external_id] = existing
                continue
            
            customer = customers.get(customer_external_id)
            if not customer:
                print(f"  ⚠️  Customer {customer_external_id} not found for loan {external_id}")
                continue
            
            loan = Loan(
                external_id=external_id,
                customer_id=customer.id,
                product_type="loan",
                annual_rate_pct=Decimal(row["annual_rate_pct"]),
                days_past_due=int(row["days_past_due"]),
                loan_type=row["product_type"],  # personal or micro
                principal=Decimal(row["principal"]),
                remaining_term_months=int(row["remaining_term_months"]),
                collateral=parse_bool(row["collateral"]),
            )
            session.add(loan)
            products[external_id] = loan
            print(f"  ✅ Created loan {external_id} ({row['product_type']})")
    
    await session.flush()
    return products


async def seed_cards(session, customers: dict[str, Customer]) -> dict[str, Product]:
    """Seed cards from cards.csv."""
    print("📥 Seeding cards...")
    products = {}
    
    with open(MOCK_DIR / "cards.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            external_id = row["card_id"]
            customer_external_id = row["customer_id"]
            
            # Check if exists
            existing = await get_product_by_external_id(session, external_id)
            if existing:
                print(f"  ⏭️  Card {external_id} already exists")
                products[external_id] = existing
                continue
            
            customer = customers.get(customer_external_id)
            if not customer:
                print(f"  ⚠️  Customer {customer_external_id} not found for card {external_id}")
                continue
            
            card = Card(
                external_id=external_id,
                customer_id=customer.id,
                product_type="card",
                annual_rate_pct=Decimal(row["annual_rate_pct"]),
                days_past_due=int(row["days_past_due"]),
                balance=Decimal(row["balance"]),
                min_payment_pct=Decimal(row["min_payment_pct"]),
                payment_due_day=int(row["payment_due_day"]),
            )
            session.add(card)
            products[external_id] = card
            print(f"  ✅ Created card {external_id}")
    
    await session.flush()
    return products


async def seed_credit_score_history(session, customers: dict[str, Customer]) -> None:
    """Seed credit score history from credit_score_history.csv."""
    print("📥 Seeding credit score history...")
    
    with open(MOCK_DIR / "credit_score_history.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            customer_external_id = row["customer_id"]
            score_date = parse_date(row["date"])
            
            customer = customers.get(customer_external_id)
            if not customer:
                print(f"  ⚠️  Customer {customer_external_id} not found")
                continue
            
            # Check if exists (by customer + date)
            result = await session.execute(
                select(CreditScoreHistory).where(
                    CreditScoreHistory.customer_id == customer.id,
                    CreditScoreHistory.score_date == score_date,
                )
            )
            if result.scalar_one_or_none():
                print(f"  ⏭️  Credit score for {customer_external_id} on {score_date} already exists")
                continue
            
            credit_score = CreditScoreHistory(
                customer_id=customer.id,
                score_date=score_date,
                credit_score=int(row["credit_score"]),
            )
            session.add(credit_score)
            print(f"  ✅ Created credit score for {customer_external_id}: {row['credit_score']}")
    
    await session.flush()


async def seed_payments(
    session, customers: dict[str, Customer], products: dict[str, Product]
) -> None:
    """Seed payments from payments_history.csv."""
    print("📥 Seeding payments...")
    
    with open(MOCK_DIR / "payments_history.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            product_external_id = row["product_id"]
            customer_external_id = row["customer_id"]
            payment_date = parse_date(row["date"])
            amount = Decimal(row["amount"])
            
            customer = customers.get(customer_external_id)
            product = products.get(product_external_id)
            
            if not customer:
                print(f"  ⚠️  Customer {customer_external_id} not found")
                continue
            if not product:
                print(f"  ⚠️  Product {product_external_id} not found")
                continue
            
            # Check if exists (by product + date + amount)
            result = await session.execute(
                select(Payment).where(
                    Payment.product_id == product.id,
                    Payment.payment_date == payment_date,
                    Payment.amount == amount,
                )
            )
            if result.scalar_one_or_none():
                print(f"  ⏭️  Payment for {product_external_id} on {payment_date} already exists")
                continue
            
            payment = Payment(
                product_id=product.id,
                customer_id=customer.id,
                payment_date=payment_date,
                amount=amount,
            )
            session.add(payment)
            print(f"  ✅ Created payment: {product_external_id} - ${amount}")
    
    await session.flush()


async def seed_database() -> None:
    """Main seeding function."""
    print("🌱 Starting database seed...")
    print(f"📂 Mock data directory: {MOCK_DIR}")
    
    async with SessionLocal() as session:
        try:
            # Seed in order of dependencies
            customers = await seed_customers(session)
            await seed_bank_offers(session)
            loan_products = await seed_loans(session, customers)
            card_products = await seed_cards(session, customers)
            
            # Merge product dictionaries
            all_products = {**loan_products, **card_products}
            
            await seed_credit_score_history(session, customers)
            await seed_payments(session, customers, all_products)
            
            # Commit all changes
            await session.commit()
            print("\n✅ Database seeded successfully!")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error seeding database: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_database())
