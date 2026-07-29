from supabase import create_client, Client
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_ANON_KEY
    if not url or not url.startswith("http"):
        url = "https://placeholder.supabase.co"
    if not key:
        key = "placeholder-key"
    try:
        return create_client(url, key)
    except Exception as e:
        logger.warning(f"Could not initialize Supabase client: {e}")
        # Create client with fallback valid format
        return create_client("https://demo.supabase.co", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy")

supabase: Client = get_supabase_client()
