import json
import logging
import math
import re
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.schemas import StrategyData

logger = logging.getLogger(__name__)


class LLMGenerationError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        self.status_code = status_code
        super().__init__(message)


class IdeaGenerationError(LLMGenerationError):
    pass


class LLMService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def _provider_error(self, action: str, exc: Exception) -> LLMGenerationError:
        if isinstance(exc, httpx.TimeoutException):
            logger.warning("AI provider timed out while %s", action)
            return LLMGenerationError(
                "The AI provider request timed out after 60 seconds. Please try again.",
                status_code=504,
            )

        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            if status_code in {404, 503}:
                logger.warning("AI provider is unavailable while %s (HTTP %s)", action, status_code)
                return LLMGenerationError(
                    "The configured AI model or provider is currently unavailable. Check that "
                    "the model ID is correct and enabled for your account, then try again later.",
                    status_code=503,
                )
            if status_code == 429:
                logger.warning("AI provider rate limit reached while %s", action)
                return LLMGenerationError(
                    "The AI provider is rate-limiting requests. Wait a little while, then try again.",
                    status_code=429,
                )

        logger.exception("AI provider failed while %s", action)
        return LLMGenerationError(
            f"The AI provider could not {action}. Check its backend configuration and try again."
        )

    async def generate_ideas(
        self, source_title: str, source_content: str, strategy: StrategyData | None = None, analytics_context: str = ""
    ) -> list[dict[str, Any]]:
        provider = self.settings.inference_provider.lower()
        prompt = self._build_ideas_prompt(source_title, source_content, strategy, analytics_context)

        if provider in {"openai_compatible", "openai", "openrouter", "custom_api"}:
            try:
                response_text = await self._call_openai_compatible(prompt)
            except Exception as exc:
                raise self._provider_error("generate ideas", exc) from exc
        elif provider == "ollama":
            try:
                response_text = await self._call_ollama(prompt)
            except Exception as exc:
                raise self._provider_error("generate ideas", exc) from exc
        else:
            raise IdeaGenerationError(
                "AI-only idea generation is enabled, but no supported AI provider is "
                "configured.",
                status_code=503,
            )

        ideas = self._parse_json_ideas(response_text)
        valid_ideas = len(ideas) == 5
        for idea in ideas:
            if not isinstance(idea, dict) or not all(
                isinstance(idea.get(field), str) and idea[field].strip()
                for field in ("title", "summary", "proposed_angle")
            ):
                valid_ideas = False
                break
            relevance_score = idea.get("relevance_score")
            if relevance_score is not None and (
                isinstance(relevance_score, bool)
                or not isinstance(relevance_score, (int, float))
                or not math.isfinite(relevance_score)
                or not 0 <= relevance_score <= 100
            ):
                valid_ideas = False
                break

        if not valid_ideas:
            raise IdeaGenerationError(
                "The AI returned an incomplete or invalid idea list. "
                "Please try generating ideas again."
            )
        return ideas

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
            except Exception as exc:
                raise self._provider_error("generate drafts", exc) from exc
        elif provider == "ollama":
            try:
                response_text = await self._call_ollama(prompt)
            except Exception as exc:
                raise self._provider_error("generate drafts", exc) from exc
        else:
            raise LLMGenerationError(
                "AI-only draft generation is enabled, but no supported AI provider is "
                "configured.",
                status_code=503,
            )

        drafts = self._parse_json_drafts(response_text)
        if (
            drafts is None
            or not isinstance(drafts.get("x_post"), str)
            or not drafts["x_post"].strip()
            or not isinstance(drafts.get("x_thread"), list)
            or not 3 <= len(drafts["x_thread"]) <= 4
            or not all(isinstance(post, str) and post.strip() for post in drafts["x_thread"])
            or not isinstance(drafts.get("linkedin_post"), str)
            or not drafts["linkedin_post"].strip()
        ):
            raise LLMGenerationError(
                "The AI returned incomplete or invalid drafts. Please try generating them again."
            )
        return drafts

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

        async with httpx.AsyncClient(timeout=60.0) as client:
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

        async with httpx.AsyncClient(timeout=60.0) as client:
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
Analyze the source material and generate exactly 5 distinct, specific social media content ideas.
Ground every idea in concrete facts, arguments, examples, or questions found in the source.
Do not reuse generic recurring formats or merely rephrase the source title. Give each idea a
different editorial angle, such as an evidence-based insight, practical implication, trade-off,
counterpoint, unanswered question, or audience-specific application where the material supports it.
Do not invent facts that are absent from the source.
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

Return exactly five objects in the JSON array.
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
Develop this idea into original, complete social media content. Do not copy the title,
summary, or proposed angle as the body; use them as a brief, then add useful explanation,
specific implications, and a clear audience-relevant takeaway. Do not invent facts beyond the
brief. Return polished, publication-ready text, not a plan or outline.
Idea Title: {idea_title}
Summary: {idea_summary}
Proposed Angle: {proposed_angle}

Tone: {tone}
Call to Action Style: {cta}
Avoided Words: {avoided}

Return a JSON object with:
- "x_post": A complete, standalone X post under 270 characters, with a clear insight and hook.
- "x_thread": An array of 3-4 complete, connected X posts that develop the idea step by step.
- "linkedin_post": A fully developed LinkedIn post with a strong opening, substantive explanation,
  clear line breaks, and a relevant closing question or call to action.
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
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass
        return None
