from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ContentDraft,
    ContentIdea,
    ContentPillar,
    PlatformPublication,
    PublicationMetricSnapshot,
)

PERFORMANCE_WINDOW_DAYS = 90
MIN_COMPARISON_POSTS = 3
CHECKPOINT_ORDER = ("24h", "7d", "30d", "90d")


def _engagement_rate(impressions: int, interactions: int) -> str:
    if impressions <= 0:
        return "not available (no impressions recorded)"
    return f"{interactions / impressions:.2%}"


def _summary(posts: list[dict]) -> dict[str, int]:
    return {
        "posts": len(posts),
        "impressions": sum(post["impressions"] for post in posts),
        "interactions": sum(post["interactions"] for post in posts),
        "late": sum(post["late"] for post in posts),
    }


def build_performance_context(
    session: Session, as_of: datetime | None = None
) -> str:
    """Build checkpoint-separated, evidence-based performance context."""
    as_of = as_of or datetime.now(UTC).replace(tzinfo=None)
    if as_of.tzinfo is not None:
        as_of = as_of.astimezone(UTC).replace(tzinfo=None)
    cutoff = as_of - timedelta(days=PERFORMANCE_WINDOW_DAYS)
    rows = session.execute(
        select(
            PublicationMetricSnapshot.checkpoint,
            PublicationMetricSnapshot.impressions,
            PublicationMetricSnapshot.reactions,
            PublicationMetricSnapshot.comments,
            PublicationMetricSnapshot.reposts,
            PublicationMetricSnapshot.clicks,
            PublicationMetricSnapshot.is_late,
            PlatformPublication.id.label("publication_id"),
            PlatformPublication.platform,
            PlatformPublication.published_at,
            ContentDraft.variant_type,
            ContentDraft.title,
            ContentDraft.body,
            ContentIdea.title.label("idea_title"),
            ContentPillar.name.label("pillar_name"),
        )
        .join(
            PlatformPublication,
            PublicationMetricSnapshot.publication_id == PlatformPublication.id,
        )
        .join(ContentDraft, PlatformPublication.draft_id == ContentDraft.id)
        .join(ContentIdea, ContentDraft.idea_id == ContentIdea.id)
        .outerjoin(ContentPillar, ContentIdea.pillar_id == ContentPillar.id)
        .where(
            PlatformPublication.published_at >= cutoff,
            PlatformPublication.published_at <= as_of,
            PlatformPublication.status.in_(("published", "manual_confirmed")),
        )
    ).all()

    if not rows:
        return (
            f"No per-checkpoint metrics are available for published posts in the last "
            f"{PERFORMANCE_WINDOW_DAYS} days. Do not infer winning platforms, formats, "
            "or pillars; use the saved Strategy and treat performance as unknown."
        )

    posts = []
    for row in rows:
        posts.append(
            {
                "checkpoint": row.checkpoint,
                "platform": row.platform.lower(),
                "publication_id": row.publication_id,
                "format": row.variant_type or "post",
                "title": row.title or row.idea_title or "Untitled post",
                "body": row.body or "",
                "pillar": row.pillar_name or "Unassigned",
                "impressions": row.impressions,
                "interactions": row.reactions + row.comments + row.reposts + row.clicks,
                "late": int(row.is_late),
            }
        )

    by_platform_format: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    by_platform_pillar: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for post in posts:
        by_platform_format[
            (post["checkpoint"], post["platform"], post["format"])
        ].append(post)
        if post["pillar"] != "Unassigned":
            by_platform_pillar[
                (post["checkpoint"], post["platform"], post["pillar"])
            ].append(post)

    lines = [
        f"Performance evidence covers publications from the last "
        f"{PERFORMANCE_WINDOW_DAYS} days and keeps 24-hour, 7-day, 30-day, and "
        "90-day snapshots separate.",
        "Tracked interactions equal reactions + comments + reposts + clicks. "
        "Interaction rate is total tracked interactions divided by total impressions.",
        f"Only compare groups with at least {MIN_COMPARISON_POSTS} posts at the same "
        "platform and checkpoint. Late-entered values remain visible as evidence but are "
        "excluded from naming a best-supported group. These are observational signals, "
        "not proof of causation or guarantees.",
        "Platform and format results:",
    ]
    platform_order = ("x", "linkedin")
    for checkpoint in CHECKPOINT_ORDER:
        for platform in platform_order:
            groups = []
            for (group_checkpoint, group_platform, variant), group_posts in (
                by_platform_format.items()
            ):
                if group_checkpoint != checkpoint or group_platform != platform:
                    continue
                totals = _summary(group_posts)
                lines.append(
                    f"- {checkpoint}, {platform}, {variant}: {totals['posts']} posts; "
                    f"{totals['impressions']} impressions; "
                    f"{totals['interactions']} tracked interactions; "
                    f"aggregate interaction rate "
                    f"{_engagement_rate(totals['impressions'], totals['interactions'])}; "
                    f"{totals['late']} late-entered."
                )
                if (
                    totals["posts"] >= MIN_COMPARISON_POSTS
                    and totals["late"] == 0
                    and totals["impressions"] > 0
                ):
                    groups.append(
                        (
                            variant,
                            totals,
                            totals["interactions"] / totals["impressions"],
                        )
                    )
            if len(groups) >= 2:
                winner = max(groups, key=lambda group: group[2])
                lines.append(
                    f"- Best-supported {platform} format at {checkpoint}: {winner[0]} "
                    f"({winner[1]['posts']} posts, "
                    f"{_engagement_rate(winner[1]['impressions'], winner[1]['interactions'])}); "
                    "directional signal only."
                )

    lines.append("Content-pillar results (compared only within the same platform and checkpoint):")
    for checkpoint in CHECKPOINT_ORDER:
        for platform in platform_order:
            groups = []
            for (group_checkpoint, group_platform, pillar), group_posts in (
                by_platform_pillar.items()
            ):
                if group_checkpoint != checkpoint or group_platform != platform:
                    continue
                totals = _summary(group_posts)
                lines.append(
                    f"- {checkpoint}, {platform}, pillar {pillar}: "
                    f"{totals['posts']} posts; {totals['impressions']} impressions; "
                    f"{totals['interactions']} tracked interactions; aggregate interaction "
                    f"rate {_engagement_rate(totals['impressions'], totals['interactions'])}; "
                    f"{totals['late']} late-entered."
                )
                if (
                    totals["posts"] >= MIN_COMPARISON_POSTS
                    and totals["late"] == 0
                    and totals["impressions"] > 0
                ):
                    groups.append(
                        (
                            pillar,
                            totals,
                            totals["interactions"] / totals["impressions"],
                        )
                    )
            if len(groups) >= 2:
                winner = max(groups, key=lambda group: group[2])
                lines.append(
                    f"- Best-supported {platform} pillar at {checkpoint}: {winner[0]} "
                    f"({winner[1]['posts']} posts, "
                    f"{_engagement_rate(winner[1]['impressions'], winner[1]['interactions'])}); "
                    "directional signal only."
                )

    exemplars = sorted(
        (post for post in posts if post["checkpoint"] == "7d" and post["impressions"] > 0),
        key=lambda post: post["interactions"] / post["impressions"],
        reverse=True,
    )[:4]
    if exemplars:
        lines.append("Illustrative 7-day post examples, not statistically conclusive:")
        for post in exemplars:
            excerpt = " ".join(post["body"].split())[:160]
            lines.append(
                f"- {post['platform']} / {post['pillar']}: {post['title']}; "
                f"{post['impressions']} impressions, "
                f"{_engagement_rate(post['impressions'], post['interactions'])}; "
                f"{'late-entered; ' if post['late'] else ''}"
                f"excerpt: {excerpt or '[no saved post text]'}"
            )

    return "\n".join(lines)
