"""Учебные функции размещения (не воспроизводят алгоритм MongoDB)."""
import hashlib
from src.config import N, SHARDS


def stable_hash(value):
    digest = hashlib.sha256(str(value).encode()).digest()
    return int.from_bytes(digest[:8], "big")


def low_card(row):         return row["branch_id"] % SHARDS
def hashed_account(row):   return stable_hash(row["account_id"]) % SHARDS
def range_operation(row):  return min(row["operation_id"] // (N // SHARDS), SHARDS - 1)
def hashed_branch_account(row):
    return stable_hash((row["branch_id"], row["account_id"])) % SHARDS


BASE_CANDIDATES = [("branch_id", low_card),
                   ("hashed_account_id", hashed_account),
                   ("range_operation_id", range_operation)]
STEP4_CANDIDATES = [("branch_id", low_card),
                    ("hashed_account_id", hashed_account),
                    ("hashed_branch+account", hashed_branch_account)]
