from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ContentDraft,
    ContentIdea,
    ContentPillar,
    PlatformPublication,
    PostMetric,
)

PERFORMANCE_WINDOW_DAYS = 90
MIN_COMPARISON_POSTS = 3
MIN_EXEMPLAR_IMPRESSIONS = 20


def _engagement_rate(impressions: int, interactions: int) -> str:
    if impressions <= 0:
        return "not available (no impressions recorded)"
    return f"{interactions / impressions:.2%}"


def _aggregate(posts: list[dict]) -> dict[str, int]:
    return {
        "posts": len(posts),
        "impressions": sum(post["impressions"] for post in posts),
        "interactions": sum(post["interactions"] for post in posts),
    }


def build_performance_context(
    session: Session, as_of: datetime | None = None
) -> str:
    """Build a bounded, evidence-based summary from saved publication metrics."""
    as_of = as_of or datetime.now(UTC).replace(tzinfo=None)
    cutoff = as_of - timedelta(days=PERFORMANCE_WINDOW_DAYS)
    rows = session.execute(
        select(
            PlatformPublication.platform,
            PlatformPublication.platform_post_id,
            ContentDraft.variant_type,
            ContentDraft.title,
            ContentDraft.body,
            ContentIdea.title.label("idea_title"),
            ContentPillar.name.label("pillar_name"),
            PostMetric.impressions,
            PostMetric.reactions,
            PostMetric.comments,
            PostMetric.reposts,
            PostMetric.clicks,
            PostMetric.imported_at,
        )
        .join(ContentDraft, PlatformPublication.draft_id == ContentDraft.id)
        .join(ContentIdea, ContentDraft.idea_id == ContentIdea.id)
        .outerjoin(ContentPillar, ContentIdea.pillar_id == ContentPillar.id)
        .join(
            PostMetric,
            (PostMetric.platform_post_id == PlatformPublication.platform_post_id)
            & (PostMetric.platform == PlatformPublication.platform),
        )
        .where(
            PlatformPublication.published_at >= cutoff,
            PlatformPublication.published_at <= as_of,
            PlatformPublication.status.in_(("published", "manual_confirmed")),
        )
        .order_by(PostMetric.imported_at.desc(), PostMetric.id.desc())
    ).all()

    # Imports can update the same post more than once. Use its latest saved metric row.
    posts_by_platform_id: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row.platform.lower(), row.platform_post_id)
        if key in posts_by_platform_id:
            continue
        interactions = row.reactions + row.comments + row.reposts + row.clicks
        posts_by_platform_id[key] = {
            "platform": row.platform.lower(),
            "platform_post_id": row.platform_post_id,
            "variant_type": row.variant_type or "post",
            "title": row.title or row.idea_title or "Untitled post",
            "body": row.body or "",
            "pillar": row.pillar_name or "Unassigned",
            "impressions": row.impressions,
            "interactions": interactions,
        }

    posts = list(posts_by_platform_id.values())
    if not posts:
        return (
            f"No linked performance metrics are available for publications in the last "
            f"{PERFORMANCE_WINDOW_DAYS} days. Do not infer winning platforms, formats, "
            "or pillars; use the saved Strategy and treat performance as unknown."
        )

    lines = [
        f"Observed performance window: last {PERFORMANCE_WINDOW_DAYS} days, ending "
        f"{as_of.date().isoformat()}.",
        f"Evidence includes {len(posts)} published platform posts with linked metric records. "
        "Tracked interactions equal reactions + comments + reposts + clicks. "
        "Interaction rate is total tracked interactions divided by total impressions.",
        "These are observational results, not proof that a format or pillar caused performance. "
        f"Only call a group a meaningful comparison when it has at least "
        f"{MIN_COMPARISON_POSTS} posts; treat smaller groups as early signals.",
    ]

    by_platform: dict[str, list[dict]] = defaultdict(list)
    by_format: dict[tuple[str, str], list[dict]] = defaultdict(list)
    by_pillar: dict[str, list[dict]] = defaultdict(list)
    for post in posts:
        by_platform[post["platform"]].append(post)
        by_format[(post["platform"], post["variant_type"])].append(post)
        by_pillar[post["pillar"]].append(post)

    lines.append("Platform results:")
    for platform, platform_posts in sorted(by_platform.items()):
        totals = _aggregate(platform_posts)
        platform_name = "X" if platform == "x" else platform.capitalize()
        lines.append(
            f"- {platform_name}: {totals['posts']} posts; "
            f"{totals['impressions']} impressions; "
            f"{totals['interactions']} tracked interactions; aggregate interaction rate "
            f"{_engagement_rate(totals['impressions'], totals['interactions'])}."
        )

    lines.append("Platform and post-format comparisons:")
    reliable_formats = []
    for (platform, variant), format_posts in sorted(by_format.items()):
        totals = _aggregate(format_posts)
        platform_name = "X" if platform == "x" else platform.capitalize()
        rate = _engagement_rate(totals["impressions"], totals["interactions"])
        lines.append(
            f"- {platform_name} / {variant}: {totals['posts']} posts; "
            f"{totals['impressions']} impressions; {totals['interactions']} tracked "
            f"interactions; aggregate interaction rate {rate}."
        )
        if totals["posts"] >= MIN_COMPARISON_POSTS and totals["impressions"] > 0:
            reliable_formats.append(
                (
                    platform,
                    variant,
                    totals,
                    totals["interactions"] / totals["impressions"],
                )
            )
    if reliable_formats:
        by_platform_reliable: dict[str, list[tuple]] = defaultdict(list)
        for result in reliable_formats:
            by_platform_reliable[result[0]].append(result)
        for platform, platform_groups in sorted(by_platform_reliable.items()):
            if len(platform_groups) < 2:
                continue
            winner = max(platform_groups, key=lambda result: result[3])
            platform_name = "X" if platform == "x" else platform.capitalize()
            lines.append(
                f"- Best-supported {platform_name} format in this sample: {winner[1]} "
                f"({winner[2]['posts']} posts, "
                f"{_engagement_rate(winner[2]['impressions'], winner[2]['interactions'])}); "
                "use as a directional signal, not a guarantee."
            )

    lines.append("Content-pillar results:")
    reliable_pillars = []
    for pillar, pillar_posts in sorted(by_pillar.items()):
        totals = _aggregate(pillar_posts)
        rate = _engagement_rate(totals["impressions"], totals["interactions"])
        lines.append(
            f"- {pillar}: {totals['posts']} posts; {totals['impressions']} impressions; "
            f"{totals['interactions']} tracked interactions; aggregate interaction rate {rate}."
        )
        if (
            pillar != "Unassigned"
            and totals["posts"] >= MIN_COMPARISON_POSTS
            and totals["impressions"] > 0
        ):
            reliable_pillars.append(
                (pillar, totals, totals["interactions"] / totals["impressions"])
            )
    if len(reliable_pillars) >= 2:
        winner = max(reliable_pillars, key=lambda result: result[2])
        lines.append(
            f"- Best-supported pillar in this sample: {winner[0]} "
            f"({winner[1]['posts']} posts, "
            f"{_engagement_rate(winner[1]['impressions'], winner[1]['interactions'])}); "
            "use as a directional signal, not a guarantee."
        )

    exemplars = sorted(
        (
            post
            for post in posts
            if post["impressions"] >= MIN_EXEMPLAR_IMPRESSIONS
        ),
        key=lambda post: post["interactions"] / post["impressions"],
        reverse=True,
    )[:3]
    if exemplars:
        lines.append(
            "Illustrative recent posts with the highest observed interaction rates "
            "(not statistically conclusive; use only as style/topic examples):"
        )
        for post in exemplars:
            excerpt = " ".join(post["body"].split())[:180]
            platform_name = "X" if post["platform"] == "x" else post["platform"].capitalize()
            lines.append(
                f"- {platform_name} / {post['variant_type']} / {post['pillar']}: "
                f"{post['title']}; {post['impressions']} impressions, "
                f"{_engagement_rate(post['impressions'], post['interactions'])}; "
                f"excerpt: {excerpt or '[no saved post text]'}"
            )

    return "\n".join(lines)
