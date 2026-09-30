from dataclasses import dataclass, field
from app.schemas import StrategyData


@dataclass
class QualityCheckResult:
    score: float
    warnings: list[str] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)


def evaluate_draft_quality(
    body: str,
    platform: str,
    variant_type: str = "post",
    strategy: StrategyData | None = None,
) -> QualityCheckResult:
    warnings: list[str] = []
    score = 1.0

    platform_lower = platform.lower()
    body_len = len(body.strip())

    # 1. Platform length checks
    if platform_lower in {"x", "twitter"} and variant_type == "post":
        if body_len > 280:
            warnings.append(f"Post length ({body_len} chars) exceeds X 280-character limit.")
            score -= 0.3
    elif platform_lower == "linkedin":
        if body_len < 50:
            warnings.append("LinkedIn post is very short. Consider providing more detail or context.")
            score -= 0.1
        elif body_len > 3000:
            warnings.append(f"LinkedIn post length ({body_len} chars) exceeds recommended limit.")
            score -= 0.2

    if not body.strip():
        warnings.append("Draft body is empty.")
        score = 0.0
        return QualityCheckResult(score=max(0.0, score), warnings=warnings)

    # 2. Strategy compliance checks
    if strategy:
        # Avoided vocabulary check
        if strategy.voice and strategy.voice.avoided_vocabulary:
            for word in strategy.voice.avoided_vocabulary:
                if word and word.lower() in body.lower():
                    warnings.append(f"Draft contains avoided vocabulary: '{word}'.")
                    score -= 0.15

        # Sensitive topics check
        if strategy.brand and strategy.brand.sensitive_topics:
            for topic in strategy.brand.sensitive_topics:
                if topic and topic.lower() in body.lower():
                    warnings.append(f"Draft mentions sensitive topic: '{topic}'.")
                    score -= 0.2

    # Hashtag density check
    hashtag_count = body.count("#")
    if hashtag_count > 5:
        warnings.append(f"Excessive hashtags ({hashtag_count}). Limit to 2-3 relevant hashtags.")
        score -= 0.1

    final_score = round(max(0.0, min(1.0, score)), 2)
    return QualityCheckResult(score=final_score, warnings=warnings)
