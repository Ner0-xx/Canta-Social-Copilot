import json
import logging
import re
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.schemas import StrategyData

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def generate_ideas(
        self, source_title: str, source_content: str, strategy: StrategyData | None = None, analytics_context: str = ""
    ) -> list[dict[str, Any]]:
        provider = self.settings.inference_provider.lower()
        prompt = self._build_ideas_prompt(source_title, source_content, strategy, analytics_context)

        if provider in {"openai_compatible", "openai", "openrouter", "custom_api"}:
            try:
                response_text = await self._call_openai_compatible(prompt)
                ideas = self._parse_json_ideas(response_text)
                if ideas:
                    return ideas
            except Exception as exc:
                logger.warning(f"External LLM API call failed: {exc}. Falling back to template generator.")

        elif provider == "ollama":
            try:
                response_text = await self._call_ollama(prompt)
                ideas = self._parse_json_ideas(response_text)
                if ideas:
                    return ideas
            except Exception as exc:
                logger.warning(f"Ollama call failed: {exc}. Falling back to template generator.")

        return self._generate_template_ideas(source_title, source_content, strategy)

    async def generate_draft_variants(
        self,
        idea_title: str,
        idea_summary: str,
        proposed_angle: str = "",
        strategy: StrategyData | None = None,
    ) -> dict[str, Any]:
        provider = self.settings.inference_provider.lower()
        prompt = self._build_drafts_prompt(idea_title, idea_summary, proposed_angle, strategy)

        if provider in {"openai_compatible", "openai", "openrouter", "custom_api"}:
            try:
                response_text = await self._call_openai_compatible(prompt)
                drafts = self._parse_json_drafts(response_text)
                if drafts:
                    return drafts
            except Exception as exc:
                logger.warning(f"External LLM draft call failed: {exc}. Falling back to template generator.")

        elif provider == "ollama":
            try:
                response_text = await self._call_ollama(prompt)
                drafts = self._parse_json_drafts(response_text)
                if drafts:
                    return drafts
            except Exception as exc:
                logger.warning(f"Ollama draft call failed: {exc}. Falling back to template generator.")

        return self._generate_template_drafts(idea_title, idea_summary, proposed_angle, strategy)

    async def _call_openai_compatible(self, prompt: str) -> str:
        base_url = self.settings.inference_base_url.rstrip("/") or "https://api.openai.com/v1"
        url = f"{base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.settings.inference_api_key:
            headers["Authorization"] = f"Bearer {self.settings.inference_api_key}"

        model = self.settings.inference_model or "gpt-4o-mini"

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional social media content assistant. Return valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _call_ollama(self, prompt: str) -> str:
        base_url = self.settings.inference_base_url.rstrip("/") or "http://localhost:11434"
        url = f"{base_url}/api/generate"
        model = self.settings.inference_model or "llama3"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "")

    def _build_ideas_prompt(
        self, source_title: str, source_content: str, strategy: StrategyData | None, analytics_context: str = ""
    ) -> str:
        pillars = [p.name for p in strategy.pillars] if strategy and strategy.pillars else ["General"]
        audiences = [a.name for a in strategy.audiences] if strategy and strategy.audiences else ["General Audience"]
        tone = ", ".join(strategy.voice.tone) if strategy and strategy.voice and strategy.voice.tone else "Professional"

        analytics_instruction = f"\n{analytics_context}\n" if analytics_context else ""

        return f"""
Given the following source material, generate 3 strategic social media content ideas.
Brand Tone: {tone}
Pillars: {', '.join(pillars)}
Target Audiences: {', '.join(audiences)}
{analytics_instruction}
Source Title: {source_title}
Source Content: {source_content[:2000]}

Return a JSON array of objects with the following keys:
- "title": concise title for the idea
- "summary": 2-3 sentence overview
- "proposed_angle": unique takeaway or hook angle
- "relevance_score": float between 70.0 and 99.0
"""

    def _build_drafts_prompt(
        self,
        idea_title: str,
        idea_summary: str,
        proposed_angle: str,
        strategy: StrategyData | None,
    ) -> str:
        tone = ", ".join(strategy.voice.tone) if strategy and strategy.voice and strategy.voice.tone else "Professional, insightful"
        cta = strategy.voice.call_to_action_style if strategy and strategy.voice else "Ask a thought-provoking question."
        avoided = ", ".join(strategy.voice.avoided_vocabulary) if strategy and strategy.voice else ""

        return f"""
Write social media post variants based on this idea:
Idea Title: {idea_title}
Summary: {idea_summary}
Proposed Angle: {proposed_angle}

Tone: {tone}
Call to Action Style: {cta}
Avoided Words: {avoided}

Return a JSON object with:
- "x_post": A concise single post under 270 characters for X.
- "x_thread": An array of 3-4 post strings forming an insightful thread for X.
- "linkedin_post": A structured, engaging long-form post for LinkedIn with clear line breaks.
"""

    def _parse_json_ideas(self, text: str) -> list[dict[str, Any]]:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass
        return []

    def _parse_json_drafts(self, text: str) -> dict[str, Any] | None:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, dict) and "x_post" in data:
                    return data
            except json.JSONDecodeError:
                pass
        return None

    def _generate_template_ideas(
        self, source_title: str, source_content: str, strategy: StrategyData | None
    ) -> list[dict[str, Any]]:
        base_name = source_title or "Ingested Topic"
        pillar_id = strategy.pillars[0].id if strategy and strategy.pillars and strategy.pillars[0].id else None
        audience_id = strategy.audiences[0].id if strategy and strategy.audiences and strategy.audiences[0].id else None

        return [
            {
                "title": f"Key Lessons from: {base_name}",
                "summary": f"Break down the actionable strategies discussed in '{base_name}'.",
                "proposed_angle": "Focus on 3 immediate practical steps professionals can take.",
                "relevance_score": 92.5,
                "pillar_id": pillar_id,
                "audience_id": audience_id,
            },
            {
                "title": f"Why {base_name} Matters Now",
                "summary": f"Analyze current industry implications based on content from '{base_name}'.",
                "proposed_angle": "Highlight emerging trends and future impact.",
                "relevance_score": 88.0,
                "pillar_id": pillar_id,
                "audience_id": audience_id,
            },
            {
                "title": f"Debunking Misconceptions: {base_name}",
                "summary": f"Contrarian take on common assumptions surrounding '{base_name}'.",
                "proposed_angle": "Challenge conventional wisdom with evidence.",
                "relevance_score": 85.0,
                "pillar_id": pillar_id,
                "audience_id": audience_id,
            },
        ]

    def _generate_template_drafts(
        self,
        idea_title: str,
        idea_summary: str,
        proposed_angle: str,
        strategy: StrategyData | None,
    ) -> dict[str, Any]:
        display_name = strategy.brand.display_name if strategy and strategy.brand.display_name else "Social Copilot"
        angle = proposed_angle or "Actionable insight"

        return {
            "x_post": f"💡 {idea_title}\n\n{angle}\n\nWhat are your thoughts on this approach?",
            "x_thread": [
                f"1/4 🧵 {idea_title}\n\nHere is what you need to know about this key concept:",
                f"2/4 {idea_summary}",
                f"3/4 Key takeaway: {angle}. Small shifts in execution yield major results.",
                f"4/4 Follow {display_name} for more daily insights on industry strategy. What's your take?",
            ],
            "linkedin_post": f"""🚀 {idea_title}

{idea_summary}

💡 Key Takeaway:
{angle}

Here are 3 core principles to consider:
1. Ground your strategy in solid data.
2. Focus on consistent execution over quick hacks.
3. Measure outcomes and adapt continuously.

What has been your experience with this in your organization? Let's discuss in the comments! 👇""",
        }
