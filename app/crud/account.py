import random
import string
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.account import Account, AccountType
from schemas.account import AccountCreate


def _generate_account_number() -> str:
    return "".join(random.choices(string.digits, k=8)) + "-" + random.choice(string.digits)


async def get_account_by_id(db: AsyncSession, account_id: int) -> Optional[Account]:
    result = await db.execute(select(Account).where(Account.id == account_id))
    return result.scalar_one_or_none()


async def get_account_by_number(db: AsyncSession, account_number: str) -> Optional[Account]:
    result = await db.execute(select(Account).where(Account.account_number == account_number))
    return result.scalar_one_or_none()


async def get_user_accounts(db: AsyncSession, user_id: int) -> List[Account]:
    result = await db.execute(select(Account).where(Account.user_id == user_id))
    return list(result.scalars().all())


async def create_account(db: AsyncSession, user_id: int, data: AccountCreate) -> Account:
    account = Account(
        user_id=user_id,
        account_number=_generate_account_number(),
        account_type=data.account_type,
        balance=data.initial_deposit,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account
