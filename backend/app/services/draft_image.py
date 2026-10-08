import asyncio
import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

from app.config import get_settings


class DraftImageError(Exception):
    pass


async def load_draft_image(image_path: str) -> tuple[bytes, str, str]:
    parsed = urlparse(image_path)
    if parsed.scheme or parsed.netloc:
        settings = get_settings()
        trusted = urlparse(settings.supabase_url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != trusted.netloc
            or not parsed.path.startswith("/storage/v1/object/public/images/")
            or parsed.username
            or parsed.password
        ):
            raise DraftImageError("The saved image URL is not an allowed public images-bucket URL.")
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(image_path)
                response.raise_for_status()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            raise DraftImageError("The saved image could not be downloaded from Supabase.") from exc
        image_bytes = response.content
        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        filename = Path(unquote(parsed.path)).name
    else:
        if not image_path.startswith("/uploads/"):
            raise DraftImageError("The saved image path is invalid.")
        upload_root = (Path.cwd() / "data" / "uploads").resolve()
        local_path = (upload_root / Path(image_path).name).resolve()
        if not local_path.is_relative_to(upload_root) or not local_path.is_file():
            raise DraftImageError("The saved image file is unavailable.")
        image_bytes = await asyncio.to_thread(local_path.read_bytes)
        content_type = mimetypes.guess_type(local_path.name)[0] or ""
        filename = local_path.name

    if not content_type.startswith("image/"):
        raise DraftImageError("The saved file is not a supported image.")
    return image_bytes, filename, content_type
