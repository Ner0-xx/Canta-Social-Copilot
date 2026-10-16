from supabase import create_client, Client
from app.config import get_settings

settings = get_settings()

def get_supabase() -> Client | None:
    storage_key = settings.supabase_service_role_key or settings.supabase_key
    if settings.supabase_url and storage_key:
        return create_client(settings.supabase_url, storage_key)
    return None
