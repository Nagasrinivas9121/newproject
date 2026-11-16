import datetime
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from server.models.subscription import Subscription


async def get_tenant_subscription(
    db: AsyncSession, tenant_id: str
) -> Optional[Subscription]:
    """Fetch the latest subscription record for a tenant."""
    query = (
        select(Subscription)
        .where(Subscription.tenant_id == tenant_id)
        .order_by(Subscription.created_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().first()


async def evaluate_subscription_status(
    db: AsyncSession, subscription: Subscription
) -> Tuple[bool, bool, int]:
    """
    Evaluate subscription validity and days remaining.
    Returns: (is_valid: bool, in_grace_period: bool, days_remaining: int)
    """
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    if subscription.status in ("SUSPENDED", "CANCELLED"):
        return False, False, 0

    grace_end = subscription.end_date + datetime.timedelta(
        days=subscription.grace_period_days
    )

    if now <= subscription.end_date:
        days_left = (subscription.end_date - now).days
        if subscription.status != "ACTIVE":
            subscription.status = "ACTIVE"
            await db.flush()
        return True, False, max(days_left, 0)
    elif now <= grace_end:
        days_left_in_grace = (grace_end - now).days
        if subscription.status != "GRACE_PERIOD":
            subscription.status = "GRACE_PERIOD"
            await db.flush()
        return True, True, days_left_in_grace
    else:
        if subscription.status != "EXPIRED":
            subscription.status = "EXPIRED"
            await db.flush()
        return False, False, 0
