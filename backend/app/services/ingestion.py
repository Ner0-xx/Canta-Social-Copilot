import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

import httpx

from app.models import Source, SourceItem


def compute_content_hash(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def clean_html(raw_html: str) -> str:
    cleaned = re.sub(r"<script.*?>.*?</script>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<style.*?>.*?</style>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class IngestionService:
    async def process_source(self, source: Source) -> list[dict[str, Any]]:
        source_type = source.source_type.lower()

        if source_type == "note":
            return self._process_text_note(source)
        elif source_type == "url":
            return await self._process_web_url(source)
        elif source_type == "rss":
            return await self._process_rss_feed(source)
        else:
            return self._process_text_note(source)

    def _process_text_note(self, source: Source) -> list[dict[str, Any]]:
        content = source.uri_or_content.strip()
        title = source.name or (content[:50] + "..." if len(content) > 50 else content)
        content_hash = compute_content_hash(content)

        return [
            {
                "title": title,
                "author": "User Note",
                "url": "",
                "canonical_url": "",
                "content": content,
                "content_hash": content_hash,
                "published_at": datetime.now(),
            }
        ]

    async def _process_web_url(self, source: Source) -> list[dict[str, Any]]:
        url = source.uri_or_content.strip()
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html_text = resp.text

        title_match = re.search(r"<title>(.*?)</title>", html_text, re.IGNORECASE)
        page_title = title_match.group(1).strip() if title_match else source.name or url
        text_content = clean_html(html_text)
        content_hash = compute_content_hash(text_content[:4000])

        return [
            {
                "title": page_title,
                "author": "Web Source",
                "url": url,
                "canonical_url": str(resp.url),
                "content": text_content[:8000],
                "content_hash": content_hash,
                "published_at": datetime.now(),
            }
        ]

    async def _process_rss_feed(self, source: Source) -> list[dict[str, Any]]:
        feed_url = source.uri_or_content.strip()
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(feed_url)
            resp.raise_for_status()
            xml_text = resp.text

        items: list[dict[str, Any]] = []
        try:
            root = ET.fromstring(xml_text)
            for item in root.findall(".//item")[:10]:
                title = item.findtext("title") or "Untitled RSS Item"
                link = item.findtext("link") or ""
                description = item.findtext("description") or ""
                clean_desc = clean_html(description)
                content_hash = compute_content_hash(f"{title} {clean_desc}")

                items.append(
                    {
                        "title": title,
                        "author": "RSS Feed",
                        "url": link,
                        "canonical_url": link,
                        "content": clean_desc[:4000],
                        "content_hash": content_hash,
                        "published_at": datetime.now(),
                    }
                )
        except Exception:
            # Fallback parsing for non-standard XML
            content_hash = compute_content_hash(xml_text[:2000])
            items.append(
                {
                    "title": source.name or "RSS Content",
                    "author": "RSS Feed",
                    "url": feed_url,
                    "canonical_url": feed_url,
                    "content": clean_html(xml_text[:4000]),
                    "content_hash": content_hash,
                    "published_at": datetime.now(),
                }
            )

        return items
