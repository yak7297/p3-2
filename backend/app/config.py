import os
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def setting(name: str, default: str = "") -> str:
    return os.getenv(name, default)

