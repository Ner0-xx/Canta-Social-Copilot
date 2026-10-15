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

    @staticmethod
    def _brand_context(strategy: StrategyData | None) -> str:
        if strategy is None:
            return "No brand identity details are configured."

        brand = strategy.brand
        details = {
            "Name": brand.display_name,
            "Purpose": brand.account_purpose,
            "Biography": brand.biography,
            "Expertise": ", ".join(brand.expertise),
            "Offers": ", ".join(brand.offers),
            "Business goals": ", ".join(brand.business_goals),
            "Sensitive topics": ", ".join(brand.sensitive_topics),
            "Required disclosures": ", ".join(brand.required_disclosures),
        }
        return "\n".join(f"- {label}: {value}" for label, value in details.items() if value)

    @classmethod
    def _strategy_context(cls, strategy: StrategyData | None, stage: str) -> str:
        if strategy is None:
            return "No saved Strategy profile is configured."

        brand = cls._brand_context(strategy)
        voice = strategy.voice
        voice_details = [
            f"- Tone: {', '.join(voice.tone)}",
            f"- Preferred vocabulary: {', '.join(voice.preferred_vocabulary)}",
            f"- Avoided vocabulary: {', '.join(voice.avoided_vocabulary)}",
        ]
        if stage == "draft":
            voice_details.extend(
                [
                    f"- Formatting preferences: {voice.formatting_preferences}",
                    f"- Call-to-action style: {voice.call_to_action_style}",
                ]
            )
        if voice.writing_examples:
            voice_details.append(
                "- Writing examples:\n"
                + "\n".join(
                    f"  {index}. {example}"
                    for index, example in enumerate(voice.writing_examples, 1)
                )
            )

        audiences = []
        for audience in strategy.audiences:
            details = [
                f"ID: {audience.id}",
                f"Name: {audience.name}",
                f"Description: {audience.description}",
                f"Needs: {', '.join(audience.needs)}",
                f"Interests: {', '.join(audience.interests)}",
                f"Desired action: {audience.desired_action}",
            ]
            audiences.append(
                "- "
                + "; ".join(
                    value for value in details if value.partition(": ")[2]
                )
            )

        pillars = []
        for pillar in strategy.pillars:
            details = [
                f"ID: {pillar.id}",
                f"Name: {pillar.name}",
                f"Description: {pillar.description}",
                f"Target share: {pillar.target_percentage:g}%",
                f"Example topics: {', '.join(pillar.example_topics)}",
            ]
            pillars.append(
                "- " + "; ".join(value for value in details if value.partition(": ")[2])
            )

        audience_context = (
            "\n".join(audiences) if audiences else "- No audience segments configured."
        )
        pillar_context = "\n".join(pillars) if pillars else "- No content pillars configured."
        return (
            f"Brand Identity:\n{brand}\n"
            f"Voice ({stage} generation):\n{chr(10).join(voice_details)}\n"
            f"Audience segments:\n{audience_context}\n"
            f"Content pillars:\n{pillar_context}"
        )

    def _provider_error(self, action: str, exc: Exception) -> LLMGenerationError:
        if isinstance(exc, httpx.TimeoutException):
            logger.warning("AI provider timed out while %s", action)
            return LLMGenerationError(
                "The AI provider request timed out after 90 seconds. Please try again.",
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
        self,
        source_title: str,
        source_content: str,
        strategy: StrategyData | None = None,
        performance_context: str = "",
    ) -> list[dict[str, Any]]:
        provider = self.settings.inference_provider.lower()
        prompt = self._build_ideas_prompt(
            source_title, source_content, strategy, performance_context
        )

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

        valid_ids = {
            "pillar_id": {pillar.id for pillar in strategy.pillars if pillar.id is not None}
            if strategy
            else set(),
            "audience_id": {
                audience.id
                for audience in strategy.audiences
                if audience.id is not None
            }
            if strategy
            else set(),
        }
        for idea in ideas:
            for field, allowed_ids in valid_ids.items():
                value = idea.get(field)
                if value is not None and (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value not in allowed_ids
                ):
                    raise IdeaGenerationError(
                        f"The AI returned an invalid {field} for a generated idea. "
                        "Please try generating ideas again."
                    )
        return ideas

    async def generate_draft_variants(
        self,
        idea_title: str,
        idea_summary: str,
        proposed_angle: str = "",
        strategy: StrategyData | None = None,
        performance_context: str = "",
    ) -> dict[str, Any]:
        provider = self.settings.inference_provider.lower()
        prompt = self._build_drafts_prompt(
            idea_title, idea_summary, proposed_angle, strategy, performance_context
        )

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

        async with httpx.AsyncClient(timeout=120.0) as client:
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

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "")

    def _build_ideas_prompt(
        self,
        source_title: str,
        source_content: str,
        strategy: StrategyData | None,
        performance_context: str = "",
    ) -> str:
        strategy_context = self._strategy_context(strategy, "idea")
        performance_instruction = (
            f"\nRecent, linked performance evidence:\n{performance_context}\n"
            if performance_context
            else ""
        )

        return f"""
Analyze the source material and generate exactly 5 distinct, specific social media content ideas.
Ground every idea in concrete facts, arguments, examples, or questions found in the source.
Do not reuse generic recurring formats or merely rephrase the source title. Give each idea a
different editorial angle, such as an evidence-based insight, practical implication, trade-off,
counterpoint, unanswered question, or audience-specific application where the material supports it.
Do not invent facts that are absent from the source.

Audience and writing guidance:
- The primary readers are Africans, especially Nigerians. Make the ideas relevant and understandable
  to them without treating African or Nigerian readers as a monolith.
- Respect the configured target audiences below while prioritizing this regional audience.
- Prefer clear, natural language an everyday reader can follow. Explain specialized or ambiguous
  terms in plain language without flattening important nuance.
- Write out the full meaning of abbreviations and acronyms on first use; avoid them when they add
  no value.
- Use a specific, honest hook or a reader-relevant question to make each idea compelling. Avoid
  clickbait, stereotypes, forced local references, or unsupported claims.
- Treat the source as material to learn from and a starting point for discussion, not a topic that
  must be promoted as-is. Focus each idea on a useful insight or question for this identity's
  audience and goals.
- Do not turn an idea into an advertisement, endorsement, or recommendation for another builder,
  company, product, or service when that would conflict with this identity's purpose, offers, or
  business goals. Mention another entity only when genuinely needed for a balanced discussion; do
  not urge readers to use or buy its product.
- You do not have live web-search access in this request. Do not claim to have researched external
  sources or invent source names, quotations, citations, or links. Use the supplied source as the
  factual anchor; only carry through external references and links that are actually present there.

Use the complete relevant saved Strategy profile below. Balance business goals, audience needs,
voice, pillar targets, and performance evidence; do not let a short-term metric override the
identity or audience value. Where evidence supports it, treat ideas as recommendations: build on
better-performing patterns while keeping ideas distinct and strategically relevant.
{strategy_context}
{performance_instruction}
Source Title: {source_title}
Source Content: {source_content[:2000]}

Return a JSON array of objects with the following keys:
- "title": concise title for the idea
- "summary": 2-3 sentence overview
- "proposed_angle": unique takeaway or hook angle
- "relevance_score": float between 70.0 and 99.0
- "pillar_id": the ID of the most relevant configured pillar, or null if none fits
- "audience_id": the ID of the most relevant configured audience, or null if none fits

Return exactly five objects in the JSON array.
"""

    def _build_drafts_prompt(
        self,
        idea_title: str,
        idea_summary: str,
        proposed_angle: str,
        strategy: StrategyData | None,
        performance_context: str = "",
    ) -> str:
        strategy_context = self._strategy_context(strategy, "draft")
        performance_instruction = (
            f"\nRecent, linked performance evidence:\n{performance_context}\n"
            if performance_context
            else ""
        )

        return f"""
Develop this idea into original, complete social media content. Do not copy the title,
summary, or proposed angle as the body; use them as a brief, then add useful explanation,
specific implications, and a clear audience-relevant takeaway. Do not invent facts beyond the
brief. Return polished, publication-ready text, not a plan or outline.

Audience and writing guidance:
- The primary readers are Africans, especially Nigerians. Make the writing relevant and
  understandable to them without treating African or Nigerian audiences as a monolith.
- Respect the configured target audiences below while prioritizing this regional audience.
- Prefer clear, natural language an everyday reader can follow. Explain specialized or ambiguous
  terms in plain language without losing the substance or integrity of the message.
- Write out the full meaning of abbreviations and acronyms on first use; avoid them when they add
  no value.
- Open with a strong, truthful hook that earns attention through relevance, a useful insight, a
  specific tension, or a thoughtful question. Avoid clickbait and forced local references.
- Treat the idea and source as a direction for discussion, not as an instruction to promote the
  source itself. Develop a useful point for this identity's audience and goals.
- Do not make the content an advertisement, endorsement, or recommendation for another builder,
  company, product, or service when that would conflict with this identity's purpose, offers, or
  business goals. Mention another entity only when genuinely needed for a balanced discussion; do
  not urge readers to use or buy its product.
- Use Nigerian or broader African examples only when they genuinely fit the idea and are supported
  by the brief; do not invent statistics, events, quotations, or claims.
- You do not have live web-search access in this request. Do not claim to have researched external
  sources or invent source names, quotations, citations, or links. Use the supplied idea as the
  factual anchor; include external references or links only when actually supplied in the brief.
- Use observed platform and format results only as directional evidence. Adapt each X or LinkedIn
  version to its own platform's supported patterns; do not promise that a past result will repeat.
- When supported by the evidence, deliberately adapt successful patterns rather than merely
  restating analytics. If the evidence is limited, prioritize the saved Strategy and the idea.

Idea Title: {idea_title}
Summary: {idea_summary}
Proposed Angle: {proposed_angle}

Complete relevant saved Strategy profile:
{strategy_context}
{performance_instruction}

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
