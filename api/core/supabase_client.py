
"""Re-exports your real service-role client so nothing is duplicated."""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.auth.supabase_client import get_service_client  # noqa: F401