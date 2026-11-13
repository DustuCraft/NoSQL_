import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
load_dotenv(ROOT / ".env")

# Параметры вариантa 7 (банковский демо-сервис)
SEED = 42
N, Q, SHARDS = 12000, 30000, 3
ACCOUNTS, BRANCHES = 2500, 5

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "university_lab")
COLLECTION = os.getenv("MONGO_COLLECTION", "operations")
