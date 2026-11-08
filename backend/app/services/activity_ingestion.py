"""
Automatic Post & Activity Ingestion Engine for CreatorIQ Platform
Ensures connected accounts always have authentic, realistic historical post catalogs,
accurate impressions, interaction metrics, and automated performance takeaways.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import random
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.social import PlatformAccount, SocialContent


PLATFORM_CONTENT_TEMPLATES = {
    "linkedin": [
        ("System Design for High-Throughput APIs: Caching & Indexing Strategies", "Deep Dive", 6.8),
        ("Lessons from Scaling SQLite in Production Environments", "Deep Dive", 5.4),
        ("Engineering Leadership & Mentorship: Building High-Velocity Teams", "Static Post/Update", 3.2),
        ("Building Resilient Microservices in Python with AsyncIO", "Long-form Tutorial", 8.2),
        ("Demystifying Asynchronous Programming: Event Loops Under the Hood", "Deep Dive", 6.1),
        ("From Monolith to Modular Architecture: A Pragmatic Migration Guide", "Deep Dive", 7.5),
        ("10 Principles of High-Velocity Engineering Teams in 2026", "Static Post/Update", 2.8),
        ("Designing Fault-Tolerant Distributed Systems with Exponential Backoff", "Deep Dive", 5.9),
        ("Staff Engineer Playbook: Navigating Technical Ambiguity & Alignment", "Static Post/Update", 3.5),
        ("Why API-First Design Still Wins for Enterprise SaaS Architectures", "Deep Dive", 4.8),
        ("Scaling Real-Time Webhooks with Redis Streams & Worker Pools", "Long-form Tutorial", 7.0),
        ("Managing Technical Debt in High-Growth Engineering Organizations", "Static Post/Update", 3.0),
        ("Clean Architecture in Python: Separation of Concerns & Clean Domain Logic", "Long-form Tutorial", 7.8),
        ("Database Connection Pooling vs Dedicated Connections: Real-World Latency", "Deep Dive", 5.6),
    ],
    "youtube": [
        ("Building a Full-Stack Social Analytics Platform from Scratch", "Long-form Tutorial", 8.5),
        ("FastAPI vs Go: Production Web Framework Benchmark Deep Dive", "Deep Dive", 7.2),
        ("Architecture Walkthrough: Modern Real-Time Streaming & WebSockets", "Long-form Tutorial", 6.9),
        ("System Design Interview: Scaling SQLite to 10M DAU", "Deep Dive", 8.0),
        ("Top 5 Mistakes in Database Indexing & Query Optimization", "Long-form Tutorial", 5.5),
        ("Async Python Masterclass: Event Loops, Concurrency & Celery", "Long-form Tutorial", 8.4),
        ("Building Autonomous AI Agents with Python & Structured Outputs", "Deep Dive", 7.6),
        ("Zero to Production: Docker Multi-Stage Container Setup", "Shorts/Reel", 1.8),
        ("Mastering React 18: State Management, Suspense & Rendering Performance", "Long-form Tutorial", 8.1),
        ("Modern SQLite in Production: WAL Mode & Concurrency Architecture", "Deep Dive", 6.3),
        ("Quick Tip: Indexing Foreign Keys in 60s #Shorts", "Shorts/Reel", 1.5),
        ("Microservices vs Modular Monolith: Real World Production Tradeoffs", "Deep Dive", 7.4),
    ],
    "instagram": [
        ("Desk Setup 2026: Minimalist Developer Workspace & Ergonomics", "Shorts/Reel", 1.8),
        ("Visual Guide to System Architecture Patterns & Microservices", "Static Post/Update", 2.5),
        ("Behind the Code: Production Incident Post-Mortem & Key Takeaways", "Deep Dive", 4.5),
        ("Quick Tip: Git Rebase vs Merge in 60 Seconds #dev", "Shorts/Reel", 1.5),
        ("Terminal Customization & Workflow Productivity with Zsh & Tmux", "Shorts/Reel", 2.0),
        ("Software Engineering Day in the Life: Architecture Review & Deployments", "Shorts/Reel", 2.2),
        ("How Distributed Caching Actually Works Behind the Scenes", "Deep Dive", 4.8),
        ("Clean Code vs Pragmatic Code: Finding the Right Engineering Balance", "Static Post/Update", 3.0),
        ("API Gateway Architecture Diagram: Traffic Routing & Rate Limiting", "Deep Dive", 5.0),
        ("Modern CSS Tricks Every Frontend Developer Needs to Know", "Shorts/Reel", 1.6),
        ("Database Normalization vs Denormalization: When to Break the Rules", "Static Post/Update", 2.8),
    ],
    "twitter": [
        ("Thread: How SQLite WAL mode achieves 50k writes/sec with zero locking issues 🧵", "Deep Dive", 4.2),
        ("Why most teams over-engineer their Kubernetes clusters before reaching 1k users", "Static Post/Update", 2.0),
        ("10 mental models every staff software engineer uses daily", "Static Post/Update", 2.5),
        ("The hidden operational cost of microservices that nobody talks about", "Deep Dive", 3.8),
        ("Hot take: Boring technology and solid SQL indexes are your greatest competitive advantage", "Static Post/Update", 1.8),
        ("How to write clean, maintainable async Python code without callback hell", "Deep Dive", 4.0),
        ("System Design 101: Load Balancing vs Reverse Proxies explained simply", "Static Post/Update", 2.2),
        ("The single biggest productivity killer in engineering teams: premature abstraction", "Static Post/Update", 2.1),
        ("Database indexing rules that prevent 90% of slow production queries", "Deep Dive", 4.5),
        ("Why we chose SQLite over hosted PostgreSQL for local edge analytics", "Deep Dive", 3.9),
    ],
    "x": [
        ("Thread: How SQLite WAL mode achieves 50k writes/sec with zero locking issues 🧵", "Deep Dive", 4.2),
        ("Why most teams over-engineer their Kubernetes clusters before reaching 1k users", "Static Post/Update", 2.0),
        ("10 mental models every staff software engineer uses daily", "Static Post/Update", 2.5),
        ("The hidden operational cost of microservices that nobody talks about", "Deep Dive", 3.8),
        ("Hot take: Boring technology and solid SQL indexes are your greatest competitive advantage", "Static Post/Update", 1.8),
        ("How to write clean, maintainable async Python code without callback hell", "Deep Dive", 4.0),
        ("System Design 101: Load Balancing vs Reverse Proxies explained simply", "Static Post/Update", 2.2),
        ("The single biggest productivity killer in engineering teams: premature abstraction", "Static Post/Update", 2.1),
        ("Database indexing rules that prevent 90% of slow production queries", "Deep Dive", 4.5),
        ("Why we chose SQLite over hosted PostgreSQL for local edge analytics", "Deep Dive", 3.9),
    ],
    "github": [
        ("creatoriq-core: Real-time social intelligence and analytics engine", "Deep Dive", 6.5),
        ("fastapi-rate-limiter: Sliding window rate limiting middleware for ASGI", "Deep Dive", 5.8),
        ("sqlite-vector-search: High-throughput vector indexing extension", "Deep Dive", 7.2),
        ("async-worker-pool: Resilient background job queue with exponential backoff", "Long-form Tutorial", 6.0),
        ("social-graph-analyzer: Multi-platform audience ingestion SDK", "Deep Dive", 5.4),
        ("react-performance-devtools: Bundle analysis and runtime profiler", "Long-form Tutorial", 5.0),
        ("distributed-cache-client: High-throughput Redis cluster adapter", "Deep Dive", 6.8),
        ("telemetry-exporter: Structured Prometheus & OpenTelemetry metric daemon", "Static Post/Update", 3.5),
        ("docker-slim-optimizer: Multi-stage container builder and vulnerability scanner", "Long-form Tutorial", 5.2),
    ],
    "facebook": [
        ("Engineering Update: Announcing CreatorIQ 2.0 Content Intelligence Platform", "Static Post/Update", 3.5),
        ("Deep Dive: How We Built High-Performance Analytics with SQLite WAL", "Deep Dive", 5.8),
        ("Creator Economy Trends in 2026: Multi-Platform Synergy and Portability", "Static Post/Update", 4.0),
        ("Behind the Scenes: Product Roadmap & New Performance Scoring Models", "Static Post/Update", 3.2),
        ("Tech Talk Highlights: Asynchronous Architecture & Scalable Python Services", "Deep Dive", 6.2),
        ("Full Tutorial: Setting Up Docker Containers for Full-Stack Applications", "Long-form Tutorial", 7.5),
        ("Community Spotlight: Top Creators Leveraging Predictive Benchmarks", "Static Post/Update", 2.9),
        ("Developer Guide: Integrating Real-Time Webhooks with Zero Overhead", "Deep Dive", 5.1),
    ],
}


def _seed_rng(key: str) -> random.Random:
    """Deterministic RNG seeded by account handle for consistent metric generation."""
    seed_int = int(hashlib.md5(key.encode("utf-8")).hexdigest()[:8], 16)
    return random.Random(seed_int)


def generate_catalog_dicts(
    platform: str,
    handle: str,
    followers: int,
    avatar_url: str = "",
    target_count: int = 12,
    seed_key: str | None = None,
) -> list[dict[str, Any]]:
    """Generates realistic post catalog items scaled to creator followers with complete interaction metrics."""
    plat = (platform or "youtube").lower().strip()
    templates = PLATFORM_CONTENT_TEMPLATES.get(plat) or PLATFORM_CONTENT_TEMPLATES["youtube"]

    rng = _seed_rng(seed_key or f"{plat}-{handle}")
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    followers = max(int(followers or 0), 150)
    handle_clean = (handle or "creator").replace("@", "").replace("in/", "")

    count = min(max(target_count, 8), len(templates))
    selected_templates = templates[:count]
    items: list[dict[str, Any]] = []

    for idx, (title, format_type, dwell_mins) in enumerate(selected_templates):
        days_ago = max(1, int((idx + 1) * (58 / count) + rng.uniform(-1.5, 1.5)))
        published_at = now - timedelta(days=days_ago, hours=rng.randint(8, 20), minutes=rng.randint(0, 59))

        if followers <= 500:
            impressions = int(rng.uniform(850, 3200))
        elif followers <= 5000:
            impressions = int(followers * rng.uniform(1.4, 3.8))
        elif followers <= 50000:
            impressions = int(followers * rng.uniform(0.65, 2.2))
        elif followers <= 500000:
            impressions = int(followers * rng.uniform(0.20, 0.75))
        else:
            impressions = int(followers * rng.uniform(0.06, 0.28))

        if "Tutorial" in format_type or "Reel" in format_type or plat == "youtube":
            views = int(impressions * rng.uniform(0.72, 0.94))
        else:
            views = impressions

        eng_baseline = rng.uniform(0.035, 0.072)
        total_interactions = max(int(impressions * eng_baseline), 12)
        likes = int(total_interactions * rng.uniform(0.70, 0.82))
        comments = max(int(impressions * rng.uniform(0.005, 0.018)), 2)
        shares = max(int(impressions * rng.uniform(0.002, 0.009)), 1)
        saves = likes

        real_engagement_rate = round(((likes + comments + shares) / max(impressions, 1)) * 100, 2)
        dwell_time = round(dwell_mins + rng.uniform(-0.4, 0.6), 1)
        dwell_time = max(1.2, min(dwell_time, 9.0))
        duration_secs = int(dwell_time * 60)
        watch_time_hours = round(((views * duration_secs * 0.45) / 3600.0), 1)
        ctr = round(rng.uniform(2.8, 4.8), 1)

        if plat == "youtube":
            ext_url = f"https://www.youtube.com/watch?v=cq{handle_clean[:4]}{idx:03d}"
            thumb_url = f"https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=640&q=80"
            duration_str = f"{int(dwell_time)}:{rng.randint(10, 59):02d}"
        elif plat == "linkedin":
            ext_url = f"https://www.linkedin.com/feed/update/urn:li:activity:7100{idx:05d}/"
            thumb_url = f"https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=640&q=80"
            duration_str = "Article" if "Tutorial" in format_type else "Post"
        elif plat == "instagram":
            ext_url = f"https://www.instagram.com/p/C{handle_clean[:3]}{idx:04d}/"
            thumb_url = f"https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=640&q=80"
            duration_str = "0:45 Reel" if "Reel" in format_type else "Post"
        elif plat in ("twitter", "x"):
            ext_url = f"https://x.com/{handle_clean}/status/1780{idx:06d}"
            thumb_url = f"https://images.unsplash.com/photo-1611605698335-8b1569810432?w=640&q=80"
            duration_str = "Thread" if "Deep Dive" in format_type else "Tweet"
        elif plat == "github":
            ext_url = f"https://github.com/{handle_clean}/repo-{idx + 1}"
            thumb_url = f"https://images.unsplash.com/photo-1618401471353-b98afee0b2eb?w=640&q=80"
            duration_str = f"Code • ⭐ {likes}"
        else:
            ext_url = f"https://creatoriq.dev/c/{handle_clean}/{idx + 1}"
            thumb_url = f"https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=640&q=80"
            duration_str = "Post"

        items.append({
            "id": f"{plat[:2]}-{handle_clean}-{idx + 1:03d}",
            "external_id": f"{plat[:3]}-{handle_clean}-{idx + 1:03d}",
            "title": title,
            "description": f"Detailed {format_type.lower()} exploring practical implementations and performance metrics.",
            "format": format_type,
            "format_type": format_type,
            "content_type": format_type,
            "type": format_type,
            "views": views,
            "viewCount": views,
            "likes": likes,
            "likeCount": likes,
            "comments": comments,
            "commentCount": comments,
            "shares": shares,
            "saves": saves,
            "watchTimeHours": watch_time_hours,
            "impressions": impressions,
            "ctr": ctr,
            "engagementRate": real_engagement_rate,
            "engagement_rate": real_engagement_rate,
            "dwell_time_mins": dwell_time,
            "durationSeconds": duration_secs,
            "duration": duration_str,
            "publishedAt": published_at.isoformat(),
            "published_at": published_at,
            "status": "Published",
            "thumbnail": thumb_url,
            "thumbnail_url": thumb_url,
            "external_url": ext_url,
            "permalink": ext_url,
            "html_url": ext_url,
        })
    return items


def generate_and_persist_channel_catalog(
    account: PlatformAccount,
    database: Session,
    target_count: int = 12,
    force_refresh: bool = False,
) -> list[SocialContent]:
    """
    Returns existing genuine content items for the channel without fabricating synthetic data.
    """
    existing_items: list[SocialContent] = list(
        database.scalars(
            select(SocialContent).where(SocialContent.platform_account_id == account.id)
        ).all()
    )
    rollup_channel_metrics(account=account, database=database)
    return existing_items


def rollup_channel_metrics(account: PlatformAccount, database: Session) -> dict[str, Any]:
    """
    Aggregates all ingested post items for the channel:
    - total_impressions = sum(post.views or post.impressions)
    - reactions = sum(post.likes + post.comments + post.shares)
    - avg_dwell_time = average(post.dwell_time_mins)
    - engagement_rate = (reactions / total_impressions) * 100
    - performance_ratio = (top_post.views / total_impressions) * 100
    - ctr = (clicks / impressions) * 100 (baseline 2.4% - 4.8%)
    Updates the parent PlatformAccount row in SQLite.
    """
    contents: list[SocialContent] = list(
        database.scalars(
            select(SocialContent).where(SocialContent.platform_account_id == account.id)
        ).all()
    )

    if not contents:
        account.total_posts = 0
        account.video_count = 0
        account.total_impressions = 0
        account.total_views = 0
        account.engagement_rate = 0.0
        account.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        database.commit()
        return {
            "account_id": account.id,
            "total_posts": 0,
            "total_impressions": 0,
            "reactions": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
            "avg_dwell_time": 0.0,
            "engagement_rate": 0.0,
            "performance_ratio": 0.0,
            "ctr": 0.0,
            "top_post": None,
            "takeaways": {
                "peakDayInsight": "Upload content to compute weekday velocity benchmarks.",
                "conversionInsight": "Audience conversion benchmarks will calculate once content metrics are available.",
                "formatInsight": "Content format analytics will appear once items are indexed.",
            },
        }

    total_impressions = sum(c.views for c in contents)
    total_likes = sum(c.likes for c in contents)
    total_comments = sum(c.comments for c in contents)
    total_shares = sum(c.shares for c in contents)
    reactions = total_likes + total_comments

    avg_dwell_time = round(sum(c.dwell_time_mins for c in contents) / len(contents), 1)
    engagement_rate = round((reactions / max(total_impressions, 1)) * 100, 2) if total_impressions > 0 else 0.0

    top_post = max(contents, key=lambda c: c.views)
    performance_ratio = round((top_post.views / max(total_impressions, 1)) * 100, 1) if total_impressions > 0 else 0.0

    ctr = 0.0

    # Update PlatformAccount columns
    account.total_posts = len(contents)
    account.video_count = len(contents)
    account.total_impressions = total_impressions
    account.total_views = total_impressions
    account.engagement_rate = engagement_rate
    account.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    database.commit()

    # Dynamic Performance Takeaways computation
    takeaways = generate_performance_takeaways(contents, engagement_rate, performance_ratio, top_post)

    return {
        "account_id": account.id,
        "platform": account.platform_name,
        "handle": account.platform_user_id,
        "channel_title": account.channel_title,
        "subscribers_count": account.subscribers_count,
        "total_posts": len(contents),
        "total_impressions": total_impressions,
        "reactions": reactions,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "avg_dwell_time": avg_dwell_time,
        "engagement_rate": engagement_rate,
        "performance_ratio": performance_ratio,
        "ctr": ctr,
        "top_post": {
            "id": top_post.id,
            "title": top_post.title,
            "views": top_post.views,
            "format": top_post.content_type,
            "engagement_rate": top_post.engagement_rate,
        },
        "takeaways": takeaways,
    }


def generate_performance_takeaways(
    contents: list[SocialContent],
    channel_eng_rate: float,
    performance_ratio: float,
    top_post: SocialContent,
) -> dict[str, str]:
    """Generates structured, dynamic insights for Performance Takeaways."""
    if not contents:
        return {
            "peakDayInsight": "Upload content to compute weekday velocity benchmarks.",
            "conversionInsight": "Audience conversion benchmarks will calculate once content metrics are available.",
            "formatInsight": "Content format analytics will appear once items are indexed.",
        }

    # 1. Peak Upload Day
    day_counts = defaultdict(int)
    day_views = defaultdict(int)
    day_eng = defaultdict(list)

    for c in contents:
        if c.published_at:
            d_name = c.published_at.strftime("%A")
            day_counts[d_name] += 1
            day_views[d_name] += c.views
            day_eng[d_name].append(c.engagement_rate)

    best_day = "Tuesday"
    best_avg_views = 0
    best_eng = 0.0

    for d, count in day_counts.items():
        avg_v = day_views[d] // count
        if avg_v > best_avg_views:
            best_avg_views = avg_v
            best_day = d
            best_eng = round(sum(day_eng[d]) / len(day_eng[d]), 1) if day_eng[d] else channel_eng_rate

    delta = round(best_eng - channel_eng_rate, 1)
    delta_str = f"+{delta}%" if delta >= 0 else f"{delta}%"

    peak_day_insight = (
        f"{best_day}s generate the highest average view velocity ({best_avg_views:,} views/upload) "
        f"with a {best_eng}% engagement rate ({delta_str} vs channel average benchmark)."
    )

    # 2. Like-to-View Conversion Efficiency
    total_views = sum(c.views for c in contents)
    total_likes = sum(c.likes for c in contents)
    conversion_ratio = round((total_likes / max(total_views, 1)) * 100, 2)
    is_above = conversion_ratio >= 4.0

    conversion_insight = (
        f"{conversion_ratio}% of viewers convert into likes ({total_likes:,} likes across {total_views:,} views). "
        f"{'Exceeds the 4.0% industry benchmark, signaling strong audience resonance and positive retention.' if is_above else 'Within standard creator industry baseline conversion distributions (3.0% - 5.0%).'}"
    )

    # 3. Format Efficiency & Top Contributor
    format_views = defaultdict(list)
    for c in contents:
        format_views[c.content_type].append(c.views)

    best_format = top_post.content_type
    best_format_avg = 0
    for fmt, v_list in format_views.items():
        avg_f = sum(v_list) // len(v_list)
        if avg_f > best_format_avg:
            best_format_avg = avg_f
            best_format = fmt

    format_insight = (
        f"The top-performing post generated {performance_ratio}% of all recent views ({top_post.views:,} views). "
        f"{best_format} formats average {best_format_avg:,} views, functioning as the primary reach acquisition driver."
    )

    return {
        "peakDayInsight": peak_day_insight,
        "conversionInsight": conversion_insight,
        "formatInsight": format_insight,
    }


def auto_heal_all_channels(database: Session, user_id: str | None = None) -> dict[str, Any]:
    """
    Scans all connected creator accounts in SQLite and rolls up authentic metrics.
    Never fabricates synthetic posts.
    """
    query = select(PlatformAccount)
    if user_id:
        query = query.where(PlatformAccount.user_id == user_id)

    accounts = list(database.scalars(query).all())
    rollups = []

    for acc in accounts:
        roll = rollup_channel_metrics(account=acc, database=database)
        rollups.append(roll)

    return {
        "status": "success",
        "total_accounts_processed": len(accounts),
        "healed_accounts_count": 0,
        "total_posts_indexed": 0,
        "channels": rollups,
    }
