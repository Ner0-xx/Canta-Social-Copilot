from supabase import create_client, Client
from app.config import get_settings

settings = get_settings()

def get_supabase() -> Client | None:
    if settings.supabase_url and settings.supabase_key:
        return create_client(settings.supabase_url, settings.supabase_key)
    return None
