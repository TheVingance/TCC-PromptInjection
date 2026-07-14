"""
Seed script — Popula o banco com dados fictícios para testes adversariais.
Execute dentro do container: python scripts/seed_data.py
"""
import asyncio
import random
from datetime import datetime, timedelta, timezone

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.security import get_password_hash
from models.account import Account, AccountType
from models.investment import Investment, InvestmentType
from models.loan import Loan, LoanStatus
from models.transaction import Transaction, TransactionStatus, TransactionType
from models.user import User

fake = Faker("pt_BR")

TICKERS = [
    ("PETR4", "Petrobras PN", InvestmentType.STOCKS),
    ("VALE3", "Vale ON", InvestmentType.STOCKS),
    ("ITUB4", "Itaú Unibanco PN", InvestmentType.STOCKS),
    ("BBDC4", "Bradesco PN", InvestmentType.STOCKS),
    ("TESOURO-SELIC", "Tesouro Selic 2027", InvestmentType.BONDS),
    ("KNRI11", "Kinea Renda Imobiliária FII", InvestmentType.REAL_ESTATE),
    ("BTC", "Bitcoin", InvestmentType.CRYPTO),
]


def gen_cpf() -> str:
    d = [random.randint(0, 9) for _ in range(9)]
    return f"{d[0]}{d[1]}{d[2]}.{d[3]}{d[4]}{d[5]}.{d[6]}{d[7]}{d[8]}-{random.randint(10,99)}"


async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        print("🌱 Criando usuários fictícios...")
        users = []
        for i in range(5):
            user = User(
                full_name=fake.name(),
                email=f"user{i+1}@finsecai.test",
                cpf=gen_cpf(),
                hashed_password=get_password_hash("senha@123"),
                is_active=True,
            )
            db.add(user)
            users.append(user)

        # Researcher user
        researcher = User(
            full_name="Dr. Pesquisador Silva",
            email="researcher@finsecai.test",
            cpf=gen_cpf(),
            hashed_password=get_password_hash("research@2026"),
            is_active=True,
        )
        db.add(researcher)
        users.append(researcher)
        await db.flush()

        print("🏦 Criando contas bancárias...")
        accounts = []
        for user in users:
            for acc_type in [AccountType.CHECKING, AccountType.SAVINGS]:
                initial = random.uniform(1000, 100_000)
                account = Account(
                    user_id=user.id,
                    account_number=f"{random.randint(10000000, 99999999)}-{random.randint(0, 9)}",
                    account_type=acc_type,
                    balance=round(initial, 2),
                )
                db.add(account)
                accounts.append(account)
        await db.flush()

        print("💸 Criando transações históricas...")
        for _ in range(50):
            acc = random.choice(accounts)
            tx_type = random.choice([TransactionType.DEPOSIT, TransactionType.WITHDRAWAL])
            amount = round(random.uniform(50, 5000), 2)
            tx = Transaction(
                from_account_id=acc.id if tx_type == TransactionType.WITHDRAWAL else None,
                to_account_id=acc.id if tx_type == TransactionType.DEPOSIT else None,
                transaction_type=tx_type,
                amount=amount,
                status=TransactionStatus.COMPLETED,
                description=f"{'Depósito' if tx_type == TransactionType.DEPOSIT else 'Saque'} fictício",
                created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90)),
            )
            db.add(tx)

        print("📈 Criando investimentos...")
        inv_accounts = [a for a in accounts if a.account_type == AccountType.SAVINGS]
        for acc in inv_accounts[:4]:
            ticker_info = random.choice(TICKERS)
            qty = round(random.uniform(1, 100), 2)
            avg_price = round(random.uniform(10, 500), 2)
            inv = Investment(
                account_id=acc.id,
                investment_type=ticker_info[2],
                ticker=ticker_info[0],
                name=ticker_info[1],
                quantity=qty,
                average_price=avg_price,
                current_price=round(avg_price * random.uniform(0.8, 1.3), 2),
                purchase_date=datetime.now(timezone.utc) - timedelta(days=random.randint(30, 365)),
            )
            db.add(inv)

        print("💳 Criando empréstimos fictícios...")
        for user in users[:3]:
            loan = Loan(
                user_id=user.id,
                requested_amount=round(random.uniform(5000, 40000), 2),
                interest_rate=2.5,
                term_months=random.choice([12, 24, 36, 48]),
                status=LoanStatus.ACTIVE,
                purpose="Empréstimo pessoal fictício",
            )
            db.add(loan)

        await db.commit()

    await engine.dispose()
    print("\n✅ Seed concluído!")
    print("──────────────────────────────────────")
    print("Credenciais de acesso:")
    print("  Email: user1@finsecai.test  | Senha: senha@123")
    print("  Email: user2@finsecai.test  | Senha: senha@123")
    print("  Email: researcher@finsecai.test | Senha: research@2026")
    print("──────────────────────────────────────")


if __name__ == "__main__":
    asyncio.run(seed())
