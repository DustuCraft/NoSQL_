"""Синтетические данные: банковские операции."""
import random
from datetime import datetime, timedelta
from src.config import N, Q, ACCOUNTS, BRANCHES, SEED


def make_rows():
    return [dict(account_id=i % ACCOUNTS, branch_id=i % BRANCHES, operation_id=i)
            for i in range(N)]


def make_skewed_rows(hot_share=0.8):
    """Шаг 4: hot_share записей приходится на отделение 0."""
    return [dict(account_id=i % ACCOUNTS,
                 branch_id=0 if random.random() < hot_share else random.randint(1, BRANCHES - 1),
                 operation_id=i) for i in range(N)]


def make_requests(data, hot_branch=0, hot_prob=0.6):
    uniform = random.choices(data, k=Q)
    hot_rows = [r for r in data if r["branch_id"] == hot_branch]
    hot = [random.choice(hot_rows) if random.random() < hot_prob else random.choice(data)
           for _ in range(Q)]
    return uniform, hot


def to_mongo_docs(rows):
    """Документы для MongoDB (camelCase), детерминированно."""
    rng = random.Random(SEED)
    start = datetime(2026, 1, 1)
    return [dict(accountId=r["account_id"], branchId=r["branch_id"],
                 operationId=r["operation_id"],
                 ts=start + timedelta(seconds=r["operation_id"]),
                 amount=round(rng.uniform(1, 5000), 2)) for r in rows]
