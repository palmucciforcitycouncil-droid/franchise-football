"""
Quick check to confirm that .env variables are being loaded.
"""

from dotenv import load_dotenv
import os

# Load variables from .env
load_dotenv()

print("DATABASE_URL =", os.getenv("DATABASE_URL"))
print("LOG_LEVEL    =", os.getenv("LOG_LEVEL"))
print("DEFAULT_SEED =", os.getenv("DEFAULT_SEED"))

